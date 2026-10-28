"""Bounded native macOS unchecked sys/net profile and host-bound controls."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import zipfile

repo = Path(sys.argv[1]).resolve()
evidence = Path(sys.argv[2]).resolve()
evidence.mkdir(parents=True, exist_ok=False)
runtime = Path(os.environ["AGENT_RUNTIME_DIR"]).resolve()
archive = repo / ".scratch/all-tickets/windows-rhai-native-20261028/attempt64/media-input/rhai-source.zip"
manifest_path = repo / ".scratch/all-tickets/windows-rhai-native-20261028/attempt64/media-input/source-manifest.json"
lock_path = repo / ".scratch/all-tickets/windows-rhai-native-20261028/attempt64/media-input/Cargo.lock"
manifest = json.loads(manifest_path.read_text())
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
assert head == "2cc58ed009ed50dbeb609203decb90b517e8d404"
assert manifest["source_commit"] == "63f18b01bc8000492dc6c777462568c8ab9824c7"
assert manifest["file_count"] == 448
assert digest(archive) == manifest["archive_sha256"]
assert digest(lock_path) == "12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802"
overlay_names = ["tests/sys_process.rs", "tests/serde.rs", "tests/net_reads.rs"]
overlay_hashes = {name: digest(repo / name) for name in overlay_names}
assert all(overlay_hashes[name] != manifest["files"][name]["sha256"] for name in overlay_names)
for name, record in manifest["files"].items():
    if name not in overlay_names:
        assert digest(repo / name) == record["sha256"], name
source = runtime / "source"
source.mkdir()
with zipfile.ZipFile(archive) as bundled:
    assert set(bundled.namelist()) == set(manifest["files"])
    for name, record in manifest["files"].items():
        target = source / name
        assert target.resolve().is_relative_to(source)
        data = bundled.read(name)
        assert len(data) == record["bytes"]
        assert hashlib.sha256(data).hexdigest() == record["sha256"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
(source / "Cargo.lock").write_bytes(lock_path.read_bytes())
for name in overlay_names:
    (source / name).write_bytes((repo / name).read_bytes())
    assert digest(source / name) == overlay_hashes[name]

profile = "testing-environ,sys,net,unchecked"
target_args = [
    "--test", "combined_sys_net", "--test", "sys_env", "--test", "sys_fs",
    "--test", "sys_policy", "--test", "net_connect", "--test", "net_listen",
    "--test", "net_reads", "--test", "net_writes", "--test", "net_metadata",
    "--test", "sys_process", "--test", "sys_process_report",
]
environment = os.environ.copy()
environment.update({
    "CARGO_TARGET_DIR": str(runtime / "target"),
    "CARGO_HOME": str(runtime / "cargo-home"),
    "CARGO_BUILD_JOBS": "4",
    "CARGO_INCREMENTAL": "0",
    "CARGO_PROFILE_TEST_DEBUG": "0",
    "CARGO_PROFILE_TEST_CODEGEN_UNITS": "256",
    "PYTHONDONTWRITEBYTECODE": "1",
})
record = {
    "checkout_head": head,
    "source_commit": manifest["source_commit"],
    "source_manifest_sha256": digest(manifest_path),
    "source_archive_sha256": digest(archive),
    "source_overlays": overlay_hashes,
    "lock_sha256": digest(lock_path),
    "features": profile,
    "os": platform.platform(),
    "machine": platform.machine(),
    "rustc": subprocess.check_output(["rustc", "+1.77.2", "--version"], text=True).strip(),
    "cargo": subprocess.check_output(["cargo", "+1.77.2", "--version"], text=True).strip(),
    "capacity_before": {
        "runtime_free_bytes": os.statvfs(runtime).f_bavail * os.statvfs(runtime).f_frsize,
        "expected_additional_peak_bytes": 4 * 1024**3,
        "estimate_source": "provisional private Cargo target/cache estimate",
    },
    "steps": [],
}

def run(name, command, seconds, extra=None):
    child_env = environment.copy()
    if extra:
        child_env.update(extra)
    start = time.monotonic()
    path = evidence / (name + ".log")
    with path.open("wb") as log:
        try:
            result = subprocess.run(command, cwd=source, env=child_env, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=seconds, check=False)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = 124
    entry = {"name": name, "command": command, "cwd": str(source),
             "exit": code, "elapsed_seconds": round(time.monotonic() - start, 3),
             "log_sha256": digest(path), "log_bytes": path.stat().st_size}
    record["steps"].append(entry)
    (evidence / "run.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(entry), flush=True)
    return code

base = ["cargo", "+1.77.2", "test", "--locked", "--features", profile]
assert run("compile", base + target_args + ["--no-run"], 900) == 0
red = run("combined-wrong", base + ["--test", "combined_sys_net",
    "sys_and_net_packages_coexist_in_one_engine_with_os_readback_and_typed_errors",
    "--", "--exact", "--nocapture"], 60,
    {"RHAI_COMBINED_WRONG_EXPECTATION": "1"})
red_log = (evidence / "combined-wrong.log").read_text(errors="replace")
assert red == 101 and "fresh host readback must match independent expected bytes" in red_log
assert "test result: FAILED. 0 passed; 1 failed" in red_log
file_red = run("file-wrong", base + ["--test", "sys_fs",
    "test_file_handle_reads_obey_host_cap_and_reject_negative_lengths_without_moving",
    "--", "--exact", "--nocapture"], 60,
    {"RHAI_FILE_READ_WRONG_EXPECTATION": "1"})
file_log = (evidence / "file-wrong.log").read_text(errors="replace")
assert file_red == 101 and "wrong expectation" in file_log
assert "test result: FAILED. 0 passed; 1 failed" in file_log
cap_red = run("net-cap-wrong", base + ["--test", "net_reads",
    "unchecked_mode_keeps_the_host_receive_cap",
    "--", "--exact", "--nocapture"], 60,
    {"RHAI_NET_UNCHECKED_WRONG_CAP_EXPECTATION": "1"})
cap_log = (evidence / "net-cap-wrong.log").read_text(errors="replace")
assert cap_red == 101 and "unchecked mode retains the host receive cap" in cap_log
assert "test result: FAILED. 0 passed; 1 failed" in cap_log
write_red = run("net-write-wrong", base + ["--test", "net_writes",
    "script_write_blob_preserves_exact_bytes",
    "--", "--exact", "--nocapture"], 60,
    {"RHAI_NET_WRONG_WRITE_EXPECTATION": "1"})
write_log = (evidence / "net-write-wrong.log").read_text(errors="replace")
assert write_red == 101 and "test result: FAILED. 0 passed; 1 failed" in write_log
assert run("suite", base + target_args + ["--", "--test-threads=1", "--nocapture"], 600) == 0
record["capacity_after"] = {
    "runtime_free_bytes": os.statvfs(runtime).f_bavail * os.statvfs(runtime).f_frsize,
    "target_bytes": sum(p.stat().st_size for p in (runtime / "target").rglob("*") if p.is_file()),
}
record["status"] = "passed"
(evidence / "run.json").write_text(json.dumps(record, indent=2) + "\n")
