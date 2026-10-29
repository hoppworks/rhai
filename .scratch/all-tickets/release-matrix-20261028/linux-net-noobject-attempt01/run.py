"""Native Rust 1.77.2 proof for Net's no_object script API."""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import time
import zipfile


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


out = Path(sys.argv[1]).resolve()
prior = Path(sys.argv[2]).resolve()
runtime = Path(os.environ["AGENT_RUNTIME_DIR"]).resolve()
assert out.is_dir() and prior.is_dir() and runtime.is_dir()
assert not str(out).startswith(str(runtime) + os.sep)
manifest_file = prior / "source-manifest.json"
archive = prior / "rhai-source.zip"
lock = prior / "Cargo.lock"
manifest = json.loads(manifest_file.read_text())
assert digest(manifest_file) == "b829308ab356d7aaaf7bf8d3acc9f65aab8fb316192d9b1b69e3365d78c834fd"
assert digest(archive) == manifest["archive_sha256"]
assert digest(lock) == manifest["lock_sha256"]
source = runtime / "source"
source.mkdir()
with zipfile.ZipFile(archive) as bundle:
    assert set(bundle.namelist()) == set(manifest["files"])
    for entry in bundle.infolist():
        name = PurePosixPath(entry.filename)
        assert not name.is_absolute() and ".." not in name.parts and not entry.is_dir()
        assert (entry.external_attr >> 16) & 0o170000 != 0o120000
        data = bundle.read(entry)
        assert len(data) == manifest["files"][entry.filename]["bytes"]
        assert hashlib.sha256(data).hexdigest() == manifest["files"][entry.filename]["sha256"]
        target = source.joinpath(*name.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
(source / "Cargo.lock").write_bytes(lock.read_bytes())

rustc = Path(subprocess.check_output(["rustup", "which", "rustc", "--toolchain", "1.77.2"], text=True).strip())
assert rustc.is_file()
environment = os.environ.copy()
environment.update({
    "CARGO_HOME": str(runtime / "cargo-home"),
    "CARGO_TARGET_DIR": str(runtime / "target"),
    "CARGO_BUILD_JOBS": "2",
    "CARGO_PROFILE_TEST_DEBUG": "0",
    "CARGO_INCREMENTAL": "0",
    "RUSTUP_TOOLCHAIN": "1.77.2",
    "RUSTC": str(rustc),
    "RUSTC_WRAPPER": "",
    "RUSTC_WORKSPACE_WRAPPER": "",
})
environment.pop("CARGO_BUILD_RUSTC", None)
commands = []


def run(label, args, expected=0, wrong=False):
    local = environment.copy()
    if wrong:
        local["RHAI_NET_NO_OBJECT_WRONG_PEER_EXPECTATION"] = "1"
    start = time.monotonic()
    with (out / (label + ".log")).open("wb") as stream:
        result = subprocess.run(args, cwd=source, env=local, stdout=stream, stderr=subprocess.STDOUT)
    record = {"label": label, "command": args, "exit": result.returncode,
              "expected": expected, "seconds": round(time.monotonic() - start, 3)}
    commands.append(record)
    (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    assert result.returncode == expected, record
    return (out / (label + ".log")).read_text(errors="replace")


base = ["cargo", "+1.77.2", "test", "--locked", "--features", "testing-environ,net,no_object",
        "--test", "net_no_object"]
result = {"accepted": False, "source_manifest_sha256": digest(manifest_file),
          "archive_sha256": digest(archive), "lock_sha256": digest(lock),
          "rustc_path": str(rustc), "rustc_sha256": digest(rustc),
          "features": "testing-environ,net,no_object", "target": "net_no_object"}
try:
    cargo_version = run("cargo-version", ["cargo", "+1.77.2", "--version"])
    rustc_version = run("rustc-version", [str(rustc), "--version"])
    assert "cargo 1.77.2" in cargo_version and "rustc 1.77.2" in rustc_version
    compile_log = run("compile", base + ["--no-run"])
    assert "Executable tests/net_no_object.rs" in compile_log
    wrong_log = run("wrong-peer", base + ["registered_stream_functions_work_without_dot_syntax",
                                            "--", "--exact", "--nocapture"], 101, True)
    assert "deliberately wrong independent peer expectation" in wrong_log
    assert "test result: FAILED. 0 passed; 1 failed;" in wrong_log
    assert "test registered_stream_functions_work_without_dot_syntax ... FAILED" in wrong_log
    green_log = run("suite", base + ["--", "--test-threads=1", "--nocapture"])
    assert "test result: ok. 3 passed; 0 failed; 0 ignored;" in green_log
    assert "test registered_stream_functions_work_without_dot_syntax ... ok" in green_log
    result.update({"accepted": True, "cargo": cargo_version.strip(), "rustc": rustc_version.strip(),
                   "wrong_exit": 101, "suite_exit": 0, "suite_passed": 3})
finally:
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
