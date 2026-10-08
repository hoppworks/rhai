#!/usr/bin/env python3
"""Run one bounded Linux env_remove sensitivity and acceptance pair."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import tarfile
import time


HELPER_STARTED = time.monotonic()
SCOPE = Path(os.environ["SESSION_SCOPE"]).resolve(strict=True)
STAGE = SCOPE / "stage"
OUT = SCOPE / "out"
RUNTIME = Path(os.environ["AGENT_RUNTIME_DIR"]).resolve(strict=True)
SOURCE = RUNTIME / "source"
RUNNER = Path("/home/workhorse/projects/agent-skills/tools/run_scoped.py")
LOCK_SHA = "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425"
TEST_NAME = "run_removes_inherited_environment_variable_from_public_child"
FEATURES = "testing-environ,sys"
COMMAND = ["cargo", "test", "--locked", "--features", FEATURES, "--test", "sys_process",
           TEST_NAME, "--", "--exact", "--nocapture", "--test-threads=1"]
WORK_SECONDS = 510
HELPER_SECONDS = 540
EXPORT_RESERVE_SECONDS = HELPER_SECONDS - WORK_SECONDS
STORAGE_PREEMPTIVE_KIB = 1_572_864
STORAGE_HARD_KIB = 2 * 1024 * 1024
RSS_HARD_KIB = 2 * 1024 * 1024
MAX_OWNED_PROCESSES = 16


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
    result = subprocess.run(["du", "-sk", str(RUNTIME)], capture_output=True, text=True,
                            timeout=5, check=True)
    fields = result.stdout.strip().split(maxsplit=1)
    if len(fields) != 2 or fields[1] != str(RUNTIME) or not fields[0].isdigit():
        raise RuntimeError(f"malformed private-runtime size sample: {result.stdout!r}")
    return int(fields[0])


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
    return {"case": label, "status": status, "elapsed_seconds": elapsed,
            "stdout_sha256": sha(stdout_path), "stderr_sha256": sha(stderr_path),
            "diagnostic": diagnostic}


if platform.system() != "Linux" or platform.machine() != "x86_64":
    raise RuntimeError("this proof is scoped to Workhorse Linux x86_64")
if not STAGE.is_dir() or STAGE.is_symlink() or not OUT.is_dir() or OUT.is_symlink():
    raise RuntimeError("the owned source and output staging directories must exist")
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

OUT.mkdir(mode=0o700, exist_ok=True)
sample_path = OUT / "resource-samples.jsonl"
sample_path.write_text("", encoding="utf-8")
SOURCE.mkdir()
source_archive = STAGE / "source.tar.gz"
with tarfile.open(source_archive, "r:gz") as archive:
    archive.extractall(SOURCE)
shutil.copy2(STAGE / "sys_process.rs", SOURCE / "tests/sys_process.rs")
shutil.copy2(STAGE / "Cargo.lock.accepted", SOURCE / "Cargo.lock")
if sha(SOURCE / "tests/sys_process.rs") != pins["files"]["sys_process.rs"]:
    raise RuntimeError("the frozen test overlay did not stage exactly")
if sha(SOURCE / "Cargo.lock") != LOCK_SHA:
    raise RuntimeError("the accepted lockfile did not stage exactly")

ENV = os.environ.copy()
ENV.update({
    "RUSTUP_TOOLCHAIN": "1.93.0",
    "PATH": "/home/linuxbrew/.linuxbrew/opt/rustup/bin:/usr/bin:/bin",
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
if "1.93.0" not in versions["rustc"] or "1.93.0" not in versions["cargo"]:
    raise RuntimeError(f"unexpected pinned toolchain versions: {versions}")

source_path = SOURCE / "src/packages/sys/process/unix.rs"
original = source_path.read_bytes()
original_sha = hashlib.sha256(original).hexdigest()
text = original.decode("utf-8")
start = text.index("pub fn run(")
end = text.index("pub fn spawn(", start)
run_body = text[start:end]
anchor = "    for key in options.env_remove {\n        command.env_remove(key);\n    }"
if run_body.count(anchor) != 1:
    raise RuntimeError("public run env_remove mutation anchor is not unique")
mutant = text[:start] + run_body.replace(anchor,
    "    for key in options.env_remove {\n        let _ = key;\n    }", 1) + text[end:]
source_path.write_text(mutant, encoding="utf-8")
mutant_sha = sha(source_path)
manifest = {
    "source_revision": pins["source_revision"],
    "source_archive_sha256": pins["files"]["source.tar.gz"],
    "test_sha256": pins["files"]["sys_process.rs"],
    "lock_sha256": LOCK_SHA,
    "product_source_sha256": original_sha,
    "mutant_product_source_sha256": mutant_sha,
    "test": f"tests/sys_process.rs::{TEST_NAME}",
    "features": FEATURES,
    "command": COMMAND,
    "toolchain": versions,
    "cargo_jobs": 2,
    "runner_sha256": pins["runner_sha256"],
    "limits": {"helper_seconds": HELPER_SECONDS, "work_seconds": WORK_SECONDS,
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
results.append(run_case("mutant-red", deadline=work_deadline, samples=samples,
                        expected_status=101, diagnostic="variable=PATH present=true"))
source_path.write_bytes(original)
if sha(source_path) != original_sha:
    raise RuntimeError("the private product source was not exactly restored before GREEN")
results.append(run_case("restored-green", deadline=work_deadline, samples=samples,
                        expected_status=0))
if time.monotonic() >= started + HELPER_SECONDS:
    raise TimeoutError("the bounded helper budget, including export reserve, was exhausted")
if sha(source_path) != original_sha:
    raise RuntimeError("private product source changed during GREEN")

result = {
    "cases": results,
    "source_restored": True,
    "aggregate_elapsed_seconds": round(time.monotonic() - started, 3),
    "samples_are_periodic_not_continuous_peaks": True,
    "sampled_max_rss_kib": max((int(row["sampled_rss_kib"]) for row in samples), default=0),
    "sampled_max_storage_kib": max((int(row["runtime_storage_kib"]) for row in samples), default=0),
    "sampled_max_owned_processes": max((int(row["owned_process_count"]) for row in samples), default=0),
    "acceptance_scope": "Linux x86_64, Rust/Cargo 1.93.0, testing-environ,sys only",
}
write_json(OUT / "proof-result.json", result)
hashes = []
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name != "SHA256SUMS":
        hashes.append(f"{sha(path)}  {path.name}\n")
(OUT / "SHA256SUMS").write_text("".join(hashes), encoding="ascii")
print(json.dumps(result, sort_keys=True), flush=True)
