#![cfg(all(feature = "sys", unix))]
//! Public process execution contracts (Unix slice).

mod sys_support;

use rhai::packages::sys::{FsAccess, ProcessCause, ProgramPolicy, SysConfig, SysError};
#[cfg(not(feature = "no_index"))]
use rhai::Blob;
use rhai::Map;
#[cfg(not(feature = "no_index"))]
use std::io::{Read, Write};
#[cfg(not(feature = "no_index"))]
use std::process;
use sys_support::engine;
use sys_support::TempDir;

const FIXTURE_ENV: &str = "RHAI_SYS_PROCESS_FIXTURE";
const FIXTURE_RECORD_ENV: &str = "RHAI_SYS_PROCESS_FIXTURE_RECORD";
const LIBTEST_QUIET_START: &[u8] = b"\nrunning 1 test\n";

/// The process API re-executes this test binary so stdout/stderr and exit status come from
/// an independently supervised OS process rather than a mocked command implementation.
#[test]
#[cfg(not(feature = "no_index"))]
fn process_fixture() {
    if let Ok(code) = std::env::var(FIXTURE_ENV) {
        let record = std::env::var_os(FIXTURE_RECORD_ENV).expect("fixture record path");
        if std::env::var_os("RHAI_SYS_PROCESS_HOLD").is_some() {
            std::fs::write(record, format!("child-pid={} child-ready=1\n", process::id())).unwrap();
            let hold_for = std::env::var("RHAI_SYS_PROCESS_HOLD_FOR_MS").ok().map(|value| value.parse::<u64>().unwrap());
            let hold_started = std::time::Instant::now();
            let mut stdout = std::io::stdout().lock();
            let mut stderr = std::io::stderr().lock();
            loop {
                stdout.write_all(b"timeout-out\n").unwrap();
                stderr.write_all(b"timeout-err\n").unwrap();
                stdout.flush().unwrap();
                stderr.flush().unwrap();
                if hold_for.is_some_and(|millis| hold_started.elapsed() >= std::time::Duration::from_millis(millis)) {
                    process::exit(code.parse().unwrap());
                }
                std::thread::sleep(std::time::Duration::from_millis(2));
            }
        }
        std::fs::write(record, format!("child-pid={} child-exit={code}\n", process::id())).unwrap();
        if let Ok(count) = std::env::var("RHAI_SYS_PROCESS_INVALID_COUNT") {
            std::io::stdout().write_all(&vec![0xff; count.parse().unwrap()]).unwrap();
            process::exit(code.parse().unwrap());
        }
        if std::env::var_os("RHAI_SYS_PROCESS_READ_STDIN").is_some() {
            let mut input = Vec::new();
            std::io::stdin().read_to_end(&mut input).unwrap();
            std::io::stdout().write_all(if input.is_empty() { &b"stdin-eof"[..] } else { &b"stdin-data"[..] }).unwrap();
            process::exit(code.parse().unwrap());
        }
        std::io::stdout().write_all(&[0x00, 0x41, 0xff]).unwrap();
        std::io::stderr().write_all(&[0xfe, 0x42, 0x00]).unwrap();
        process::exit(code.parse().unwrap());
    }
}

#[test]
#[cfg(not(feature = "no_index"))]
fn run_raw_captures_exact_stream_bytes_and_nonzero_exit_as_data() {
    let engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    let executable = std::env::current_exe().unwrap();
    let executable = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");

    for code in [0, 7] {
        let records = TempDir::new();
        let record_path = records.path().join("child-record.txt");
        let record_path = record_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let script = format!(
            r#"run_raw("{executable}", ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
                env_clear: true,
                env: #{{ {FIXTURE_ENV}: "{code}", {FIXTURE_RECORD_ENV}: "{record_path}" }},
                max_output: 1024,
                timeout: 5.0
            }})"#
        );
        let result = engine.eval::<Map>(&script).unwrap();
        assert_eq!(result["success"].as_bool().unwrap(), code == 0);
        assert_eq!(result["code"].as_int().unwrap(), code);
        assert!(result["stdout_complete"].as_bool().unwrap());
        assert!(result["stderr_complete"].as_bool().unwrap());
        let mut expected_stdout = LIBTEST_QUIET_START.to_vec();
        expected_stdout.extend_from_slice(&[0x00, 0x41, 0xff]);
        assert_eq!(result["stdout"].clone().try_cast::<Blob>().unwrap(), expected_stdout);
        assert_eq!(result["stderr"].clone().try_cast::<Blob>().unwrap(), [0xfe, 0x42, 0x00]);
        assert_child_record(&records.path().join("child-record.txt"), code);
        let expected_stdout_text = String::from_utf8_lossy(&expected_stdout);
        let expected_stderr_text = String::from_utf8_lossy(&[0xfe, 0x42, 0x00]);
        let text_result = engine.eval::<Map>(&script.replacen("run_raw(", "run(", 1)).unwrap();
        assert_eq!(text_result["success"].as_bool().unwrap(), code == 0);
        assert_eq!(text_result["code"].as_int().unwrap(), code);
        assert!(text_result["stdout_complete"].as_bool().unwrap());
        assert!(text_result["stderr_complete"].as_bool().unwrap());
        assert_eq!(text_result["stdout"].as_immutable_string_ref().unwrap().as_str(), expected_stdout_text);
        assert_eq!(text_result["stderr"].as_immutable_string_ref().unwrap().as_str(), expected_stderr_text);
        assert_child_record(&records.path().join("child-record.txt"), code);
    }
}

