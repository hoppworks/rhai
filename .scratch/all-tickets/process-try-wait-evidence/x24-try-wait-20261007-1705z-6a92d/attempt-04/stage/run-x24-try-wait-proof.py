#!/usr/bin/env python3
"""Run one bounded Linux X24 restored-GREEN MSRV acceptance using pinned sensitivity proof."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import tarfile
import time


HELPER_STARTED = time.monotonic()
SCOPE = Path(os.environ["SESSION_SCOPE"]).resolve(strict=True)
STAGE = SCOPE / "stage"
ATTEMPT_ID = os.environ.get("ATTEMPT_ID", "attempt-04")
if not re.fullmatch(r"attempt-[0-9]{2}", ATTEMPT_ID):
    raise RuntimeError("ATTEMPT_ID must be a two-digit attempt label")
OUT = SCOPE / "out" / ATTEMPT_ID
RUNTIME = Path(os.environ["AGENT_RUNTIME_DIR"]).resolve(strict=True)
SOURCE = RUNTIME / "source"
RUNNER = Path("/home/workhorse/projects/agent-skills/tools/run_scoped.py")
LOCK_SHA = "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425"
TEST_NAME = "direct_spawn_try_wait_returns_unit_until_child_exits"
FEATURES = "testing-environ,sys"
TOOLCHAIN = Path("/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin")
COMMAND = [str(TOOLCHAIN / "cargo"), "test", "--locked", "--features", FEATURES, "--test", "sys_process",
           TEST_NAME, "--", "--exact", "--nocapture", "--test-threads=1"]
WORK_SECONDS = 510
HELPER_SECONDS = 540
RUNNER_SECONDS = 585
EXPORT_RESERVE_SECONDS = HELPER_SECONDS - WORK_SECONDS
STORAGE_PREEMPTIVE_KIB = 1_572_864
STORAGE_HARD_KIB = 2 * 1024 * 1024
RSS_HARD_KIB = 2 * 1024 * 1024
MAX_OWNED_PROCESSES = 16
SAMPLER_RETRIES: list[dict[str, object]] = []


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def proc_rows() -> list[dict[str, int]]:
    rows: list[dict[str, int]] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            raw = (entry / "stat").read_text(encoding="ascii")
            fields = raw[raw.rfind(")") + 2:].split()
            ppid, pgid, start = int(fields[1]), int(fields[2]), int(fields[19])
            status = (entry / "status").read_text(encoding="ascii")
            rss_line = next((line for line in status.splitlines() if line.startswith("VmRSS:")), "VmRSS: 0 kB")
            rss_kib = int(rss_line.split()[1])
            rows.append({"pid": pid, "ppid": ppid, "pgid": pgid, "start_ticks": start, "rss_kib": rss_kib})
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        except (IndexError, ValueError) as exc:
            raise RuntimeError(f"cannot parse live /proc identity for PID {pid}: {exc}") from exc
    return rows


def runtime_storage_kib() -> int:
    for attempt in range(2):
        result = subprocess.run(["du", "-sk", str(RUNTIME)], capture_output=True, text=True,
                                timeout=5, check=False)
        if result.returncode != 0:
            diagnostics = [line for line in result.stderr.splitlines() if line.strip()]
            vanished_paths_only = bool(diagnostics) and all(
                "No such file or directory" in line for line in diagnostics
            )
            if (attempt == 0 and result.returncode == 1 and vanished_paths_only
                    and RUNTIME.is_dir()):
                event = {
                    "utc_epoch": time.time(),
                    "command": ["du", "-sk", str(RUNTIME)],
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "retry_reason": "du encountered only paths removed during the concurrent build",
                }
                SAMPLER_RETRIES.append(event)
                with (OUT / "runtime-storage-retries.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(event, sort_keys=True) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                continue
            raise RuntimeError(
                f"du private-runtime sample failed: status={result.returncode}; "
                f"stdout={result.stdout!r}; stderr={result.stderr!r}"
            )
        fields = result.stdout.strip().split(maxsplit=1)
        if len(fields) != 2 or fields[1] != str(RUNTIME) or not fields[0].isdigit():
            raise RuntimeError(f"malformed private-runtime size sample: {result.stdout!r}")
        return int(fields[0])
    raise RuntimeError("du private-runtime sample remained incomplete after one ENOENT retry")


def owned_tree(root_pid: int, known: dict[int, int]) -> list[dict[str, int]]:
    rows = proc_rows()
    by_pid = {row["pid"]: row for row in rows}
    active = {root_pid}
    selected: dict[int, dict[str, int]] = {}
    changed = True
    while changed:
        changed = False
        for row in rows:
            if row["pid"] in active or row["ppid"] in active:
                if row["pid"] not in active:
                    active.add(row["pid"])
                    changed = True
                selected[row["pid"]] = row
    for pid, start in known.items():
        row = by_pid.get(pid)
        if row is not None and row["start_ticks"] == start:
            selected[pid] = row
    return list(selected.values())


def signal_owned(identities: dict[int, int], signum: int) -> None:
    if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
        raise RuntimeError("pidfd signaling is unavailable; refusing PID-based cleanup")
    rows = {row["pid"]: row for row in proc_rows()}
    for pid, start_ticks in identities.items():
        row = rows.get(pid)
        if row is None or row["start_ticks"] != start_ticks:
            continue
        try:
            fd = os.pidfd_open(pid, 0)
        except ProcessLookupError:
            continue
        try:
            current = next((item for item in proc_rows() if item["pid"] == pid), None)
            if current is not None and current["start_ticks"] == start_ticks:
                try:
                    signal.pidfd_send_signal(fd, signum)
                except ProcessLookupError:
                    pass
        finally:
            os.close(fd)


def stop_owned(root_pid: int, known: dict[int, int]) -> None:
    for row in owned_tree(root_pid, known):
        known[row["pid"]] = row["start_ticks"]
    signal_owned(known, signal.SIGTERM)
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        remaining = owned_tree(root_pid, known)
        if not remaining:
            return
        for row in remaining:
            known[row["pid"]] = row["start_ticks"]
        signal_owned(known, signal.SIGTERM)
        time.sleep(0.1)
    remaining = owned_tree(root_pid, known)
    for row in remaining:
        known[row["pid"]] = row["start_ticks"]
    signal_owned(known, signal.SIGKILL)


def run_case(label: str, *, deadline: float, samples: list[dict[str, object]],
             expected_status: int, diagnostic: str | None = None) -> dict[str, object]:
    stdout_path, stderr_path = OUT / f"{label}.stdout", OUT / f"{label}.stderr"
    started = time.monotonic()
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        process = subprocess.Popen(COMMAND, cwd=SOURCE, env=ENV, stdout=stdout, stderr=stderr)
        first = next((row for row in proc_rows() if row["pid"] == process.pid), None)
        if first is None or first["ppid"] != os.getpid():
            process.terminate()
            raise RuntimeError("Cargo process identity was not captured under the proof helper")
        known = {process.pid: first["start_ticks"]}
        while process.poll() is None:
            now = time.monotonic()
            if now >= deadline:
                stop_owned(process.pid, known)
                process.wait(timeout=10)
                raise TimeoutError(f"{label} exceeded the aggregate Cargo work deadline")
            rows = owned_tree(process.pid, known)
            for row in rows:
                known[row["pid"]] = row["start_ticks"]
            storage_kib = runtime_storage_kib()
            rss_kib = sum(row["rss_kib"] for row in rows)
            sample = {"utc_epoch": time.time(), "case": label,
                      "root_pid": process.pid, "members": rows, "owned_process_count": len(rows),
                      "sampled_rss_kib": rss_kib, "runtime_storage_kib": storage_kib}
            samples.append(sample)
            with (OUT / "resource-samples.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(sample, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            if len(rows) > MAX_OWNED_PROCESSES:
                stop_owned(process.pid, known)
                process.wait(timeout=10)
                raise RuntimeError(f"{label} exceeded {MAX_OWNED_PROCESSES} owned processes")
            if storage_kib >= STORAGE_PREEMPTIVE_KIB or storage_kib >= STORAGE_HARD_KIB:
                stop_owned(process.pid, known)
                process.wait(timeout=10)
                raise RuntimeError(f"{label} reached the sampled private storage stop at {storage_kib} KiB")
            if rss_kib >= RSS_HARD_KIB:
                stop_owned(process.pid, known)
                process.wait(timeout=10)
                raise RuntimeError(f"{label} reached the sampled private RSS cap at {rss_kib} KiB")
            time.sleep(0.8)
        remaining = owned_tree(process.pid, known)
        if remaining:
            for row in remaining:
                known[row["pid"]] = row["start_ticks"]
            stop_owned(process.pid, known)
            raise RuntimeError(f"{label} returned while owned processes were still live")
    elapsed = round(time.monotonic() - started, 3)
    status = process.returncode
    (OUT / f"{label}.status").write_text(f"{status}\n", encoding="ascii")
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    combined = stdout_text + "\n" + stderr_text
    if status != expected_status:
        raise RuntimeError(f"{label} returned {status}, expected {expected_status}; see captured outputs")
    if diagnostic is not None and diagnostic not in combined:
        raise RuntimeError(f"{label} missed the intended assertion diagnostic {diagnostic!r}")
    if f"test {TEST_NAME} ... {'FAILED' if expected_status else 'ok'}" not in stdout_text:
        raise RuntimeError(f"{label} output lacks the exact selected test result")
    independent_readback = None
    if label == "restored-green":
        running = re.search(r"x24_running pid=(\d+) alive_before_try_wait=true result_is_unit=true", combined)
        post_exit = re.search(r"x24_post_exit_try_wait pid=(\d+) result_observed_before_wait=true code=0 success=true", combined)
        finished = re.search(r"x24_finished pid=(\d+) wait_code=0 try_wait_code=0 success=true reaped_esrch=true", combined)
        if running is None or post_exit is None or finished is None or not (running.group(1) == post_exit.group(1) == finished.group(1)):
            raise RuntimeError("GREEN output lacks matching pending, direct post-exit try_wait, and reaping read-back")
        independent_readback = {
            "pid": int(running.group(1)),
            "alive_before_try_wait": True,
            "pending_try_wait_is_unit": True,
            "wait_exit_code": 0,
            "terminal_try_wait_exit_code": 0,
            "terminal_try_wait_observed_before_wait": True,
            "wait_returned_cached_result": True,
            "reaped_esrch": True,
        }
    return {"case": label, "status": status, "elapsed_seconds": elapsed,
            "stdout_sha256": sha(stdout_path), "stderr_sha256": sha(stderr_path),
            "diagnostic": diagnostic, "independent_readback": independent_readback}


if platform.system() != "Linux" or platform.machine() != "x86_64":
    raise RuntimeError("this proof is scoped to Workhorse Linux x86_64")
if not STAGE.is_dir() or STAGE.is_symlink() or OUT.exists() or OUT.is_symlink():
    raise RuntimeError("the owned source stage must exist and this attempt output must be new")
if not RUNTIME.is_absolute() or not RUNTIME.is_dir():
    raise RuntimeError("run_scoped did not supply an absolute private runtime")

pins = json.loads((STAGE / "input-identities.json").read_text(encoding="utf-8"))
for name, expected in pins["files"].items():
    path = STAGE / name
    if path.is_symlink() or not path.is_file() or sha(path) != expected:
        raise RuntimeError(f"staged input identity mismatch: {name}")
if sha(RUNNER) != pins["runner_sha256"]:
    raise RuntimeError("canonical run_scoped.py changed after preflight")
if pins["files"]["Cargo.lock.accepted"] != LOCK_SHA:
    raise RuntimeError("the accepted Cargo.lock identity differs from the recorded baseline")
if sha(STAGE / "source.commit") != pins["files"]["source.commit"]:
    raise RuntimeError("source revision marker hash mismatch")
if (STAGE / "source.commit").read_text().strip() != pins["source_revision"]:
    raise RuntimeError("source revision marker does not match input manifest")
if sha(STAGE / "source-manifest.json") != pins["files"]["source-manifest.json"]:
    raise RuntimeError("source manifest hash mismatch")

OUT.mkdir(mode=0o700)
sample_path = OUT / "resource-samples.jsonl"
sample_path.write_text("", encoding="utf-8")
SOURCE.mkdir()
source_archive = STAGE / "source.tar.gz"
with tarfile.open(source_archive, "r:gz") as archive:
    archive.extractall(SOURCE)
source_manifest = json.loads((STAGE / "source-manifest.json").read_text(encoding="utf-8"))
if source_manifest["base_commit"] != pins["source_revision"]:
    raise RuntimeError("source archive base revision does not match")
if source_manifest["archive_sha256"] != pins["files"]["source.tar.gz"]:
    raise RuntimeError("source archive manifest hash mismatch")
archive_test_sha = next((item["sha256"] for item in source_manifest["files"]
                         if item["path"] == "tests/sys_process.rs"), None)
if archive_test_sha is None or sha(SOURCE / "tests/sys_process.rs") != archive_test_sha:
    raise RuntimeError("the archived test source does not match its frozen source manifest")
if sha(SOURCE / "tests/sys_process.rs") != pins["test_source_sha256"]:
    raise RuntimeError("the frozen source archive test does not match its pinned identity")
sensitivity = json.loads((STAGE / "sensitivity-control.json").read_text(encoding="utf-8"))
if (sensitivity["test_source_sha256"] != pins["test_source_sha256"]
        or sensitivity["mutant_red_status"] != 101
        or sensitivity["restored_green_status"] != 0
        or "try_wait after child exit must return a result, got ()" not in sensitivity["mutant_red_diagnostic"]):
    raise RuntimeError("the reused X24 assertion sensitivity result does not match this test source")
shutil.copy2(STAGE / "Cargo.lock.accepted", SOURCE / "Cargo.lock")
if sha(SOURCE / "Cargo.lock") != LOCK_SHA:
    raise RuntimeError("the accepted lockfile did not stage exactly")

ENV = os.environ.copy()
ENV.pop("RUSTUP_TOOLCHAIN", None)
ENV.pop("RUSTUP_HOME", None)
ENV.update({
    "PATH": str(TOOLCHAIN) + ":/usr/bin:/bin",
    "RUSTC": str(TOOLCHAIN / "rustc"),
    "RUSTDOC": str(TOOLCHAIN / "rustdoc"),
    "CARGO_TARGET_DIR": str(RUNTIME / "target"),
    "CARGO_HOME": str(RUNTIME / "cargo-home"),
    "CARGO_BUILD_JOBS": "2",
})
(RUNTIME / "target").mkdir()
(RUNTIME / "cargo-home").mkdir()
versions = {
    "rustc": subprocess.run(["rustc", "--version"], env=ENV, text=True, capture_output=True,
                             check=True, timeout=10).stdout.strip(),
    "cargo": subprocess.run(["cargo", "--version"], env=ENV, text=True, capture_output=True,
                             check=True, timeout=10).stdout.strip(),
}
if "1.77.2" not in versions["rustc"] or "1.77.2" not in versions["cargo"]:
    raise RuntimeError(f"unexpected pinned toolchain versions: {versions}")

source_path = SOURCE / "tests/sys_process.rs"
original = source_path.read_bytes()
original_sha = hashlib.sha256(original).hexdigest()
if original_sha != pins["test_source_sha256"]:
    raise RuntimeError("the X24 test source differs from its frozen revision")
manifest = {
    "source_revision": pins["source_revision"],
    "source_archive_sha256": pins["files"]["source.tar.gz"],
    "test_source_sha256": original_sha,
    "lock_sha256": LOCK_SHA,
    "test": f"tests/sys_process.rs::{TEST_NAME}",
    "features": FEATURES,
    "command": COMMAND,
    "toolchain": versions,
    "cargo_jobs": 2,
    "runner_sha256": pins["runner_sha256"],
    "sensitivity_control_reused": sensitivity,
    "limits": {"helper_seconds": HELPER_SECONDS, "work_seconds": WORK_SECONDS,
                "runner_seconds": RUNNER_SECONDS,
                "export_reserve_seconds": EXPORT_RESERVE_SECONDS,
                "storage_preemptive_kib": STORAGE_PREEMPTIVE_KIB,
                "storage_hard_kib": STORAGE_HARD_KIB, "rss_hard_kib": RSS_HARD_KIB,
                "max_owned_processes": MAX_OWNED_PROCESSES},
}
write_json(OUT / "run-manifest.json", manifest)

started = HELPER_STARTED
work_deadline = started + WORK_SECONDS
samples: list[dict[str, object]] = []
results: list[dict[str, object]] = []
results.append(run_case("restored-green", deadline=work_deadline, samples=samples,
                        expected_status=0))
if sha(source_path) != original_sha:
    raise RuntimeError("frozen test source changed during GREEN")
if time.monotonic() >= started + HELPER_SECONDS:
    raise TimeoutError("the bounded helper budget, including export reserve, was exhausted")
if sha(source_path) != original_sha:
    raise RuntimeError("private product source changed during GREEN")

result = {
    "cases": results,
    "source_restored": True,
    "aggregate_elapsed_seconds": round(time.monotonic() - started, 3),
    "samples_are_periodic_not_continuous_peaks": True,
    "runtime_storage_sample_retries": SAMPLER_RETRIES,
    "sampled_max_rss_kib": max((int(row["sampled_rss_kib"]) for row in samples), default=0),
    "sampled_max_storage_kib": max((int(row["runtime_storage_kib"]) for row in samples), default=0),
    "sampled_max_owned_processes": max((int(row["owned_process_count"]) for row in samples), default=0),
    "acceptance_scope": "Workhorse Linux x86_64, Rust/Cargo 1.77.2, testing-environ,sys only",
    "sensitivity_control_reused": sensitivity,
    "independent_readback": results[-1]["independent_readback"],
}
write_json(OUT / "proof-result.json", result)
hashes = []
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name != "SHA256SUMS":
        hashes.append(f"{sha(path)}  {path.name}\n")
(OUT / "SHA256SUMS").write_text("".join(hashes), encoding="ascii")
print(json.dumps(result, sort_keys=True), flush=True)
