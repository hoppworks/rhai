#![cfg(all(feature = "sys", windows, not(feature = "no_index")))]
//! Minimal public process contract for native Windows.

mod sys_support;

use rhai::packages::sys::{ProgramPolicy, SysConfig, SysError};
use rhai::{Blob, EvalAltResult, ImmutableString, Map, Scope};
use std::ffi::c_void;
use std::process;
use std::thread;
use std::time::{Duration, Instant};
use sys_support::{engine, TempDir};

const FIXTURE_CODE_ENV: &str = "RHAI_SYS_WINDOWS_PROCESS_CODE";
const FIXTURE_RECORD_ENV: &str = "RHAI_SYS_WINDOWS_PROCESS_RECORD";
const FIXTURE_FAST_RECORD_ENV: &str = "RHAI_SYS_WINDOWS_PROCESS_FAST_RECORD";
const FIXTURE_INVALID_COUNT_ENV: &str = "RHAI_SYS_WINDOWS_PROCESS_INVALID_COUNT";
const WRONG_EXPECTATION_ENV: &str = "RHAI_WINDOWS_PROCESS_WRONG_EXPECTATION";
const TEXT_LIMIT_WRONG_EXPECTATION_ENV: &str = "RHAI_WINDOWS_TEXT_LIMIT_WRONG_EXPECTATION";
const TIMEOUT_RECORD_ENV: &str = "RHAI_WINDOWS_TIMEOUT_RECORD";
const TIMEOUT_WRONG_EXPECTATION_ENV: &str = "RHAI_WINDOWS_TIMEOUT_WRONG_EXPECTATION";
const STDIN_RECORD_ENV: &str = "RHAI_WINDOWS_STDIN_RECORD";
const STDIN_DATA_ENV: &str = "RHAI_WINDOWS_STDIN_DATA";
const STDIN_WRONG_EXPECTATION_ENV: &str = "RHAI_WINDOWS_STDIN_WRONG_EXPECTATION";
const STDIN_TIMEOUT_WRONG_EXPECTATION_ENV: &str = "RHAI_WINDOWS_STDIN_TIMEOUT_WRONG_EXPECTATION";
const LIBTEST_QUIET_START: &[u8] = b"\nrunning 1 test\n";

type Handle = *mut c_void;
const PROCESS_QUERY_LIMITED_INFORMATION: u32 = 0x1000;
const PROCESS_TERMINATE: u32 = 0x0001;
const SYNCHRONIZE: u32 = 0x0010_0000;
const WAIT_OBJECT_0: u32 = 0;

#[link(name = "kernel32")]
extern "system" {
    fn OpenProcess(access: u32, inherit: i32, pid: u32) -> Handle;
    fn WaitForSingleObject(handle: Handle, milliseconds: u32) -> u32;
    fn GetExitCodeProcess(handle: Handle, exit_code: *mut u32) -> i32;
    fn TerminateProcess(handle: Handle, exit_code: u32) -> i32;
    fn CloseHandle(handle: Handle) -> i32;
}

struct OwnedProcessHandle(Handle);

impl Drop for OwnedProcessHandle {
    fn drop(&mut self) {
        unsafe { CloseHandle(self.0) };
    }
}

struct TimeoutChildGuard {
    handle: OwnedProcessHandle,
    pid: u32,
    exit_observed: bool,
}

impl Drop for TimeoutChildGuard {
    fn drop(&mut self) {
        if self.exit_observed {
            return;
        }
        if unsafe { WaitForSingleObject(self.handle.0, 0) } == WAIT_OBJECT_0 {
            return;
        }
        let terminated = unsafe { TerminateProcess(self.handle.0, 1) };
        if terminated == 0 {
            eprintln!("failed to terminate exact timeout fixture {}: {}", self.pid, std::io::Error::last_os_error());
        }
        let wait = unsafe { WaitForSingleObject(self.handle.0, 10_000) };
        if wait != WAIT_OBJECT_0 {
            eprintln!("exact timeout fixture {} remained unconfirmed after cleanup: {wait:#x}", self.pid);
        }
    }
}

