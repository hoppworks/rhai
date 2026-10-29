"""Bounded native Linux combined no_index,sync,metadata release-profile proof."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import zipfile
import time

input_dir = Path(sys.argv[1]).resolve()
evidence = Path(sys.argv[2]).resolve()
evidence.mkdir(parents=True, exist_ok=False)
runtime = Path(os.environ["AGENT_RUNTIME_DIR"]).resolve()
archive = input_dir / "rhai-source.zip"
manifest_path = input_dir / "source-manifest.json"
lock_path = input_dir / "Cargo.lock"
binding = json.loads((input_dir / "binding.json").read_text())
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert binding["checkout_head"] == "b93645f46a1262a0b4c7b83135ad29ea89e5d3fe"
assert digest(archive) == binding["archive_sha256"]
assert digest(manifest_path) == binding["manifest_sha256"]
assert digest(lock_path) == binding["lock_sha256"]
assert binding["lock_sha256"] == "12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802" and binding["features"] == "testing-environ,sys,net,no_index,sync,metadata"
manifest = json.loads(manifest_path.read_text())
assert manifest["file_count"] == 448
assert manifest["archive_sha256"] == binding["archive_sha256"]
source = runtime / "source"
source.mkdir()
with zipfile.ZipFile(archive) as bundled:
    assert set(bundled.namelist()) == set(manifest["files"])
    for name, expected in manifest["files"].items():
        target = source / name
        assert target.resolve().is_relative_to(source), name
        data = bundled.read(name)
        assert len(data) == expected["bytes"]
        assert hashlib.sha256(data).hexdigest() == expected["sha256"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
(source / "Cargo.lock").write_bytes(lock_path.read_bytes())
assert (source / "Cargo.toml").is_file()

profile = "testing-environ,sys,net,no_index,sync,metadata"
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
    **binding,
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
assert run("suite", base + target_args + ["--", "--test-threads=1", "--nocapture"], 600) == 0
record["capacity_after"] = {
    "runtime_free_bytes": os.statvfs(runtime).f_bavail * os.statvfs(runtime).f_frsize,
    "target_bytes": sum(p.stat().st_size for p in (runtime / "target").rglob("*") if p.is_file()),
}
record["status"] = "passed"
(evidence / "run.json").write_text(json.dumps(record, indent=2) + "\n")
