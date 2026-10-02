import ast
import ctypes
import importlib.util
import json
import os
import socket
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).with_name("macos-process-overhead.py")
ADAPTER = Path(__file__).with_name("run-macos-process-overhead-scoped.py")
READER = Path(__file__).with_name("darwin-process-reader.py")
CONTROL_CLIENT = Path(__file__).with_name("macos-process-overhead-control.py")
ADAPTER_SPEC = importlib.util.spec_from_file_location("macos_process_custodian", ADAPTER)
custodian = importlib.util.module_from_spec(ADAPTER_SPEC)
ADAPTER_SPEC.loader.exec_module(custodian)
CONTROL_SPEC = importlib.util.spec_from_file_location("macos_process_overhead_control", CONTROL_CLIENT)
control_client = importlib.util.module_from_spec(CONTROL_SPEC)
CONTROL_SPEC.loader.exec_module(control_client)
SPEC = importlib.util.spec_from_file_location("macos_process_overhead", SOURCE)
module = importlib.util.module_from_spec(SPEC)
os.environ.setdefault("AGENT_RUNTIME_DIR", "/tmp/unused-source-test-runtime")
os.environ.setdefault("RHAI_OVERHEAD_LOG_BASE", "/tmp/unused-source-test.log")
SPEC.loader.exec_module(module)
READER_SPEC = importlib.util.spec_from_file_location("darwin_process_reader_source_test", READER)
reader_module = importlib.util.module_from_spec(READER_SPEC)
READER_SPEC.loader.exec_module(reader_module)


