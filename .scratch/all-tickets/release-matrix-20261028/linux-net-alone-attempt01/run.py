"""One bounded native Linux net-only Engine/real-OS acceptance invocation."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import time
import zipfile

stage = Path(sys.argv[1]).resolve()
assert stage.name == "linux-net-alone-b1f047c8" and stage.is_dir() and not stage.is_symlink()
runtime = Path(os.environ["AGENT_RUNTIME_DIR"]).resolve()
assert runtime.is_dir() and runtime != stage and not str(stage).startswith(str(runtime) + os.sep)
source = runtime / "source"
source.mkdir()
archive = stage / "rhai-source.zip"
manifest_file = stage / "source-manifest.json"
lock_file = stage / "Cargo.lock"
manifest = json.loads(manifest_file.read_text())
def digest(file):
    with file.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()
assert digest(archive) == manifest["archive_sha256"] == "0005b38a387b419802335e141cb259de86f1ec9424e6e4cf2b8bc3beaf30bdd7"
assert digest(manifest_file) == "254d021566408f44b2b645551e2598f7cf9db5fee63c5e34bcc7ea20012ec9ba"
assert digest(lock_file) == manifest["lock_sha256"] == "12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802"
with zipfile.ZipFile(archive) as bundle:
    members = bundle.infolist()
    assert len(members) == manifest["file_count"] == 448
    assert set(bundle.namelist()) == set(manifest["files"])
    for member in members:
        path = PurePosixPath(member.filename)
        assert not path.is_absolute() and ".." not in path.parts and not member.is_dir()
        assert (member.external_attr >> 16) & 0o170000 != 0o120000
        payload = bundle.read(member)
        expected = manifest["files"][member.filename]
        assert len(payload) == expected["bytes"]
        assert hashlib.sha256(payload).hexdigest() == expected["sha256"]
        destination = source.joinpath(*path.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
(source / "Cargo.lock").write_bytes(lock_file.read_bytes())
assert digest(source / "Cargo.lock") == manifest["lock_sha256"]

environment = os.environ.copy()
rustc = subprocess.check_output(["rustup", "which", "rustc", "--toolchain", "1.77.2"], text=True).strip()
assert Path(rustc).is_file() and Path(rustc).name == "rustc"
environment.update({
    "CARGO_HOME": str(runtime / "cargo-home"),
    "CARGO_TARGET_DIR": str(runtime / "target"),
    "CARGO_BUILD_JOBS": "2",
    "CARGO_PROFILE_TEST_DEBUG": "0",
    "CARGO_INCREMENTAL": "0",
    "RUSTUP_TOOLCHAIN": "1.77.2",
    "RUSTC": rustc,
    "RUSTC_WRAPPER": "",
    "RUSTC_WORKSPACE_WRAPPER": "",
})
environment.pop("CARGO_BUILD_RUSTC", None)
for name in ("cargo-home", "target"):
    (runtime / name).mkdir()
commands = []
def run(label, command, expected_exit=0, extra=None):
    env = environment.copy()
    if extra:
        env.update(extra)
    start = time.monotonic()
    with (stage / (label + ".log")).open("wb") as out:
        result = subprocess.run(command, cwd=source, env=env, stdout=out,
                                stderr=subprocess.STDOUT, check=False)
        code = result.returncode
    record = {"label": label, "command": command, "exit": code,
              "expected_exit": expected_exit, "elapsed_seconds": round(time.monotonic() - start, 3)}
    commands.append(record)
    (stage / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    assert code == expected_exit, record
    return (stage / (label + ".log")).read_text(errors="replace")

started = time.time()
version = run("cargo-version", ["cargo", "+1.77.2", "--version"])
rust = run("rustc-version", [rustc, "--version"])
assert "cargo 1.77.2" in version and "rustc 1.77.2" in rust
targets = ["net_connect", "net_listen", "net_reads", "net_writes"]
base = ["cargo", "+1.77.2", "test", "--locked", "--features", "testing-environ,net"]
for target in targets:
    base += ["--test", target]
try:
    compile_log = run("compile", base + ["--no-run"])
    assert all("Executable tests/" + target + ".rs" in compile_log for target in targets)
    wrong = run("wrong-peer-eof", ["cargo", "+1.77.2", "test", "--locked", "--features",
        "testing-environ,net", "--test", "net_connect", "authorized_connect_is_observed_and_clone_close_is_shared",
        "--", "--exact", "--nocapture"], 101, {"RHAI_NET_WRONG_EXPECTATION": "1"})
    assert "deliberately wrong peer EOF expectation" in wrong
    assert "test result: FAILED. 0 passed; 1 failed;" in wrong
    assert "test authorized_connect_is_observed_and_clone_close_is_shared ... FAILED" in wrong
    suite = run("suite", base + ["--", "--test-threads=1", "--nocapture"])
    counts = [int(item) for item in re.findall(r"(?m)^test result: ok\. ([1-9][0-9]*) passed; 0 failed; 0 ignored;", suite)]
    assert len(counts) == 4 and all(count > 0 for count in counts), counts
    assert "test authorized_connect_is_observed_and_clone_close_is_shared ... ok" in suite
    result = {"accepted": True, "source_manifest_sha256": digest(manifest_file),
              "archive_sha256": digest(archive), "lock_sha256": digest(lock_file),
              "cargo": version.strip(), "rustc": rust.strip(), "rustc_path": rustc,
              "rustc_sha256": digest(Path(rustc)), "features": "testing-environ,net",
              "targets": targets, "wrong_exit": 101, "suite_exit": 0,
              "suite_passed_counts": counts, "elapsed_seconds": round(time.time() - started, 3)}
finally:
    run("cargo-clean", ["cargo", "+1.77.2", "clean", "--locked"])
(stage / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