#[cfg(not(feature = "no_index"))]
fn assert_child_record(path: &std::path::Path, code: i64) {
    let record = std::fs::read_to_string(path).unwrap();
    let fields: Vec<_> = record.split_whitespace().collect();
    assert_eq!(fields.len(), 2, "child record: {record:?}");
    let pid: libc::pid_t = fields[0].strip_prefix("child-pid=").unwrap().parse().unwrap();
    assert_eq!(fields[1], format!("child-exit={code}"));
    // The API must return only after its owned direct child has been reaped.
    assert_eq!(unsafe { libc::kill(pid, 0) }, -1, "child {pid} is still present");
    assert_eq!(std::io::Error::last_os_error().raw_os_error(), Some(libc::ESRCH));
}

#[test]
#[cfg(not(feature = "no_index"))]
fn run_deadline_returns_bounded_partial_output_after_terminating_child() {
    let engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    let executable = std::env::current_exe().unwrap();
    let executable = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    for raw in [true, false] {
        let records = TempDir::new();
        let record_path = records.path().join("timeout-record.txt");
        let record_literal = record_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let api = if raw { "run_raw" } else { "run" };
        let script = format!(
            r#"{api}("{executable}", ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
                env_clear: true,
                env: #{{ {FIXTURE_ENV}: "0", {FIXTURE_RECORD_ENV}: "{record_literal}", RHAI_SYS_PROCESS_HOLD: "1" }},
                max_output: 1048576,
                timeout: 0.1
            }})"#
        );
        let result = match engine.eval::<Map>(&script) {
            Ok(result) => result,
            Err(error) => {
                assert_timed_child_record(&record_path);
                let sys_error = match error.as_ref() {
                    rhai::EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>().unwrap(),
                    other => panic!("unexpected timeout error: {other:?}"),
                };
                assert!(matches!(sys_error, SysError::Process { cause: ProcessCause::Timeout(_), .. }), "unexpected primary timeout cause: {sys_error:?}");
                panic!("successful timeout cleanup returned an error instead of a run result map");
            }
        };
        assert!(result["timed_out"].as_bool().unwrap());
        assert!(!result["stdout_complete"].as_bool().unwrap());
        assert!(!result["stderr_complete"].as_bool().unwrap());
        if raw {
            let stdout = result["stdout"].clone().try_cast::<Blob>().unwrap();
            let stderr = result["stderr"].clone().try_cast::<Blob>().unwrap();
            assert!(stdout.starts_with(LIBTEST_QUIET_START));
            assert!(stdout.windows(b"timeout-out\n".len()).any(|b| b == b"timeout-out\n"));
            assert!(stderr.windows(b"timeout-err\n".len()).any(|b| b == b"timeout-err\n"));
            assert!(stdout.len() <= 1_048_576 && stderr.len() <= 1_048_576);
        } else {
            let stdout = result["stdout"].as_immutable_string_ref().unwrap();
            let stderr = result["stderr"].as_immutable_string_ref().unwrap();
            assert!(stdout.starts_with(&*String::from_utf8_lossy(LIBTEST_QUIET_START)));
            assert!(stdout.contains("timeout-out\n"));
            assert!(stderr.contains("timeout-err\n"));
            assert!(stdout.len() <= 1_048_576 && stderr.len() <= 1_048_576);
        }
        assert_timed_child_record(&record_path);
    }
}

