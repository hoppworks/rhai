"""Bounded native Rust 1.77.2 standalone Sys package proof."""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
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
targets = ["sys_policy", "sys_env", "sys_fs", "sys_process", "sys_process_report"]
features = "testing-environ,sys"
base = ["cargo", "+1.77.2", "test", "--locked", "--features", features]
commands = []
result = {"accepted": False, "features": features, "targets": targets,
          "source_manifest_sha256": digest(manifest_file), "archive_sha256": digest(archive),
          "lock_sha256": digest(lock), "rustc_path": str(rustc), "rustc_sha256": digest(rustc)}


def run(label, args, expected=0, wrong=False):
    local = environment.copy()
    if wrong:
        local["RHAI_FILE_HANDLE_WRONG_EXPECTATION"] = "1"
    start = time.monotonic()
    with (out / (label + ".log")).open("wb") as stream:
        completed = subprocess.run(args, cwd=source, env=local, stdout=stream, stderr=subprocess.STDOUT)
    record = {"label": label, "command": args, "exit": completed.returncode,
              "expected": expected, "seconds": round(time.monotonic() - start, 3)}
    commands.append(record)
    (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    assert completed.returncode == expected, record
    return (out / (label + ".log")).read_text(errors="replace")


def executable(log, target):
    match = re.search(r"(?m)^\s*Running tests/" + re.escape(target) + r"\.rs \(([^)]+)\)", log)
    assert match, "missing Cargo executable line for " + target
    return match.group(1)


try:
    cargo_version = run("cargo-version", ["cargo", "+1.77.2", "--version"])
    rustc_version = run("rustc-version", [str(rustc), "--version"])
    assert "cargo 1.77.2" in cargo_version and "rustc 1.77.2" in rustc_version
    selections = [item for target in targets for item in ("--test", target)]
    compile_log = run("compile", base + selections + ["--no-run"])
    for target in targets:
        assert "Executable tests/" + target + ".rs" in compile_log, target
    wrong_log = run("wrong-host-readback", base + ["--test", "sys_fs",
        "test_open_file_default_preserves_contents_and_shares_cursor",
        "--", "--exact", "--nocapture"], expected=101, wrong=True)
    assert 'independent host readback: "original XYyload"' in wrong_log
    assert 'left: [111, 114, 105, 103, 105, 110, 97, 108, 32, 88, 89, 121, 108, 111, 97, 100]' in wrong_log
    assert 'right: [119, 114, 111, 110, 103, 32, 101, 120, 112, 101, 99, 116, 97, 116, 105, 111, 110]' in wrong_log
    assert re.search(r"test result: FAILED\. 0 passed; 1 failed;", wrong_log)
    assert "test_open_file_default_preserves_contents_and_shares_cursor" in wrong_log
    compiled = {}
    for target in targets:
        match = re.search(r"(?m)^\s*Executable tests/" + re.escape(target) + r"\.rs \(([^)]+)\)", compile_log)
        assert match, target
        compiled[target] = match.group(1)
    assert executable(wrong_log, "sys_fs") == compiled["sys_fs"]
    passed = {}
    for target in targets:
        label = "green-" + target
        log = run(label, base + ["--test", target, "--", "--test-threads=1", "--nocapture"])
        assert executable(log, target) == compiled[target], target
        summaries = re.findall(r"test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;", log)
        assert summaries, target
        count = int(summaries[-1][0])
        assert count > 0, target
        passed[target] = {"passed": count, "ignored": int(summaries[-1][1]),
                          "executable": compiled[target]}
    assert "test_open_file_default_preserves_contents_and_shares_cursor ... ok" in (out / "green-sys_fs.log").read_text(errors="replace")
    result.update({"accepted": True, "cargo": cargo_version.strip(), "rustc": rustc_version.strip(),
                   "wrong_exit": 101, "green_exit": 0, "passed": passed,
                   "total_passed": sum(value["passed"] for value in passed.values()),
                   "same_sys_fs_executable": compiled["sys_fs"]})
finally:
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