fn observe_exact_child_exit(record: std::path::PathBuf, release: std::path::PathBuf) -> (u32, u32) {
    let deadline = Instant::now() + Duration::from_secs(5);
    let text = loop {
        match std::fs::read_to_string(&record) {
            Ok(text) => break text,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound && Instant::now() < deadline => {
                thread::sleep(Duration::from_millis(10));
            }
            Err(error) => panic!("child readiness record unavailable: {error}"),
        }
    };
    let fields: Vec<_> = text.split_whitespace().collect();
    assert_eq!(fields.len(), 2, "child record: {text:?}");
    let pid = fields[0].strip_prefix("pid=").unwrap().parse::<u32>().unwrap();
    assert!(pid > 0);
    let expected_exit = fields[1].strip_prefix("exit=").unwrap().parse::<u32>().unwrap();
    let raw = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, 0, pid) };
    assert!(!raw.is_null(), "open exact child process {pid}: {}", std::io::Error::last_os_error());
    let handle = OwnedProcessHandle(raw);
    std::fs::write(&release, b"release\n").expect("release observed child");
    let wait = unsafe { WaitForSingleObject(handle.0, 10_000) };
    assert_eq!(wait, WAIT_OBJECT_0, "exact child process {pid} did not exit: wait={wait:#x}");
    let mut exit_code = u32::MAX;
    let queried = unsafe { GetExitCodeProcess(handle.0, &mut exit_code) };
    assert_ne!(queried, 0, "query exact child process {pid}: {}", std::io::Error::last_os_error());
    assert_eq!(exit_code, expected_exit, "exact child process {pid} exit code");
    (pid, exit_code)
}

/// Re-executed by the public `run_raw` contract to produce OS output and a pre-exit record.
#[test]
fn windows_process_fixture() {
    let Ok(code) = std::env::var(FIXTURE_CODE_ENV) else {
        return;
    };
    let code: i32 = code.parse().unwrap();
    let record = std::env::var(FIXTURE_RECORD_ENV).expect("fixture record path");
    let temporary = std::path::Path::new(&record).with_extension("tmp");
    std::fs::write(&temporary, format!("pid={} exit={code}\n", process::id())).unwrap();
    std::fs::rename(&temporary, &record).unwrap();
    let release = std::path::Path::new(&record).with_extension("release");
    let deadline = Instant::now() + Duration::from_secs(8);
    while !release.exists() {
        assert!(Instant::now() < deadline, "parent did not acquire exact child process handle");
        thread::sleep(Duration::from_millis(10));
    }
    std::io::Write::write_all(&mut std::io::stdout(), &[0x00, 0x41, 0xff]).unwrap();
    if let Ok(count) = std::env::var(FIXTURE_INVALID_COUNT_ENV) {
        let count: usize = count.parse().expect("valid invalid-byte count");
        std::io::Write::write_all(&mut std::io::stdout(), &vec![0xff; count]).unwrap();
    }
    std::io::Write::flush(&mut std::io::stdout()).unwrap();
    std::io::Write::write_all(&mut std::io::stderr(), &[0xfe, 0x42, 0x00]).unwrap();
    std::io::Write::flush(&mut std::io::stderr()).unwrap();
    process::exit(code);
}

#[test]
fn windows_process_fast_probe() {
    let Ok(record) = std::env::var(FIXTURE_FAST_RECORD_ENV) else {
        return;
    };
    std::fs::write(record, format!("pid={}\n", process::id())).expect("write fast child record");
}

/// A real child writes its PID only after flushing the bytes the supervisor must retain.
#[test]
fn windows_timeout_fixture() {
    let Ok(record) = std::env::var(TIMEOUT_RECORD_ENV) else {
        return;
    };
    std::io::Write::write_all(&mut std::io::stdout(), b"timeout-ready").unwrap();
    std::io::Write::flush(&mut std::io::stdout()).unwrap();
    let path = std::path::Path::new(&record);
    let temporary = path.with_extension("tmp");
    std::fs::write(&temporary, format!("pid={}\n", process::id())).unwrap();
    std::fs::rename(&temporary, path).unwrap();
    let observed = path.with_extension("observed");
    let safety_deadline = Instant::now() + Duration::from_secs(20);
    while !observed.exists() {
        assert!(Instant::now() < safety_deadline, "observer never acquired child handle");
        thread::sleep(Duration::from_millis(10));
    }
    while Instant::now() < safety_deadline {
        thread::sleep(Duration::from_millis(20));
    }
    panic!("parent did not terminate the child before its safety deadline");
}