#[test]
#[cfg(not(feature = "no_index"))]
fn unit_timeout_disables_configured_default_deadline() {
    let engine = engine(SysConfig::default().default_timeout(Some(0.05)).programs(ProgramPolicy::Any));
    let executable = std::env::current_exe().unwrap();
    let executable = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let records = TempDir::new();
    let record_path = records.path().join("override-record.txt");
    let record_literal = record_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script = format!(
        r#"run_raw("{executable}", ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {FIXTURE_ENV}: "0", {FIXTURE_RECORD_ENV}: "{record_literal}", RHAI_SYS_PROCESS_HOLD: "1", RHAI_SYS_PROCESS_HOLD_FOR_MS: "250" }},
            max_output: 1048576,
            timeout: ()
        }})"#
    );
    let started = std::time::Instant::now();
    let result = engine.eval::<Map>(&script).unwrap();
    assert!(started.elapsed() >= std::time::Duration::from_millis(200));
    assert!(!result["timed_out"].as_bool().unwrap());
    assert_eq!(result["success"].as_bool().unwrap(), true);
    assert!(result["stdout_complete"].as_bool().unwrap());
    assert!(result["stderr_complete"].as_bool().unwrap());
    assert_timed_child_record(&record_path);
}

#[cfg(not(feature = "no_index"))]
fn assert_timed_child_record(path: &std::path::Path) {
    let record = std::fs::read_to_string(path).unwrap();
    let fields: Vec<_> = record.split_whitespace().collect();
    assert_eq!(fields.len(), 2, "child readiness record: {record:?}");
    let pid: libc::pid_t = fields[0].strip_prefix("child-pid=").unwrap().parse().unwrap();
    assert_eq!(fields[1], "child-ready=1");
    assert_eq!(unsafe { libc::kill(pid, 0) }, -1, "timed-out child {pid} is still present");
    assert_eq!(std::io::Error::last_os_error().raw_os_error(), Some(libc::ESRCH));
}

#[test]
#[cfg(not(feature = "no_index"))]
fn unit_stdin_means_immediate_eof() {
    let engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    let executable = std::env::current_exe().unwrap();
    let executable = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let records = TempDir::new();
    let record_path = records.path().join("stdin-record.txt");
    let record_path = record_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script = format!(
        r#"run_raw("{executable}", ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {FIXTURE_ENV}: "0", {FIXTURE_RECORD_ENV}: "{record_path}", RHAI_SYS_PROCESS_READ_STDIN: "1" }},
            stdin: (),
            timeout: 5.0
        }})"#
    );
    let result = match engine.eval::<Map>(&script) {
        Ok(result) => result,
        Err(error) => {
            let detail = match error.as_ref() {
                rhai::EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>().map(|value| format!("{value:?}")).unwrap_or_else(|| format!("{value:?}")),
                other => format!("{other:?}"),
            };
            panic!("scalar run failed: {detail}");
        }
    };
    let stdout = result["stdout"].clone().try_cast::<Blob>().unwrap();
    let mut expected = LIBTEST_QUIET_START.to_vec();
    expected.extend_from_slice(b"stdin-eof");
    assert_eq!(stdout, expected);
    assert_child_record(&records.path().join("stdin-record.txt"), 0);
}

