"""Bounded adapter for exact public Engine process-I/O integration tests."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import sys
import time
import traceback

BASE_SHA256 = "59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06"
SOURCE_REVISION = "9e56d5f2ef42303493907907454562f72a24b60b"
SOURCE_ARCHIVE_SHA256 = "40ddedbf8ff27d21c4be7066cb54f20be4192f5ae01de05579064cca4a254a61"
PRESCRIBED_STAGE = Path("/root/rhai-linux-process-io-20261003-9e56d5f2")
PRESCRIBED_SCOPE = Path("/root/.local/share/agent-builds/rhai/linux-process-io-20261003-9e56d5f2")
LOCK_SHA256 = "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425"
TEST_FILE = Path("tests/sys_process.rs")
FEATURE_ROWS = (
    "testing-environ,sys",
    "testing-environ,sys,sync",
    "testing-environ,sys,metadata,serde",
    "testing-environ,sys,net,sync,metadata,serde",
    "testing-environ,sys,f32_float",
)
TESTS = (
    "run_raw_captures_exact_stream_bytes_and_nonzero_exit_as_data",
    "process_supervisor_handles_large_simultaneous_io_and_exact_per_stream_caps",
    "process_output_limit_is_primary_and_retains_each_stream_prefix_at_n_plus_one",
    "zero_output_cap_reports_output_limit_with_an_empty_retained_prefix",
    "run_deadline_returns_bounded_partial_output_after_terminating_child",
    "run_deadline_with_blocked_stdin_and_active_stdout_stderr",
    "unit_timeout_disables_configured_default_deadline",
    "unit_stdin_means_immediate_eof",
    "process_cwd_uses_the_opened_filesystem_capability_after_root_replacement",
    "lossy_run_reports_engine_limit_expansion_without_returning_truncated_text",
)
CONTROL_TESTS = {
    "process_supervisor_handles_large_simultaneous_io_and_exact_per_stream_caps": "simultaneous-io",
    "run_deadline_with_blocked_stdin_and_active_stdout_stderr": "deadline-io",
}
HELPER = None


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_command(cargo: Path, features: str, name: str) -> list[str]:
    return [str(cargo), "test", "--locked", "--features", features,
            "--test", "sys_process", name, "--", "--exact", "--nocapture",
            "--test-threads=1"]


def combined_output(h, name: str) -> str:
    return (h.read_text(h.STAGE / f"{name}.stdout")
            + h.read_text(h.STAGE / f"{name}.stderr"))


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"{label} anchor must occur exactly once; got {text.count(old)}")
    return text.replace(old, new, 1)


def receipt_block(label: str, path_expr: str) -> str:
    return (
        f'    let receipt = std::fs::read_to_string({path_expr}).unwrap();\n'
        '    let pid: libc::pid_t = receipt.split_whitespace().next().unwrap()\n'
        '        .strip_prefix("child-pid=").unwrap().parse().unwrap();\n'
        '    assert_eq!(unsafe { libc::kill(pid, 0) }, -1);\n'
        '    assert_eq!(std::io::Error::last_os_error().raw_os_error(), Some(libc::ESRCH));\n'
        f'    eprintln!("{label} reap=ESRCH pid={{pid}}");\n'
    )


def apply_control_overlay(name: str, original: bytes) -> str:
    text = original.decode("utf-8")
    if name == "process_supervisor_handles_large_simultaneous_io_and_exact_per_stream_caps":
        assertion = "    const EXPECTED_OUTPUT_BYTE: u8 = b'o';"
        text = replace_once(text, assertion,
                            "    const EXPECTED_OUTPUT_BYTE: u8 = b'x';", "wrong-byte control")
        reap = "    assert_io_stress_record(&records.path().join(\"exact-cap.txt\"), INPUT_BYTES, true);"
        receipt = receipt_block(
            "simultaneous-io",
            'records.path().join("exact-cap.txt")',
        )
        function_start = text.index(f"fn {name}() {{")
        function_end = text.index("\n#[test]", function_start)
        function = text[function_start:function_end]
        function = replace_once(function, reap, "", "simultaneous-I/O original reap assertion relocation")
        eval_anchor = "    let result = engine.eval::<Map>(&script).unwrap();\n"
        function = replace_once(function, eval_anchor, eval_anchor + reap + "\n" + receipt,
                                "simultaneous-I/O cleanup-before-output assertion")
        text = text[:function_start] + function + text[function_end:]
    elif name == "run_deadline_with_blocked_stdin_and_active_stdout_stderr":
        assertion = 'const ACTIVE_STDERR_MARKER: &str = "stderr-active-marker\\n";'
        text = replace_once(text, assertion,
                            'const ACTIVE_STDERR_MARKER: &str = "wrong-deadline-marker\\n";',
                            "wrong-deadline-marker control")
        anchor = (
            "        // Check independent child ownership before output assertions, so the wrong-marker\n"
            "        // control still proves that the timed-out child was terminated and reaped.\n"
            "        assert_timed_child_record(&record_path);\n"
        )
        text = replace_once(text, anchor,
                            anchor + receipt_block("deadline-io", "&record_path"),
                            "deadline-I/O independent reap receipt")
    else:
        raise RuntimeError(f"unsupported control test: {name}")
    return text


def verify_positive(h, name: str, status: int, output: str, test_name: str) -> None:
    required = (f"test {test_name} ... ok", "test result: ok. 1 passed; 0 failed; 0 ignored;")
    missing = [item for item in required if item not in output]
    if status != 0 or missing:
        raise RuntimeError(f"{name} exact positive test did not pass: status={status}, missing={missing!r}")
    h.verify_pass(name, status, output, "test result: ok. 1 passed; 0 failed; 0 ignored;")


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

    # Reuse only the accepted identity, deadline, resource, archive, command,
    # evidence-export and source-restoration primitives.
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
    test_path = h.SOURCE / TEST_FILE
    original = test_path.read_bytes()
    h.ORIGINAL_EXAMPLES[test_path] = original
    relative = test_path.relative_to(h.SOURCE).as_posix()
    original_hash = hashlib.sha256(original).hexdigest()
    h.ORIGINAL_EXAMPLE_HASHES[relative] = original_hash
    overlays: list[dict[str, str]] = []

    for row_index, features in enumerate(FEATURE_ROWS):
        for test_index, (test_name, label) in enumerate(CONTROL_TESTS.items()):
            overlay = apply_control_overlay(test_name, original)
            test_path.write_text(overlay, encoding="utf-8")
            overlay_hash = sha(test_path)
            h.INJECTED_EXAMPLE_HASHES[f"row-{row_index}-{label}"] = overlay_hash
            overlays.append({"row": str(row_index), "test": test_name,
                             "label": label, "sha256": overlay_hash,
                             "cleanup_assertion_unchanged": True,
                             "expectations_intentionally_wrong": True})
            h.write_json(h.STAGE / "control-source-overlays.json", {
                "original_test_sha256": original_hash,
                "overlays": overlays,
                "cleanup_assertion_unchanged": True,
                "expectations_intentionally_wrong": True,
                "private_only": True,
                "restored_byte_for_byte_after_every_control": True,
            })
            command_name = f"row-{row_index}-{label}-wrong-assertion"
            expected_diagnostics = (
                [f"test {test_name} ... FAILED", "stdout differs at byte", "left: 111", "right: 120",
                 "simultaneous-io reap=ESRCH pid="]
                if label == "simultaneous-io"
                else [f"test {test_name} ... FAILED", "stderr active-stream marker missing",
                      "deadline-io reap=ESRCH pid="]
            )
            try:
                h.run_command(command_name,
                              test_command(cargo, features, test_name), env,
                              expected_status=101)
                output = combined_output(h, command_name)
                h.verify_control(command_name, 101, 101, output, expected_diagnostics)
            finally:
                h.restore_example_sources()
            if sha(test_path) != original_hash:
                raise RuntimeError("private integration-test source restoration mismatch after RED")

        for test_index, test_name in enumerate(TESTS):
            command_name = f"row-{row_index}-test-{test_index}-green"
            h.run_command(command_name, test_command(cargo, features, test_name), env)
            verify_positive(h, command_name, 0, combined_output(h, command_name), test_name)
            if sha(test_path) != original_hash:
                raise RuntimeError("integration-test source is not original during GREEN")
        if h.manifest_hashes() != original_manifests or sha(h.SOURCE / "Cargo.lock") != LOCK_SHA256:
            raise RuntimeError("Cargo manifest or compatible lock changed")

    h.write_json(h.STAGE / "control-source-overlays.json", {
        "original_test_sha256": original_hash,
        "overlays": overlays,
        "cleanup_assertion_unchanged": True,
        "expectations_intentionally_wrong": True,
        "private_only": True,
        "restored_byte_for_byte_after_every_control": True,
    })
    h.write_json(h.STAGE / "package-result.json", {
        "revision": SOURCE_REVISION, "archive_sha256": SOURCE_ARCHIVE_SHA256,
        "compatible_lock_sha256": LOCK_SHA256, "test_file": str(TEST_FILE),
        "feature_rows": FEATURE_ROWS, "exact_tests": TESTS,
        "positive_count_expected": len(FEATURE_ROWS) * len(TESTS),
        "negative_controls_expected": len(FEATURE_ROWS) * len(CONTROL_TESTS),
        "commands_expected": len(FEATURE_ROWS) * (len(TESTS) + len(CONTROL_TESTS)),
        "limitations": [
            "Test-internal fresh PID reaping assertions are independent readbacks; short-lived fixture PIDs are not guaranteed in periodic process samples.",
            "The active-deadline cases prove the test's configured timeout behavior; this package makes no separate bounded-latency claim.",
        ],
        "acceptance_claim": False,
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
    rows = len(FEATURE_ROWS)
    positives = rows * len(TESTS)
    negatives = rows * len(CONTROL_TESTS)
    h.write_json(h.STAGE / "package-result.json", {
        "source_revision": SOURCE_REVISION, "compatible_lock_sha256": LOCK_SHA256,
        "test_file": str(TEST_FILE), "exact_tests": TESTS,
        "feature_rows": FEATURE_ROWS, "controls": h.CONTROL_RESULTS,
        "commands": h.COMMANDS,
        "all_commands_passed": len(h.CONTROL_RESULTS) == positives + negatives
            and all(row.get("status") == row.get("expected_status") for row in h.CONTROL_RESULTS),
        "source_restored": bool(h.ORIGINAL_EXAMPLES) and all(
            h.sha256(path) == h.ORIGINAL_EXAMPLE_HASHES[path.relative_to(h.SOURCE).as_posix()]
            for path in h.ORIGINAL_EXAMPLES
        ),
        "acceptance_claim": False,
        "restoration_error": restoration_error,
        "limitations": [
            "Test-internal fresh PID reaping assertions are independent readbacks; short-lived fixture PIDs are not guaranteed in periodic process samples.",
            "The active-deadline cases prove the test's configured timeout behavior; this package makes no separate bounded-latency claim.",
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
        raise RuntimeError("private integration-test source restoration failed; evidence exported")


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