/// Fill both output streams before reading input, so a blocking input writer deadlocks.
#[test]
fn windows_stdin_fixture() {
    let Ok(record) = std::env::var(STDIN_RECORD_ENV) else {
        return;
    };
    let record = std::path::Path::new(&record);
    let temporary = record.with_extension("tmp");
    std::fs::write(&temporary, format!("pid={}\n", process::id())).unwrap();
    std::fs::rename(&temporary, record).unwrap();
    let observed = record.with_extension("observed");
    let deadline = Instant::now() + Duration::from_secs(20);
    while !observed.exists() {
        assert!(Instant::now() < deadline, "observer never acquired child handle");
        thread::sleep(Duration::from_millis(10));
    }
    std::io::Write::write_all(&mut std::io::stdout(), &vec![b'S'; 65_536]).unwrap();
    std::io::Write::flush(&mut std::io::stdout()).unwrap();
    std::io::Write::write_all(&mut std::io::stderr(), &vec![b'E'; 65_536]).unwrap();
    std::io::Write::flush(&mut std::io::stderr()).unwrap();
    let mut input = Vec::new();
    std::io::Read::read_to_end(&mut std::io::stdin(), &mut input).unwrap();
    let data = std::env::var(STDIN_DATA_ENV).expect("input record path");
    let data = std::path::Path::new(&data);
    let temporary = data.with_extension("tmp");
    std::fs::write(&temporary, input).unwrap();
    std::fs::rename(&temporary, data).unwrap();
    process::exit(0);
}

#[test]
fn windows_run_raw_transfers_blob_while_draining_both_streams() {
    let records = TempDir::new();
    let record = records.path().join("stdin-child.txt");
    let data = records.path().join("stdin-data.bin");
    let observed = record.with_extension("observed");
    let observer = thread::spawn({
        let record = record.clone();
        move || {
            let deadline = Instant::now() + Duration::from_secs(4);
            let text = loop {
                match std::fs::read_to_string(&record) {
                    Ok(text) => break text,
                    Err(error) if error.kind() == std::io::ErrorKind::NotFound && Instant::now() < deadline => thread::sleep(Duration::from_millis(10)),
                    Err(error) if error.kind() == std::io::ErrorKind::NotFound => return None,
                    Err(error) => panic!("stdin child readiness: {error}"),
                }
            };
            let pid = text.trim().strip_prefix("pid=").unwrap().parse::<u32>().unwrap();
            let raw = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE | SYNCHRONIZE, 0, pid) };
            assert!(!raw.is_null(), "open exact stdin child {pid}: {}", std::io::Error::last_os_error());
            let mut guard = TimeoutChildGuard {
                handle: OwnedProcessHandle(raw),
                pid,
                exit_observed: false,
            };
            std::fs::write(observed, b"handle acquired\n").unwrap();
            let wait = unsafe { WaitForSingleObject(guard.handle.0, 25_000) };
            assert_eq!(wait, WAIT_OBJECT_0, "stdin child {pid} did not terminate: {wait:#x}");
            guard.exit_observed = true;
            let mut exit = u32::MAX;
            assert_ne!(unsafe { GetExitCodeProcess(guard.handle.0, &mut exit) }, 0);
            Some((pid, exit))
        }
    });
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let record_literal = record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let data_literal = data.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let input: Blob = (0..131_072).map(|n| (n % 251) as u8).collect();
    let mut scope = Scope::new();
    scope.push("input", input.clone());
    let mut engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    #[cfg(not(feature = "unchecked"))]
    engine.set_max_array_size(1_048_576);
    let script = format!(
        r#"run_raw("{executable}", ["--exact", "windows_stdin_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {STDIN_RECORD_ENV}: "{record_literal}", {STDIN_DATA_ENV}: "{data_literal}" }},
            stdin: input, max_output: 262144, timeout: 15
        }})"#
    );
    let result = engine.eval_with_scope::<Map>(&mut scope, &script);
    let observation = observer.join().expect("join stdin child observer");
    let result = result.unwrap_or_else(|error| panic!("stdin must support concurrent transfer: {error:?}; child_observed={}", observation.is_some()));
    let (pid, exit) = observation.expect("exact child was independently observed");
    eprintln!("windows_stdin_child_readback pid={pid} exit={exit} exact_handle_signaled=true");
    assert_eq!(exit, 0);
    assert!(result["success"].as_bool().unwrap());
    let mut expected_stdout = LIBTEST_QUIET_START.to_vec();
    expected_stdout.extend(vec![b'S'; 65_536]);
    assert_eq!(result["stdout"].clone().try_cast::<Blob>().unwrap(), expected_stdout);
    assert_eq!(result["stderr"].clone().try_cast::<Blob>().unwrap(), vec![b'E'; 65_536]);
    let readback = std::fs::read(&data).expect("child-written input readback");
    if std::env::var_os(STDIN_WRONG_EXPECTATION_ENV).is_some() {
        assert!(readback != input, "deliberately wrong stdin round-trip expectation");
    }
    assert_eq!(readback, input);
    assert_eq!(std::fs::read_to_string(&record).unwrap().trim(), format!("pid={pid}"));
}

