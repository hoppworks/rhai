#!/usr/bin/env python3
"""Read-only preflight for the frozen Linux overhead measurement inputs."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import tarfile


REVISION = "00bed4a0dfeb103ff209ba4c76dac7ae797b7c56"
ARCHIVE_SHA = "5414ea195ad00152b1eae36b3f4e10943ba5d9bf323baff6410cca0c5b4d8b98"
BASELINE_SHA = "8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa"
EDGE_LOCK_SHA = "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425"
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
    driver_path = stage / "measure-process-overhead.py"
    proof_path = stage / "process-overhead-proof.py"
    launcher_path = stage / "remote-overhead-launch.sh"
    contract_path = stage / "linux-overhead-launch-contract.md"
    runner_path = stage / "runner/tools/run_scoped.py"
    files = (archive, lock_path, driver_path, proof_path, launcher_path, contract_path, runner_path)
    if any(not path.is_file() or path.is_symlink() for path in files):
        raise SystemExit("preflight failed: a required staged regular file is missing or symlinked")
    if sha(archive.read_bytes()) != ARCHIVE_SHA or sha(lock_path.read_bytes()) != BASELINE_SHA:
        raise SystemExit("preflight failed: candidate archive or baseline lock hash mismatch")

    with tarfile.open(archive, "r") as source:
        members = {member.name: member for member in source.getmembers() if member.isfile()}
        absent = [relative for relative in SOURCE_PATHS if relative not in members]
        if absent:
            raise SystemExit(f"preflight failed: source archive omits manifest paths: {absent}")
        manifest = source.extractfile(members["Cargo.toml"]).read()
        test_source = source.extractfile(members["tests/sys_process.rs"]).read()
    if b'libc = { version = "=0.2.189", optional = true }' not in manifest:
        raise SystemExit("preflight failed: exact optional libc edge not found in frozen source")
    if b"fn process_scope_overhead_measurement()" not in test_source or b"const PAIRS: usize = 30" not in test_source:
        raise SystemExit("preflight failed: frozen source lacks the fixed 120-sample test")

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
    proof = proof_path.read_text(encoding="utf-8")
    launcher = launcher_path.read_text(encoding="utf-8")
    contract = contract_path.read_text(encoding="utf-8")
    if "--source-revision" not in driver or "--source-archive-sha256" not in driver:
        raise SystemExit("preflight failed: extracted archive provenance arguments are absent")
    if REVISION not in proof or ARCHIVE_SHA not in proof or BASELINE_SHA not in proof or EDGE_LOCK_SHA not in proof:
        raise SystemExit("preflight failed: runtime verifier is not bound to reviewed inputs")
    if "process-overhead-proof.py" not in launcher or "--timeout 585" not in launcher:
        raise SystemExit("preflight failed: launcher does not dispatch the measurement or preserve scoped bound")
    if not re.search(r"timeout --signal=TERM --kill-after=2 598s", contract):
        raise SystemExit("preflight failed: expected explicit 600-second outer timeout wrapper is not recorded")

    print(f"preflight=pass revision={REVISION}")
    print(f"archive_sha256={ARCHIVE_SHA}")
    print(f"baseline_lock_sha256={BASELINE_SHA}")
    print(f"private_edge_lock_sha256={EDGE_LOCK_SHA}")
    for path in files:
        print(f"file_sha256={sha(path.read_bytes())} path={path.name}")
    print("manifest_paths=" + ",".join(SOURCE_PATHS))
    print("limits=outer600 scoped585 driver580 cargo540 jobs2 descendants16 memory2GiB sampled-stop1572864KiB@1s samples120 warmups0 retries0")
    print("execution=none (hash, archive, lock, and static launcher checks only)")


if __name__ == "__main__":
    main()
