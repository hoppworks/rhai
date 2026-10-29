"""Bounded native current-source default-core Rust 1.66 proof."""

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
    state = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b""):
            state.update(part)
    return state.hexdigest()


out = Path(sys.argv[1]).resolve()
prior = Path(sys.argv[2]).resolve()
runtime = Path(os.environ["AGENT_RUNTIME_DIR"]).resolve()
assert out.is_dir() and prior.is_dir() and runtime.is_dir()
manifest_file = prior / "source-manifest.json"
archive = prior / "rhai-source.zip"
lock_file = prior / "Cargo.lock"
manifest = json.loads(manifest_file.read_text())
assert digest(manifest_file) == "b829308ab356d7aaaf7bf8d3acc9f65aab8fb316192d9b1b69e3365d78c834fd"
assert digest(archive) == manifest["archive_sha256"]
assert digest(lock_file) == manifest["lock_sha256"]
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
(source / "Cargo.lock").write_bytes(lock_file.read_bytes())
example = source / "examples" / "core_current_msrv.rs"
assert not example.exists()
example.write_text('''use rhai::Engine;
fn main() {
    let engine = Engine::new();
    let actual: i64 = engine.eval("40 + 2").expect("real Engine evaluation");
    assert!(engine.compile("spawn()").is_err(), "spawn remains reserved without sys");
    let expected = if std::env::args().any(|x| x == "--wrong") { 43 } else { 42 };
    assert_eq!(actual, expected, "independent Engine expectation");
    println!("actual={actual} expected={expected} spawn_reserved=true");
}
''')

rustc = Path(subprocess.check_output(["rustup", "which", "rustc", "--toolchain", "1.66.0"], text=True).strip())
assert rustc.is_file()
environment = os.environ.copy()
environment.update({
    "CARGO_HOME": str(runtime / "cargo-home"),
    "CARGO_TARGET_DIR": str(runtime / "target"),
    "CARGO_BUILD_JOBS": "2",
    "CARGO_PROFILE_DEV_DEBUG": "0",
    "CARGO_PROFILE_TEST_DEBUG": "0",
    "CARGO_INCREMENTAL": "0",
    "RUSTUP_TOOLCHAIN": "1.66.0",
    "RUSTC": str(rustc),
    "RUSTC_WRAPPER": "",
    "RUSTC_WORKSPACE_WRAPPER": "",
    "RUSTFLAGS": "",
})
for name in ("CARGO_BUILD_RUSTC", "CARGO_BUILD_TARGET", "CARGO_ENCODED_RUSTFLAGS"):
    environment.pop(name, None)
commands = []


def run(label, command, expected=0):
    start = time.monotonic()
    with (out / (label + ".log")).open("wb") as output:
        completed = subprocess.run(command, cwd=source, env=environment,
                                   stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
    record = {"label": label, "command": command, "exit": completed.returncode,
              "expected": expected, "seconds": round(time.monotonic() - start, 3),
              "lock_sha256_after": digest(source / "Cargo.lock")}
    commands.append(record)
    (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    assert record["lock_sha256_after"] == manifest["lock_sha256"], record
    assert completed.returncode == expected, record
    return (out / (label + ".log")).read_text(errors="replace")


result = {"accepted": False, "source_manifest_sha256": digest(manifest_file),
          "archive_sha256": digest(archive), "lock_sha256": digest(lock_file),
          "rustc_path": str(rustc), "rustc_sha256": digest(rustc),
          "example_sha256": digest(example), "target": "aarch64-apple-darwin"}
try:
    cargo_version = run("cargo-version", ["cargo", "+1.66.0", "--version"])
    rustc_version = run("rustc-version", [str(rustc), "--version"])
    assert "cargo 1.66.0" in cargo_version and "rustc 1.66.0" in rustc_version
    base = ["cargo", "+1.66.0", "run", "--locked", "--target", "aarch64-apple-darwin",
            "--example", "core_current_msrv"]
    run("core-check", ["cargo", "+1.66.0", "check", "--locked", "--lib", "--target", "aarch64-apple-darwin"])
    positive = run("engine-positive", base)
    assert "actual=42 expected=42 spawn_reserved=true" in positive
    wrong = run("engine-wrong", base[:3] + ["--offline"] + base[3:] + ["--", "--wrong"], 101)
    assert "assertion failed: `(left == right)`" in wrong or "assertion `left == right` failed" in wrong
    assert re.search(r"left: (?:`)?42", wrong) and re.search(r"right: (?:`)?43", wrong)
    restored = run("engine-restored", base[:3] + ["--offline"] + base[3:])
    assert "actual=42 expected=42 spawn_reserved=true" in restored
    result.update({"accepted": True, "cargo": cargo_version.strip(), "rustc": rustc_version.strip(),
                   "core_check_exit": 0, "wrong_exit": 101, "restored_exit": 0})
except BaseException as error:
    result["failure"] = repr(error)
    raise
finally:
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