fn observe_timeout_child(record: std::path::PathBuf) -> (u32, u32) {
    let observed = record.with_extension("observed");
    let deadline = Instant::now() + Duration::from_secs(4);
    let text = loop {
        match std::fs::read_to_string(&record) {
            Ok(text) => break text,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound && Instant::now() < deadline => {
                thread::sleep(Duration::from_millis(10));
            }
            Err(error) => panic!("timeout child readiness unavailable: {error}"),
        }
    };
    let pid = text.trim().strip_prefix("pid=").unwrap().parse::<u32>().unwrap();
    let raw = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE | SYNCHRONIZE, 0, pid) };
    assert!(!raw.is_null(), "open exact timeout child {pid}: {}", std::io::Error::last_os_error());
    let mut guard = TimeoutChildGuard {
        handle: OwnedProcessHandle(raw),
        pid,
        exit_observed: false,
    };
    std::fs::write(observed, b"handle acquired\n").unwrap();
    let wait = unsafe { WaitForSingleObject(guard.handle.0, 15_000) };
    assert_eq!(wait, WAIT_OBJECT_0, "exact timeout child {pid} did not terminate: {wait:#x}");
    guard.exit_observed = true;
    let mut exit_code = u32::MAX;
    assert_ne!(unsafe { GetExitCodeProcess(guard.handle.0, &mut exit_code) }, 0, "query exact timeout child {pid}: {}", std::io::Error::last_os_error());
    (pid, exit_code)
}

#[test]
fn windows_run_raw_timeout_terminates_exact_child_and_retains_output() {
    use rhai::packages::sys::ProcessCause;

    let records = TempDir::new();
    let record = records.path().join("timeout-child.txt");
    let observer = thread::spawn({
        let record = record.clone();
        move || observe_timeout_child(record)
    });
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script_record = record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script = format!(
        r#"run_raw("{executable}", ["--exact", "windows_timeout_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {TIMEOUT_RECORD_ENV}: "{script_record}" }},
            max_output: 1024,
            timeout: 5
        }})"#
    );
    let result = engine(SysConfig::default().programs(ProgramPolicy::Any)).eval::<Map>(&script);
    let (pid, observed_exit) = observer.join().expect("join exact timeout-child observer");
    eprintln!("windows_timeout_child_readback pid={pid} exit={observed_exit} exact_handle_signaled=true");
    let error = result.expect_err("a running child must time out");
    let sys_error = match *error {
        EvalAltResult::ErrorRuntime(value, _) => value.try_cast::<SysError>().expect("typed process error"),
        other => panic!("unexpected error: {other:?}"),
    };
    match sys_error {
        SysError::Process { cause: ProcessCause::Timeout(_), report } => {
            eprintln!(
                "windows_timeout_report timed_out={} stdout_complete={} stderr_complete={} exit={:?} diagnostics={:?}",
                report.timed_out(),
                report.stdout_complete(),
                report.stderr_complete(),
                report.exit_code(),
                report.cleanup_diagnostics()
            );
            if std::env::var_os(TIMEOUT_WRONG_EXPECTATION_ENV).is_some() {
                assert!(!report.timed_out(), "deliberately wrong timeout expectation");
            }
            assert!(report.timed_out());
            let mut expected = LIBTEST_QUIET_START.to_vec();
            expected.extend_from_slice(b"timeout-ready");
            assert_eq!(report.stdout_bytes(), expected);
            assert_eq!(report.exit_code().map(|code| code as u32), Some(observed_exit), "report differs from exact child exit status");
            eprintln!("windows_timeout_capture stdout_complete={} stderr_complete={}", report.stdout_complete(), report.stderr_complete());
            assert!(report.cleanup_diagnostics().is_empty(), "cleanup diagnostics: {:?}", report.cleanup_diagnostics());
        }
        other => panic!("expected a timeout with a retained report, got {other:?}"),
    }
    assert_eq!(std::fs::read_to_string(&record).unwrap().trim(), format!("pid={pid}"));
}

