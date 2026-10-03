"""Bounded adapter over the accepted Linux 1.77.2 process/resource primitives."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import sys
import time
import traceback

BASE_SHA256 = "59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06"
SOURCE_REVISION = "08507d6831f73f28aa0b95a4255c5df8ebe2ec13"
SOURCE_ARCHIVE_SHA256 = "37e2b95ac05bcc8291b48eb7aac01ac6c260b27d18669d78935009e6bb579e03"
PRESCRIBED_STAGE = Path("/root/rhai-linux-wait-entry-20261003-08507d68")
PRESCRIBED_SCOPE = Path("/root/.local/share/agent-builds/rhai/linux-wait-entry-20261003-08507d68")
LOCK_SHA256 = "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425"
TEST = "packages::sys::process::unix::tests::public_wait_is_cancelled_after_entering_condvar"
FEATURE_ROWS = (
    "testing-environ,sys,sync",
    "testing-environ,sys,sync,no_float",
)
HELPER = None


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_positive_row(h, name: str, status: int, output: str) -> None:
    required = (
        f"test result: ok. 1 passed; 0 failed; 0 ignored;",
        f"{TEST} ... ok",
        "wait-entry checkpoint pid=",
        "nonterminal=true",
        "shared-child entered-wait pid=",
        "nonterminal_at_cancel=true waiter_woke=true reap=ESRCH",
    )
    for receipt in required:
        if receipt not in output:
            raise RuntimeError(f"{name} lacks required receipt: {receipt!r}")
    checkpoint = re.search(r"wait-entry checkpoint pid=\d+ count=(\d+) nonterminal=true", output)
    if checkpoint is None or int(checkpoint.group(1)) <= 0:
        raise RuntimeError(f"{name} lacks a positive nonterminal wait-entry checkpoint")
    entry_receipt = re.search(
        r"shared-child entered-wait pid=\d+ wait_entries=(\d+) "
        r"nonterminal_at_cancel=true waiter_woke=true reap=ESRCH",
        output,
    )
    if entry_receipt is None or int(entry_receipt.group(1)) <= 0:
        raise RuntimeError(f"{name} lacks a positive cancellation wait-entry receipt")
    h.verify_pass(name, status, output, "1 passed; 0 failed;")


def main() -> int:
    global HELPER
    stage = Path(os.environ["PROOF_STAGE"])
    runtime = Path(os.environ["AGENT_RUNTIME_DIR"])
    base = stage / "check-linux-current-msrv-examples.py"
    if sha(base) != BASE_SHA256:
        raise RuntimeError("accepted base helper pin mismatch")
    spec = importlib.util.spec_from_file_location("accepted_linux_helper", base)
    assert spec and spec.loader
    h = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
    HELPER = h
    signal.signal(signal.SIGTERM, h.on_signal)
    signal.signal(signal.SIGINT, h.on_signal)

    # Reuse reviewed identity, deadline, sampling, command, archive and restoration
    # primitives while keeping this package's paths and limits local.
    h.INPUT_STAGE = stage
    h.EXPECTED_STAGE = Path(os.environ["EXPECTED_PROOF_STAGE"])
    h.PRESCRIBED_STAGE = PRESCRIBED_STAGE
    h.PRESCRIBED_SCOPE = PRESCRIBED_SCOPE
    h.RUNTIME = runtime
    h.STAGE = runtime / "evidence"
    h.EVIDENCE = stage / "proof-evidence"
    h.CONTRACT = stage / "contract.md"
    h.SOURCE_ARCHIVE = stage / "source.tar"
    h.LOCK_SOURCE = stage / "Cargo.lock.accepted"
    h.RUSTUP = Path(os.environ["RUSTUP_BIN"])
    h.LOCK_SHA256 = LOCK_SHA256
    h.SOURCE_ARCHIVE_SHA256 = SOURCE_ARCHIVE_SHA256
    h.REVISION = SOURCE_REVISION
    h.TOOLCHAIN = "1.77.2-x86_64-unknown-linux-gnu"
    h.START = time.monotonic()
    h.DEADLINE = h.START + 540
    h.WORK_DEADLINE = h.DEADLINE - 30
    h.SOURCE = runtime / "source"
    h.CARGO_HOME = runtime / "cargo-home"
    h.RUSTUP_HOME = runtime / "rustup-home"
    h.TARGET = runtime / "target"
    h.PRIVATE_HOME = runtime / "home"
    h.PRIVATE_TMP = Path(os.environ["TMPDIR"])
    h.capture_runtime_proof()
    h.validate_stage_inputs()
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        raise RuntimeError("native Linux x86_64 is required")
    h.write_json(h.STAGE / "source-inputs.json", {
        "revision": SOURCE_REVISION, "archive_sha256": sha(h.SOURCE_ARCHIVE),
        "lock_sha256": sha(h.LOCK_SOURCE), "base_helper_sha256": BASE_SHA256,
    })
    for folder in (h.CARGO_HOME, h.RUSTUP_HOME, h.PRIVATE_HOME):
        folder.mkdir(mode=0o700)
    h.PRIVATE_TMP.mkdir(mode=0o700, exist_ok=True)
    env = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(h.PRIVATE_HOME),
        "TMPDIR": str(h.PRIVATE_TMP), "TMP": str(h.PRIVATE_TMP), "TEMP": str(h.PRIVATE_TMP),
        "CARGO_HOME": str(h.CARGO_HOME), "RUSTUP_HOME": str(h.RUSTUP_HOME),
        "CARGO_TARGET_DIR": str(h.TARGET), "CARGO_BUILD_JOBS": "2",
        "CARGO_INCREMENTAL": "0", "CARGO_PROFILE_DEV_DEBUG": "0",
        "CARGO_TERM_COLOR": "never", "RUST_BACKTRACE": "0",
        "AGENT_RUNTIME_DIR": str(runtime),
    }
    h.extract_archive(h.SOURCE_ARCHIVE)
    shutil.copy2(h.LOCK_SOURCE, h.SOURCE / "Cargo.lock")
    original_manifests = h.manifest_hashes()
    h.write_json(h.STAGE / "source-lock-manifests.json", {
        "revision": SOURCE_REVISION, "manifests_sha256": original_manifests,
        "lock_sha256": sha(h.SOURCE / "Cargo.lock"),
    })
    h.run_command("rustup-install", [str(h.RUSTUP), "toolchain", "install", h.TOOLCHAIN,
                                     "--profile", "minimal", "--no-self-update"], env, cwd=runtime)
    bin_dir = h.RUSTUP_HOME / "toolchains" / h.TOOLCHAIN / "bin"
    rustc, cargo = bin_dir / "rustc", bin_dir / "cargo"
    if not rustc.is_file() or not cargo.is_file():
        raise RuntimeError("private Rust 1.77.2 toolchain is incomplete")
    env["PATH"] = f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin"
    env["RUSTC"] = str(rustc)
    h.run_command("rustc-version", [str(rustc), "--version", "--verbose"], env)
    h.run_command("cargo-version", [str(cargo), "--version", "--verbose"], env)
    test_path = h.SOURCE / "src/packages/sys/process/unix.rs"
    original = test_path.read_bytes()
    h.ORIGINAL_EXAMPLES[test_path] = original
    relative = test_path.relative_to(h.SOURCE).as_posix()
    h.ORIGINAL_EXAMPLE_HASHES[relative] = hashlib.sha256(original).hexdigest()
    text = original.decode("utf-8")
    assertion = "            entered_waits > 0,"
    if text.count(assertion) != 1:
        raise RuntimeError("wait-entry assertion anchor must occur exactly once")
    test_path.write_bytes(text.replace(assertion, "            entered_waits == 0,", 1).encode())
    h.INJECTED_EXAMPLE_HASHES[relative] = sha(test_path)
    for index, features in enumerate(FEATURE_ROWS):
        cargo_args = [str(cargo), "test", "--locked", "--features", features,
                      "--lib", TEST, "--", "--exact", "--nocapture", "--test-threads=1"]
        try:
            h.run_command(f"row-{index}-wrong-wait-entry", cargo_args, env, expected_status=101)
            wrong_log = (h.read_text(h.STAGE / f"row-{index}-wrong-wait-entry.stdout")
                         + h.read_text(h.STAGE / f"row-{index}-wrong-wait-entry.stderr"))
            h.verify_control(
                f"row-{index}-wrong-wait-entry", 101, 101, wrong_log,
                ["wait-entry checkpoint pid=", "count=", "nonterminal=true",
                 "observer acquired snapshot mutex after Condvar wait entry",
                 "FAILED", "wait-entry fixture cleanup pid=", "reap=ESRCH"],
            )
            checkpoint = re.search(r"wait-entry checkpoint pid=\d+ count=(\d+) nonterminal=true", wrong_log)
            cleanup = re.search(r"wait-entry fixture cleanup pid=\d+ reap=ESRCH", wrong_log)
            if checkpoint is None or int(checkpoint.group(1)) <= 0 or cleanup is None:
                raise RuntimeError(f"row-{index}-wrong-wait-entry lacks positive checkpoint or reaped fixture receipt")
        finally:
            h.restore_example_sources()
        if sha(test_path) != hashlib.sha256(original).hexdigest():
            raise RuntimeError("private source restoration mismatch")
        h.run_command(f"row-{index}-green", cargo_args, env)
        output = (h.read_text(h.STAGE / f"row-{index}-green.stdout")
                  + h.read_text(h.STAGE / f"row-{index}-green.stderr"))
        verify_positive_row(h, f"row-{index}-green", 0, output)
        if h.manifest_hashes() != original_manifests or sha(h.SOURCE / "Cargo.lock") != LOCK_SHA256:
            raise RuntimeError("Cargo manifest or compatible lock changed")
        if index == 0:
            # Restore before overlaying the same private assertion for the next row.
            test_path.write_bytes(text.replace(assertion, "            entered_waits == 0,", 1).encode())
            h.INJECTED_EXAMPLE_HASHES[relative] = sha(test_path)
    h.write_json(h.STAGE / "package-result.json", {
        "revision": SOURCE_REVISION, "test": TEST, "features": FEATURE_ROWS,
        "rows": h.CONTROL_RESULTS, "acceptance_claim": False,
        "note": "Preparation recipe only until native wait-entry receipts and independent cleanup readback are reviewed.",
    })
    return 0


def export_evidence() -> None:
    h = HELPER
    if h is None or not h.STAGE.is_dir() or h.EVIDENCE.exists():
        return
    h.check_deadline(during_export=True)
    restoration_error = None
    try:
        if h.ORIGINAL_EXAMPLES:
            h.restore_example_sources()
    except BaseException:
        restoration_error = traceback.format_exc()
        (h.STAGE / "restoration-failure.txt").write_text(restoration_error)
    h.write_json(h.STAGE / "source-restoration.json", {
        "original_test_sha256": h.ORIGINAL_EXAMPLE_HASHES,
        "private_overlay_sha256": h.INJECTED_EXAMPLE_HASHES,
        "restored_test_matches_original": bool(h.ORIGINAL_EXAMPLES) and all(
            h.sha256(path) == h.ORIGINAL_EXAMPLE_HASHES[path.relative_to(h.SOURCE).as_posix()]
            for path in h.ORIGINAL_EXAMPLES
        ),
        "manifests_sha256_after_restoration": h.manifest_hashes() if h.SOURCE.is_dir() else {},
        "cargo_lock_sha256_after_execution": h.sha256(h.SOURCE / "Cargo.lock")
            if (h.SOURCE / "Cargo.lock").is_file() else None,
        "restoration_error": restoration_error,
    })
    h.write_json(h.STAGE / "resource-samples.json", {
        "samples": h.SAMPLES, "sampled_maxima": h.MAXIMA,
        "samples_are_periodic_not_continuous_peak": True,
        "storage_preemptive_stop_kib": h.PREEMPTIVE_STORAGE_KIB,
        "storage_hard_stop_kib": h.HARD_STORAGE_KIB,
        "rss_hard_stop_kib": h.HARD_RSS_KIB,
        "max_descendants": h.MAX_DESCENDANTS,
    })
    h.write_json(h.STAGE / "package-result.json", {
        "source_revision": SOURCE_REVISION, "compatible_lock_sha256": LOCK_SHA256,
        "test": TEST, "feature_rows": FEATURE_ROWS, "controls": h.CONTROL_RESULTS,
        "commands": h.COMMANDS, "all_rows_passed": len(h.CONTROL_RESULTS) == 4
            and all(row.get("status") == row.get("expected_status") for row in h.CONTROL_RESULTS),
        "acceptance_claim": False,
        "restoration_error": restoration_error,
        "scope": "Two native Linux 1.77.2 exact public wait-entry test rows; independent process cleanup readback still required.",
        "criteria": [
            "wrong-wait-entry exits 101 at observer acquired snapshot mutex after Condvar wait entry and cleanup reports reap=ESRCH",
            "green row reports one exact test passed, positive entered wait count, nonterminal_at_cancel=true, waiter_woke=true, and reap=ESRCH",
        ],
    })
    h.write_json(h.STAGE / "export.json", {
        "runtime": str(h.RUNTIME), "scope": str(h.RUNTIME.parent),
        "destination": str(h.EVIDENCE),
        "elapsed_seconds_at_export": round(time.monotonic() - h.START, 3),
        "export_reserve_seconds": 30,
    })
    h.EVIDENCE.mkdir(mode=0o700)
    for item in h.STAGE.iterdir():
        h.check_deadline(during_export=True)
        target = h.EVIDENCE / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    if restoration_error:
        raise RuntimeError("private test source restoration failed; evidence exported")


if __name__ == "__main__":
    status = 1
    try:
        status = main()
    except BaseException as exc:
        if HELPER is not None and HELPER.STAGE.is_dir():
            (HELPER.STAGE / "failure.txt").write_text("".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)))
        traceback.print_exc()
        status = 1
    finally:
        try:
            export_evidence()
        except BaseException:
            traceback.print_exc()
            status = 1
    raise SystemExit(status)
