"""One-case Linux managed-zombie boundary proof at the locked Rust 1.77.2 MSRV."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback

REVISION = "257edf695f953271adf17b12dcc70c4287ae76b5"
ARCHIVE_SHA256 = "ea085b4d28ee5ce3c7b998044242a50c755d9e9252638dbcf28c036b3df7c922"
LOCK_SHA256 = "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425"
BASE_SHA256 = "59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06"
TEST_SHA256 = "8ec4d456672338920249446618ce768bc2fa1d29798d571dca1e897db87a076b"
TEST = "managed_run_reports_while_fixture_reaper_holds_stopped_zombies"
FEATURES = "testing-environ,sys"
STAGE_PATH = Path("/root/rhai-linux-managed-zombie-20261003-257edf69-94")
SCOPE_PATH = Path("/root/.local/share/agent-builds/rhai/linux-managed-zombie-20261003-257edf69-94")
BASE = None


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_base(stage: Path):
    path = stage / "check-linux-current-msrv-examples.py"
    if sha(path) != BASE_SHA256:
        raise RuntimeError("accepted Linux base helper hash mismatch")
    spec = importlib.util.spec_from_file_location("accepted_linux_msrv_base", path)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load accepted Linux base helper")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def overlay(original: bytes, control: str) -> bytes:
    text = original.decode("utf-8")
    anchor = '    eprintln!("managed_held_zombie_cleanup worker={} reaped=true leaf={} reaped=true", worker_fields["pid"], leaf_fields["pid"]);'
    if text.count(anchor) != 1:
        raise RuntimeError(f"cleanup receipt anchor is not unique: {text.count(anchor)}")
    if control == "require-success-while-held":
        assertion = '    assert!(api_result.contains("api_outcome=success_report"), "managed-zombie-control require-success assertion");\n'
    elif control == "require-exit-seven":
        assertion = '    assert!(api_result.contains("exit=Some(7)"), "managed-zombie-control require-exit-seven assertion");\n'
    else:
        raise RuntimeError(f"unknown managed-zombie control: {control}")
    return text.replace(anchor, anchor + "\n" + assertion.rstrip("\n"), 1).encode("utf-8")


def command_output(h, name: str) -> str:
    return h.read_text(h.STAGE / f"{name}.stdout") + h.read_text(h.STAGE / f"{name}.stderr")


def cargo_test(cargo: Path) -> list[str]:
    return [str(cargo), "test", "--locked", "--features", FEATURES,
            "--test", "sys_process", TEST, "--", "--exact", "--nocapture",
            "--test-threads=1"]


def exact_boundary(output: str) -> tuple[list[tuple[str, int, str]], int, list[dict[str, int]]]:
    pattern = re.compile(
        r"managed_held_zombie_boundary host_live_at_return=true "
        r"leader=(\d+) leader_start=(\d+) leader_reaped=true "
        r"worker=(\d+) worker_start=(\d+) worker_state=Z worker_pgid=(\d+) "
        r"leaf=(\d+) leaf_start=(\d+) leaf_state=Z leaf_pgid=(\d+) group=(\d+) "
        r".*?capture_complete=true host=(\d+) host_start=(\d+) "
        r"api_success=false api_outcome=typed_process_io "
        r"cause_op=observe_process_group_closure cause_op_matches=true kind=TimedOut exit=Some\(0\) "
        r"stdout_complete=true stderr_complete=true diagnostic=true cause_details=.*? cleanup_diagnostics=.*?\s+held=\"pid=(\d+) start=(\d+) host_status=(\d+) "
        r"worker=Some\((\d+)\) worker_start=Some\((\d+)\) "
        r"leaf=Some\((\d+)\) leaf_start=Some\((\d+)\) held_zombies=true\\n\" "
        r"reaper_status=ExitStatus\(unix_wait_status\(0\)\)", re.DOTALL)
    match = pattern.search(output)
    if not match:
        raise RuntimeError("exact managed-zombie boundary, held-reaper, typed timeout, direct exit, or successful cleanup status receipt missing")
    values = list(map(int, match.groups()))
    (leader, leader_start, worker, worker_start, worker_pgid, leaf, leaf_start,
     leaf_pgid, group, host, host_start, reaper, reaper_start, host_status,
     held_worker, held_worker_start, held_leaf, held_leaf_start) = values
    if len({leader, worker, leaf}) != 3 or len({leader, group, worker_pgid, leaf_pgid}) != 1:
        raise RuntimeError("leader/worker/leaf identities must be distinct members of the exact leader process group")
    if host_status != 0 or (held_worker, held_worker_start, held_leaf, held_leaf_start) != (worker, worker_start, leaf, leaf_start):
        raise RuntimeError("fixture reaper held record does not match the exact successful host/worker/leaf identities")
    cleanup = re.search(
        r"managed_held_zombie_cleanup worker=(\d+) reaped=true leaf=(\d+) reaped=true", output)
    if not cleanup or tuple(map(int, cleanup.groups())) != (worker, leaf):
        raise RuntimeError("fixture cleanup receipt does not name the exact held worker and leaf")
    acquired = re.findall(r"managed_pidfd_acquired pid=(\d+) start=(\d+) ppid=(\d+) pgid=(\d+)", output)
    if len(acquired) != 3:
        raise RuntimeError(f"expected exactly three managed pidfd identity receipts, got {len(acquired)}")
    pidfds = {int(pid): (int(start), int(ppid), int(pgid)) for pid, start, ppid, pgid in acquired}
    expected = {
        leader: (leader_start, host, group),
        worker: (worker_start, leader, worker_pgid),
        leaf: (leaf_start, worker, leaf_pgid),
    }
    if set(pidfds) != set(expected):
        raise RuntimeError("acquired pidfd PID set differs from boundary leader/worker/leaf")
    for pid, facts in expected.items():
        if pidfds[pid] != facts:
            raise RuntimeError(f"acquired pidfd identity disagrees with exact boundary for pid={pid}: {pidfds[pid]} != {facts}")
    identities = [("leader", leader, str(leader_start)), ("worker", worker, str(worker_start)),
                  ("leaf", leaf, str(leaf_start)), ("host", host, str(host_start)),
                  ("fixture-reaper", reaper, str(reaper_start))]
    pidfd_rows = sorted(
        ({"pid": pid, "start_ticks": fields[0], "ppid": fields[1], "pgid": fields[2]}
         for pid, fields in pidfds.items()), key=lambda row: row["pid"])
    return identities, group, pidfd_rows

def alive_at_start(pid: int, start: str) -> bool | None:
    try:
        raw = Path("/proc", str(pid), "stat").read_text(encoding="ascii")
        fields = raw[raw.rfind(")") + 2:].split()
        return fields[19] == start
    except (FileNotFoundError, ProcessLookupError):
        return False
    except (PermissionError, OSError, IndexError, ValueError):
        return None


def verify_cleanup(output: str, h, label: str) -> None:
    identities, group, pidfds = exact_boundary(output)
    rows = []
    for name, pid, start in identities:
        present = alive_at_start(pid, start)
        if present is None or present:
            raise RuntimeError(f"fixture identity not independently absent after cleanup: {name} pid={pid} start={start} present={present}")
        rows.append({"label": name, "pid": pid, "start_ticks": start, "matching_identity_alive": False})
    ps = subprocess.check_output(["/bin/ps", "-e", "-o", "pid=,pgid="], text=True, timeout=5)
    group_members = []
    for line in ps.splitlines():
        fields = line.split()
        if len(fields) == 2 and int(fields[1]) == group:
            group_members.append((int(fields[0]), int(fields[1])))
    if group_members:
        raise RuntimeError(f"managed fixture group still has process members: {group_members!r}")
    h.write_json(h.STAGE / f"{label}-fixture-closure.json", {
        "fixture_pid_start_identities": rows, "fixture_group": group,
        "fixture_group_members_after_cleanup": group_members,
        "managed_pidfd_acquired_identities": pidfds,
        "cleanup_receipt_required": "managed_held_zombie_cleanup worker=... reaped=true leaf=... reaped=true",
        "test_watchdog_receipt_required": "reaper_status=ExitStatus(unix_wait_status(0))",
    })


def main() -> int:
    global BASE
    input_stage = Path(os.environ["PROOF_STAGE"])
    runtime = Path(os.environ["AGENT_RUNTIME_DIR"])
    BASE = load_base(input_stage)
    signal.signal(signal.SIGTERM, BASE.on_signal)
    signal.signal(signal.SIGINT, BASE.on_signal)
    BASE.INPUT_STAGE = input_stage
    BASE.EXPECTED_STAGE = Path(os.environ["EXPECTED_PROOF_STAGE"])
    BASE.PRESCRIBED_STAGE = STAGE_PATH
    BASE.PRESCRIBED_SCOPE = SCOPE_PATH
    BASE.RUNTIME = runtime
    BASE.STAGE = runtime / "evidence"
    BASE.EVIDENCE = input_stage / "proof-evidence"
    BASE.CONTRACT = input_stage / "contract.md"
    BASE.SOURCE_ARCHIVE = input_stage / "source.tar"
    BASE.LOCK_SOURCE = input_stage / "Cargo.lock.accepted"
    BASE.RUSTUP = Path(os.environ["RUSTUP_BIN"])
    BASE.SOURCE_ARCHIVE_SHA256 = ARCHIVE_SHA256
    BASE.LOCK_SHA256 = LOCK_SHA256
    BASE.REVISION = REVISION
    BASE.TOOLCHAIN = "1.77.2-x86_64-unknown-linux-gnu"
    BASE.START = time.monotonic()
    BASE.DEADLINE = BASE.START + 540
    BASE.WORK_DEADLINE = BASE.DEADLINE - 30
    BASE.SOURCE = runtime / "source"
    BASE.CARGO_HOME = runtime / "cargo-home"
    BASE.RUSTUP_HOME = runtime / "rustup-home"
    BASE.TARGET = runtime / "target"
    BASE.PRIVATE_HOME = runtime / "home"
    BASE.PRIVATE_TMP = Path(os.environ["TMPDIR"])
    BASE.capture_runtime_proof()
    BASE.validate_stage_inputs()
    if platform.system() != "Linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        raise RuntimeError("native Linux x86_64 required")
    BASE.write_json(BASE.STAGE / "source-inputs.json", {
        "revision": REVISION, "archive_sha256": sha(BASE.SOURCE_ARCHIVE),
        "lock_sha256": sha(BASE.LOCK_SOURCE), "base_helper_sha256": BASE_SHA256,
        "test_file_sha256": TEST_SHA256, "test": TEST, "features": FEATURES,
    })
    for folder in (BASE.CARGO_HOME, BASE.RUSTUP_HOME, BASE.PRIVATE_HOME):
        folder.mkdir(mode=0o700)
    BASE.PRIVATE_TMP.mkdir(mode=0o700, exist_ok=True)
    env = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(BASE.PRIVATE_HOME),
        "TMPDIR": str(BASE.PRIVATE_TMP), "TMP": str(BASE.PRIVATE_TMP), "TEMP": str(BASE.PRIVATE_TMP),
        "CARGO_HOME": str(BASE.CARGO_HOME), "RUSTUP_HOME": str(BASE.RUSTUP_HOME),
        "CARGO_TARGET_DIR": str(BASE.TARGET), "CARGO_BUILD_JOBS": "2",
        "CARGO_INCREMENTAL": "0", "CARGO_PROFILE_DEV_DEBUG": "0",
        "CARGO_TERM_COLOR": "never", "RUST_BACKTRACE": "0",
        "AGENT_RUNTIME_DIR": str(runtime),
    }
    BASE.extract_archive(BASE.SOURCE_ARCHIVE)
    shutil.copy2(BASE.LOCK_SOURCE, BASE.SOURCE / "Cargo.lock")
    manifests = BASE.manifest_hashes()
    BASE.write_json(BASE.STAGE / "source-lock-manifests.json", {
        "revision": REVISION, "manifests_sha256": manifests,
        "lock_sha256": sha(BASE.SOURCE / "Cargo.lock"),
    })
    BASE.run_command("rustup-install", [str(BASE.RUSTUP), "toolchain", "install", BASE.TOOLCHAIN,
                                         "--profile", "minimal", "--no-self-update"], env, cwd=runtime)
    bin_dir = BASE.RUSTUP_HOME / "toolchains" / BASE.TOOLCHAIN / "bin"
    rustc, cargo = bin_dir / "rustc", bin_dir / "cargo"
    if not rustc.is_file() or not cargo.is_file():
        raise RuntimeError("private Rust 1.77.2 toolchain incomplete")
    env["PATH"] = f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin"
    env["RUSTC"] = str(rustc)
    BASE.run_command("rustc-version", [str(rustc), "--version", "--verbose"], env)
    BASE.run_command("cargo-version", [str(cargo), "--version", "--verbose"], env)
    test_path = BASE.SOURCE / "tests/sys_process.rs"
    original = test_path.read_bytes()
    if hashlib.sha256(original).hexdigest() != TEST_SHA256:
        raise RuntimeError("frozen managed-zombie test source hash mismatch")
    BASE.ORIGINAL_EXAMPLES[test_path] = original
    BASE.ORIGINAL_EXAMPLE_HASHES["tests/sys_process.rs"] = TEST_SHA256
    controls = (
        ("require-success-while-held", "managed-zombie-control require-success assertion"),
        ("require-exit-seven", "managed-zombie-control require-exit-seven assertion"),
    )
    invocations = []
    for control, diagnostic in controls:
        try:
            changed = overlay(original, control)
            test_path.write_bytes(changed)
            injected_hash = sha(test_path)
            BASE.INJECTED_EXAMPLE_HASHES[control] = injected_hash
            BASE.run_command(control, cargo_test(cargo), env, expected_status=101)
            output = command_output(BASE, control)
            verify_cleanup(output, BASE, control)
            expected = [f"test {TEST} ... FAILED", diagnostic,
                        "managed_held_zombie_boundary", "api_outcome=typed_process_io",
                        "kind=TimedOut exit=Some(0)", "stdout_complete=true stderr_complete=true diagnostic=true",
                        "managed_held_zombie_cleanup", "reaper_status=ExitStatus(unix_wait_status(0))",
                        "test result: FAILED. 0 passed; 1 failed;"]
            BASE.verify_control(control, 101, 101, output, expected)
            invocations.append({"name": control, "status": 101, "overlay_sha256": injected_hash,
                                "intended_assertion": diagnostic, "boundary_and_cleanup_precede_assertion": True})
        finally:
            test_path.write_bytes(original)
        if sha(test_path) != TEST_SHA256:
            raise RuntimeError(f"test source restoration failed after {control}")
    BASE.run_command("managed-zombie-green", cargo_test(cargo), env)
    green = command_output(BASE, "managed-zombie-green")
    verify_cleanup(green, BASE, "green")
    green_required = (f"test {TEST} ... ok", "test result: ok. 1 passed; 0 failed; 0 ignored;")
    if any(item not in green for item in green_required):
        raise RuntimeError(f"exact managed-zombie positive test did not pass: {green_required!r}")
    BASE.verify_pass("managed-zombie-green", 0, green, green_required[1])
    if sha(test_path) != TEST_SHA256 or BASE.manifest_hashes() != manifests or sha(BASE.SOURCE / "Cargo.lock") != LOCK_SHA256:
        raise RuntimeError("test source, Cargo manifests, or accepted lock did not restore unchanged")
    BASE.write_json(BASE.STAGE / "package-result.json", {
        "revision": REVISION, "archive_sha256": ARCHIVE_SHA256,
        "compatible_lock_sha256": LOCK_SHA256, "test_file_sha256": TEST_SHA256,
        "test": TEST, "features": FEATURES, "positive_exact_invocations": 1,
        "negative_controls": invocations, "helper_commands_expected": 6,
        "source_restored": True, "manifests_and_lock_unchanged": True,
        "acceptance_claim": False,
        "limitations": ["One Linux feature row and one managed zombie boundary only; no general process-ticket or release closure."],
    })
    return 0


def export_evidence() -> None:
    if BASE is None or not BASE.STAGE.is_dir() or BASE.EVIDENCE.exists():
        return
    BASE.check_deadline(during_export=True)
    restoration_error = None
    try:
        if BASE.ORIGINAL_EXAMPLES:
            BASE.restore_example_sources()
    except BaseException:
        restoration_error = traceback.format_exc()
        (BASE.STAGE / "restoration-failure.txt").write_text(restoration_error)
    BASE.write_json(BASE.STAGE / "source-restoration.json", {
        "original_test_sha256": BASE.ORIGINAL_EXAMPLE_HASHES,
        "injected_overlay_sha256": BASE.INJECTED_EXAMPLE_HASHES,
        "restored_test_matches_original": bool(BASE.ORIGINAL_EXAMPLES) and all(
            BASE.sha256(path) == BASE.ORIGINAL_EXAMPLE_HASHES[path.relative_to(BASE.SOURCE).as_posix()]
            for path in BASE.ORIGINAL_EXAMPLES
        ), "restoration_error": restoration_error,
    })
    BASE.write_json(BASE.STAGE / "package-result.json", {
        "revision": REVISION, "test": TEST, "features": FEATURES,
        "expected_controls": 2, "observed_commands": BASE.CONTROL_RESULTS,
        "all_commands_passed": len(BASE.CONTROL_RESULTS) == 3 and all(
            item.get("status") == item.get("expected_status") for item in BASE.CONTROL_RESULTS),
        "source_restored": bool(BASE.ORIGINAL_EXAMPLES) and all(
            BASE.sha256(path) == BASE.ORIGINAL_EXAMPLE_HASHES[path.relative_to(BASE.SOURCE).as_posix()]
            for path in BASE.ORIGINAL_EXAMPLES),
        "acceptance_claim": False, "restoration_error": restoration_error,
    })
    BASE.write_json(BASE.STAGE / "export.json", {
        "runtime": str(BASE.RUNTIME), "scope": str(BASE.RUNTIME.parent),
        "destination": str(BASE.EVIDENCE), "elapsed_seconds_at_export": round(time.monotonic() - BASE.START, 3),
        "export_reserve_seconds": 30,
    })
    BASE.EVIDENCE.mkdir(mode=0o700)
    for item in BASE.STAGE.iterdir():
        BASE.check_deadline(during_export=True)
        target = BASE.EVIDENCE / item.name
        shutil.copytree(item, target) if item.is_dir() else shutil.copy2(item, target)
    if restoration_error:
        raise RuntimeError("private test source restoration failed")


if __name__ == "__main__":
    status = 1
    try:
        status = main()
    except BaseException as exc:
        if BASE is not None and BASE.STAGE.is_dir():
            (BASE.STAGE / "failure.txt").write_text("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        traceback.print_exc()
        status = 1
    finally:
        try:
            export_evidence()
        except BaseException:
            traceback.print_exc()
            status = 1
    raise SystemExit(status)