#[test]
fn windows_run_raw_times_out_with_unread_stdin() {
    use rhai::packages::sys::ProcessCause;

    let records = TempDir::new();
    let record = records.path().join("blocked-stdin-child.txt");
    let observer = thread::spawn({
        let record = record.clone();
        move || observe_timeout_child(record)
    });
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script_record = record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let mut scope = Scope::new();
    scope.push("input", vec![0x5au8; 1_048_576]);
    let mut engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    #[cfg(not(feature = "unchecked"))]
    engine.set_max_array_size(2_097_152);
    let script = format!(
        r#"run_raw("{executable}", ["--exact", "windows_timeout_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true, env: #{{ {TIMEOUT_RECORD_ENV}: "{script_record}" }},
            stdin: input, max_output: 1024, timeout: 5
        }})"#
    );
    let result = engine.eval_with_scope::<Map>(&mut scope, &script);
    let (pid, observed_exit) = observer.join().expect("join blocked-input child observer");
    eprintln!("windows_blocked_stdin_child_readback pid={pid} exit={observed_exit} exact_handle_signaled=true");
    let error = result.expect_err("unread input must not bypass the deadline");
    let sys_error = match *error {
        EvalAltResult::ErrorRuntime(value, _) => value.try_cast::<SysError>().expect("typed process error"),
        other => panic!("unexpected error: {other:?}"),
    };
    match sys_error {
        SysError::Process { cause: ProcessCause::Timeout(_), report } => {
            eprintln!("windows_blocked_stdin_report timed_out={} exit={:?} diagnostics={:?}", report.timed_out(), report.exit_code(), report.cleanup_diagnostics());
            if std::env::var_os(STDIN_TIMEOUT_WRONG_EXPECTATION_ENV).is_some() {
                assert!(!report.timed_out(), "deliberately wrong blocked stdin timeout expectation");
            }
            assert!(report.timed_out());
            assert_eq!(report.exit_code().map(|code| code as u32), Some(observed_exit));
            assert!(report.cleanup_diagnostics().is_empty(), "cleanup diagnostics: {:?}", report.cleanup_diagnostics());
        }
        other => panic!("expected blocked-input timeout, got {other:?}"),
    }
    assert_eq!(std::fs::read_to_string(&record).unwrap().trim(), format!("pid={pid}"));
}

#[test]
fn windows_run_raw_rejects_timeout_outside_duration_range_before_spawn() {
    let records = TempDir::new();
    let record = records.path().join("fast-child-record.txt");
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script_record = record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script = format!(
        r#"run_raw("{executable}", ["--exact", "windows_process_fast_probe", "--quiet"], #{{
            env_clear: true,
            env: #{{ {FIXTURE_FAST_RECORD_ENV}: "{script_record}" }},
            timeout: 1.0e20
        }})"#
    );
    let result = engine(SysConfig::default().programs(ProgramPolicy::Any)).eval::<Map>(&script);
    let child_record = std::fs::read_to_string(&record).ok();
    eprintln!("timeout_range_child_record={child_record:?}");
    let error = result.expect_err("timeout outside Duration range must be rejected before spawn");
    match *error {
        EvalAltResult::ErrorRuntime(value, _) => {
            assert!(matches!(value.try_cast::<SysError>(), Some(SysError::Denied(_))));
        }
        other => panic!("expected typed Denied error, got {other:?}"),
    }
    assert!(child_record.is_none(), "rejected timeout started a real child");
}

