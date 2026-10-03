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
SOURCE_REVISION = "469998db6e23e3ce68f000fa01bf2dc44f709ced"
SOURCE_ARCHIVE_SHA256 = "3ab4701771809777afe6555c382da8719ed8b201844ebcabff85a82959199100"
PRESCRIBED_STAGE = Path("/root/rhai-linux-process-options-20261003-469998db")
PRESCRIBED_SCOPE = Path("/root/.local/share/agent-builds/rhai/linux-process-options-20261003-469998db")
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
    "process_output_limit_is_primary_and_retains_each_stream_prefix_at_n_plus_one",
    "zero_output_cap_reports_output_limit_with_an_empty_retained_prefix",
    "run_deadline_returns_bounded_partial_output_after_terminating_child",
    "unit_timeout_disables_configured_default_deadline",
    "unit_stdin_means_immediate_eof",
    "process_cwd_uses_the_opened_filesystem_capability_after_root_replacement",
    "lossy_run_reports_engine_limit_expansion_without_returning_truncated_text",
)
CONTROL_TESTS = {
    "capture-raw-code0": TESTS[0], "capture-raw-code7": TESTS[0],
    "capture-text-code0": TESTS[0], "capture-text-code7": TESTS[0],
    "overflow-stdout": TESTS[1], "overflow-stderr": TESTS[1],
    "zero-none": TESTS[2], "zero-stdout": TESTS[2], "zero-stderr": TESTS[2],
    "deadline-raw": TESTS[3], "deadline-text": TESTS[3],
    "unit-timeout": TESTS[4], "unit-stdin": TESTS[5],
    "cwd-positive": TESTS[6], "cwd-denial": TESTS[6],
    "lossy-expansion": TESTS[7],
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


def apply_control_overlay(control: str, original: bytes) -> str:
    text = original.decode("utf-8")
    def edit(name: str, old: str, new: str, label: str) -> None:
        nonlocal text
        start, end, fn = function_slice(text, name)
        fn = replace_once(fn, old, new, label)
        text = text[:start] + fn + text[end:]
    def add_after(name: str, anchor: str, addition: str, label: str) -> None:
        edit(name, anchor, anchor + addition, label)
    capture = TESTS[0]
    if control.startswith("capture-"):
        _, mode, code_label = control.split("-")
        code = int(code_label.removeprefix("code"))
        add_after(capture, '        let result = engine.eval::<Map>(&script).unwrap();\n',
                  '        assert_child_record(&records.path().join("child-record.txt"), code);\n', control+" cleanup")
        if mode == "raw":
            add_after(capture, '        let result = engine.eval::<Map>(&script).unwrap();\n        assert_child_record(&records.path().join("child-record.txt"), code);\n',
                      receipt_block(control, '&records.path().join("child-record.txt")'), control+" raw-child receipt")
            edit(capture, '        let mut expected_stdout = LIBTEST_QUIET_START.to_vec();',
                 f'        let mut expected_stdout = LIBTEST_QUIET_START.to_vec();\n        if code == {code} {{ eprintln!("{control} intended_wrong_expectation=true"); expected_stdout[0] ^= 1; }}', control+" wrong raw value")
            edit(capture, '        assert_eq!(result["stdout"].clone().try_cast::<Blob>().unwrap(), expected_stdout);',
                 '        assert_eq!(result["stdout"].clone().try_cast::<Blob>().unwrap(), expected_stdout, "capture raw expected deliberate mismatch");', control+" raw mismatch diagnostic")
        else:
            if 'const LIBTEST_QUIET_START: &[u8] = b"\\nrunning 1 test\\n";' not in text:
                raise RuntimeError("text mapping mutation anchor is absent from the frozen fixture output")
            add_after(capture, '        let text_result = engine.eval::<Map>(&script.replacen("run_raw(", "run(", 1)).unwrap();',
                     '\n        assert_child_record(&records.path().join("child-record.txt"), code);\n'+receipt_block(control, '&records.path().join("child-record.txt")'), control+" text-child cleanup")
            edit(capture, '        let expected_stdout_text = String::from_utf8_lossy(&expected_stdout);',
                 f'        let expected_stdout_text = String::from_utf8_lossy(&expected_stdout);\n        let expected_stdout_text = if code == {code} {{ expected_stdout_text.replacen("test", "xest", 1) }} else {{ expected_stdout_text.into_owned() }};', control+" wrong text value")
            edit(capture, '        assert_eq!(text_result["stdout"].as_immutable_string_ref().unwrap().as_str(), expected_stdout_text);',
                 f'        if code == {code} {{ eprintln!("{control} intended_wrong_expectation=true"); }}\n        assert_eq!(text_result["stdout"].as_immutable_string_ref().unwrap().as_str(), expected_stdout_text, "capture text expected deliberate mismatch");', control+" intended RED marker")
    elif control.startswith("overflow-"):
        name=TESTS[1]
        add_after(name, '        let error = engine.eval::<Map>(&script).unwrap_err();\n',
                  '        assert_io_stress_record(&record_path, INPUT_BYTES, false);\n'+receipt_block(control, '&record_path'), control+" cleanup")
        if control.endswith("stdout"):
            edit(name, "prefix.extend(std::iter::repeat(b'o').take(CAP - LIBTEST_QUIET_START.len()));", "prefix.extend(std::iter::repeat(b'x').take(CAP - LIBTEST_QUIET_START.len()));", control+" wrong prefix")
            edit(name, 'assert_output_limit_error(error, stream, &expected_prefix);', 'if stream == "stdout" { eprintln!("overflow-stdout intended_wrong_expectation=true"); }\n        assert_output_limit_error(error, stream, &expected_prefix);', control+" RED marker")
        else:
            edit(name, "vec![b'e'; CAP]", "vec![b'x'; CAP]", control+" wrong prefix")
            edit(name, 'assert_output_limit_error(error, stream, &expected_prefix);', 'if stream == "stderr" { eprintln!("overflow-stderr intended_wrong_expectation=true"); }\n        assert_output_limit_error(error, stream, &expected_prefix);', control+" RED marker")
    elif control.startswith("zero-"):
        name=TESTS[2]
        rb='\n        let record = std::fs::read_to_string(&record_path).unwrap();\n        let pid: libc::pid_t = record.trim().strip_prefix("child-pid=").unwrap().parse().unwrap();\n        assert_eq!(unsafe { libc::kill(pid, 0) }, -1);\n        assert_eq!(std::io::Error::last_os_error().raw_os_error(), Some(libc::ESRCH));\n        eprintln!("'+control+' reap=ESRCH pid={pid}");\n'
        if control == "zero-none":
            add_after(name, '            let result = engine.eval::<Map>(&script).unwrap();', rb, control+" cleanup")
            edit(name, 'assert!(result["stdout"].as_immutable_string_ref().unwrap().as_str().is_empty());', 'eprintln!("zero-none intended_wrong_expectation=true"); assert!(!result["stdout"].as_immutable_string_ref().unwrap().as_str().is_empty(), "zero-none expected non-empty output");', control+" wrong expectation")
        else:
            add_after(name, '            let error = engine.eval::<Map>(&script).unwrap_err();', rb, control+" cleanup")
            target = "stdout" if control == "zero-stdout" else "stderr"
            edit(name, 'assert_output_limit_error(error, stream, &[]);',
                 f'if stream == "{target}" {{ eprintln!("{control} intended_wrong_expectation=true"); }}\n            assert_output_limit_error(error, stream, if stream == "{target}" {{ &[b\'x\'] }} else {{ &[] }});',
                 control+" wrong prefix")
    elif control.startswith("deadline-"):
        name=TESTS[3]
        add_after(name, '        assert!(result["timed_out"].as_bool().unwrap());', '\n        assert_timed_child_record(&record_path);\n'+receipt_block(control, '&record_path'), control+" cleanup")
        if control == "deadline-raw":
            edit(name, '            assert!(stdout.windows(b"timeout-out\\n".len()).any(|b| b == b"timeout-out\\n"));', '            if raw { eprintln!("deadline-raw intended_wrong_expectation=true"); }\n            assert!(stdout.windows(b"wrong-out\\n".len()).any(|b| b == b"wrong-out\\n"), "deadline-raw expected wrong-out marker");', control+" wrong marker")
        else:
            edit(name, '            assert!(stdout.contains("timeout-out\\n"));', '            if !raw { eprintln!("deadline-text intended_wrong_expectation=true"); }\n            assert!(stdout.contains("wrong-out\\n"), "deadline-text expected wrong-out marker");', control+" wrong marker")
    elif control == "unit-timeout":
        name=TESTS[4]
        add_after(name, '    let result = engine.eval::<Map>(&script).unwrap();', '\n    assert_timed_child_record(&record_path);\n'+receipt_block(control, '&record_path'), control+" cleanup")
        edit(name, 'assert!(!result["timed_out"].as_bool().unwrap());', 'eprintln!("unit-timeout intended_wrong_expectation=true"); assert!(result["timed_out"].as_bool().unwrap(), "unit-timeout expected timed_out=true");', control+" wrong expectation")
    elif control == "unit-stdin":
        name=TESTS[5]
        add_after(name, '    let stdout = result["stdout"].clone().try_cast::<Blob>().unwrap();', '\n    assert_child_record(&records.path().join("stdin-record.txt"), 0);\n'+receipt_block(control, '&records.path().join("stdin-record.txt")'), control+" cleanup")
        edit(name, 'expected.extend_from_slice(b"stdin-eof");', 'expected.extend_from_slice(b"wrong-eof");', control+" wrong expected bytes")
        edit(name, 'assert_eq!(stdout, expected);', 'eprintln!("unit-stdin intended_wrong_expectation=true");\n    assert_eq!(stdout, expected, "unit-stdin expected deliberately wrong bytes");', control+" wrong output")
    elif control == "cwd-positive":
        name = TESTS[6]
        path_assert = '    assert_eq!(path, format!("{}\\n", expected_cwd.display()));'
        edit(name, path_assert, "", control+" move original assertion")
        add_after(name, '    assert!(!attempted_record.exists(), "child started before cwd denial");',
                  '\n    eprintln!("cwd attempted-record-absent=true");\n    eprintln!("cwd-positive intended_wrong_expectation=true");\n'+path_assert.replace('format!("{}\\n", expected_cwd.display())', '"wrong-cwd\\n"'),
                  control+" wrong path after absence readback")
    elif control == "cwd-denial":
        edit(TESTS[6], '    assert!(denied, "symlink escape was not denied: {error:?}");\n    assert!(!attempted_record.exists(), "child started before cwd denial");', '    assert!(!attempted_record.exists(), "child started before cwd denial");\n    eprintln!("cwd attempted-record-absent=true");\n    eprintln!("cwd-denial intended_wrong_expectation=true");\n    assert!(!denied, "cwd-denial wrong-process-option expectation: {error:?}");', control+" absence before RED")
    elif control == "lossy-expansion":
        name=TESTS[7]
        add_after(name, '    assert_child_record(&records.path().join("child-record.txt"), 0);', '\n'+receipt_block(control, '&records.path().join("child-record.txt")'), control+" cleanup")
        edit(name, 'assert_eq!(report.stdout_bytes().last(), Some(&0xff));', 'eprintln!("lossy-expansion intended_wrong_expectation=true"); assert_eq!(report.stdout_bytes().last(), Some(&0xfe), "lossy-expansion expected wrong final byte");', control+" wrong byte")
    else:
        raise RuntimeError(f"unsupported control {control}")
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
        for control_index, (label, test_name) in enumerate(CONTROL_TESTS.items()):
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
            if label in ("cwd-positive", "cwd-denial"):
                expected_diagnostics.append("cwd attempted-record-absent=true")
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
                "zero-none": "zero-none expected non-empty output",
                "zero-stdout": "assertion `left == right` failed",
                "zero-stderr": "assertion `left == right` failed",
                "deadline-raw": "deadline-raw expected wrong-out marker",
                "deadline-text": "deadline-text expected wrong-out marker",
                "unit-timeout": "unit-timeout expected timed_out=true",
                "unit-stdin": "unit-stdin expected deliberately wrong bytes",
                "cwd-positive": "assertion `left == right` failed",
                "cwd-denial": "cwd-denial wrong-process-option expectation",
                "lossy-expansion": "lossy-expansion expected wrong final byte",
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
        "test_invocations_expected": len(FEATURE_ROWS) * (len(TESTS) + len(CONTROL_TESTS)),
        "setup_commands_expected": 3,
        "commands_expected": len(FEATURE_ROWS) * (len(TESTS) + len(CONTROL_TESTS)) + 3,
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
