"""Acceptance assertion for workload-created managed and escaped processes."""
import json
import os
import signal
import sys
import unittest
from pathlib import Path


EXPECTED_WORKERS = ["stderr-reader", "stdin-writer", "stdout-reader"]


def _assert_sigkill(child):
    status = child["wait_status"]
    assert type(status) is int
    assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL


def assert_workload_topology(receipt):
    topology = receipt.get("workload_topology")
    assert isinstance(topology, dict), (
        "cancellation receipt lacks workload-spawned topology; an external custodian holder "
        "does not prove workload child/grandchild ownership"
    )
    leader = topology["leader"]
    managed = topology["managed_child"]
    escaped = topology["escaped_grandchild"]
    children = receipt["children"]

    assert managed["ppid"] == leader["pid"]
    assert escaped["ppid"] == managed["pid"]
    assert managed["pgid"] == leader["pgid"]
    assert escaped["pgid"] != leader["pgid"]
    assert escaped["sid"] == leader["sid"]
    escaped_pre = topology["escaped_grandchild_pre_escape"]
    assert escaped_pre["pid"] == escaped["pid"]
    assert escaped_pre["start_identity"] == escaped["start_identity"]
    assert escaped_pre["pgid"] == leader["pgid"]
    assert escaped_pre["sid"] == leader["sid"]
    for name, node in (("leader", leader), ("anchor", managed), ("holder", escaped)):
        child = children[name]
        assert child["pid"] == node["pid"]
        assert child["start_identity"] == node["start_identity"]
        assert type(node["start_identity"]) is list and len(node["start_identity"]) == 2

    assert topology["pre_escape_group_shared"] is True
    assert topology["custodian_subreaper"] == receipt["custodian"]["pid"]
    assert topology["adoption_before_cancel"] == {
        "managed_child_ppid": receipt["custodian"]["pid"],
        "grandchild_ppid": managed["pid"],
        "custodian_pid": receipt["custodian"]["pid"],
        "grandchild_live": True,
    }
    snapshot = topology["pre_cancel_workers"]
    assert snapshot == {
        "workers_started": 3,
        "active_workers": EXPECTED_WORKERS,
        "pending_workers": EXPECTED_WORKERS,
    }
    assert topology["pre_cancel_live"] == {
        "managed_child": True, "escaped_grandchild": True, "sentinel": True
    }
    assert topology["grandchild_live_after_worker_joins"] is True
    native_io = receipt["native_io"]
    assert native_io["case"] == "topology-cancel"
    assert type(native_io["workers_started"]) is int and native_io["workers_started"] == 3
    assert type(native_io["workers_joined"]) is int and native_io["workers_joined"] == 3
    assert type(native_io["wake_to_join_ms"]) is int
    assert 0 <= native_io["wake_to_join_ms"] <= 1000
    assert topology["managed_group_signal"] == "SIGKILL"
    assert topology["cleanup"]["managed_child_adopted_and_reaped"] == managed["pid"]
    assert topology["cleanup"]["escaped_grandchild_adopted_and_exactly_signaled_and_reaped"] == escaped["pid"]
    _assert_sigkill(children["anchor"])
    _assert_sigkill(children["holder"])
    assert receipt["sentinel_alive_before_cleanup"] is True


class WorkloadTopologyReceiptTests(unittest.TestCase):
    def valid_receipt(self):
        killed = int(signal.SIGKILL)
        leader = {"pid": 101, "ppid": 1, "pgid": 101, "sid": 90,
                  "start_identity": [1700000000, 1010]}
        managed = {"pid": 102, "ppid": 101, "pgid": 101, "sid": 90,
                   "start_identity": [1700000000, 1020]}
        escaped = {"pid": 103, "ppid": 102, "pgid": 103, "sid": 90,
                   "start_identity": [1700000000, 1030]}
        return {
            "custodian": {"pid": 200},
            "native_io": {"case": "topology-cancel", "workers_started": 3,
                          "workers_joined": 3, "wake_to_join_ms": 0},
            "children": {
                "leader": {"pid": 101, "start_identity": leader["start_identity"], "wait_status": 0},
                "anchor": {"pid": 102, "start_identity": managed["start_identity"], "wait_status": killed},
                "holder": {"pid": 103, "start_identity": escaped["start_identity"], "wait_status": killed},
            },
            "sentinel_alive_before_cleanup": True,
            "workload_topology": {
                "leader": leader, "managed_child": managed, "escaped_grandchild": escaped,
                "escaped_grandchild_pre_escape": {**escaped, "pgid": 101},
                "pre_escape_group_shared": True, "custodian_subreaper": 200,
                "adoption_before_cancel": {"managed_child_ppid": 200, "grandchild_ppid": 102,
                    "custodian_pid": 200, "grandchild_live": True},
                "pre_cancel_workers": {"workers_started": 3,
                    "active_workers": EXPECTED_WORKERS, "pending_workers": EXPECTED_WORKERS},
                "pre_cancel_live": {"managed_child": True, "escaped_grandchild": True,
                    "sentinel": True},
                "grandchild_live_after_worker_joins": True,
                "managed_group_signal": "SIGKILL",
                "cleanup": {"managed_child_adopted_and_reaped": 102,
                    "escaped_grandchild_adopted_and_exactly_signaled_and_reaped": 103},
            },
        }

    def test_accepts_exact_workload_lineage_and_reap_evidence(self):
        assert_workload_topology(self.valid_receipt())

    def test_rejects_wrong_session_or_wait_status(self):
        receipt = self.valid_receipt()
        receipt["workload_topology"]["escaped_grandchild"]["sid"] = 103
        with self.assertRaises(AssertionError):
            assert_workload_topology(receipt)
        receipt = self.valid_receipt()
        receipt["children"]["holder"]["wait_status"] = 0
        with self.assertRaises(AssertionError):
            assert_workload_topology(receipt)

    def test_rejects_non_pending_worker_or_mismatched_direct_child(self):
        receipt = self.valid_receipt()
        receipt["workload_topology"]["pre_cancel_workers"]["pending_workers"] = []
        with self.assertRaises(AssertionError):
            assert_workload_topology(receipt)
        receipt = self.valid_receipt()
        receipt["children"]["anchor"]["pid"] = 999
        with self.assertRaises(AssertionError):
            assert_workload_topology(receipt)

    def test_rejects_incomplete_or_late_native_worker_join(self):
        receipt = self.valid_receipt()
        receipt["native_io"]["workers_joined"] = 2
        with self.assertRaises(AssertionError):
            assert_workload_topology(receipt)
        receipt = self.valid_receipt()
        receipt["native_io"]["wake_to_join_ms"] = 1001
        with self.assertRaises(AssertionError):
            assert_workload_topology(receipt)


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ["PROCESS_TOPOLOGY_RECEIPT"])
    assert_workload_topology(json.loads(path.read_text()))
    print("workload topology receipt accepted: " + str(path))


if __name__ == "__main__":
    main()