/// Public Windows run contract: raw streams, nonzero exit as data, and completion after the
/// child-written pre-exit record, captured streams and exact OS process-handle termination
/// are observed independently.
#[test]
fn windows_run_raw_captures_output_and_nonzero_exit() {
    let engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");

    for code in [0, 7] {
        let records = TempDir::new();
        let record = records.path().join("child-record.txt");
        let release = record.with_extension("release");
        let observer = thread::spawn({
            let record = record.clone();
            move || observe_exact_child_exit(record, release)
        });
        let script_record = record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let script = format!(
            r#"run_raw("{executable}", ["--exact", "windows_process_fixture", "--nocapture", "--quiet"], #{{
                env_clear: true,
                env: #{{ {FIXTURE_CODE_ENV}: "{code}", {FIXTURE_RECORD_ENV}: "{script_record}" }},
                max_output: 1024,
                timeout: 15
            }})"#
        );
        let result = engine.eval::<Map>(&script);
        let observation = observer.join();
        let result = result.unwrap_or_else(|error| panic!("windows public run_raw failed before OS observation: {error:?}; child_observed={}", observation.is_ok()));
        let (observed_pid, observed_exit) = observation.expect("join independent OS observer");
        eprintln!("windows_process_os_readback pid={observed_pid} exit={observed_exit} exact_handle_signaled=true");
        assert_eq!(result["success"].as_bool().unwrap(), code == 0);
        assert_eq!(result["code"].as_int().unwrap(), rhai::INT::from(code));
        assert!(result["stdout_complete"].as_bool().unwrap());
        assert!(result["stderr_complete"].as_bool().unwrap());
        let mut expected_stdout = LIBTEST_QUIET_START.to_vec();
        expected_stdout.extend_from_slice(&[0x00, 0x41, 0xff]);
        assert_eq!(result["stdout"].clone().try_cast::<Blob>().unwrap(), expected_stdout);
        assert_eq!(result["stderr"].clone().try_cast::<Blob>().unwrap(), [0xfe, 0x42, 0x00]);

        let record = std::fs::read_to_string(&record).unwrap();
        let fields: Vec<_> = record.split_whitespace().collect();
        assert_eq!(fields.len(), 2, "child record: {record:?}");
        assert_eq!(fields[0].strip_prefix("pid=").unwrap().parse::<u32>().unwrap(), observed_pid);
        assert_eq!(fields[1], format!("exit={code}"));
        assert_eq!(observed_exit, code as u32);
        if std::env::var_os(WRONG_EXPECTATION_ENV).is_some() {
            assert_eq!(observed_exit, code as u32 + 1, "deliberately wrong native process exit expectation");
        }
    }
}

