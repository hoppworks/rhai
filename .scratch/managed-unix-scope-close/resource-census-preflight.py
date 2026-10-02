#!/usr/bin/env python3
"""Read-only preflight for the frozen Linux retained-resource census inputs."""

from __future__ import annotations

import argparse
import ast
import hashlib
import pathlib
import re
import subprocess
import sys
import tarfile


REVISION = "0b3841a03657463f40fae01f9af2797d5c3812ed"
ARCHIVE_SHA = "e52fe1903537da4f58cf3315feec3e4eff33408f3de37688d81bdcdd9c558cd4"
BASELINE_SHA = "8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa"
EDGE_LOCK_SHA = "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425"
RUNNER_FILES = {
    "runner/tools/run_scoped.py": "9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d",
    "runner/tools/agentskills/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "runner/tools/agentskills/pyguard.py": "a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f",
}
SOURCE_PATHS = (
    "Cargo.toml",
    "src/packages/sys/config.rs",
    "src/packages/sys/mod.rs",
    "src/packages/sys/process.rs",
    "src/packages/sys/process/unix.rs",
    "tests/sys_process.rs",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, type=pathlib.Path)
    args = parser.parse_args()
    stage = args.stage.resolve(strict=True)
    archive = stage / "source.tar"
    lock_path = stage / "Cargo.lock.baseline"
    driver_path = stage / "resource-census-proof.py"
    launcher_path = stage / "remote-resource-census-launch.sh"
    contract_path = stage / "linux-resource-census-contract.md"
    runner_paths = tuple(stage / relative for relative in RUNNER_FILES)
    files = (archive, lock_path, driver_path, launcher_path, contract_path, *runner_paths)
    if any(not path.is_file() or path.is_symlink() for path in files):
        raise SystemExit("preflight failed: a required staged regular file is missing or symlinked")
    if sha(archive.read_bytes()) != ARCHIVE_SHA or sha(lock_path.read_bytes()) != BASELINE_SHA:
        raise SystemExit("preflight failed: candidate archive or baseline lock hash mismatch")
    for relative, expected in RUNNER_FILES.items():
        if sha((stage / relative).read_bytes()) != expected:
            raise SystemExit(f"preflight failed: configured runner dependency hash mismatch: {relative}")

    version_result = subprocess.run(
        ["python3", "--version"], capture_output=True, text=True, timeout=3, check=True
    )
    python_version = (version_result.stdout or version_result.stderr).strip()
    match = re.fullmatch(r"Python (\d+)\.(\d+)\.\d+", python_version)
    if not match or tuple(map(int, match.groups())) < (3, 12):
        raise SystemExit(f"preflight failed: launcher Python3 must be 3.12+ for tarfile data filter; found {python_version}")
    import inspect
    if "filter" not in inspect.signature(tarfile.TarFile.extractall).parameters:
        raise SystemExit("preflight failed: tarfile.extractall lacks the required filter parameter")
    runner_help = subprocess.run(
        ["python3", str(stage / "runner/tools/run_scoped.py"), "--help"],
        capture_output=True, text=True, timeout=5,
    )
    if runner_help.returncode != 0 or "usage:" not in runner_help.stdout.lower():
        raise SystemExit(
            "preflight failed: staged run_scoped dependency import/help check failed: "
            + runner_help.stderr[-1200:]
        )

    with tarfile.open(archive, "r") as source:
        members = {member.name: member for member in source.getmembers() if member.isfile()}
        absent = [relative for relative in SOURCE_PATHS if relative not in members]
        if absent:
            raise SystemExit(f"preflight failed: source archive omits manifest paths: {absent}")
        manifest = source.extractfile(members["Cargo.toml"]).read()
        test_source = source.extractfile(members["tests/sys_process.rs"]).read()
    if b'libc = { version = "=0.2.189", optional = true }' not in manifest:
        raise SystemExit("preflight failed: exact optional libc edge not found in frozen source")
    if b"fn process_scope_retained_resource_census()" not in test_source or b"held_child_control" not in test_source:
        raise SystemExit("preflight failed: frozen source lacks the retained-resource census and held-child control")

    lock = lock_path.read_text(encoding="utf-8")
    start = lock.index('name = "rhai"\n')
    end = lock.index("[[package]]", start)
    package = lock[start:end]
    if ' "libc",\n' not in package:
        if ' "libm",\n' not in package:
            raise SystemExit("preflight failed: accepted lock insertion anchor missing")
        lock = lock[:start] + package.replace(' "libm",\n', ' "libc",\n "libm",\n', 1) + lock[end:]
    if sha(lock.encode()) != EDGE_LOCK_SHA:
        raise SystemExit("preflight failed: generated private lock differs from accepted edge-only SHA")

    driver = driver_path.read_text(encoding="utf-8")
    proof = driver
    launcher = launcher_path.read_text(encoding="utf-8")
    contract = contract_path.read_text(encoding="utf-8")
    if "--self-test" not in driver or "validate_census_log" not in driver:
        raise SystemExit("preflight failed: pure census classifier checks are absent")
    if "test process_scope_retained_resource_census ... " not in driver:
        raise SystemExit("preflight failed: exact libtest first-receipt framing is not covered")
    manifest_at = driver.find('source_manifest(evidence, source, "after-census")')
    classifier_at = driver.find("records = validate_census_log(census_text)")
    if manifest_at < 0 or classifier_at < 0 or manifest_at >= classifier_at:
        raise SystemExit("preflight failed: post-census source manifest is not written before receipt classification")
    parser_check = subprocess.run(
        ["python3", str(driver_path), "--self-test"], capture_output=True, text=True, timeout=5
    )
    if parser_check.returncode != 0 or "census_log_self_test=pass" not in parser_check.stdout:
        raise SystemExit("preflight failed: census parser controls failed: " + parser_check.stderr[-1200:])
    if REVISION not in proof or ARCHIVE_SHA not in proof or BASELINE_SHA not in proof or EDGE_LOCK_SHA not in proof:
        raise SystemExit("preflight failed: runtime verifier is not bound to reviewed inputs")
    for required in (
        "MAX_DRIVER_SECONDS = 580",
        "MAX_CARGO_SECONDS = 540",
        "FINALIZATION_RESERVE_SECONDS = 20",
        "cwd=source",
        '"HOME": str(private_home)',
        '"CARGO_HOME": str(cargo_home)',
        '"TMPDIR": str(runtime / "tmp")',
        "cargo_deadline = min(",
        'bundle.extractall(source, filter="data")',
    ):
        if required not in driver:
            raise SystemExit(f"preflight failed: bounded private driver property missing: {required}")
    if "env = dict(os.environ)" in driver or "CARGO_TEST_SETSID" in driver:
        raise SystemExit("preflight failed: driver inherits an open-ended environment or Cargo session escape")
    if "resource-census-proof.py" not in launcher or "--timeout 585" not in launcher:
        raise SystemExit("preflight failed: launcher does not dispatch the census or preserve scoped bound")
    if "def valid_runner_identity_row(row):" not in launcher or "not fields[5]" in launcher:
        raise SystemExit("preflight failed: runner cleanup identity validator rejects descriptive empty cmdline")
    if (
        'session_base="$HOME/.local/share/agent-builds/rhai"' not in launcher
        or 'TMPDIR="$session_scope"' not in launcher
        or 'rmdir "$session_scope"' not in launcher
    ):
        raise SystemExit("preflight failed: per-session TMPDIR custody/empty-only retirement is absent")
    if (
        "SAMPLED_STORAGE_STOP_KIB = 1_572_864" not in proof
        or '["du", "-sk", str(runtime)]' not in proof
        or "timeout=4" not in proof
        or "resource-samples.tsv" not in proof
    ):
        raise SystemExit("preflight failed: bounded private-runtime storage sampling/stop is absent")
    for required in (
        "VmRSS:",
        "memory_limit_bytes = 2 * 1024 * 1024 * 1024",
        "process-resource-samples.tsv",
        "measurement-command-identities.tsv",
        "sampled_owned_tree_rss_max_bytes=",
    ):
        if required not in launcher:
            raise SystemExit(f"preflight failed: live RSS/identity custody component is absent: {required}")
    if not re.search(r"timeout --signal=TERM --kill-after=2 598s", contract):
        raise SystemExit("preflight failed: expected explicit 600-second outer timeout wrapper is not recorded")
    if "SAMPLED_PRIVATE_RUNTIME_STORAGE_MAX_KIB" not in driver or "not continuous peak" not in driver:
        raise SystemExit("preflight failed: sampled storage reporting is absent or overclaimed")
    if "measurement-driver\\t" not in driver or "measurement-command-identities.tsv" not in driver:
        raise SystemExit("preflight failed: exact Cargo test command identity receipt is absent")
    finalizer_match = re.search(
        r'python3 - "\$evidence" <<\'PY\'\n(.*?)\nPY', launcher, re.DOTALL
    )
    if not finalizer_match:
        raise SystemExit("preflight failed: exact cleanup finalizer block is absent")
    finalizer_tree = ast.parse(finalizer_match.group(1))
    validator_node = next(
        (node for node in finalizer_tree.body if isinstance(node, ast.FunctionDef) and node.name == "valid_runner_identity_row"),
        None,
    )
    if validator_node is None:
        raise SystemExit("preflight failed: runner identity validator is absent from cleanup finalizer")
    validator_namespace: dict[str, object] = {}
    exec(compile(ast.Module(body=[validator_node], type_ignores=[]), "finalizer-validator", "exec"), validator_namespace)
    validate_runner_identity = validator_namespace["valid_runner_identity_row"]
    if not validate_runner_identity("123.0\t10\t20\t1\t1\t"):
        raise SystemExit("preflight failed: empty descriptive cmdline incorrectly invalidates numeric identity")
    if validate_runner_identity("123.0\t10\tbad\t1\t1\t") or validate_runner_identity("123.0\t10\t20\t1\t1"):
        raise SystemExit("preflight failed: malformed runner identity passed cleanup validator")

    print(f"preflight=pass revision={REVISION}")
    print(f"archive_sha256={ARCHIVE_SHA}")
    print(f"baseline_lock_sha256={BASELINE_SHA}")
    print(f"private_edge_lock_sha256={EDGE_LOCK_SHA}")
    print(f"python={python_version} tarfile_data_filter=available staged_run_scoped_help=pass")
    print(parser_check.stdout.strip())
    print("finalizer_identity_controls=pass empty_cmdline_numeric_identity_accepted malformed_or_missing_identity_rejected")
    for path in files:
        print(f"file_sha256={sha(path.read_bytes())} path={path.name}")
    print("manifest_paths=" + ",".join(SOURCE_PATHS))
    print("limits=outer600 scoped585 driver580 cargo540+20s-finalize jobs2 descendants16 memory2GiB sampled-stop1572864KiB@1s completed6 held2 retries0")
    print("execution=none (hash, archive, lock, synthetic parser, and static launcher checks only)")


if __name__ == "__main__":
    main()