class EnvironmentTests(unittest.TestCase):
    def test_cargo_measurement_and_control_commands_are_locked(self):
        self.assertEqual(
            module.measurement_cargo_argv(),
            [str(module.CARGO), 'test', '--locked', '--features',
             'testing-environ,sys', '--test', 'sys_process',
             'process_scope_overhead_measurement', '--', '--exact', '--ignored',
             '--nocapture', '--test-threads=1'])
        self.assertEqual(
            module.cargo_build_argv('test', '--features', 'testing-environ,sys',
                                    '--test', 'sys_process', '--no-run'),
            [str(module.CARGO), 'test', '--locked', '--features',
             'testing-environ,sys', '--test', 'sys_process', '--no-run'])

    def test_stable_cargo_tree_and_metadata_preflight_cover_reviewed_candidate_superset(self):
        source = Path('/private/runtime/source')
        self.assertEqual(module.cargo_source_graph_argv(source), [
            str(module.CARGO), 'tree', '--locked', '--manifest-path',
            str(source / 'Cargo.toml'), '--target', 'aarch64-apple-darwin',
            '--package', 'rhai', '--features', 'testing-environ,sys', '--edges', 'normal,build,dev',
            '--no-dedupe', '--prefix', 'none'])
        self.assertEqual(module.cargo_metadata_graph_argv(source), [
            str(module.CARGO), 'metadata', '--format-version', '1', '--locked',
            '--manifest-path', str(source / 'Cargo.toml'), '--filter-platform',
            'aarch64-apple-darwin', '--features', 'testing-environ,sys'])

        graph = 'rhai v1.26.1\nahash v0.8.12\n'
        metadata = {
            'packages': [
                {'id': 'path+file:///src#rhai@1.26.1', 'name': 'rhai',
                 'version': '1.26.1', 'targets': [{'kind': ['lib'],
                 'crate_types': ['lib']}]},
                {'id': 'registry+https://github.com/rust-lang/crates.io-index#ahash@0.8.12',
                 'name': 'ahash', 'version': '0.8.12', 'targets': [
                     {'kind': ['lib'], 'crate_types': ['lib']},
                     {'kind': ['custom-build'], 'crate_types': ['bin']} ]},
            ],
            'resolve': {'nodes': [
                {'id': 'path+file:///src#rhai@1.26.1'},
                {'id': 'registry+https://github.com/rust-lang/crates.io-index#ahash@0.8.12'},
            ]},
        }
        result = module.validate_cargo_source_graph(graph, json.dumps(metadata))
        self.assertEqual(result['selected_package_count'], 2)
        self.assertEqual(result['selected_build_or_proc_macro_packages'], ['ahash v0.8.12'])

        unreviewed_graph = graph + 'unreviewed-build v9.0.0\n'
        unreviewed = dict(metadata)
        unreviewed['packages'] = metadata['packages'] + [
            {'id': 'registry+https://example.invalid#unreviewed-build@9.0.0',
             'name': 'unreviewed-build', 'version': '9.0.0', 'targets': [
                 {'kind': ['custom-build'], 'crate_types': ['bin']}]},
        ]
        unreviewed['resolve'] = {'nodes': metadata['resolve']['nodes'] + [
            {'id': 'registry+https://example.invalid#unreviewed-build@9.0.0'}]}
        with self.assertRaisesRegex(RuntimeError, 'unreviewed build/proc-macro candidate'):
            module.validate_cargo_source_graph(unreviewed_graph, json.dumps(unreviewed))

        with self.assertRaisesRegex(RuntimeError, 'malformed Cargo tree package row'):
            module.validate_cargo_source_graph(graph + 'not a package row\n', json.dumps(metadata))

        # Cargo documents feature-edge rows separately from package rows;
        # they are intentionally excluded by the requested edge kinds.
        with self.assertRaisesRegex(RuntimeError, 'malformed Cargo tree package row'):
            module.validate_cargo_source_graph(
                'rhai v1.26.1\nlog feature "serde"\n', json.dumps(metadata))

    def test_stable_graph_queries_use_custodian_rpc_and_validate_returned_bytes(self):
        source = Path('/private/runtime/source')
        graph = b'rhai v1.26.1\nahash v0.8.12\n'
        metadata = json.dumps({
            'packages': [
                {'id': 'path+file:///src#rhai@1.26.1', 'name': 'rhai',
                 'version': '1.26.1', 'targets': [{'kind': ['lib'],
                 'crate_types': ['lib']}]},
                {'id': 'registry+https://github.com/rust-lang/crates.io-index#ahash@0.8.12',
                 'name': 'ahash', 'version': '0.8.12', 'targets': [
                     {'kind': ['lib'], 'crate_types': ['lib']},
                     {'kind': ['custom-build'], 'crate_types': ['bin']}]},
            ],
            'resolve': {'nodes': [
                {'id': 'path+file:///src#rhai@1.26.1'},
                {'id': 'registry+https://github.com/rust-lang/crates.io-index#ahash@0.8.12'},
            ]},
        }).encode()
        calls = []

        def rpc(argv, cwd, env, stdout, deadline, **kwargs):
            calls.append((argv, cwd, env, stdout, deadline, kwargs))
            return 0, (graph if len(calls) == 1 else metadata)

        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            with patch.object(module, 'RUNTIME', runtime), \
                    patch.object(module, 'run_anchored_command', side_effect=rpc), \
                    patch.object(module.time, 'monotonic', return_value=100), \
                    patch('builtins.print'):
                result = module.run_source_graph_preflight(source, {'PATH': '/bin'}, 200)

        self.assertEqual(len(calls), 2)
        self.assertEqual([call[0] for call in calls], [
            module.cargo_source_graph_argv(source),
            module.cargo_metadata_graph_argv(source)])
        for call in calls:
            self.assertEqual(call[1:3], (source, {'PATH': '/bin'}))
            self.assertTrue(call[5]['monitor_resources'])
            self.assertFalse(call[5]['include_stderr'])
            self.assertEqual(call[5]['stderr_path'].parent, runtime)
        self.assertEqual(result['selected_build_or_proc_macro_packages'], ['ahash v0.8.12'])
        self.assertEqual(result['cargo_tree_sha256'], __import__('hashlib').sha256(graph).hexdigest())
        self.assertEqual(result['cargo_metadata_sha256'], __import__('hashlib').sha256(metadata).hexdigest())

    def test_stable_graph_preflight_runs_after_private_lock_and_before_any_build(self):
        source = SOURCE.read_text(encoding='utf-8')
        main_body = source[source.index('def main():'):source.index("if __name__ == '__main__':")]
        self.assertIn('run_source_graph_preflight(source, env, package_deadline)', main_body)
        self.assertLess(main_body.index("print(f'accepted_lock_sha256="),
                        main_body.index('run_source_graph_preflight(source, env, package_deadline)'))
        self.assertLess(main_body.index('run_source_graph_preflight(source, env, package_deadline)'),
                        main_body.index("run_control_only(control_case, env, package_deadline, source)"))
        self.assertLess(main_body.index('run_source_graph_preflight(source, env, package_deadline)'),
                        main_body.index("print('phase=process_scope_overhead_measurement'"))

    def test_harness_paths_follow_own_worktree_not_removed_checkout(self):
        expected_repo = SOURCE.resolve().parents[2]
        expected_evidence = expected_repo / ".scratch/all-tickets/macos-process-overhead-evidence"
        self.assertEqual(module.REPO, expected_repo)
        self.assertTrue(module.REPO.is_dir())
        self.assertEqual(module.EVIDENCE, expected_evidence)
        self.assertEqual(custodian.REPO, expected_repo)
        for path in (SOURCE, ADAPTER, Path(__file__).with_name("run-macos-process-overhead.sh")):
            self.assertNotIn("/Users/hoppworks/projects/rhai-all-tickets",
                             path.read_text(encoding="utf-8"))

    def test_managed_readiness_requires_exact_identity_four_tasks_and_live_stream_proof(self):
        identity = {"pid": 101, "start_seconds": 7, "start_microseconds": 123}
        self.assertTrue(custodian.validate_managed_task_sample(
            {**identity, "thread_count": 4}, identity))
        for sample in (
                {**identity, "thread_count": 3},
                {**identity, "thread_count": 5},
                {**identity, "start_microseconds": 124, "thread_count": 4},
                {**identity, "thread_count": True},
                {**identity, "thread_count": 4, "foreign": True}):
            with self.subTest(sample=sample), self.assertRaisesRegex(ValueError, "Managed task sample"):
                custodian.validate_managed_task_sample(sample, identity)

        progress = {"schema": 1, "stage": "capturing",
                    "host": {"pid": 90, "start_seconds": 8, "start_microseconds": 90},
                    "fixture": identity, "stdout_bytes_read": 17, "stderr_bytes_read": 19}
        self.assertTrue(custodian.validate_managed_capture_progress(
            progress, progress["host"], identity))
        for bad in (
                {**progress, "stdout_bytes_read": 0},
                {**progress, "stderr_bytes_read": 0},
                {**progress, "host": {**progress["host"], "start_microseconds": 91}},
                {**progress, "fixture": {**identity, "start_microseconds": 124}},
                {**progress, "stage": "starting"},
                {**progress, "extra": True}):
            with self.subTest(progress=bad), self.assertRaisesRegex(ValueError, "capture progress"):
                custodian.validate_managed_capture_progress(bad, progress["host"], identity)

        evidence = {"managed_host_live": True, "fixture_live": True,
                    "fixture_topology_live": True, "fixture_thread_count": 4,
                    "stdout_bytes_read": 17, "stderr_bytes_read": 19}
        self.assertEqual(custodian.validate_case_evidence("managed", evidence), evidence)
        for key in ("managed_host_live", "fixture_live", "fixture_topology_live"):
            bad = dict(evidence, **{key: False})
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "evidence"):
                custodian.validate_case_evidence("managed", bad)
        for key, value in (("fixture_thread_count", 5), ("stdout_bytes_read", 0),
                           ("stderr_bytes_read", 0), ("stderr_bytes_read", True)):
            bad = dict(evidence, **{key: value})
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, "evidence"):
                custodian.validate_case_evidence("managed", bad)

    def test_managed_ready_event_requires_host_fixture_and_exact_task_count(self):
        identities = {slot: {"pid": pid, "start_seconds": 8,
            "start_microseconds": pid} for slot, pid in
            (("client", 90), ("gate", 91), ("anchor", 92),
             ("managed_host", 93), ("fixture", 94))}
        evidence = {"managed_host_live": True, "fixture_live": True,
                    "fixture_topology_live": True, "fixture_thread_count": 4,
                    "stdout_bytes_read": 17, "stderr_bytes_read": 19}
        event = custodian.make_case_ready_event("managed", "managed-1", identities, evidence)
        self.assertEqual(set(event["identities"]), set(identities))
        bad = dict(identities)
        bad.pop("fixture")
        with self.assertRaisesRegex(ValueError, "identities"):
            custodian.make_case_ready_event("managed", "managed-2", bad, evidence)

    def test_managed_native_snapshot_requires_progress_for_both_real_capture_streams(self):
        runtime = Path("/private/owned-runtime")
        host_path = str(runtime / "target/debug/examples/macos-managed-capture-companion")
        fixture_path = str(runtime / "target/debug/deps/sys_process-frozen")
        rows = [
            {"pid": 90, "ppid": 1, "pgid": 90, "path": __import__("sys").executable,
             "start_seconds": 1, "start_microseconds": 90},
            {"pid": 91, "ppid": 90, "pgid": 91, "path": host_path,
             "start_seconds": 2, "start_microseconds": 91},
            {"pid": 92, "ppid": 91, "pgid": 91, "path": "/usr/bin/python3",
             "start_seconds": 2, "start_microseconds": 92},
            {"pid": 93, "ppid": 91, "pgid": 93, "path": fixture_path,
             "start_seconds": 3, "start_microseconds": 93, "thread_count": 4},
        ]

        class Census:
            @staticmethod
            def descendants(by_pid, root):
                selected = []
                pending = [root]
                while pending:
                    parent = pending.pop()
                    children = [row for row in by_pid.values() if row["ppid"] == parent]
                    selected.extend(children)
                    pending.extend(row["pid"] for row in children)
                return selected

        host = {"pid": 91, "start_seconds": 2, "start_microseconds": 91}
        fixture = {"pid": 93, "start_seconds": 3, "start_microseconds": 93}
        progress = {"schema": 1, "stage": "capturing", "host": host,
            "fixture": fixture, "stdout_bytes_read": 17, "stderr_bytes_read": 19}
        snapshot = custodian.validate_managed_snapshot(rows, 91, 92, 91, 93,
            host_path, fixture_path, progress, Census(), 90)
        self.assertEqual(snapshot["evidence"]["stdout_bytes_read"], 17)
        self.assertEqual(snapshot["evidence"]["stderr_bytes_read"], 19)
        for changed, capture in (
                (rows[:-1], progress),
                ([*rows[:3], {**rows[3], "thread_count": 5}], progress),
                ([*rows[:3], {**rows[3], "pgid": 91}], progress),
                (rows, {**progress, "stderr_bytes_read": 0}),
                (rows, {**progress, "fixture": {**fixture, "start_microseconds": 94}})):
            with self.subTest(changed=changed, capture=capture), self.assertRaises(ValueError):
                custodian.validate_managed_snapshot(changed, 91, 92, 91, 93,
                    host_path, fixture_path, capture, Census(), 90)

    def test_managed_host_signal_defers_gate_reap_until_anchored_group_signal(self):
        class Child:
            pid = 101
            returncode = None

            def __init__(self, name, events):
                self.name = name
                self.events = events

            def poll(self):
                self.events.append((self.name, "poll"))
                raise AssertionError("gate must not be polled before group signal")

            def wait(self, timeout):
                self.events.append((self.name, "wait"))
                return -custodian.signal.SIGKILL

            def kill(self):
                self.events.append((self.name, "popen-kill"))
                raise AssertionError("Popen.kill may poll and reap the gate")

        events = []
        gate = Child("gate", events)
        anchor = Child("anchor", events)
        event = {"event": "case-ready", "case": "managed", "event_id": "m-1",
            "identities": {slot: {"pid": pid, "start_seconds": 1,
                "start_microseconds": pid} for slot, pid in
                (("managed_host", gate.pid), ("client", 90), ("gate", gate.pid),
                 ("anchor", anchor.pid), ("fixture", 102))},
            "evidence": {"managed_host_live": True, "fixture_live": True,
                "fixture_topology_live": True, "fixture_thread_count": 4,
                "stdout_bytes_read": 1, "stderr_bytes_read": 1}}
        request = {"op": "interrupt", "case": "managed", "event_id": "m-1",
            "target": "managed_host", "signal": "KILL"}
        controller, peer = socket.socketpair()
        peer.sendall(__import__("json").dumps(request).encode() + b"\n")
        deadline = __import__("time").monotonic() + 2
        signal_state = {"issued": False}

        class Custody:
            @staticmethod
            def waitid_nonreap(_pid):
                return None

        def record_direct(pid, signum):
            events.append(("direct-signal", pid, signum))

        def record_group(pgid, signum):
            events.append(("group-signal", pgid, signum))

        try:
            with patch.object(custodian.os, "kill", side_effect=record_direct), \
                 patch.object(custodian.os, "killpg", side_effect=record_group), \
                 patch.object(custodian.os, "getpgid", return_value=gate.pid), \
                 patch.object(custodian, "waitid_nonreap", return_value=None):
                action = custodian.service_controller(controller, "managed", event,
                    False, None, gate, deadline)
                self.assertEqual(action["action"], "managed-host-interrupted")
                self.assertIsNone(action["status"])
                self.assertFalse(__import__("select").select([peer], [], [], 0)[0],
                    "controller must wait for anchored cleanup before reap confirmation")
                statuses = custodian.stop_anchored(Custody(), gate, anchor, gate.pid,
                    deadline, signal_state)
            self.assertEqual(statuses, [-custodian.signal.SIGKILL] * 2)
            self.assertEqual(events, [
                ("direct-signal", gate.pid, custodian.signal.SIGKILL),
                ("group-signal", gate.pid, custodian.signal.SIGKILL),
                ("gate", "wait"), ("anchor", "wait")])
        finally:
            controller.close()
            peer.close()

    def test_managed_observer_stays_unready_without_real_capture_progress_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory).resolve()
            host = runtime / "target/debug/examples/macos-managed-capture-companion"
            fixture = runtime / "target/debug/deps/sys_process-frozen"
            fixture.parent.mkdir(parents=True)
            fixture.touch()
            (runtime / "managed-host-ready.json").write_text(
                '{"schema":1,"host_pid":91,"stage":"managed-run-entering"}\n')
            (runtime / "managed-fixture.record").write_text(
                "child-pid=93 child-ready=1\n")
            argv = [str(host), str(fixture), str(runtime / "managed-host-ready.json"),
                str(runtime / "managed-fixture.record"), str(runtime / "managed-host-complete"),
                str(runtime / "managed-capture-progress.json")]

            class Gate:
                pid = 91

            class Anchor:
                pid = 92

            class NoCensus:
                class Reader:
                    def complete_listing(self, _deadline):
                        raise AssertionError("missing capture progress must stop before census/readiness")
                _adapter_process_reader = Reader()

            self.assertIsNone(custodian.observe_managed_case_ready(
                NoCensus(), argv, Gate(), Anchor(), None, custodian.time.monotonic() + 1, runtime))

    def test_managed_command_vector_is_exact_and_runtime_private(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory).resolve()
            host = runtime / "target/debug/examples/macos-managed-capture-companion"
            fixture = runtime / "target/debug/deps/sys_process-frozen"
            fixture.parent.mkdir(parents=True)
            fixture.touch()
            argv = [str(host), str(fixture), str(runtime / "managed-host-ready.json"),
                str(runtime / "managed-fixture.record"), str(runtime / "managed-host-complete"),
                str(runtime / "managed-capture-progress.json")]
            self.assertEqual(custodian.validate_managed_command_argv(argv, runtime), (host, fixture))
            for bad in (argv[:-1], [*argv[:1], str(Path("/tmp/foreign-fixture")), *argv[2:]],
                        [*argv[:2], str(runtime / "foreign-ready.json"), *argv[3:]]):
                with self.subTest(argv=bad), self.assertRaises((ValueError, OSError)):
                    custodian.validate_managed_command_argv(bad, runtime)

    def test_managed_fixture_artifact_path_parser_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            executable_path = runtime / "target/debug/deps/sys_process-abc"
            executable_path.parent.mkdir(parents=True)
            executable_path.write_bytes(b"source-only synthetic artifact")
            valid = (f'{{"reason":"compiler-artifact","target":{{"kind":["test"],'
                     f'"name":"sys_process"}},"executable":"{executable_path}"}}\n').encode()
            executable = module.parse_managed_fixture_executable(valid, runtime)
            self.assertEqual(executable, executable_path.resolve())
            for output in (
                    valid.replace(str(runtime).encode(), b"/tmp/foreign"),
                    valid + valid,
                    b'{"reason":"compiler-artifact","target":{"kind":["bin"],"name":"other"},"executable":"/private/owned-runtime/other"}\n',
                    b'{"reason":"compiler-artifact","target":{"kind":["test"],"name":"sys_process"},"executable":null}\n'):
                with self.subTest(output=output), self.assertRaises((ValueError, RuntimeError, OSError)):
                    module.parse_managed_fixture_executable(output, runtime)

    def test_managed_cargo_parser_receives_only_json_stdout_and_keeps_stderr(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory).resolve()
            executable_path = runtime / "target/debug/deps/sys_process-cargo"
            executable_path.parent.mkdir(parents=True)
            executable_path.write_bytes(b"synthetic test artifact")
            stdout = runtime / "cargo.stdout"
            stderr = runtime / "cargo.stderr"
            record = (f'{{"reason":"compiler-artifact","target":{{"kind":["test"],'
                      f'"name":"sys_process"}},"executable":"{executable_path}"}}\n')
            progress = b"   Compiling rhai v0.1.0\n    Finished test profile [unoptimized]\n"
            stdout.write_text(record, encoding="utf-8")
            stderr.write_bytes(progress)
            parser_input, retained_stderr = module.read_command_output(
                stdout, stderr, include_stderr=False)
            self.assertEqual(retained_stderr, progress)
            self.assertEqual(module.parse_managed_fixture_executable(parser_input, runtime),
                             executable_path)

    def test_managed_build_requests_keep_cargo_streams_separate(self):
        source = SOURCE.read_text(encoding="utf-8")
        control = source[source.index("def run_control_only("):source.index("def _parse_cargo_executable(")]
        self.assertEqual(control.count("include_stderr=False"), 2)
        self.assertGreaterEqual(control.count("stderr_path="), 2)

    def test_controller_client_uses_one_case_and_waits_for_owned_readiness(self):
        self.assertTrue(CONTROL_CLIENT.is_file())
        source = CONTROL_CLIENT.read_text(encoding="utf-8")
        self.assertIn("def run_control_protocol(", source)
        self.assertNotIn("subprocess.", source)

        server, client = socket.socketpair()
        deadline = __import__("time").monotonic() + 2
        errors = []

        def fake_adapter():
            try:
                self.assertEqual(custodian.read_line(server, deadline),
                                 {"op": "select", "case": "setup"})
                server.sendall(b'{"event":"selected","case":"setup"}\n')
                event = {"event": "case-ready", "case": "setup", "event_id": "setup-1",
                    "identities": {slot: {"pid": pid, "start_seconds": 4,
                        "start_microseconds": pid} for slot, pid in
                        (("client", 9), ("gate", 10), ("anchor", 11))},
                    "evidence": {"setup_command_live": True}}
                server.sendall(__import__("json").dumps(event).encode() + b"\n")
                self.assertEqual(custodian.read_line(server, deadline), {
                    "op": "interrupt", "case": "setup", "event_id": "setup-1",
                    "target": "client", "signal": "TERM"})
                server.sendall(b'{"event":"client-reaped","case":"setup",'
                    b'"event_id":"setup-1","status":-15}\n')
            except BaseException as exc:
                errors.append(exc)
            finally:
                server.close()

        thread = threading.Thread(target=fake_adapter)
        thread.start()
        try:
            result = control_client.run_control_protocol(client, "setup", deadline)
            self.assertEqual(result, {"case": "setup", "event_id": "setup-1",
                                      "action": "client-interrupted", "status": -15})
        finally:
            client.close()
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])

    def test_controller_client_rejects_readiness_absence_and_deadline_never_signals(self):
        server, client = socket.socketpair()
        deadline = __import__("time").monotonic() + 2
        def close_before_readiness():
            self.assertEqual(custodian.read_line(server, deadline),
                             {"op": "select", "case": "build"})
            server.sendall(b'{"event":"selected","case":"build"}\n')
            server.close()
        thread = threading.Thread(target=close_before_readiness)
        thread.start()
        try:
            with self.assertRaisesRegex(RuntimeError, "before publishing readiness"):
                control_client.run_control_protocol(client, "build", deadline)
        finally:
            client.close()
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())

        server, client = socket.socketpair()
        errors = []
        def fake_deadline_adapter():
            try:
                self.assertEqual(custodian.read_line(server, deadline),
                                 {"op": "select", "case": "deadline"})
                server.sendall(b'{"event":"selected","case":"deadline"}\n')
                event = {"event": "case-ready", "case": "deadline", "event_id": "deadline-1",
                    "identities": {slot: {"pid": pid, "start_seconds": 5,
                        "start_microseconds": pid} for slot, pid in (("gate", 20), ("anchor", 21))},
                    "evidence": {"command_live": True}}
                server.sendall(__import__("json").dumps(event).encode() + b"\n")
                server.sendall(b'{"event":"deadline-expired","case":"deadline",'
                    b'"event_id":"deadline-1","reason":"work-deadline-expired",'
                    b'"command_status":-9}\n')
                server.close()
            except BaseException as exc:
                errors.append(exc)
            finally:
                server.close()

        thread = threading.Thread(target=fake_deadline_adapter)
        thread.start()
        try:
            result = control_client.run_control_protocol(client, "deadline", deadline)
            self.assertEqual(result["action"], "deadline-stop-observed")
        finally:
            client.close()
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])

        server, client = socket.socketpair()
        def eof_after_deadline_readiness():
            custodian.read_line(server, deadline)
            server.sendall(b'{"event":"selected","case":"deadline"}\n')
            server.sendall(b'{"event":"case-ready","case":"deadline","event_id":"d-eof",'
                b'"identities":{"gate":{"pid":20,"start_seconds":5,"start_microseconds":20},'
                b'"anchor":{"pid":21,"start_seconds":5,"start_microseconds":21}},'
                b'"evidence":{"command_live":true}}\n')
            server.close()
        thread = threading.Thread(target=eof_after_deadline_readiness)
        thread.start()
        try:
            with self.assertRaisesRegex(RuntimeError, "before the actual deadline cleanup"):
                control_client.run_control_protocol(client, "deadline", deadline)
        finally:
            client.close()
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())

    def test_control_finalization_requires_recorded_readiness_action_and_full_readback(self):
        ready = {"event": "case-ready", "case": "setup", "event_id": "s-1",
                 "identities": {"client": {"pid": 9, "start_seconds": 1,
                     "start_microseconds": 2}, "gate": {"pid": 10, "start_seconds": 1,
                     "start_microseconds": 3}, "anchor": {"pid": 11, "start_seconds": 1,
                     "start_microseconds": 4}}, "evidence": {"setup_command_live": True}}
        record = {"setup_complete": True, "group_signal_issued": True,
                  "gate_status": -9, "anchor_status": -9, "cleanup_complete": True,
                  "control_case": "setup", "control_readiness_event": ready,
                  "control_action": {"action": "client-interrupted", "case": "setup",
                      "event_id": "s-1", "status": -15}}
        ledger = {"observed_identity_readback_complete": True}
        absence = {"complete": True, "candidates": []}
        self.assertTrue(custodian.control_finalization_complete(
            "setup", [record], ledger, absence, [], 2, "client-eof", -15, None))
        variants = [
            ({**record, "control_readiness_event": None}, ledger, absence, [], 2,
             "client-eof", -15, None),
            ({**record, "control_action": None}, ledger, absence, [], 2,
             "client-eof", -15, None),
            (record, {"observed_identity_readback_complete": False}, absence, [], 2,
             "client-eof", -15, None),
            (record, ledger, {"complete": False, "candidates": []}, [], 2,
             "client-eof", -15, None),
            (record, ledger, absence, [ready["identities"]["gate"]], 2,
             "client-eof", -15, None),
            (record, ledger, absence, [], 1, "client-eof", -15, None),
        ]
        for args in variants:
            with self.subTest(args=args), self.assertRaisesRegex(ValueError, "control finalization"):
                custodian.control_finalization_complete("setup", [args[0]], *args[1:])

        deadline_record = {"setup_complete": True, "group_signal_issued": True,
            "gate_status": -9, "anchor_status": -9, "cleanup_complete": True,
            "control_case": "deadline", "control_readiness_event": {
                "event": "case-ready", "case": "deadline", "event_id": "d-1",
                "identities": {slot: {"pid": pid, "start_seconds": 2,
                    "start_microseconds": pid} for slot, pid in (("gate", 20), ("anchor", 21))},
                "evidence": {"command_live": True}},
            "control_stop_reason": "work-deadline-expired",
            "control_completion_event": {"event": "deadline-expired", "case": "deadline",
                "event_id": "d-1", "reason": "work-deadline-expired", "command_status": -9}}
        self.assertTrue(custodian.control_finalization_complete(
            "deadline", [deadline_record], ledger, absence, [], 2,
            "deadline-control-stop", None, -9))
        for reason, status, action in ((None, -9, None), ("work-deadline-expired", 0, None),
                                       ("work-deadline-expired", -9, {"action": "interrupt"})):
            bad = dict(deadline_record, control_stop_reason=reason, control_action=action)
            with self.subTest(reason=reason, status=status), self.assertRaisesRegex(
                    ValueError, "control finalization"):
                custodian.control_finalization_complete("deadline", [bad], ledger, absence,
                    [], 2, "deadline-control-stop", None, status)

        wrong_readiness = dict(record, control_readiness_event={**ready, "identities": {}})
        with self.assertRaisesRegex(ValueError, "control finalization"):
            custodian.control_finalization_complete("setup", [wrong_readiness], ledger,
                absence, [], 2, "client-eof", -15, None)
        wrong_signal = dict(record, control_action={**record["control_action"], "status": -2})
        with self.assertRaisesRegex(ValueError, "control finalization"):
            custodian.control_finalization_complete("setup", [wrong_signal], ledger,
                absence, [], 2, "client-eof", -2, None)

    def test_control_case_selection_is_finite_and_required(self):
        for case in custodian.CONTROL_CASES:
            self.assertEqual(custodian.validate_control_case(case), case)
        for case in (None, "", "build,managed", "unknown"):
            with self.subTest(case=case), self.assertRaisesRegex(ValueError, "one finite"):
                custodian.validate_control_case(case)
        self.assertEqual(custodian.validate_control_selection(
            {"op": "select", "case": "setup"}, "setup"), "setup")
        with self.assertRaisesRegex(ValueError, "does not match"):
            custodian.validate_control_selection({"op": "select", "case": "build"}, "setup")

    def test_adapter_keeps_normal_mode_and_accepts_one_optional_control_case(self):
        self.assertEqual(custodian.parse_adapter_arguments(["--timeout", "585"]), (585.0, None))
        self.assertEqual(custodian.parse_adapter_arguments(
            ["--timeout", "585", "--control-case", "build"]), (585.0, "build"))
        for args in (["--timeout", "585", "--control-case", "setup,build"],
                     ["--control-case", "build"], ["--timeout", "586"]):
            with self.subTest(args=args), self.assertRaises(ValueError):
                custodian.parse_adapter_arguments(args)
        self.assertEqual(custodian.parse_adapter_arguments(
            ["--timeout", "585", "--control-case", "managed"]), (585.0, "managed"))
        adapter_main = ADAPTER.read_text(encoding="utf-8")
        main_body = adapter_main[adapter_main.index("def main():"):]
        self.assertLess(main_body.index("timeout, control_case = parse_adapter_arguments"),
                        main_body.index("subprocess.Popen(client_argv(driver, mask_arg)"))
        self.assertIn("client_env['RHAI_CONTROL_CASE'] = control_case", main_body)

    def test_control_request_requires_matching_case_and_ready_event(self):
        slots = {
            slot: {"pid": pid, "start_seconds": 4, "start_microseconds": pid + 5}
            for slot, pid in (("client", 9), ("gate", 11), ("anchor", 12))
        }
        event = custodian.make_case_ready_event(
            "build", "build-1", slots,
            {"cargo_live": True, "compiler_descendant_live": True})
        request = {"op": "interrupt", "case": "build", "event_id": "build-1",
                   "target": "client", "signal": "KILL"}
        self.assertEqual(custodian.validate_control_request(request, "build", event, False),
                         ("client", custodian.signal.SIGKILL))
        for bad in (
            dict(request, case="setup"),
            dict(request, event_id="stale"),
            dict(request, target="gate"),
            dict(request, signal="USR1"),
        ):
            with self.subTest(request=bad), self.assertRaisesRegex(ValueError, "control request"):
                custodian.validate_control_request(bad, "build", event, False)
        with self.assertRaisesRegex(ValueError, "readiness"):
            custodian.validate_control_request(request, "build", None, False)
        with self.assertRaisesRegex(ValueError, "already consumed"):
            custodian.validate_control_request(request, "build", event, True)

    def test_case_ready_event_requires_exact_slot_identities_and_case_evidence(self):
        slots = {
            slot: {"pid": pid, "start_seconds": 4, "start_microseconds": pid + 5}
            for slot, pid in (("client", 9), ("gate", 11), ("anchor", 12))
        }
        for case, evidence in (
            ("setup", {"setup_command_live": True}),
            ("build", {"cargo_live": True, "compiler_descendant_live": True}),
            ("managed", {"managed_host_live": True, "fixture_live": True,
                          "fixture_topology_live": True, "fixture_thread_count": 4,
                          "stdout_bytes_read": 17, "stderr_bytes_read": 19}),
            ("deadline", {"command_live": True}),
        ):
            case_slots = dict(slots)
            if case == "managed":
                case_slots.update({slot: {"pid": pid, "start_seconds": 4,
                    "start_microseconds": pid + 5}
                    for slot, pid in (("managed_host", 13), ("fixture", 14))})
            if case == "deadline":
                case_slots.pop("client")
            event = custodian.make_case_ready_event(case, case + "-event", case_slots, evidence)
            self.assertEqual(event["case"], case)
            missing = dict(evidence)
            missing.pop(next(iter(missing)))
            with self.subTest(case=case), self.assertRaisesRegex(ValueError, "evidence is incomplete"):
                custodian.make_case_ready_event(case, case + "-event", slots, missing)
        incomplete_slots = dict(slots)
        del incomplete_slots["anchor"]
        with self.assertRaisesRegex(ValueError, "exact owned process identities"):
            custodian.make_case_ready_event(
                "setup", "setup-event", incomplete_slots, {"setup_command_live": True})

    def test_control_channel_is_separate_private_and_selected_before_client_spawn(self):
        source = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("controller.sock", source)
        self.assertIn("os.chmod(controller_path, 0o600)", source)
        self.assertIn("control_case = validate_control_case(args[3]) if len(args) == 4 else None", source)
        main_body = source[source.index("def main():"):source.index("if __name__ == '__main__':")]
        self.assertLess(main_body.index("accept_controller(controller_server"),
                        main_body.index("subprocess.Popen(client_argv(driver, mask_arg)"))
        self.assertIn("observe_case_ready(", source)
        self.assertIn("service_controller(", source)

    def test_deadline_control_is_owned_by_anchored_adapter_without_rpc_client(self):
        source = ADAPTER.read_text(encoding="utf-8")
        main_body = source[source.index("def main():"):source.index("if __name__ == '__main__':")]
        self.assertIn("DEADLINE_CONTROL_ARGV", source)
        self.assertIn("if control_case == 'deadline':", main_body)
        self.assertIn("run_deadline_control(", main_body)
        self.assertNotIn("subprocess.Popen(DEADLINE_CONTROL_ARGV", main_body)
        self.assertIn("deadline-control-stop", main_body)
        self.assertIn("client_status = None", main_body)

        runtime = Path("/private/runtime")
        controller = object()
        expected = (0, 31, "ready")
        with patch.object(custodian, "owned_command", return_value=expected) as owned:
            self.assertEqual(custodian.run_deadline_control(
                module, runtime, {"TMPDIR": "/private/runtime/tmp"},
                560.0, 575.0, controller), expected)
        args, kwargs = owned.call_args
        self.assertEqual(args[:5], (module, custodian.DEADLINE_CONTROL_ARGV,
                                    runtime, {"TMPDIR": "/private/runtime/tmp"},
                                    runtime / "deadline-control.out"))
        self.assertEqual(args[5:7], (560.0, 575.0))
        self.assertIs(kwargs["control_context"][0], controller)
        self.assertEqual(kwargs["control_context"][1:], ("deadline", None))
        self.assertFalse(kwargs["monitor"])

    def test_deadline_readiness_requires_only_exact_adapter_command_and_slots(self):
        slots = {
            "gate": {"pid": 11, "start_seconds": 4, "start_microseconds": 2},
            "anchor": {"pid": 12, "start_seconds": 4, "start_microseconds": 3},
        }
        event = custodian.make_case_ready_event(
            "deadline", "deadline-1", slots, {"command_live": True})
        self.assertEqual(set(event["identities"]), {"gate", "anchor"})
        with self.assertRaisesRegex(ValueError, "evidence is incomplete"):
            custodian.make_case_ready_event("deadline", "deadline-2", slots, {})
        source = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("DEADLINE_CONTROL_ARGV", source)
        self.assertIn("argv != DEADLINE_CONTROL_ARGV", source)

    def test_setup_build_control_stops_before_measurement_and_build_is_compile_only(self):
        source = SOURCE.read_text(encoding="utf-8")
        main_body = source[source.index("def main():"):source.index("if __name__ == '__main__':")]
        self.assertIn("run_control_only(control_case", main_body)
        self.assertLess(main_body.index("run_control_only(control_case"),
                        main_body.index("phase=process_scope_overhead_measurement"))
        self.assertIn("'--no-run'", source)
        self.assertIn("if control_case == 'setup':", main_body)
        self.assertIn("if control_case in ('build', 'managed'):", main_body)
        control_helper = source[source.index("def run_control_only("):source.index("def _parse_cargo_executable(")]
        self.assertNotIn("process_scope_overhead_measurement'", control_helper)

    def test_wrapper_preserves_normal_mode_without_control_selector(self):
        wrapper = Path(__file__).with_name("run-macos-process-overhead.sh").read_text()
        self.assertIn("if [[ $# == 0 ]]", wrapper)
        self.assertIn("control_case=normal", wrapper)
        self.assertIn("--control-case", wrapper)
        self.assertIn("--control-case", ADAPTER.read_text(encoding="utf-8"))
        self.assertIn("normal", ADAPTER.read_text(encoding="utf-8"))

    def test_controller_action_uses_only_exact_direct_client_handle(self):
        class Child:
            pid = 42
            returncode = None

            def __init__(self):
                self.kills = 0
                self.waits = 0

            def poll(self):
                return self.returncode

            def kill(self):
                self.kills += 1

            def wait(self, timeout):
                self.waits += 1
                self.returncode = -9
                return self.returncode

        child = Child()
        with patch.object(custodian.os, "kill", side_effect=AssertionError("numeric PID signal forbidden")), \
             patch.object(custodian.os, "killpg", side_effect=AssertionError("group signal forbidden")):
            status = custodian.signal_and_reap_owned_client(
                child, custodian.signal.SIGKILL, custodian.time.monotonic() + 1)
        self.assertEqual(status, -9)
        self.assertEqual((child.kills, child.waits), (1, 1))

    def test_controller_selection_socket_rejects_mismatched_case(self):
        server, client = socket.socketpair()
        try:
            client.sendall(b'{"op":"select","case":"build"}\n')
            with self.assertRaisesRegex(ValueError, "does not match"):
                custodian.validate_control_selection(
                    custodian.read_line(server, custodian.time.monotonic() + 1), "setup")
        finally:
            server.close()
            client.close()

    def test_tool_identity_rejects_mismatched_or_missing_probe(self):
        expected = module.expected_tool_identity()
        module.validate_tool_identity(expected)

        changed = dict(expected)
        changed['cargo_version'] = 'cargo 99.0.0 (unreviewed)'
        with self.assertRaisesRegex(RuntimeError, 'cargo_version'):
            module.validate_tool_identity(changed)

        omitted = dict(expected)
        del omitted['rustdoc_version']
        with self.assertRaisesRegex(RuntimeError, 'rustdoc_version'):
            module.validate_tool_identity(omitted)

    def test_tool_preflight_is_before_archive_and_cargo_measurement(self):
        source = SOURCE.read_text(encoding='utf-8')
        main_body = source[source.index('def main():'):source.index("if __name__ == '__main__':")]
        preflight = main_body.index('verify_toolchain_identity(')
        archive = main_body.index("'archive',SOURCE_REF")
        measurement = main_body.index('cmd=measurement_cargo_argv()')
        self.assertLess(preflight, archive)
        self.assertLess(preflight, measurement)

    def test_closed_path_and_version_probes_use_the_same_xcode_tool_directory(self):
        with tempfile.TemporaryDirectory(prefix="tool-path-contract-") as directory:
            runtime = Path(directory) / "runtime"
            env = module.build_environment(runtime)
            paths = env["PATH"].split(":")
            tool_bin = Path(paths[1])
            self.assertEqual(paths[0], str(module.TOOL))
            self.assertEqual(tool_bin, runtime / "tool-bin")
            self.assertNotIn(str(module.XCODE_TOOLS), paths)
            self.assertEqual({path.name for path in tool_bin.iterdir()}, {"cc", "clang", "ld", "dsymutil"})
            self.assertFalse((tool_bin / "ar").exists())
            for name in ("cc", "clang", "ld", "dsymutil"):
                self.assertEqual(os.readlink(tool_bin / name), str(module.XCODE_TOOLS / name))
        probes = {key: argv for key, argv, _filename in module.tool_identity_probes()}
        for key, executable, args in (
            ("cc_identity", module.XCODE_TOOLS / "cc", ["--version"]),
            ("clang_identity", module.XCODE_TOOLS / "clang", ["--version"]),
            ("ld_identity", module.XCODE_TOOLS / "ld", ["-v"]),
            ("dsymutil_identity", module.XCODE_TOOLS / "dsymutil", ["--version"]),
        ):
            self.assertEqual(probes[key], [str(executable), *args])

    def test_adapter_xcode_queries_are_exact_and_read_only(self):
        self.assertTrue(custodian.is_exact_xcode_preflight(['/usr/bin/xcrun', '--find', 'cc']))
        self.assertTrue(custodian.is_exact_xcode_preflight([str(custodian.XCODE_TOOLS/'cc'), '--version']))
        self.assertFalse(custodian.is_exact_xcode_preflight(['/usr/bin/xcrun', '--find', 'unreviewed']))
        self.assertFalse(custodian.is_exact_xcode_preflight([str(custodian.XCODE_TOOLS/'cc'), 'unreviewed-argument']))
        self.assertFalse(custodian.is_exact_xcode_preflight(['/usr/bin/cc', '--version']))

    def test_darwin_siginfo_layout_and_waitid_constants_match_active_sdk(self):
        # The declaration maps sys/signal.h siginfo_t on LP64 Darwin.
        info = module._DarwinSigInfo
        self.assertEqual(ctypes.sizeof(info), 104)
        self.assertEqual((info.si_signo.offset, info.si_errno.offset, info.si_code.offset,
                          info.si_pid.offset, info.si_uid.offset, info.si_status.offset,
                          info.si_addr.offset, info.si_value.offset, info.si_band.offset,
                          getattr(info, "__pad").offset),
                         (0, 4, 8, 12, 16, 20, 24, 32, 40, 48))
        self.assertEqual((module.DARWIN_P_PID, module.DARWIN_WNOHANG,
                          module.DARWIN_WEXITED, module.DARWIN_WNOWAIT),
                         (1, 0x01, 0x04, 0x20))

    def test_native_waitid_binding_matches_header_without_calling_native_api(self):
        class Function:
            argtypes = None
            restype = None

            def __call__(self, *_args):
                raise AssertionError("native waitid must not be called by this source test")

        class Library:
            waitid = Function()

        library = Library()
        with patch.object(module.os, "waitid", None, create=True), \
                patch.object(module.sys, "platform", "darwin"), \
                patch.object(module.ctypes, "CDLL", return_value=library) as load:
            module.require_nonreaping_waitid()
        load.assert_called_once_with(None, use_errno=True)
        self.assertEqual(library.waitid.argtypes,
                         (ctypes.c_int, ctypes.c_uint32,
                          ctypes.POINTER(module._DarwinSigInfo), ctypes.c_int))
        self.assertIs(library.waitid.restype, ctypes.c_int)
        self.assertTrue(callable(module._WAITID))

    def test_measurement_run_decodes_successful_bytes_before_parser_and_export(self):
        parser_path = Path(__file__).parents[1] / "managed-unix-scope-close" / "measure-process-overhead.py"
        parser_spec = importlib.util.spec_from_file_location("overhead_parser_source_test", parser_path)
        parser = importlib.util.module_from_spec(parser_spec)
        parser_spec.loader.exec_module(parser)
        rows = []
        for pair in range(parser.PAIRS):
            scopes = ("DirectChild", "Managed") if pair % 2 == 0 else ("Managed", "DirectChild")
            workloads = ("true", "capture") if pair % 2 == 0 else ("capture", "true")
            for scope in scopes:
                for workload in workloads:
                    count = parser.STREAM_BYTES if workload == "capture" else 0
                    rows.append(f"PROCESS_SCOPE_SAMPLE,{pair},{scope},{workload},1000,{count},{count},0")
        raw = ("\n".join(rows) + "\n").encode("ascii")
        with tempfile.TemporaryDirectory(prefix="measurement-bytes-test-") as directory:
            output_path = Path(directory) / "cargo.log"
            output_path.write_bytes(raw)

            class Reader:
                @staticmethod
                def complete_listing(_deadline):
                    return []

            class ReaderModule:
                @staticmethod
                def candidate_absence(_reader, _runtime, _deadline):
                    return 0

            with patch.object(module, "run_anchored_command", return_value=(0, raw)), \
                    patch.object(module, "_LAST_CUSTODY_RESULT", {"pgid": 99}), \
                    patch.object(module, "_load_process_reader", return_value=(ReaderModule(), Reader())), \
                    patch.object(module, "emit"):
                status, output = module.run(["/bin/true"], output_path,
                    __import__("time").monotonic() + 10, {}, Path(directory))
            samples = parser.parse_samples(output)
            summary = parser.summarize(samples)
            exported = Path(directory) / "samples.log"
            exported.write_text(output, encoding="utf-8")
            exported_text, exported_samples, exported_summary = module.export_measurement_output(
                Path(directory) / "measurement", status, raw, parser)
            self.assertEqual(status, 0)
            self.assertIs(type(output), str)
            self.assertEqual(exported.read_text(encoding="utf-8"), output)
            self.assertEqual(summary["samples_total"], 120)
            self.assertEqual(summary["warmups"], 0)
            self.assertEqual(exported_text, output)
            self.assertEqual(exported_summary["samples_total"], 120)
            self.assertEqual(len(exported_samples), 120)
            self.assertEqual((Path(directory) / "measurement" / "cargo.status").read_text(), "0\n")
            self.assertEqual((Path(directory) / "measurement" / "cargo-output.log").read_text(), output)

    def test_final_acceptance_requires_cleanup_complete_even_after_eof(self):
        uncertain = {"setup_complete": True, "group_signal_issued": True,
                     "gate_status": -9, "anchor_status": -9,
                     "cleanup_complete": False, "group_signal_error": "PermissionError"}
        cleaned = dict(uncertain, cleanup_complete=True)
        self.assertFalse(custodian.records_closed([uncertain]))
        self.assertFalse(custodian.clean_interruption("client-eof", -15, [uncertain]))
        self.assertTrue(custodian.records_closed([cleaned]))
        self.assertTrue(custodian.clean_interruption("client-eof", -15, [cleaned]))
        with tempfile.TemporaryDirectory(prefix="incomplete-custody-test-") as directory:
            runtime = Path(directory) / "runtime"
            runtime.mkdir()
            receipt = runtime / "incomplete-receipt.json"
            receipt.write_text('{"complete": false}\n')
            before = receipt.read_bytes()
            with self.assertRaisesRegex(RuntimeError, "runtime retained"):
                custodian.require_complete_custody(False, "client-eof", -15, [uncertain])
            self.assertTrue(runtime.is_dir())
            self.assertEqual(receipt.read_bytes(), before)
        source = ADAPTER.read_text(encoding="utf-8")
        self.assertLess(source.index("require_complete_custody(clean_success"), source.index("shutil.rmtree(runtime)"))

    def test_client_connection_deadline_is_work_stop_with_closure_reserve(self):
        source = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("conn = wait_for_client_connection(server, proc, work_deadline)", source)
        connection_wait = source[source.index("def wait_for_client_connection("):source.index("def read_live_identities(")]
        self.assertNotIn("time.monotonic() >= deadline", connection_wait)
        self.assertIn("terminate_and_reap_client(proc, closure_deadline)", source)

        class Server:
            def __init__(self):
                self.accepts = 0

            def accept(self):
                self.accepts += 1
                raise BlockingIOError

        class Client:
            returncode = None

            @staticmethod
            def poll():
                return None

        server, client = Server(), Client()
        work_deadline = 10.0
        clock = iter((9.0, 9.0, 10.01))
        with patch.object(custodian.time, "monotonic", side_effect=lambda: next(clock)), \
                patch.object(custodian.time, "sleep") as sleep:
            with self.assertRaisesRegex(TimeoutError, "deadline expired before RPC client connection"):
                custodian.wait_for_client_connection(server, client, work_deadline)
        self.assertEqual(server.accepts, 1)
        sleep.assert_called_once()

    def test_wrapper_runtime_record_parser_accepts_only_identical_duplicates(self):
        helper = Path(__file__).with_name("runtime-path-parser.zsh")
        cases = [
            ("runtime_path=/scope/runtime\n", "/scope/runtime", 0),
            ("runtime_path=/scope/runtime\nruntime_path=/scope/runtime\n", "/scope/runtime", 0),
            ("runtime_path=/scope/runtime\nruntime_path=/other/runtime\n", "", 1),
            ("no runtime record\n", "", 1),
        ]
        for evidence, expected, status in cases:
            with self.subTest(evidence=evidence), tempfile.TemporaryDirectory(prefix="runtime-record-test-") as directory:
                evidence_path = Path(directory) / "evidence"
                evidence_path.write_text(evidence)
                script = f'source {str(helper)!r}; runtime_path_from_evidence {str(evidence_path)!r} /scope/runtime'
                result = subprocess.run(["/bin/zsh", "-c", script], text=True, capture_output=True)
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)
        wrapper = Path(__file__).with_name("run-macos-process-overhead.sh").read_text()
        self.assertIn("runtime_path_from_evidence", wrapper)
    def test_child_environment_is_closed_and_runtime_local(self):
        with tempfile.TemporaryDirectory(prefix="overhead-env-test-") as directory:
            runtime = (Path(directory) / "private-run").resolve()
            inherited = {
                "__CARGO_TEST_SETSID_PLEASE_DONT_USE_ELSEWHERE": "1",
                "RUSTC_WRAPPER": "/tmp/foreign-wrapper",
                "CARGO_ENCODED_RUSTFLAGS": "-C link-arg=-Wl,--plugin",
                "CC": "/tmp/foreign-compiler",
            }
            with patch.dict(os.environ, inherited, clear=False):
                env = module.build_environment(runtime)
            self.assertEqual(set(env), {
                "PATH", "HOME", "TMPDIR", "TMP", "TEMP", "CARGO_HOME",
                "RUSTUP_HOME", "CARGO_TARGET_DIR", "CARGO_BUILD_JOBS",
                "CARGO_INCREMENTAL", "CARGO_PROFILE_DEV_DEBUG",
                "CARGO_PROFILE_TEST_DEBUG", "CARGO_TERM_COLOR", "RUSTC",
                "RUSTDOC", "SDKROOT",
            })
            self.assertEqual(
                env["SDKROOT"],
                "/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk",
            )
            self.assertTrue(set(inherited).isdisjoint(env))
            for name in ("HOME", "TMPDIR", "CARGO_HOME", "RUSTUP_HOME", "CARGO_TARGET_DIR"):
                self.assertTrue(Path(env[name]).is_relative_to(runtime))
            self.assertNotIn("/opt/homebrew/bin", env["PATH"])
            self.assertEqual(env["CARGO_BUILD_JOBS"], "2")

    def test_anchor_readiness_binds_distinct_pid_and_group(self):
        self.assertEqual(compile(custodian.GATE_CODE, "gate", "exec").co_name, "<module>")
        self.assertEqual(compile(custodian.ANCHOR_CODE, "anchor", "exec").co_name, "<module>")
        read_fd, write_fd = os.pipe()
        try:
            os.write(write_fd, b"ANCHOR_READY pid=21 pgid=20\n")
            self.assertEqual(custodian.read_anchor_ready(read_fd, 21, 20, __import__("time").monotonic() + 1),
                             "ANCHOR_READY pid=21 pgid=20")
        finally:
            os.close(read_fd)
            os.close(write_fd)
        read_fd, write_fd = os.pipe()
        try:
            os.write(write_fd, b"ANCHOR_READY pid=21 pgid=21\n")
            with self.assertRaises(RuntimeError):
                custodian.read_anchor_ready(read_fd, 21, 20, __import__("time").monotonic() + 1)
        finally:
            os.close(read_fd)
            os.close(write_fd)

    def test_gate_requires_exact_release_token(self):
        for token in (b"", b"0"):
            with self.subTest(token=token), patch.object(custodian.os, "read", return_value=token), \
                    patch.object(custodian.os, "close"), patch.object(custodian.os, "execve") as execve, \
                    patch.object(custodian.sys, "argv", ["gate", "7", "", "/bin/true"]):
                with self.assertRaises(SystemExit) as raised:
                    exec(compile(custodian.GATE_CODE, "gate", "exec"), {})
                self.assertEqual(raised.exception.code, 125)
                execve.assert_not_called()
        with patch.object(custodian.os, "read", return_value=b"1"), patch.object(custodian.os, "close"), \
                patch.object(custodian.os, "execve", side_effect=LookupError("exec observed")) as execve, \
                patch.object(custodian.signal, "pthread_sigmask") as setmask, \
                patch.object(custodian.sys, "argv", ["gate", "7", "2,15", "/bin/true", "arg"]):
            with self.assertRaisesRegex(LookupError, "exec observed"):
                exec(compile(custodian.GATE_CODE, "gate", "exec"), {})
            setmask.assert_called_once_with(custodian.signal.SIG_SETMASK,
                                            {custodian.signal.Signals(2), custodian.signal.Signals(15)})
            execve.assert_called_once_with("/bin/true", ["/bin/true", "arg"], custodian.os.environ)

    def test_waitid_capability_fails_before_any_spawn(self):
        source = ADAPTER.read_text(encoding="utf-8")
        self.assertLess(source.index("custody.require_nonreaping_waitid()"),
                        source.index("subprocess.Popen(client_argv(driver, mask_arg)"))

    def test_main_resolves_waitid_before_setup_children(self):
        source = ADAPTER.read_text(encoding="utf-8")
        self.assertLess(source.index("custody.require_launch_readiness()"),
                        source.index("custody.require_nonreaping_waitid()"))
        self.assertLess(source.index("custody.require_nonreaping_waitid()"),
                        source.index("subprocess.Popen(client_argv(driver, mask_arg)"))

    def test_command_cleanup_reserves_closure_deadline(self):
        source = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("min(float(requested_deadline), work_deadline)", source)
        self.assertIn("closure_deadline, conn=conn", source)
        self.assertIn("stop_anchored(custody, gate, anchor, gate.pid", source)
        self.assertIn("work_deadline = min(started + 560", source)
        self.assertIn("read_live_identities(runtime, readback_deadline, reader)", source)
        self.assertNotIn("min(closure_deadline, time.monotonic() + timeout", source)

    def test_group_kill_is_not_repeated_when_first_reap_times_out(self):
        class Child:
            def __init__(self, pid, waits):
                self.pid = pid
                self.waits = iter(waits)

            def wait(self, timeout):
                result = next(self.waits)
                if isinstance(result, BaseException):
                    raise result
                return result

        gate = Child(20, [custodian.subprocess.TimeoutExpired("gate", 1), 0])
        anchor = Child(21, [0, 0])
        state = {"issued": False}
        with patch.object(custodian, "waitid_nonreap", return_value=None), \
                patch.object(custodian.os, "getpgid", return_value=20), \
                patch.object(custodian.os, "killpg") as killpg:
            with self.assertRaisesRegex(RuntimeError, "reap incomplete"):
                custodian.stop_anchored(module, gate, anchor, 20, custodian.time.monotonic() + 2, state)
            self.assertTrue(state["issued"])
            self.assertEqual(custodian.stop_anchored(module, gate, anchor, 20,
                                                  custodian.time.monotonic() + 2, state), [0, 0])
            killpg.assert_called_once_with(20, custodian.signal.SIGKILL)

    def test_setup_cleanup_accounts_for_ambiguous_release(self):
        source = ADAPTER.read_text(encoding="utf-8")
        self.assertLess(source.index("released = True\n        record['released'] = True\n        if os.write(release_w, b'1')"),
                        source.index("except BaseException as setup_error:"))
        self.assertIn("stop_anchored(custody, gate, anchor, gate.pid", source)
        self.assertIn("phase = 'post-release' if released else 'pre-release'", source)

    def test_group_setup_uses_exact_child_side_options(self):
        leader = custodian.popen_group_options()
        anchor = custodian.popen_group_options(731)
        if "process_group" in __import__("inspect").signature(custodian.subprocess.Popen).parameters:
            self.assertEqual(leader, {"process_group": 0})
            self.assertEqual(anchor, {"process_group": 731})
        else:
            import threading
            self.assertTrue(callable(leader["preexec_fn"]))
            self.assertTrue(callable(anchor["preexec_fn"]))
            self.assertNotIn("process_group", leader)
            self.assertNotIn("process_group", anchor)
            with patch.object(threading, "active_count", return_value=2):
                with self.assertRaises(RuntimeError):
                    custodian.popen_group_options()

    def test_all_harness_spawns_are_confined_to_gate_registration(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        spawns = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and \
                    isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                spawns.append(node.func.attr)
        self.assertEqual(spawns, [])
        adapter = ast.parse(ADAPTER.read_text(encoding="utf-8"))
        calls = [node.func.attr for node in ast.walk(adapter) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                 and node.func.value.id == "subprocess"]
        self.assertIn("Popen", calls)
        self.assertFalse(any(name in {"run", "check_call", "check_output"} for name in calls))
        self.assertFalse(module.CUSTODY_IMPLEMENTATION_FROZEN)
        driver = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("owned-process-ledger", driver)
        self.assertNotIn("persist_ledger", driver)

    def test_child_exec_paths_restore_the_parent_signal_mask(self):
        self.assertIn("pthread_sigmask(signal.SIG_SETMASK", custodian.GATE_CODE)
        self.assertIn("pthread_sigmask(signal.SIG_SETMASK", custodian.ANCHOR_CODE)
        self.assertIn("pthread_sigmask(signal.SIG_SETMASK", custodian.CLIENT_CODE)
        self.assertEqual(custodian._mask_argument({custodian.signal.SIGTERM, custodian.signal.SIGINT}),
                         f"{int(custodian.signal.SIGINT)},{int(custodian.signal.SIGTERM)}")

    def test_client_exec_vector_runs_python_driver_with_restored_signal_mask(self):
        driver = Path("/private/runtime/macos-process-overhead.py")
        mask = "2,15"
        command = custodian.client_argv(driver, mask)
        self.assertEqual(command, [custodian.sys.executable, "-c", custodian.CLIENT_CODE,
                                   mask, custodian.sys.executable, str(driver)])
        adapter = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("subprocess.Popen(client_argv(driver, mask_arg)", adapter)
        with patch.object(custodian.sys, "argv", ["-c", *command[3:]]), \
                patch.object(custodian.signal, "pthread_sigmask") as setmask, \
                patch.object(custodian.os, "execv", side_effect=LookupError("exec observed")) as execv:
            with self.assertRaisesRegex(LookupError, "exec observed"):
                exec(compile(custodian.CLIENT_CODE, "client", "exec"), {})
            setmask.assert_called_once_with(custodian.signal.SIG_SETMASK,
                                            {custodian.signal.Signals(2), custodian.signal.Signals(15)})
            execv.assert_called_once_with(custodian.sys.executable,
                                          [custodian.sys.executable, str(driver)])

    def test_native_resource_sample_persists_identities_before_rss_limit_rejection(self):
        root_pid = os.getpid()
        root = {"pid": root_pid, "uid": os.getuid(), "ppid": 1, "pgid": root_pid,
                "start_seconds": 10, "start_microseconds": 2,
                "rss_bytes": module.MAX_RSS_KIB * 1024}
        child = {"pid": 994, "uid": os.getuid(), "ppid": root_pid, "pgid": root_pid,
                 "start_seconds": 11, "start_microseconds": 3, "rss_bytes": 1024}

        class Reader:
            def complete_listing(self, _deadline):
                return [root, child]

            resident_kib = staticmethod(reader_module.resident_kib)

        with tempfile.TemporaryDirectory(prefix="native-resource-ledger-test-") as directory:
            ledger = Path(directory) / "owned-process-ledger.json"
            with patch.object(module, "_adapter_process_reader", Reader(), create=True), \
                    patch.object(custodian, "CUSTODIAN_IDENTITY", root), \
                    patch.object(custodian, "CUSTODY_IDENTITIES", {}), \
                    patch.object(custodian, "LEDGER_PATH", ledger):
                with self.assertRaisesRegex(RuntimeError, "sampled process RSS"):
                    custodian.sample_owned_resources(module, Path(directory), {},
                        __import__("time").monotonic() + 10, __import__("time").monotonic() + 10)
                saved = __import__("json").loads(ledger.read_text())
                self.assertEqual([row["pid"] for row in saved["identities"]], [994])
                self.assertIn("one native complete census", saved["identity_observation"])

    def test_frozen_resource_monitor_uses_native_census_without_ps_join(self):
        source = ADAPTER.read_text(encoding="utf-8")
        record_start = source.index("def record_sampled_descendants(")
        record_end = source.index("\ndef sample_owned_resources(", record_start)
        sample_end = source.index("\ndef ", record_end + 2)
        self.assertIn("reader.complete_listing(deadline)", source[record_start:record_end])
        self.assertIn("reader.resident_kib(live)", source[record_end:sample_end])
        self.assertNotIn("parse_ps_snapshot", source[record_start:sample_end])
        self.assertNotIn("/bin/ps", source[record_start:sample_end])

    def test_cancellation_prevents_a_command_spawn(self):
        with patch.object(custodian, "REQUESTED_SIGNAL", custodian.signal.SIGTERM), \
                patch.object(custodian.subprocess, "Popen") as popen:
            with self.assertRaisesRegex(InterruptedError, "before owned command setup"):
                custodian.spawn_anchored(module, ["/bin/true"], Path("/tmp"), {}, Path("/tmp/out"),
                                         custodian.time.monotonic() + 5,
                                         custodian.time.monotonic() + 10)
            popen.assert_not_called()

    def test_client_termination_escalates_to_exact_child_kill_and_reap(self):
        class Child:
            returncode = None

            def __init__(self):
                self.waits = 0
                self.kills = 0

            def terminate(self):
                self.terminated = True

            def kill(self):
                self.kills += 1

            def wait(self, timeout):
                self.waits += 1
                if self.waits == 1:
                    raise custodian.subprocess.TimeoutExpired("client", timeout)
                self.returncode = -9
                return self.returncode

        child = Child()
        self.assertEqual(custodian.terminate_and_reap_client(child, custodian.time.monotonic() + 4), -9)
        self.assertTrue(child.terminated)
        self.assertEqual(child.kills, 1)
        self.assertEqual(child.waits, 2)

    def test_client_exit_racing_term_is_still_reaped_by_exact_child_handle(self):
        class Child:
            returncode = None

            def __init__(self):
                self.waits = 0

            def terminate(self):
                raise ProcessLookupError("child exited before terminate")

            def wait(self, timeout):
                self.waits += 1
                self.returncode = 0
                return 0

        child = Child()
        self.assertEqual(custodian.terminate_and_reap_client(child, custodian.time.monotonic() + 4), 0)
        self.assertEqual(child.waits, 1)

    def test_exact_direct_child_fallback_kills_once_and_reaps(self):
        class Child:
            def __init__(self, pid):
                self.pid = pid
                self.returncode = None
                self.kills = 0

            def kill(self):
                self.kills += 1
                self.returncode = -9

            def wait(self, timeout):
                return self.returncode

        gate, anchor = Child(20), Child(21)
        issued = {}
        first = custodian.kill_and_reap_direct_children((('gate', gate), ('anchor', anchor)),
            custodian.time.monotonic() + 2, issued)
        second = custodian.kill_and_reap_direct_children((('gate', gate), ('anchor', anchor)),
            custodian.time.monotonic() + 2, issued)
        self.assertEqual(first, [-9, -9])
        self.assertEqual(second, [-9, -9])
        self.assertEqual((gate.kills, anchor.kills), (1, 1))

    def test_adapter_ledger_unions_observed_identities_and_owns_completion(self):
        with tempfile.TemporaryDirectory(prefix="custody-ledger-test-") as directory:
            path = Path(directory) / "owned-process-ledger.json"
            first = {"pid": 31, "start_seconds": 100, "start_microseconds": 1}
            second = {"pid": 32, "start_seconds": 101, "start_microseconds": 2}
            with patch.object(custodian, "LEDGER_PATH", path), \
                    patch.object(custodian, "CUSTODIAN_IDENTITY", {"pid": 1, "start_seconds": 1,
                        "start_microseconds": 1}), \
                    patch.object(custodian, "CUSTODY_IDENTITIES", {}):
                custodian.merge_observed_identities([first])
                custodian.merge_observed_identities([second])
                custodian.merge_observed_identities([])
                ledger = __import__("json").loads(path.read_text())
                self.assertEqual({row["pid"] for row in ledger["identities"]}, {31, 32})
                self.assertFalse(ledger["observed_identity_readback_complete"])
                self.assertEqual(ledger["custodian_identity"]["pid"], 1)

    def test_control_registered_processes_are_persisted_from_complete_native_census(self):
        rows = [
            {"pid": 31, "uid": os.getuid(), "start_seconds": 4,
             "start_microseconds": 1, "ppid": 8, "pgid": 31, "path": "/bin/git"},
            {"pid": 32, "uid": os.getuid(), "start_seconds": 4,
             "start_microseconds": 2, "ppid": 8, "pgid": 31, "path": "/bin/python"},
        ]

        class Reader:
            def __init__(self, values):
                self.values = values

            def complete_listing(self, _deadline):
                return self.values

        class Custody:
            _adapter_process_reader = Reader(rows)

        with tempfile.TemporaryDirectory(prefix="control-ledger-test-") as directory:
            ledger_path = Path(directory) / "owned-process-ledger.json"
            with patch.object(custodian, "LEDGER_PATH", ledger_path), \
                    patch.object(custodian, "CUSTODIAN_IDENTITY", {"pid": 1}), \
                    patch.object(custodian, "CUSTODY_IDENTITIES", {}):
                registered = custodian.record_registered_processes(
                    Custody(), (31, 32), custodian.time.monotonic() + 2)
                self.assertEqual([row["pid"] for row in registered], [31, 32])
                stored = __import__("json").loads(ledger_path.read_text())
                self.assertEqual({row["pid"] for row in stored["identities"]}, {31, 32})
                Custody._adapter_process_reader = Reader(rows[:1])
                with self.assertRaisesRegex(RuntimeError, "omitted an exact registered"):
                    custodian.record_registered_processes(
                        Custody(), (31, 32), custodian.time.monotonic() + 2)

    def test_final_identity_readback_uses_reserved_deadline_and_exact_start_tuple(self):
        identity = {"pid": 44, "uid": os.getuid(), "start_seconds": 200,
                    "start_microseconds": 7, "ppid": 1, "pgid": 44, "path": "/tmp/tool"}

        class Reader:
            def __init__(self, rows):
                self.rows = rows
                self.deadline = None

            def complete_listing(self, deadline):
                self.deadline = deadline
                return self.rows

        with tempfile.TemporaryDirectory(prefix="custody-readback-test-") as directory:
            runtime = Path(directory).resolve()
            path = runtime / "owned-process-ledger.json"
            path.write_text(__import__("json").dumps({"identities": [identity],
                "observed_identity_readback_complete": False}))
            with patch.object(custodian, "LEDGER_PATH", path), \
                    patch.object(custodian, "CUSTODIAN_IDENTITY", {"pid": 1}), \
                    patch.object(custodian, "CUSTODY_IDENTITIES", {custodian._identity_key(identity): identity}):
                alive = Reader([identity])
                deadline = custodian.time.monotonic() + 5
                self.assertEqual(custodian.read_live_identities(runtime, deadline, alive), [identity])
                self.assertEqual(alive.deadline, deadline)
                self.assertFalse(__import__("json").loads(path.read_text())[
                    "observed_identity_readback_complete"])
                gone = Reader([])
                self.assertEqual(custodian.read_live_identities(runtime, deadline, gone), [])
                self.assertTrue(__import__("json").loads(path.read_text())[
                    "observed_identity_readback_complete"])
                expired = Reader([])
                with self.assertRaisesRegex(RuntimeError, "no scoped time remains"):
                    custodian.read_live_identities(runtime, custodian.time.monotonic() - 1, expired)
                self.assertIsNone(expired.deadline)

    def test_server_stops_dispatch_after_custody_uncertainty(self):
        class Custody:
            CARGO = Path("/bin/true")
            RUSTC = CARGO
            RUSTDOC = CARGO

            @staticmethod
            def build_environment(_runtime):
                return {}

        for closed, expected in ((False, "custody-incomplete"), (True, "command-failed")):
            with self.subTest(closed=closed), tempfile.TemporaryDirectory(prefix="custody-rpc-test-") as directory:
                runtime = Path(directory).resolve()
                output = runtime / "out"
                request = {"op": "command", "argv": ["/bin/true"], "env": {},
                           "output": str(output), "cwd": str(runtime),
                           "deadline": custodian.time.monotonic() + 10, "monitor_resources": False}
                server, client = socket.socketpair()
                record = {"cleanup_complete": closed}
                with patch.object(custodian, "REQUESTED_SIGNAL", None), \
                        patch.object(custodian, "read_line", return_value=request), \
                        patch.object(custodian, "owned_command", side_effect=RuntimeError("stop")) as command, \
                        patch.object(custodian, "client_gone", return_value=False), \
                        patch.object(custodian, "CUSTODY_RECORDS", [record]):
                    result = custodian.serve_requests(Custody(), server, runtime,
                        custodian.time.monotonic() + 20, custodian.time.monotonic() + 25)
                    self.assertEqual(result, expected)
                    command.assert_called_once()
                server.close()
                client.close()

    def test_rpc_is_single_frame_bounded_and_rejects_truncation(self):
        server, client = socket.socketpair()
        try:
            client.sendall(b'{"op":"command"}\n')
            self.assertEqual(custodian.read_line(server, __import__("time").monotonic() + 1),
                             {"op": "command"})
        finally:
            server.close()
            client.close()
        server, client = socket.socketpair()
        try:
            client.sendall(b'{"op":')
            client.close()
            with self.assertRaisesRegex(RuntimeError, "truncated custody RPC frame"):
                custodian.read_line(server, __import__("time").monotonic() + 1)
        finally:
            server.close()
        server, client = socket.socketpair()
        try:
            sender = threading.Thread(target=client.sendall, args=(b"x" * 65536,))
            sender.start()
            with self.assertRaisesRegex(RuntimeError, "exceeds 64 KiB"):
                custodian.read_line(server, __import__("time").monotonic() + 1)
            sender.join(timeout=1)
            self.assertFalse(sender.is_alive())
        finally:
            server.close()
            client.close()

    def test_rpc_output_path_is_confined_after_resolution(self):
        with tempfile.TemporaryDirectory(prefix="custody-path-test-") as directory:
            runtime = (Path(directory) / "runtime").resolve()
            evidence = (Path(directory) / "evidence").resolve()
            runtime.mkdir()
            evidence.mkdir()
            self.assertEqual(custodian._private_path(runtime / "output", runtime, evidence, "output"),
                             runtime / "output")
            with self.assertRaisesRegex(RuntimeError, "escapes"):
                custodian._private_path(Path(directory) / "foreign", runtime, evidence, "output")

    def test_client_eof_signals_once_and_reaps_exact_command_children(self):
        class Child:
            def __init__(self, pid):
                self.pid = pid
                self.returncode = None

            def wait(self, timeout):
                self.returncode = 0
                return 0

        gate, anchor = Child(20), Child(21)
        server, client = socket.socketpair()
        client.close()
        state = {"issued": False}
        record = {"group_signal_issued": False, "gate_status": None, "anchor_status": None}
        with patch.object(custodian, "spawn_anchored",
                          return_value=(gate, anchor, "ready", {}, set(), state, record)), \
                patch.object(custodian, "waitid_nonreap", return_value=None), \
                patch.object(custodian.os, "getpgid", return_value=20), \
                patch.object(custodian.os, "killpg") as killpg, \
                patch.object(custodian.signal, "pthread_sigmask"):
            with self.assertRaisesRegex(RuntimeError, "disconnected"):
                custodian.owned_command(custodian, ["/bin/true"], Path("/tmp"), {},
                    Path("/tmp/out"), __import__("time").monotonic() + 2,
                    __import__("time").monotonic() + 4, conn=server)
            killpg.assert_called_once_with(20, custodian.signal.SIGKILL)
            self.assertEqual((gate.returncode, anchor.returncode), (0, 0))
            self.assertTrue(record["group_signal_issued"])
            self.assertEqual((record["gate_status"], record["anchor_status"]), (0, 0))
        server.close()

    def test_process_snapshot_missing_owned_root_fails_closed(self):
        with patch.object(module, "run_anchored_command", return_value=(0, b"")):
            with self.assertRaisesRegex(RuntimeError, "owned harness is absent"):
                module.process_snapshot(321, __import__("time").monotonic() + 1, {}, Path("/tmp"))


if __name__ == "__main__":
    unittest.main()