/// Public text contract uses the same real child and independent exact-handle observation
/// as the raw-byte contract, but returns replacement characters for invalid UTF-8.
#[test]
fn windows_run_returns_lossy_text_and_nonzero_exit() {
    let mut engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    // Leave room for the four argument literals while keeping the raw output larger.
    #[cfg(not(feature = "unchecked"))]
    engine.set_max_array_size(16);
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    for code in [0, 7] {
        let records = TempDir::new();
        let record = records.path().join("text-child-record.txt");
        let release = record.with_extension("release");
        let observer = thread::spawn({
            let record = record.clone();
            move || observe_exact_child_exit(record, release)
        });
        let script_record = record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let script = format!(
            r#"run("{executable}", ["--exact", "windows_process_fixture", "--nocapture", "--quiet"], #{{
                env_clear: true,
                env: #{{ {FIXTURE_CODE_ENV}: "{code}", {FIXTURE_RECORD_ENV}: "{script_record}" }},
                max_output: 1024,
                timeout: 15
            }})"#
        );
        let result = engine.eval::<Map>(&script);
        let observation = observer.join();
        let result = result.unwrap_or_else(|error| panic!("Windows public run failed before OS observation: {error:?}; child_observed={}", observation.is_ok()));
        let (pid, observed_exit) = observation.expect("join independent OS observer");
        eprintln!("windows_process_text_readback pid={pid} exit={observed_exit} exact_handle_signaled=true");
        assert_eq!(result["success"].as_bool().unwrap(), code == 0);
        assert_eq!(result["code"].as_int().unwrap(), rhai::INT::from(code));
        assert!(result["stdout_complete"].as_bool().unwrap());
        assert!(result["stderr_complete"].as_bool().unwrap());
        let mut expected_stdout = LIBTEST_QUIET_START.to_vec();
        expected_stdout.extend_from_slice(&[0x00, 0x41, 0xff]);
        assert_eq!(result["stdout"].clone().try_cast::<ImmutableString>().unwrap().as_str(), String::from_utf8_lossy(&expected_stdout));
        assert_eq!(result["stderr"].clone().try_cast::<ImmutableString>().unwrap().as_str(), "\u{fffd}B\0");
        let record_text = std::fs::read_to_string(&record).unwrap();
        assert!(record_text.contains(&format!("pid={pid} exit={code}")));
        assert_eq!(observed_exit, code as u32);
        if std::env::var_os(WRONG_EXPECTATION_ENV).is_some() {
            assert_eq!(observed_exit, code as u32 + 1, "deliberately wrong native text process exit expectation");
        }
    }
}

#[test]
#[cfg(not(feature = "unchecked"))]
fn windows_run_rejects_decoded_text_expansion_with_original_raw_report() {
    use rhai::packages::sys::ProcessCause;

    let mut engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let records = TempDir::new();
    let record = records.path().join("limit-child-record.txt");
    let release = record.with_extension("release");
    let script_record = record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let engine_limit = executable.len().max(script_record.len()) + 24;
    let invalid_count = engine_limit / 2;
    assert!(LIBTEST_QUIET_START.len() + 3 + invalid_count < engine_limit);
    assert!(LIBTEST_QUIET_START.len() + 5 + 3 * invalid_count > engine_limit);
    engine.set_max_string_size(engine_limit);
    let observer = thread::spawn({
        let record = record.clone();
        move || observe_exact_child_exit(record, release)
    });
    let script = format!(
        r#"run("{executable}", ["--exact", "windows_process_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {FIXTURE_CODE_ENV}: "0", {FIXTURE_RECORD_ENV}: "{script_record}", {FIXTURE_INVALID_COUNT_ENV}: "{invalid_count}" }},
            max_output: 1024,
            timeout: 15
        }})"#
    );
    let result = engine.eval::<Map>(&script);
    let (pid, exit) = observer.join().expect("join independent OS observer");
    assert_eq!(exit, 0, "exact child {pid} exit");
    if std::env::var_os(TEXT_LIMIT_WRONG_EXPECTATION_ENV).is_some() {
        assert!(result.is_ok(), "deliberately wrong decoded expansion expectation");
    }
    let error = result.expect_err("lossy text exceeded engine string limit");
    let sys_error = match *error {
        EvalAltResult::ErrorRuntime(value, _) => value.try_cast::<SysError>().expect("typed process error"),
        other => panic!("unexpected error: {other:?}"),
    };
    match sys_error {
        SysError::Process { cause: ProcessCause::OutputLimit(_), report } => {
            let mut expected = LIBTEST_QUIET_START.to_vec();
            expected.extend_from_slice(&[0x00, 0x41, 0xff]);
            expected.extend(std::iter::repeat(0xff).take(invalid_count));
            assert_eq!(report.stdout_bytes(), expected);
            assert!(report.stdout_complete() && report.stderr_complete());
            assert_eq!(report.exit_code(), Some(0));
        }
        other => panic!("expected output-limit report, got {other:?}"),
    }
    assert!(std::fs::read_to_string(&record).unwrap().contains(&format!("pid={pid} exit=0")));
}
