#!/usr/bin/env python3
"""Run private compiler-negative gate proof under run_scoped.py."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path.cwd().resolve()
EVIDENCE = ROOT / ".scratch/unsupported-feature-proof"
LOGS = EVIDENCE / "logs"
RUNTIME = Path(os.environ["AGENT_RUNTIME_DIR"]).resolve()
SRC = RUNTIME / "source"
CARGO_HOME = RUNTIME / "cargo-home"
TARGET = RUNTIME / "target"
LIMIT_BYTES = 1536 * 1024 * 1024

EXPECTED = {
    "sys-no_std": ("the `sys` feature requires `std`; it cannot be combined with `no_std`",),
    "net-no_std": ("the `net` feature requires `std`; it cannot be combined with `no_std`",),
    "sys-no_object": ("the `sys` feature requires object maps; it cannot be combined with `no_object`",),
    "sys-wasm": ("the `sys` feature is not available on WASM targets",),
    "net-wasm": ("the `net` feature is not available on WASM targets",),
    "sys-net-wasm": (
        "the `sys` feature is not available on WASM targets",
        "the `net` feature is not available on WASM targets",
    ),
}


def storage_bytes(path: Path) -> int:
    total = 0
    for base, dirs, files in os.walk(path):
        for name in dirs + files:
            p = Path(base) / name
            try:
                st = p.lstat()
                total += getattr(st, "st_blocks", (st.st_size + 511) // 512) * 512
            except FileNotFoundError:
                continue
    return total


def diagnostic_count(name: str, output: str) -> int:
    lines = output.splitlines()
    return sum(lines.count("error: " + expected) for expected in EXPECTED[name])


def matcher(name: str, output: str) -> bool:
    lines = output.splitlines()
    return all(lines.count("error: " + expected) == 1 for expected in EXPECTED[name])


shutil.copytree(
    ROOT,
    SRC,
    ignore=shutil.ignore_patterns(".git", ".scratch", "target", "build"),
)
CARGO_HOME.mkdir()
(RUNTIME / "tmp").mkdir(exist_ok=True)
(EVIDENCE / "runtime-path.txt").write_text(str(RUNTIME) + "\n")

base = ["cargo", "check", "--no-default-features"]
env = os.environ.copy()
env.update(
    {
        "CARGO_HOME": str(CARGO_HOME),
        "CARGO_TARGET_DIR": str(TARGET),
        "CARGO_BUILD_JOBS": "2",
        "CARGO_PROFILE_DEV_DEBUG": "0",
        "CARGO_PROFILE_TEST_DEBUG": "0",
        "CARGO_INCREMENTAL": "0",
        "TMPDIR": str(RUNTIME / "tmp"),
        "TMP": str(RUNTIME / "tmp"),
        "TEMP": str(RUNTIME / "tmp"),
    }
)

rows: list[tuple[str, int, int, bool, str]] = []
smoke_rows: list[tuple[str, int, str]] = []
peak = 0
samples = []
start = time.monotonic()
last_sample = 0.0
lock_hash = ""
failures = []


def run(
    name: str,
    features: str | None = None,
    target: str | None = None,
    *,
    locked: bool = True,
    command_override: list[str] | None = None,
    environment_overrides: dict[str, str] | None = None,
    source_dir: Path | None = None,
    diagnostic_name: str | None = None,
) -> tuple[int, str]:
    global peak, last_sample
    command = list(command_override) if command_override else base.copy()
    if command_override is None:
        if locked and (SRC / "Cargo.lock").exists():
            command.append("--locked")
        if features:
            command.extend(["--features", features])
        if target:
            command.extend(["--target", target])
    log_path = LOGS / f"{name}.log"
    with log_path.open("w", encoding="utf-8") as log:
        log.write("$ " + " ".join(command) + "\n")
        log.flush()
        child_env = env.copy()
        if environment_overrides:
            child_env.update(environment_overrides)
        proc = subprocess.Popen(
            command,
            cwd=source_dir or SRC,
            env=child_env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        killed_for_cap = False
        while proc.poll() is None:
            now = time.monotonic()
            if now - start >= 555:
                proc.terminate()
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                raise RuntimeError("package execution exceeded internal 555-second stop")
            if now - last_sample >= 1.0:
                size = storage_bytes(RUNTIME)
                peak = max(peak, size)
                samples.append(f"{now - start:.3f}\t{size}\n")
                last_sample = now
                if size >= LIMIT_BYTES:
                    killed_for_cap = True
                    proc.terminate()
                    try:
                        proc.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    break
            time.sleep(0.1)
        status = proc.wait()
    output = log_path.read_text(encoding="utf-8", errors="replace")
    diagnostic_name = diagnostic_name or ("sys-no_object" if name == "sys-no_object-restored" else name)
    if diagnostic_name in EXPECTED:
        hit = matcher(diagnostic_name, output)
        rows.append((name, status, diagnostic_count(diagnostic_name, output), hit, str(log_path.relative_to(ROOT))))
    else:
        smoke_rows.append((name, status, str(log_path.relative_to(ROOT))))
    if killed_for_cap:
        raise RuntimeError("private runtime reached the 1.5 GiB preemptive stop")
    return status, output


# Preserve the actual base-revision WASM dependency failure as the RED that drove
# the target-specific manifest change. The package guard must not be credited here.
baseline = RUNTIME / "baseline-source"
shutil.copytree(SRC, baseline)
base_manifest = subprocess.check_output(
    ["git", "show", "79eca3c0b88787db64e758ee080ce1ccc14dde28:Cargo.toml"],
    cwd=ROOT,
    text=True,
)
(baseline / "Cargo.toml").write_text(base_manifest)
old_command = ["cargo", "check", "--no-default-features", "--features", "sys", "--target", "wasm32-unknown-unknown"]
status, output = run(
    "prechange-sys-wasm-unknown-boundary",
    command_override=old_command,
    source_dir=baseline,
)
if status == 0 or "The target OS is \"unknown\" or \"none\", so it's unsupported by the errno crate." not in output:
    failures.append("pre-change unknown-unknown boundary did not show the expected errno dependency failure")
if EXPECTED["sys-wasm"][0] in output:
    failures.append("pre-change unknown-unknown run unexpectedly reached the sys package guard")

# Expected package diagnostics are asserted separately for every combination.
checks = [
    ("sys-no_std", "sys,no_std", None),
    ("net-no_std", "net,no_std", None),
    ("sys-no_object", "sys,no_object", None),
]
for name, features, target in checks:
    status, output = run(name, features, target, locked=False)
    if status == 0 or not matcher(name, output):
        failures.append(f"{name}: expected nonzero exit plus exactly one intended diagnostic; status={status}")

# False-green control: remove only the sys/no_object guard in the private copy.
source_file = SRC / "src/packages/sys/mod.rs"
source_text = source_file.read_text()
guard = '#[cfg(feature = "no_object")]\ncompile_error!("the `sys` feature requires object maps; it cannot be combined with `no_object`");\n\n'
if source_text.count(guard) != 1:
    raise RuntimeError("control setup could not identify exactly one sys/no_object guard")
source_file.write_text(source_text.replace(guard, "", 1))
status, output = run(
    "control-sys-no_object-guard-removed",
    "sys,no_object",
    diagnostic_name="sys-no_object",
)
if status == 0 or matcher("sys-no_object", output):
    failures.append("guard-removed control did not demonstrate matcher rejection")
# Restore byte-for-byte and show the same matcher detects the package diagnostic.
source_file.write_text(source_text)
status, output = run("sys-no_object-restored", "sys,no_object")
if status == 0 or not matcher("sys-no_object", output):
    failures.append("restored sys/no_object guard was not detected")

wasm_checks = [
    ("sys-wasm", "sys"),
    ("net-wasm", "net"),
    ("sys-net-wasm", "sys,net"),
]
for target_triple in ("wasm32-unknown-unknown", "wasm32-wasip1"):
    for base_name, features in wasm_checks:
        name = f"{base_name}-{target_triple}"
        status, output = run(name, features, target_triple, diagnostic_name=base_name)
        if status == 0 or not matcher(base_name, output):
            failures.append(f"{name}: expected nonzero exit plus intended package diagnostic(s); status={status}")

# Native smoke: the public sys Engine test observes independent fixture bytes.
test_command = [
    "cargo", "test", "--locked", "--features", "testing-environ,sys,metadata",
    "--test", "sys_fs",
    "test_file_handle_reads_obey_host_cap_and_reject_negative_lengths_without_moving",
    "--", "--exact",
]
smoke_name = "native-sys-smoke-correct"
status, output = run(smoke_name, command_override=test_command)
if status != 0:
    failures.append(f"{smoke_name} expected status 0, got {status}")
wrong_name = "native-sys-smoke-wrong-expectation"
status, output = run(
    wrong_name,
    command_override=test_command,
    environment_overrides={"RHAI_FILE_READ_WRONG_EXPECTATION": "1"},
)
if status == 0 or "wrong expectation" not in output:
    failures.append(f"{wrong_name} did not fail at the deliberately wrong fixture assertion; status={status}")
status, output = run("native-sys-smoke-restored", command_override=test_command)
if status != 0:
    failures.append(f"native-sys-smoke-restored expected status 0, got {status}")

lock = SRC / "Cargo.lock"
if lock.exists():
    lock_hash = hashlib.sha256(lock.read_bytes()).hexdigest()
    shutil.copy2(lock, EVIDENCE / "Cargo.lock")
(EVIDENCE / "resource-samples.tsv").write_text("elapsed_seconds\truntime_bytes\n" + "".join(samples))
(EVIDENCE / "results.tsv").write_text(
    "check\texit_status\texpected_diagnostic_occurrences\tmatcher\tlog\n"
    + "".join(f"{n}\t{s}\t{c}\t{'accept' if m else 'reject'}\t{p}\n" for n, s, c, m, p in rows)
)
(EVIDENCE / "native-smoke-results.tsv").write_text(
    "check\texit_status\tlog\n"
    + "".join(f"{n}\t{s}\t{p}\n" for n, s, p in smoke_rows)
)
(EVIDENCE / "metrics.txt").write_text(
    f"elapsed_seconds={time.monotonic() - start:.3f}\n"
    f"sample_count={len(samples)}\npeak_sampled_runtime_bytes={peak}\n"
    f"preemptive_limit_bytes={LIMIT_BYTES}\nlock_sha256={lock_hash}\n"
    f"runtime_path={RUNTIME}\n"
)
if failures:
    print("compiler gate mismatches: " + "; ".join(failures), file=sys.stderr)
    raise SystemExit(1)
print(f"all compiler gate assertions passed; peak sampled private runtime bytes={peak}; lock sha256={lock_hash}")
