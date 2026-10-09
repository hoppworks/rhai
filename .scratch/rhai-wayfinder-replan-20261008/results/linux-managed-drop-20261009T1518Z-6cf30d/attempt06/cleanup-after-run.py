#!/usr/bin/env python3
import json
import os
import re
from pathlib import Path

ATTEMPT = Path(__file__).resolve().parent
SELECTORS = [
    "managed_run_closes_worker_after_leader_exit_and_preserves_sentinel",
    "managed_run_closes_pipe_closed_worker_before_return",
    "direct_run_returns_with_pipe_closed_worker_live_control",
]
receipt = {"phases": {}, "complete": True}


def proc(pid):
    base = Path("/proc") / str(pid)
    try:
        stat = (base / "stat").read_text()
    except (FileNotFoundError, ProcessLookupError):
        return None
    rest = stat[stat.rfind(")") + 2 :].split()
    try:
        state, ppid, pgid = rest[0], int(rest[1]), int(rest[2])
        start = int(rest[19])
    except (IndexError, ValueError):
        return {"pid": pid, "unreadable": True}
    try:
        cmd = (base / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")
        env = (base / "environ").read_bytes().split(b"\0")
    except (FileNotFoundError, ProcessLookupError):
        try:
            (base / "stat").read_text()
        except (FileNotFoundError, ProcessLookupError):
            return None
        return {"pid": pid, "state": state, "ppid": ppid, "pgid": pgid, "start": start, "unreadable": True}
    except (PermissionError, IndexError, ValueError):
        return {"pid": pid, "state": state, "ppid": ppid, "pgid": pgid, "start": start, "unreadable": True}
    return {"pid": pid, "state": state, "ppid": ppid, "pgid": pgid, "start": start, "cmd": cmd, "env": env}


def group_members(group):
    found = []
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            row = proc(int(entry.name))
            if row and row.get("pgid") == group:
                found.append(row)
    return found


def phase_readback(phase):
    result = {"selectors": {}, "complete": True}
    started_any = any((ATTEMPT / f"{phase}-{index:02d}.started").is_file() for index in range(1, len(SELECTORS) + 1))
    for index, selector in enumerate(SELECTORS, 1):
        stem = f"{phase}-{index:02d}"
        marker = ATTEMPT / f"{stem}.started"
        if not marker.is_file():
            result["selectors"][selector] = {"started": False, "complete": not started_any}
            if started_any:
                result["complete"] = False
            continue
        log = (ATTEMPT / f"{stem}.combined.log").read_text(errors="replace")
        start = re.search(r"managed_fixture_started root=(\S+) test_pid=(\d+)(?: sentinel_pid=(\d+))?", log)
        if not start:
            result["selectors"][selector] = {"started": True, "complete": False, "error": "fixture identity line missing"}
            result["complete"] = False
            continue
        root = Path(start.group(1))
        test_pid = int(start.group(2))
        record = {"started": True, "root": str(root), "test_pid": test_pid}
        envelope = json.loads((ATTEMPT / "invocation-envelope.json").read_text())
        if not root.is_relative_to(Path(envelope["scope"])):
            record["complete"] = False
            record["error"] = "fixture root is outside this attempt's exact owned scope"
            result["complete"] = False
            result["selectors"][selector] = record
            continue
        if root.exists():
            record["complete"] = False
            record["error"] = "fixture root remains after test"
            result["complete"] = False
            result["selectors"][selector] = record
            continue

        managed = re.findall(r"managed_pidfd_acquired pid=(\d+) start=(\d+) ppid=(\d+) pgid=(\d+)", log)
        if index == 1:
            leader = re.search(r"managed_normal_leader pid=(\d+) pgid=(\d+) esrch=true", log)
            children = re.search(r"managed_normal_worker_leaf worker_pid=(\d+) worker_esrch=true leaf_pid=(\d+) leaf_esrch=true", log)
            sentinel = re.search(r"managed_normal_sentinel pid=(\d+) live=true", log)
            if not (leader and children and sentinel):
                record["complete"] = False
                record["error"] = "normal managed-run lifecycle or sentinel readback missing"
                result["complete"] = False
                result["selectors"][selector] = record
                continue
            group = int(leader.group(2))
            pids = [int(leader.group(1)), int(children.group(1)), int(children.group(2))]
            sentinel_pid = int(sentinel.group(1))
            record["managed_pids"] = pids
            record["unrelated_sentinel_live_after_api_return"] = True
            sentinel_row = proc(sentinel_pid)
            if sentinel_row and sentinel_row.get("cmd") == [b"/bin/sleep", b"30"]:
                record["complete"] = False
                record["error"] = "fixture-owned sentinel remains live after test cleanup"
                result["complete"] = False
            else:
                record["fixture_sentinel_absent_after_owned_drop"] = True
        else:
            if len(managed) != 3:
                record["complete"] = False
                record["error"] = f"expected three exact PIDfd identity events, observed {len(managed)}"
                result["complete"] = False
                result["selectors"][selector] = record
                continue
            ids = [(int(pid), int(start_time), int(ppid), int(pgid)) for pid, start_time, ppid, pgid in managed]
            groups = {item[3] for item in ids}
            if len({item[0] for item in ids}) != 3 or len(groups) != 1 or ids[0][2] != test_pid:
                record["complete"] = False
                record["error"] = "PIDfd identities do not form one leader/worker/leaf fixture group"
                result["complete"] = False
                result["selectors"][selector] = record
                continue
            group = next(iter(groups))
            pids = [item[0] for item in ids]
            record["pidfd_identities"] = [{"pid": pid, "start": start_time, "ppid": ppid, "pgid": pgid} for pid, start_time, ppid, pgid in ids]
            if index == 2 and not re.search(r"managed_pidfd_acquired", log):
                record["complete"] = False
                record["error"] = "managed PIDfd readback missing"
                result["complete"] = False
            if index == 3 and not re.search(r"managed_pidfd_acquired", log):
                record["complete"] = False
                record["error"] = "direct control PIDfd readback missing"
                result["complete"] = False

        cleanup = re.search(r"managed_fixture_cleanup worker_pid=Some\((\d+)\) worker_esrch=true leaf_pid=Some\((\d+)\) leaf_esrch=true", log)
        leader_cleanup = re.search(r"managed_spawn_fixture_leader_cleanup leader_pid=Some\((\d+)\) leader_esrch=true", log)
        if not cleanup or not leader_cleanup:
            record["complete"] = False
            record["error"] = "fixture worker/leaf/leader cleanup readback missing"
            result["complete"] = False
        elif index != 1 and {int(cleanup.group(1)), int(cleanup.group(2)), int(leader_cleanup.group(1))} != set(pids):
            record["complete"] = False
            record["error"] = "fixture cleanup PIDs differ from acquired PIDfd identities"
            result["complete"] = False

        marker_env = f"RHAI_SYS_MANAGED_ROOT={root}".encode()
        hold_env = b"RHAI_SYS_MANAGED_SPAWN_HOLD=1"
        live_members = []
        for member in group_members(group):
            if member.get("unreadable"):
                record["complete"] = False
                record["error"] = f"cannot independently read process-group member {member['pid']}"
                result["complete"] = False
                continue
            live_members.append(member)
        if live_members:
            record["complete"] = False
            record["managed_group_members_remaining"] = [m["pid"] for m in live_members]
            record["managed_group_member_identities"] = [
                {"pid": m["pid"], "pgid": m.get("pgid"), "state": m.get("state"), "owned_marker": marker_env in m.get("env", []) and hold_env in m.get("env", [])}
                for m in live_members
            ]
            result["complete"] = False
        for pid in pids:
            row = proc(pid)
            if row and row.get("start") == next((x[1] for x in managed if int(x[0]) == pid), row.get("start")) and marker_env in row.get("env", []):
                record["complete"] = False
                record.setdefault("owned_pids_remaining", []).append(pid)
                result["complete"] = False
        record["managed_group_absent"] = not live_members
        record["complete"] = record.get("complete", True)
        result["selectors"][selector] = record
    return result


for phase in ("red", "green"):
    try:
        result = phase_readback(phase)
    except Exception as exc:
        result = {"complete": False, "error": f"observer exception: {type(exc).__name__}: {exc}"}
    receipt["phases"][phase] = result
    if not result.get("complete"):
        receipt["complete"] = False

out = ATTEMPT / "post-run-cleanup-readback.json"
out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps(receipt, sort_keys=True))
if not receipt["complete"]:
    raise SystemExit(2)
