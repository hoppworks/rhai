"""Bounded adapter for exact public Engine process-options integration tests."""
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
SOURCE_REVISION = "6c451c5c99e751e50023a08912a035a2c8754ff6"
SOURCE_ARCHIVE_SHA256 = "a158051f476cddc02744ab551c76a5b2458d3a69910f673ee6fb39745411d391"
PRESCRIBED_STAGE = Path("/root/rhai-linux-process-feature-20261003-6c451c5c-92")
PRESCRIBED_SCOPE = Path("/root/.local/share/agent-builds/rhai/linux-process-feature-20261003-6c451c5c-92")
LOCK_SHA256 = "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425"
PATCH_SHA256 = "5cf5d4533ca3adb99a9313e710b91f184bf5f2ee90ce2e215644fddf71b17693"
BASELINE_TEST_SHA256 = "379db748d4b84a60538d172059df1feafaa62b337eaf49c1178d3e6467d40c74"
PATCHED_TEST_SHA256 = "8ec4d456672338920249446618ce768bc2fa1d29798d571dca1e897db87a076b"
OPTIONS_HELPER_SHA256 = "ac679734a00a39aec0369f96861655982320c75b637ae86d41adbe3104024503"
IO_HELPER_SHA256 = "00aba0d09535ab63e0ef4cf344f9d1ad31197456ad6adca11decab1ab2ec3396"
TEST_FILE = Path("tests/sys_process.rs")
FEATURE_ROWS = (
    "testing-environ,sys",
    "testing-environ,sys,only_i32,no_float",
    "testing-environ,sys,unchecked",
)
TESTS = (
    "run_raw_captures_exact_stream_bytes_and_nonzero_exit_as_data",
    "process_output_limit_is_primary_and_retains_each_stream_prefix_at_n_plus_one",
    "zero_output_cap_reports_output_limit_with_an_empty_retained_prefix",
    "run_deadline_returns_bounded_partial_output_after_terminating_child",
    "unit_timeout_disables_configured_default_deadline",
    "unit_stdin_means_immediate_eof",
    "process_cwd_uses_the_opened_filesystem_capability_after_root_replacement",
    "lossy_run_reports_engine_limit_expansion_without_returning_truncated_text",
    "process_supervisor_handles_large_simultaneous_io_and_exact_per_stream_caps",
    "run_deadline_with_blocked_stdin_and_active_stdout_stderr",
    "process_script_output_option_cannot_raise_the_host_cap",
)
CONTROL_TESTS = {
    "capture-raw-code0": TESTS[0], "capture-text-code7": TESTS[0],
    "overflow-stdout": TESTS[1], "overflow-stderr": TESTS[1],
    "zero-stdout": TESTS[2], "zero-stderr": TESTS[2],
    "deadline-raw": TESTS[3], "deadline-text": TESTS[3],
    "unit-timeout": TESTS[4], "unit-stdin": TESTS[5],
    "cwd-denial": TESTS[6],
    "lossy-expansion": TESTS[7],
    "simultaneous-io": TESTS[8], "deadline-io": TESTS[9],
    "host-cap-stdout": TESTS[10], "host-cap-stderr": TESTS[10],
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


def function_slice(text: str, name: str) -> tuple[int, int, str]:
    start = text.index(f"fn {name}() {{")
    ends = [x for x in (text.find("\n#[test]", start), text.find("\n#[cfg", start)) if x >= 0]
    end = min(ends) if ends else len(text)
    return start, end, text[start:end]


OPTIONS_ADAPTER = None
IO_ADAPTER = None


def load_adapter(path: Path, expected_sha256: str, module_name: str):
    if sha(path) != expected_sha256:
        raise RuntimeError(f"accepted control adapter pin mismatch: {path.name}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load control adapter: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def apply_control_overlay(control: str, original: bytes) -> str:
    if control in OPTIONS_ADAPTER.CONTROL_TESTS:
        return OPTIONS_ADAPTER.apply_control_overlay(control, original)
    if control == "simultaneous-io":
        text = IO_ADAPTER.apply_control_overlay(
            "process_supervisor_handles_large_simultaneous_io_and_exact_per_stream_caps", original)
        return replace_once(text, '    for (index, (actual, expected)) in stdout.iter().zip(&expected_stdout).enumerate() {',
                            '    eprintln!("simultaneous-io intended_wrong_expectation=true");\n    for (index, (actual, expected)) in stdout.iter().zip(&expected_stdout).enumerate() {',
                            "simultaneous-I/O RED marker")
    if control == "deadline-io":
        text = IO_ADAPTER.apply_control_overlay(
            "run_deadline_with_blocked_stdin_and_active_stdout_stderr", original)
        anchor = '            assert!(stderr.windows(ACTIVE_STDERR_MARKER.len()).any(|bytes| bytes == ACTIVE_STDERR_MARKER.as_bytes()), "stderr active-stream marker missing");'
        return replace_once(text, anchor,
                            '            eprintln!("deadline-io intended_wrong_expectation=true");\n' + anchor,
                            "deadline-I/O RED marker")
    if control in ("host-cap-stdout", "host-cap-stderr"):
        text = original.decode("utf-8")
        name = TESTS[10]
        target = "stdout" if control.endswith("stdout") else "stderr"
        start, end, function = function_slice(text, name)
        record_assert = '        assert_io_stress_record(&record_path, 0, false);'
        receipt = (
            '\n        let receipt = std::fs::read_to_string(&record_path).unwrap();\n'
            '        let pid: libc::pid_t = receipt.split_whitespace().next().unwrap()\n'
            '            .strip_prefix("child-pid=").unwrap().parse().unwrap();\n'
            '        assert_eq!(unsafe { libc::kill(pid, 0) }, -1);\n'
            '        assert_eq!(std::io::Error::last_os_error().raw_os_error(), Some(libc::ESRCH));\n'
            f'        eprintln!("{control} reap=ESRCH pid={{pid}}");'
        )
        function = replace_once(function, record_assert, record_assert + receipt,
                                control + " independent fixture receipt")
        function = replace_once(function, '        let expected_prefix = if stream == "stdout" {',
                                '        let mut expected_prefix = if stream == "stdout" {',
                                control + " selected prefix")
        assertion = '        assert_output_limit_error(error, stream, &expected_prefix);'
        replacement = (
            f'        if stream == "{target}" {{\n'
            f'            eprintln!("{control} intended_wrong_expectation=true");\n'
            '            expected_prefix[0] ^= 1;\n'
            '        }\n'
            + assertion
        )
        function = replace_once(function, assertion, replacement,
                                control + " selected wrong prefix")
        return text[:start] + function + text[end:]
    raise RuntimeError(f"unsupported process-feature control: {control}")

def verify_positive(h, name: str, status: int, output: str, test_name: str) -> None:
    required = (f"test {test_name} ... ok", "test result: ok. 1 passed; 0 failed; 0 ignored;")
    missing = [item for item in required if item not in output]
    if status != 0 or missing:
        raise RuntimeError(f"{name} exact positive test did not pass: status={status}, missing={missing!r}")
    h.verify_pass(name, status, output, "test result: ok. 1 passed; 0 failed; 0 ignored;")


def main() -> int:
    global HELPER, OPTIONS_ADAPTER, IO_ADAPTER
    stage = Path(os.environ["PROOF_STAGE"])
    runtime = Path(os.environ["AGENT_RUNTIME_DIR"])
    OPTIONS_ADAPTER = load_adapter(stage / "linux-process-options-control.py",
                                   OPTIONS_HELPER_SHA256, "accepted_options_control")
    IO_ADAPTER = load_adapter(stage / "linux-process-io-control.py",
                              IO_HELPER_SHA256, "accepted_io_control")
    if sha(stage / "process-feature.patch") != PATCH_SHA256:
        raise RuntimeError("process-feature source patch pin mismatch")
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
        "options_control_helper_sha256": OPTIONS_HELPER_SHA256,
        "io_control_helper_sha256": IO_HELPER_SHA256,
        "process_feature_patch_sha256": PATCH_SHA256,
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
    baseline_bytes = test_path.read_bytes()
    relative = test_path.relative_to(h.SOURCE).as_posix()
    baseline_hash = hashlib.sha256(baseline_bytes).hexdigest()
    if baseline_hash != BASELINE_TEST_SHA256:
        raise RuntimeError(f"baseline private test source pin mismatch: {baseline_hash}")

    baseline_checks = (
        ("only-i32-no-float", "testing-environ,sys,only_i32,no_float", "E0308"),
        ("unchecked", "testing-environ,sys,unchecked", "E0599"),
    )
    baseline_results = []
    for label, features, expected_code in baseline_checks:
        name = f"baseline-no-run-{label}"
        argv = [str(cargo), "test", "--locked", "--features", features,
                "--test", "sys_process", "--no-run"]
        h.run_command(name, argv, env, expected_status=101)
        output = combined_output(h, name)
        required = ("no method named `set_max_string_size`",) if expected_code == "E0599" else ("expected `i64`, found `i32`",)
        if expected_code not in output or any(term not in output for term in required):
            raise RuntimeError(f"{name} did not reproduce the expected test-compatibility diagnostic {expected_code}: {required!r}")
        baseline_results.append({"name": name, "features": features, "status": 101,
                                "expected_code": expected_code,
                                "expected_diagnostics": [expected_code, *required],
                                "compatibility_failure_not_product_red": True})
    h.write_json(h.STAGE / "baseline-compatibility.json", {
        "baseline_test_sha256": baseline_hash, "checks": baseline_results,
    })
    patch_command = ["patch", "-p1", "--batch", "--forward", "-i",
                     str(stage / "process-feature.patch")]
    h.run_command("apply-process-feature-patch", patch_command, env, cwd=h.SOURCE)
    patched_bytes = test_path.read_bytes()
    patched_hash = hashlib.sha256(patched_bytes).hexdigest()
    if patched_hash != PATCHED_TEST_SHA256:
        raise RuntimeError(f"patched private test source pin mismatch: {patched_hash}")
    h.ORIGINAL_EXAMPLES[test_path] = patched_bytes
    h.ORIGINAL_EXAMPLE_HASHES[relative] = patched_hash
    h.write_json(h.STAGE / "process-feature-patch.json", {
        "baseline_revision": SOURCE_REVISION,
        "baseline_test_sha256": baseline_hash,
        "patch_sha256": PATCH_SHA256,
        "patched_test_sha256": patched_hash,
        "private_source_only": True,
    })
    original = patched_bytes
    original_hash = patched_hash
    overlays: list[dict[str, str]] = []

    for row_index, features in enumerate(FEATURE_ROWS):
        row_controls = list(CONTROL_TESTS.items())
        if row_index == 0:
            row_controls = [(label, test_name) for label, test_name in row_controls
                            if label.startswith("host-cap-")]
        if "unchecked" in features:
            row_controls = [(label, test_name) for label, test_name in row_controls
                            if label != "lossy-expansion"]
        for control_index, (label, test_name) in enumerate(row_controls):
            overlay = apply_control_overlay(label, original)
            test_path.write_text(overlay, encoding="utf-8")
            overlay_hash = sha(test_path)
            h.INJECTED_EXAMPLE_HASHES[f"row-{row_index}-{label}"] = overlay_hash
            overlays.append({"row": str(row_index), "test": test_name, "label": label,
                             "sha256": overlay_hash, "cleanup_assertion_unchanged": True,
                             "expectations_intentionally_wrong": True})
            h.write_json(h.STAGE / "control-source-overlays.json", {
                "original_test_sha256": original_hash, "overlays": overlays,
                "cleanup_assertion_unchanged": True, "expectations_intentionally_wrong": True,
                "private_only": True, "restored_byte_for_byte_after_every_control": True,
            })
            command_name = f"row-{row_index}-control-{control_index}-{label}-red"
            expected_diagnostics = [f"test {test_name} ... FAILED"]
            if label == "cwd-denial":
                expected_diagnostics.append("cwd attempted-record-absent=true")
            elif label.startswith("host-cap-") or label in ("simultaneous-io", "deadline-io"):
                expected_diagnostics.append(f"{label} reap=ESRCH pid=")
            else:
                expected_diagnostics.append(f"{label} reap=ESRCH pid=")
            expected_diagnostics.append(f"{label} intended_wrong_expectation=true")
            assertion_diagnostics = {
                "capture-raw-code0": "capture raw expected deliberate mismatch",
                "capture-raw-code7": "capture raw expected deliberate mismatch",
                "capture-text-code0": "capture text expected deliberate mismatch",
                "capture-text-code7": "capture text expected deliberate mismatch",
                "overflow-stdout": "assertion `left == right` failed",
                "overflow-stderr": "assertion `left == right` failed",
                "zero-stdout": "assertion `left == right` failed",
                "zero-stderr": "assertion `left == right` failed",
                "deadline-raw": "deadline-raw expected wrong-out marker",
                "deadline-text": "deadline-text expected wrong-out marker",
                "unit-timeout": "unit-timeout expected timed_out=true",
                "unit-stdin": "unit-stdin expected deliberately wrong bytes",
                "cwd-positive": "assertion `left == right` failed",
                "cwd-denial": "cwd-denial wrong-process-option expectation",
                "lossy-expansion": "lossy-expansion expected wrong final byte",
                "simultaneous-io": "stdout differs at byte",
                "deadline-io": "stderr active-stream marker missing",
                "host-cap-stdout": "assertion `left == right` failed",
                "host-cap-stderr": "assertion `left == right` failed",
            }
            expected_diagnostics.append(assertion_diagnostics[label])
            expected_diagnostics.append("test result: FAILED. 0 passed; 1 failed;")
            try:
                h.run_command(command_name,
                              test_command(cargo, features, test_name), env,
                              expected_status=101)
                output = combined_output(h, command_name)
                h.verify_control(command_name, 101, 101, output, expected_diagnostics)
            finally:
                test_path.write_bytes(patched_bytes)
            if sha(test_path) != original_hash:
                raise RuntimeError("private integration-test source did not restore to reviewed patch after RED")

        row_tests = [test_name for test_name in TESTS
                     if not ("unchecked" in features and test_name == TESTS[7])]
        for test_index, test_name in enumerate(row_tests):
            command_name = f"row-{row_index}-test-{test_index}-green"
            h.run_command(command_name, test_command(cargo, features, test_name), env)
            verify_positive(h, command_name, 0, combined_output(h, command_name), test_name)
            if sha(test_path) != original_hash:
                raise RuntimeError("reviewed patched test source changed during GREEN")
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
    row_control_counts = [2, 16, 15]
    control_total = sum(row_control_counts)
    h.write_json(h.STAGE / "package-result.json", {
        "revision": SOURCE_REVISION, "archive_sha256": SOURCE_ARCHIVE_SHA256,
        "baseline_test_sha256": baseline_hash, "process_feature_patch_sha256": PATCH_SHA256,
        "patched_test_sha256": patched_hash,
        "compatible_lock_sha256": LOCK_SHA256, "test_file": str(TEST_FILE),
        "feature_rows": FEATURE_ROWS, "exact_tests": TESTS,
        "positive_count_expected_by_row": [11, 11, 10],
        "negative_control_count_expected_by_row": row_control_counts,
        "positive_count_expected": 32,
        "negative_controls_expected": control_total,
        "baseline_compatibility_no_run_checks": 2,
        "test_invocations_expected": 32 + control_total + 2,
        "setup_commands_expected": 3,
        "patch_application_commands": 1,
        "commands_expected": 32 + control_total + 2 + 1 + 3,
        "reused_positive_evidence": [
            "linux-process-options-evidence-90: unchanged pre-existing options assertions",
            "linux-process-io-evidence-89: simultaneous I/O and active deadline assertions",
        ],
        "limitations": [
            "Test-internal PID records and ESRCH checks are independent readbacks; short-lived fixture PIDs are not guaranteed in periodic process samples.",
            "The cwd positive case has no PID receipt; denied escape verifies no fixture record was written, not absence of every transient process.",
            "Raw/text capture iterations reuse a record path, so receipts do not uniquely map PID to each API call.",
            "Deadline checks prove configured timeout behavior and selected partial-output assertions; no separate upper-latency guarantee is claimed.",
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
    positive_counts = [sum(1 for name in TESTS if not ("unchecked" in row and name == TESTS[7]))
                       for row in FEATURE_ROWS]
    control_counts = [2, 16, 15]
    positives = sum(positive_counts)
    negatives = sum(control_counts)
    h.write_json(h.STAGE / "package-result.json", {
        "source_revision": SOURCE_REVISION, "compatible_lock_sha256": LOCK_SHA256,
        "test_file": str(TEST_FILE), "exact_tests": TESTS,
        "feature_rows": FEATURE_ROWS, "controls": h.CONTROL_RESULTS,
        "commands": h.COMMANDS,
        "positive_count_expected_by_row": positive_counts,
        "negative_control_count_expected_by_row": control_counts,
        "baseline_test_sha256": BASELINE_TEST_SHA256,
        "process_feature_patch_sha256": PATCH_SHA256,
        "patched_test_sha256": PATCHED_TEST_SHA256,
        "tested_source_identity": {"baseline_revision": SOURCE_REVISION,
                                   "patch_sha256": PATCH_SHA256,
                                   "patched_test_sha256": PATCHED_TEST_SHA256},
        "all_commands_passed": len(h.CONTROL_RESULTS) == positives + negatives
            and all(row.get("status") == row.get("expected_status") for row in h.CONTROL_RESULTS),
        "source_restored": bool(h.ORIGINAL_EXAMPLES) and all(
            h.sha256(path) == h.ORIGINAL_EXAMPLE_HASHES[path.relative_to(h.SOURCE).as_posix()]
            for path in h.ORIGINAL_EXAMPLES
        ),
        "acceptance_claim": False,
        "restoration_error": restoration_error,
        "limitations": [
            "Test-internal PID records and ESRCH checks are independent readbacks; short-lived fixture PIDs are not guaranteed in periodic process samples.",
            "The cwd positive case has no PID receipt; denied escape verifies no fixture record was written, not absence of every transient process.",
            "Raw/text capture iterations reuse a record path, so receipts do not uniquely map PID to each API call.",
            "Deadline checks prove configured timeout behavior and selected partial-output assertions; no separate upper-latency guarantee is claimed.",
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