#[test]
#[cfg(not(feature = "no_index"))]
fn process_cwd_uses_the_opened_filesystem_capability_after_root_replacement() {
    let temp = TempDir::new();
    let allowed = temp.path().join("allowed");
    let moved = temp.path().join("renamed-root");
    let outside = temp.path().join("outside");
    std::fs::create_dir_all(allowed.join("subdir")).unwrap();
    std::fs::create_dir_all(outside.join("subdir")).unwrap();
    let fixture_executable = std::env::current_exe().unwrap();
    let fixture_executable = fixture_executable.to_string_lossy().to_string();
    let engine = engine(
        SysConfig::default()
            .fs_root(&allowed, FsAccess::Read)
            .programs(ProgramPolicy::AllowList(vec!["/bin/pwd".into(), fixture_executable.clone()])),
    );

    std::fs::rename(&allowed, &moved).unwrap();
    std::os::unix::fs::symlink(&outside, &allowed).unwrap();
    let result = engine.eval::<Map>(r#"run_raw("/bin/pwd", #{ cwd: "subdir" })"#).unwrap();
    let stdout = result["stdout"].clone().try_cast::<Blob>().unwrap();
    let path = String::from_utf8(stdout).unwrap();
    let expected_cwd = std::fs::canonicalize(moved.join("subdir")).unwrap();
    assert_eq!(path, format!("{}\n", expected_cwd.display()));

    let escape = moved.join("escape");
    std::os::unix::fs::symlink(&outside, &escape).unwrap();
    let attempted_record = temp.path().join("escape-record.txt");
    let attempted_record_literal = attempted_record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let denied = engine.eval::<Map>(&format!(
        r#"run_raw("{fixture_executable}", ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
            cwd: "escape/subdir", env_clear: true,
            env: #{{ {FIXTURE_ENV}: "0", {FIXTURE_RECORD_ENV}: "{attempted_record_literal}" }} }})"#
    ));
    let error = denied.unwrap_err();
    let denied = matches!(
        error.as_ref(),
        rhai::EvalAltResult::ErrorRuntime(value, _)
            if matches!(value.clone().try_cast::<SysError>(), Some(SysError::Denied(_)))
    );
    assert!(denied, "symlink escape was not denied: {error:?}");
    assert!(!attempted_record.exists(), "child started before cwd denial");
}

#[test]
#[cfg(not(feature = "no_index"))]
fn lossy_run_reports_engine_limit_expansion_without_returning_truncated_text() {
    let mut engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    let executable = std::env::current_exe().unwrap();
    let executable = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let records = TempDir::new();
    let record_path = records.path().join("child-record.txt");
    let record_path = record_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let engine_limit = executable.len().max(record_path.len()) + 24;
    let invalid_count = engine_limit / 2;
    assert!(LIBTEST_QUIET_START.len() + invalid_count < engine_limit);
    assert!(String::from_utf8_lossy(LIBTEST_QUIET_START).len() + invalid_count * 3 > engine_limit);
    engine.set_max_string_size(engine_limit);
    let script = format!(
        r#"run("{executable}", ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {FIXTURE_ENV}: "0", {FIXTURE_RECORD_ENV}: "{record_path}", RHAI_SYS_PROCESS_INVALID_COUNT: "{invalid_count}" }},
            max_output: 1024,
            timeout: 5.0
        }})"#
    );
    let error = engine.eval::<Map>(&script).unwrap_err();
    assert_child_record(&records.path().join("child-record.txt"), 0);
    let sys_error = match error.as_ref() {
        rhai::EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>().unwrap(),
        other => panic!("unexpected error: {other:?}"),
    };
    match sys_error {
        SysError::Process { cause: ProcessCause::OutputLimit(_), report } => {
            assert!(report.stdout_bytes().len() <= engine_limit);
            assert_eq!(report.stdout_bytes().last(), Some(&0xff));
        }
        other => panic!("expected preserved process output-limit error, got {other:?}"),
    }
}

/// The scalar text API remains registered and usable when collections are disabled.
#[cfg(feature = "no_index")]
#[test]
fn scalar_run_with_cwd_works_without_collections() {
    let temp = sys_support::TempDir::new();
    let child_dir = temp.path().join("child");
    std::fs::create_dir_all(&child_dir).unwrap();
    let engine = engine(SysConfig::permissive());
    let cwd = child_dir.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let record_path = temp.path().join("child-record.txt");
    let record = record_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script = format!(
        r#"run("/bin/sh", #{{
            cwd: "{cwd}",
            env_clear: true,
            env: #{{ RECORD: "{record}" }},
            stdin: "printf 'child-pid=%s\\n' \"$$\" > \"$RECORD\"; pwd"
        }})"#
    );
    let result = match engine.eval::<Map>(&script) {
        Ok(result) => result,
        Err(error) => {
            let detail = match error.as_ref() {
                rhai::EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>().map(|value| format!("{value:?}")).unwrap_or_else(|| format!("{value:?}")),
                other => format!("{other:?}"),
            };
            panic!("scalar run failed: {detail}");
        }
    };
    let expected = std::fs::canonicalize(&child_dir).unwrap();
    assert_eq!(result["stdout"].as_immutable_string_ref().unwrap().as_str(), format!("{}\n", expected.display()));
    assert!(result["stdout_complete"].as_bool().unwrap());
    assert!(result["stderr_complete"].as_bool().unwrap());
    assert!(result["success"].as_bool().unwrap());
    assert_eq!(result["code"].as_int().unwrap(), 0);
    let missing_raw_api = engine.eval::<Map>(r#"run_raw("/bin/pwd")"#).unwrap_err();
    assert!(matches!(missing_raw_api.as_ref(), rhai::EvalAltResult::ErrorFunctionNotFound(name, _) if name.starts_with("run_raw")), "run_raw remains registered: {missing_raw_api:?}");
    let record = std::fs::read_to_string(&record_path).unwrap();
    let pid: libc::pid_t = record.trim().strip_prefix("child-pid=").unwrap().parse().unwrap();
    assert_eq!(unsafe { libc::kill(pid, 0) }, -1, "child {pid} is still present");
    assert_eq!(std::io::Error::last_os_error().raw_os_error(), Some(libc::ESRCH));
}
