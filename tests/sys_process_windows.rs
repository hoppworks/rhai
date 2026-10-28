#![cfg(all(feature = "sys", windows, not(feature = "no_index")))]
//! Minimal public process contract for native Windows.

mod sys_support;

use rhai::packages::sys::{ProcessCause, ProcessScope, ProgramPolicy, SysConfig, SysError};
use rhai::{Blob, Dynamic, EvalAltResult, ImmutableString, Map, Scope};
use std::ffi::c_void;
use std::os::windows::io::AsRawHandle;
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
const STDIN_OUTPUT_ENV: &str = "RHAI_WINDOWS_STDIN_OUTPUT_BYTES";
const STDIN_WRONG_EXPECTATION_ENV: &str = "RHAI_WINDOWS_STDIN_WRONG_EXPECTATION";
const STDIN_SCALAR_WRONG_EXPECTATION_ENV: &str = "RHAI_WINDOWS_STDIN_SCALAR_WRONG_EXPECTATION";
const STDIN_TIMEOUT_WRONG_EXPECTATION_ENV: &str = "RHAI_WINDOWS_STDIN_TIMEOUT_WRONG_EXPECTATION";
const SPAWN_WRONG_EXPECTATION_ENV: &str = "RHAI_WINDOWS_SPAWN_WRONG_EXPECTATION";
const CHILD_SNAPSHOT_WRONG_EXPECTATION_ENV: &str = "RHAI_WINDOWS_CHILD_SNAPSHOT_WRONG_EXPECTATION";
const SPAWN_KILL_RECORD_ENV: &str = "RHAI_WINDOWS_SPAWN_KILL_RECORD";
const SPAWN_KILL_WRONG_EXPECTATION_ENV: &str = "RHAI_WINDOWS_SPAWN_KILL_WRONG_EXPECTATION";
const CHILD_DROP_WRONG_EXPECTATION_ENV: &str = "RHAI_WINDOWS_CHILD_DROP_WRONG_EXPECTATION";
const CHILD_DROP_RECORD_ENV: &str = "RHAI_WINDOWS_CHILD_DROP_RECORD";
const MANAGED_ROOT_ENV: &str = "RHAI_WINDOWS_MANAGED_ROOT";
const MANAGED_LEAF_ENV: &str = "RHAI_WINDOWS_MANAGED_LEAF";
const MANAGED_WRONG_ENV: &str = "RHAI_WINDOWS_MANAGED_WRONG_EXPECTATION";
const MANAGED_RUN_CLOSURE_WRONG_ENV: &str = "RHAI_WINDOWS_MANAGED_RUN_CLOSURE_WRONG_EXPECTATION";
const MANAGED_BATCH_WRONG_ENV: &str = "RHAI_WINDOWS_MANAGED_BATCH_WRONG_EXPECTATION";
const MANAGED_CWD_CONTROLLER_ENV: &str = "RHAI_WINDOWS_MANAGED_CWD_CONTROLLER";
const MANAGED_CWD_WRONG_ENV: &str = "RHAI_WINDOWS_MANAGED_CWD_WRONG_EXPECTATION";
const MANAGED_PATH_WRONG_ENV: &str = "RHAI_WINDOWS_MANAGED_PATH_WRONG_EXPECTATION";
const LIBTEST_QUIET_START: &[u8] = b"\nrunning 1 test\n";

type Handle = *mut c_void;
const PROCESS_QUERY_LIMITED_INFORMATION: u32 = 0x1000;
const PROCESS_TERMINATE: u32 = 0x0001;
const SYNCHRONIZE: u32 = 0x0010_0000;
const WAIT_OBJECT_0: u32 = 0;
const WAIT_TIMEOUT: u32 = 258;

#[link(name = "kernel32")]
extern "system" {
    fn OpenProcess(access: u32, inherit: i32, pid: u32) -> Handle;
    fn WaitForSingleObject(handle: Handle, milliseconds: u32) -> u32;
    fn GetExitCodeProcess(handle: Handle, exit_code: *mut u32) -> i32;
    fn TerminateProcess(handle: Handle, exit_code: u32) -> i32;
    fn CloseHandle(handle: Handle) -> i32;
    fn GetStdHandle(kind: u32) -> Handle;
    fn PeekNamedPipe(handle: Handle, buffer: *mut c_void, size: u32, read: *mut u32, available: *mut u32, left: *mut u32) -> i32;
    fn QueryInformationJobObject(job: Handle, class: i32, info: *mut c_void, length: u32, returned: *mut u32) -> i32;
}

struct OwnedProcessHandle(Handle);

// SAFETY: this wrapper exclusively owns the Windows handle, which may be moved across threads.
unsafe impl Send for OwnedProcessHandle {}

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

/// Read one byte, then wait for a full input pipe without draining the rest.
#[test]
fn windows_spawn_blocked_input_fixture() {
    let Ok(record) = std::env::var(SPAWN_KILL_RECORD_ENV) else { return; };
    let mut first = [0u8; 1];
    std::io::Read::read_exact(&mut std::io::stdin(), &mut first).unwrap();
    assert_eq!(first, [0x5a]);
    let input = unsafe { GetStdHandle((-10i32) as u32) };
    assert!(!input.is_null());
    let deadline = Instant::now() + Duration::from_secs(15);
    let available = loop {
        let mut available = 0u32;
        let ok = unsafe { PeekNamedPipe(input, std::ptr::null_mut(), 0, std::ptr::null_mut(), &mut available, std::ptr::null_mut()) };
        assert_ne!(ok, 0, "observe child stdin pipe: {}", std::io::Error::last_os_error());
        if available >= 8_191 { break available; }
        assert!(Instant::now() < deadline, "stdin pipe never reached the bounded buffer readiness condition");
        thread::yield_now();
    };
    let path = std::path::Path::new(&record);
    let temporary = path.with_extension("tmp");
    std::fs::write(&temporary, format!("pid={} first=5a available={available}\n", process::id())).unwrap();
    std::fs::rename(&temporary, path).unwrap();
    while Instant::now() < deadline { thread::sleep(Duration::from_millis(20)); }
    panic!("parent did not terminate the child before its safety deadline");
}

/// A gated child acknowledges challenges after the parent drops each public handle.
#[test]
fn windows_child_drop_fixture() {
    let Ok(record) = std::env::var(CHILD_DROP_RECORD_ENV) else { return; };
    let path = std::path::Path::new(&record);
    let temporary = path.with_extension("tmp");
    std::fs::write(&temporary, format!("pid={}\n", process::id())).unwrap();
    std::fs::rename(&temporary, path).unwrap();
    let deadline = Instant::now() + Duration::from_secs(15);
    while Instant::now() < deadline {
        for mode in ["nonfinal", "final"] {
            if path.with_extension(format!("{mode}-challenge")).exists() {
                std::fs::write(path.with_extension(format!("{mode}-ack")), b"alive\n").unwrap();
            }
        }
        if path.with_extension("release").exists() { process::exit(0); }
        thread::sleep(Duration::from_millis(10));
    }
    panic!("parent did not complete drop challenge before its safety deadline");
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
    let output_bytes = std::env::var(STDIN_OUTPUT_ENV).ok().map(|value| value.parse::<usize>().unwrap()).unwrap_or(65_536);
    assert!(output_bytes <= 262_144, "fixture output limit");
    std::io::Write::write_all(&mut std::io::stdout(), &vec![b'S'; output_bytes]).unwrap();
    std::io::Write::flush(&mut std::io::stdout()).unwrap();
    std::io::Write::write_all(&mut std::io::stderr(), &vec![b'E'; output_bytes]).unwrap();
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

fn observe_stdin_child(record: std::path::PathBuf) -> Option<(u32, u32)> {
    let observed = record.with_extension("observed");
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

#[test]
fn windows_run_raw_transfers_blob_while_draining_both_streams() {
    let records = TempDir::new();
    let record = records.path().join("stdin-child.txt");
    let data = records.path().join("stdin-data.bin");
    let observer = thread::spawn({
        let record = record.clone();
        move || observe_stdin_child(record)
    });
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let record_literal = record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let data_literal = data.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let input: Blob = (0..1_048_576).map(|n| (n % 251) as u8).collect();
    let mut scope = Scope::new();
    scope.push("input", input.clone());
    let mut engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    #[cfg(not(feature = "unchecked"))]
    engine.set_max_array_size(2_097_152);
    let script = format!(
        r#"run_raw("{executable}", ["--exact", "windows_stdin_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {STDIN_RECORD_ENV}: "{record_literal}", {STDIN_DATA_ENV}: "{data_literal}", {STDIN_OUTPUT_ENV}: "262144" }},
            stdin: input, max_output: 524288, timeout: 15
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
    expected_stdout.extend(vec![b'S'; 262_144]);
    let stdout = result["stdout"].clone().try_cast::<Blob>().unwrap();
    let stderr = result["stderr"].clone().try_cast::<Blob>().unwrap();
    assert!(stdout == expected_stdout, "stdout mismatch: {} bytes", stdout.len());
    assert!(stderr == vec![b'E'; 262_144], "stderr mismatch: {} bytes", stderr.len());
    let readback = std::fs::read(&data).expect("child-written input readback");
    if std::env::var_os(STDIN_WRONG_EXPECTATION_ENV).is_some() {
        assert!(readback != input, "deliberately wrong stdin round-trip expectation");
    }
    assert!(readback == input, "child input mismatch: {} bytes", readback.len());
    assert_eq!(std::fs::read_to_string(&record).unwrap().trim(), format!("pid={pid}"));
}

#[test]
fn windows_run_string_empty_and_unit_stdin_reach_child_eof() {
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    let cases = [("string", Some("Rhai stdin: café, 東京, and a newline\n")), ("empty", Some("")), ("unit", None)];
    for (mode, input) in cases {
        let records = TempDir::new();
        let record = records.path().join("scalar-stdin-child.txt");
        let data = records.path().join("scalar-stdin-data.bin");
        let observer = thread::spawn({
            let record = record.clone();
            move || observe_stdin_child(record)
        });
        let record_literal = record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let data_literal = data.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let mut scope = Scope::new();
        if let Some(input) = input {
            scope.push("input", input.to_string());
        } else {
            scope.push_dynamic("input", rhai::Dynamic::UNIT);
        }
        let script = format!(
            r#"run("{executable}", ["--exact", "windows_stdin_fixture", "--nocapture", "--quiet"], #{{
                env_clear: true,
                env: #{{ {STDIN_RECORD_ENV}: "{record_literal}", {STDIN_DATA_ENV}: "{data_literal}", {STDIN_OUTPUT_ENV}: "0" }},
                stdin: input, max_output: 1024, timeout: 15
            }})"#
        );
        let result = engine.eval_with_scope::<Map>(&mut scope, &script);
        let observation = observer.join().expect("join scalar stdin child observer");
        let result = result.unwrap_or_else(|error| panic!("{mode} stdin failed: {error:?}; child_observed={}", observation.is_some()));
        let (pid, exit) = observation.expect("exact scalar child was independently observed");
        let readback = std::fs::read(&data).expect("child-written input readback");
        let expected = input.unwrap_or("").as_bytes();
        eprintln!("windows_scalar_stdin_readback mode={mode} pid={pid} exit={exit} bytes={} exact_handle_signaled=true", readback.len());
        if std::env::var(STDIN_SCALAR_WRONG_EXPECTATION_ENV).as_deref() == Ok(mode) {
            assert!(readback != expected, "deliberately wrong scalar stdin {mode} expectation");
        }
        assert_eq!(readback, expected, "{mode} input differs");
        assert_eq!(exit, 0);
        assert!(result["success"].as_bool().unwrap());
        assert_eq!(result["code"].as_int().unwrap(), 0);
        assert!(result["stdout_complete"].as_bool().unwrap());
        assert!(result["stderr_complete"].as_bool().unwrap());
        assert_eq!(result["stdout"].clone().try_cast::<ImmutableString>().unwrap().as_str(), std::str::from_utf8(LIBTEST_QUIET_START).unwrap());
        assert!(result["stderr"].clone().try_cast::<ImmutableString>().unwrap().is_empty());
        assert_eq!(std::fs::read_to_string(&record).unwrap().trim(), format!("pid={pid}"));
    }
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

/// A child-local PATH resolves a name without `.exe` to the exact copied fixture.
#[test]
fn windows_path_probe_fixture() {
    let Ok(record) = std::env::var("RHAI_WINDOWS_PATH_PROBE_RECORD") else { return; };
    let executable = std::env::current_exe().expect("resolve running fixture executable");
    std::fs::write(record, format!("pid={}\npath={}\n", process::id(), executable.display()))
        .expect("write own PID and executable path");
}

#[test]
fn windows_direct_run_resolves_child_path_and_implicit_exe() {
    let records = TempDir::new();
    let copied = records.path().join("rhai-path-fixture.exe");
    let record = records.path().join("path-child.txt");
    std::fs::copy(std::env::current_exe().unwrap(), &copied).expect("copy own path fixture");
    let mut scope = Scope::new();
    scope.push("fixture_path", records.path().to_string_lossy().into_owned());
    scope.push("record", record.to_string_lossy().into_owned());
    let engine = engine(SysConfig::default().programs(ProgramPolicy::AllowList(vec![
        "rhai-path-fixture".into(),
    ])));
    let result = engine.eval_with_scope::<Map>(&mut scope, r#"
        run_raw("rhai-path-fixture", ["--exact", "windows_path_probe_fixture", "--quiet"], #{
            env_clear: true,
            env: #{ PATH: fixture_path, RHAI_WINDOWS_PATH_PROBE_RECORD: record },
            timeout: 15
        })
    "#).expect("public run resolves copied fixture through child PATH");
    assert_eq!(result["code"].as_int().unwrap(), 0);
    let observed = std::fs::read_to_string(&record).expect("independent child PID record");
    let mut lines = observed.lines();
    let pid = lines.next().unwrap().strip_prefix("pid=").unwrap().parse::<u32>().unwrap();
    assert_ne!(pid, 0);
    let actual = std::fs::canonicalize(lines.next().unwrap().strip_prefix("path=").unwrap()).unwrap();
    let expected = std::fs::canonicalize(&copied).unwrap();
    assert!(lines.next().is_none());
    assert_eq!(actual, expected, "child must run the exact PATH fixture");
    eprintln!("windows_child_path_readback pid={pid} exact_exe=true");
    if std::env::var_os("RHAI_WINDOWS_PATH_WRONG_EXPECTATION").is_some() {
        assert_ne!(actual, expected, "deliberately wrong child PATH expectation");
    }
}

/// Only this child process changes its cwd; the parent test environment is untouched.
#[test]
fn windows_managed_cwd_controller() {
    let Some(root) = std::env::var_os(MANAGED_CWD_CONTROLLER_ENV) else { return; };
    let root = std::path::PathBuf::from(root);
    std::env::set_current_dir(&root).expect("enter isolated controller cwd");
    let mut scope = Scope::new();
    scope.push("record", root.join("cwd-child.txt").to_string_lossy().into_owned());
    let config = SysConfig::default()
        .programs(ProgramPolicy::AllowList(vec![
            "rhai-managed-cwd-probe".into(),
            "rhai-managed-path-probe".into(),
        ]))
        .process_scope(ProcessScope::Managed);
    let engine = engine(config);
    let report = engine
        .eval_with_scope::<Map>(&mut scope, r#"
            run_raw("rhai-managed-cwd-probe", ["--exact", "windows_path_probe_fixture", "--quiet"], #{
                env_clear: true,
                env: #{ RHAI_WINDOWS_PATH_PROBE_RECORD: record },
                timeout: 15
            })
        "#)
        .expect("public Managed run must find a simple executable in parent cwd");
    assert_eq!(report["code"].as_int().unwrap(), 0);
    scope.push("selected_path", root.join("selected-path").to_string_lossy().into_owned());
    scope.push("path_record", root.join("path-child.txt").to_string_lossy().into_owned());
    let report = engine
        .eval_with_scope::<Map>(&mut scope, r#"
            run_raw("rhai-managed-path-probe", ["--exact", "windows_path_probe_fixture", "--quiet"], #{
                env_clear: true,
                env: #{ PATH: selected_path, RHAI_WINDOWS_PATH_PROBE_RECORD: path_record },
                timeout: 15
            })
        "#)
        .expect("public Managed run must prefer explicit child PATH over parent cwd");
    assert_eq!(report["code"].as_int().unwrap(), 0);
}

#[test]
fn windows_managed_run_resolves_simple_program_from_parent_cwd() {
    struct ControllerGuard {
        child: Option<std::process::Child>,
        root: Option<TempDir>,
        root_safe_to_retire: bool,
    }
    impl Drop for ControllerGuard {
        fn drop(&mut self) {
            if let Some(mut child) = self.child.take() {
                let exact = child.as_raw_handle() as Handle;
                if unsafe { WaitForSingleObject(exact, 0) } != WAIT_OBJECT_0 {
                    let _ = child.kill();
                }
                if unsafe { WaitForSingleObject(exact, 10_000) } != WAIT_OBJECT_0 {
                    eprintln!("cwd controller exit unconfirmed; retain exact handle and fixture root");
                    std::mem::forget(child);
                    if let Some(root) = self.root.take() { std::mem::forget(root); }
                    return;
                }
                let _ = child.wait();
            }
            if !self.root_safe_to_retire {
                eprintln!("cwd controller did not prove fixture cleanup; retain root for scoped runner");
                if let Some(root) = self.root.take() { std::mem::forget(root); }
            }
        }
    }

    let parent_cwd = std::env::current_dir().expect("read unchanged parent cwd");
    let records = TempDir::new();
    let root = records.path().to_path_buf();
    let copied = root.join("rhai-managed-cwd-probe.exe");
    std::fs::copy(std::env::current_exe().unwrap(), &copied)
        .expect("copy executable into isolated controller cwd");
    let competing = root.join("rhai-managed-path-probe.exe");
    let selected_dir = root.join("selected-path");
    std::fs::create_dir(&selected_dir).expect("create isolated child PATH directory");
    let selected = selected_dir.join("rhai-managed-path-probe.exe");
    std::fs::copy(std::env::current_exe().unwrap(), &competing)
        .expect("copy competing executable into isolated controller cwd");
    std::fs::copy(std::env::current_exe().unwrap(), &selected)
        .expect("copy selected executable into child PATH directory");
    let out = std::fs::File::create(root.join("controller.out")).unwrap();
    let err = std::fs::File::create(root.join("controller.err")).unwrap();
    let child = std::process::Command::new(std::env::current_exe().unwrap())
        .args(["--exact", "windows_managed_cwd_controller", "--quiet"])
        .env_clear()
        .env(MANAGED_CWD_CONTROLLER_ENV, &root)
        .stdin(std::process::Stdio::null())
        .stdout(out)
        .stderr(err)
        .spawn()
        .expect("start isolated cwd controller");
    let mut guard = ControllerGuard { child: Some(child), root: Some(records), root_safe_to_retire: false };
    let deadline = Instant::now() + Duration::from_secs(30);
    let status = loop {
        if let Some(status) = guard.child.as_mut().unwrap().try_wait().expect("wait for cwd controller") {
            break status;
        }
        assert!(Instant::now() < deadline, "isolated cwd controller exceeded 30 seconds");
        thread::sleep(Duration::from_millis(10));
    };
    let stderr = std::fs::read_to_string(root.join("controller.err")).unwrap();
    assert!(status.success(), "public Managed cwd controller failed: {status:?}; {stderr}");
    let observed = std::fs::read_to_string(root.join("cwd-child.txt"))
        .expect("fresh independent child-written executable record");
    let mut lines = observed.lines();
    let pid = lines.next().unwrap().strip_prefix("pid=").unwrap().parse::<u32>().unwrap();
    let actual = std::fs::canonicalize(lines.next().unwrap().strip_prefix("path=").unwrap()).unwrap();
    let expected = std::fs::canonicalize(&copied).unwrap();
    assert!(lines.next().is_none());
    assert_ne!(pid, 0);
    assert_eq!(actual, expected, "Managed child must run the exact cwd executable");
    let path_observed = std::fs::read_to_string(root.join("path-child.txt"))
        .expect("fresh independent child PATH executable record");
    let mut path_lines = path_observed.lines();
    let path_pid = path_lines.next().unwrap().strip_prefix("pid=").unwrap().parse::<u32>().unwrap();
    let path_actual = std::fs::canonicalize(path_lines.next().unwrap().strip_prefix("path=").unwrap()).unwrap();
    let path_expected = std::fs::canonicalize(&selected).unwrap();
    assert!(path_lines.next().is_none());
    assert_ne!(path_pid, 0);
    assert_eq!(path_actual, path_expected, "Managed child must select explicit child PATH before parent cwd");
    assert_eq!(std::env::current_dir().unwrap(), parent_cwd, "parent test cwd changed");
    guard.root_safe_to_retire = true;
    drop(guard);
    eprintln!("windows_managed_cwd_readback child_pid={pid} exact_cwd_exe=true parent_cwd_unchanged=true");
    eprintln!("windows_managed_path_readback child_pid={path_pid} selected_child_path=true competing_parent_cwd=true");
    if std::env::var_os(MANAGED_CWD_WRONG_ENV).is_some() {
        assert_ne!(actual, expected, "deliberately wrong Managed cwd executable expectation");
    }
    if std::env::var_os(MANAGED_PATH_WRONG_ENV).is_some() {
        assert_ne!(path_actual, path_expected, "deliberately wrong Managed child PATH precedence expectation");
    }
}

/// Public argument encoding is checked against a file written by a real PowerShell
/// child, not against another copy of the parent-side quoting algorithm.
#[test]
fn windows_direct_run_preserves_embedded_quote_argument() {
    let records = TempDir::new();
    let script_file = records.path().join("read argument.ps1");
    let record = records.path().join("argument.txt");
    std::fs::write(
        &script_file,
        b"[IO.File]::WriteAllText($env:RHAI_WINDOWS_ARG_RECORD, [string]$args[0], [Text.UTF8Encoding]::new($false))\r\n",
    )
    .expect("write own PowerShell argument fixture");
    let powershell = std::path::PathBuf::from(std::env::var_os("SystemRoot").expect("SystemRoot"))
        .join(r"System32\WindowsPowerShell\v1.0\powershell.exe");
    let argument = "before\"after";
    let mut scope = Scope::new();
    scope.push("program", powershell.to_string_lossy().into_owned());
    scope.push("fixture", script_file.to_string_lossy().into_owned());
    scope.push("argument", argument.to_owned());
    scope.push("record", record.to_string_lossy().into_owned());
    let result = engine(SysConfig::default().programs(ProgramPolicy::Any))
        .eval_with_scope::<Map>(
            &mut scope,
            r#"run_raw(program, ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", fixture, argument],
                #{ env: #{ RHAI_WINDOWS_ARG_RECORD: record }, timeout: 15 })"#,
        )
        .expect("public run of argument fixture");
    assert_eq!(result["code"].as_int().unwrap(), 0);
    let observed = std::fs::read_to_string(&record).expect("independent child argument record");
    eprintln!("windows_argument_readback={observed:?}");
    if std::env::var_os("RHAI_WINDOWS_ARG_WRONG_EXPECTATION").is_some() {
        assert_ne!(observed, argument, "deliberately wrong Windows argument expectation");
    }
    assert_eq!(observed, argument, "child must receive the embedded quote intact");
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

/// A spawned child remains observable through cloned script handles until its exact OS
/// process exits; waiting twice returns the same completed snapshot.
#[test]
fn windows_spawn_child_can_be_polled_and_waited_through_clones() {
    let engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let records = TempDir::new();
    let record = records.path().join("spawn-child-record.txt");
    let script_record = record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script = format!(
        r#"spawn("{executable}", ["--exact", "windows_process_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {FIXTURE_CODE_ENV}: "7", {FIXTURE_RECORD_ENV}: "{script_record}" }},
            max_output: 1024
        }})"#
    );
    let child = engine.eval::<Dynamic>(&script).unwrap_or_else(|error| {
        if matches!(&*error, EvalAltResult::ErrorFunctionNotFound(name, _) if name.starts_with("spawn (")) {
            eprintln!("windows_spawn_contract_missing_public_spawn");
        }
        panic!("Windows spawn must return a shared Child handle: {error:?}")
    });
    let deadline = Instant::now() + Duration::from_secs(5);
    let text = loop {
        match std::fs::read_to_string(&record) {
            Ok(text) => break text,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound && Instant::now() < deadline => {
                thread::sleep(Duration::from_millis(10));
            }
            Err(error) => panic!("spawned child readiness record unavailable: {error}"),
        }
    };
    let pid = text.split_whitespace().next().unwrap().strip_prefix("pid=").unwrap().parse::<u32>().unwrap();
    let raw = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE | SYNCHRONIZE, 0, pid) };
    assert!(!raw.is_null(), "open exact spawned process {pid}: {}", std::io::Error::last_os_error());
    let mut guard = TimeoutChildGuard { handle: OwnedProcessHandle(raw), pid, exit_observed: false };
    let mut scope = Scope::new();
    scope.push_dynamic("child", child.clone());
    scope.push_dynamic("sibling", child);
    assert!(engine.eval_with_scope::<Dynamic>(&mut scope, "child.try_wait()").unwrap().is_unit(), "gated child must still be running");
    assert!(engine.eval_with_scope::<Dynamic>(&mut scope, "child.wait(0.0)").unwrap().is_unit(), "zero-time wait must not cancel the gated child");
    std::fs::write(record.with_extension("release"), b"release\n").unwrap();
    let first = engine.eval_with_scope::<Map>(&mut scope, "child.wait()").unwrap();
    let second = engine.eval_with_scope::<Map>(&mut scope, "sibling.wait()").unwrap();
    assert_eq!(unsafe { WaitForSingleObject(guard.handle.0, 10_000) }, WAIT_OBJECT_0, "exact spawned child did not exit");
    let mut exit_code = u32::MAX;
    assert_ne!(unsafe { GetExitCodeProcess(guard.handle.0, &mut exit_code) }, 0);
    guard.exit_observed = true;
    assert_eq!(exit_code, 7);
    assert_eq!(first["code"].as_int().unwrap(), 7);
    assert_eq!(second["code"].as_int().unwrap(), 7);
    assert!(!first["success"].as_bool().unwrap());
    assert!(first["stdout_complete"].as_bool().unwrap());
    assert!(first["stderr_complete"].as_bool().unwrap());
    assert_eq!(first["stdout"].clone().cast::<ImmutableString>().as_str(), "\nrunning 1 test\n\0A\u{fffd}");
    assert_eq!(first["stderr"].clone().cast::<ImmutableString>().as_str(), "\u{fffd}B\0");
    assert_eq!(first["stdout"].clone().cast::<ImmutableString>(), second["stdout"].clone().cast::<ImmutableString>());
    assert_eq!(first["stderr"].clone().cast::<ImmutableString>(), second["stderr"].clone().cast::<ImmutableString>());
    let third = engine.eval_with_scope::<Map>(&mut scope, r#"let result = child.wait(); result.code = 99; result.stdout = "altered"; sibling.wait()"#).unwrap();
    assert_eq!(third["code"].as_int().unwrap(), 7, "mutating one result must not change the cached exit");
    assert_eq!(third["stdout"].clone().cast::<ImmutableString>().as_str(), "\nrunning 1 test\n\0A\u{fffd}", "mutating one result must not change cached output");
    eprintln!("windows_spawn_os_readback pid={pid} exit={exit_code} exact_handle_signaled=true");
    if std::env::var_os(CHILD_SNAPSHOT_WRONG_EXPECTATION_ENV).is_some() {
        assert_eq!(third["code"].as_int().unwrap(), 99, "deliberately wrong cached snapshot expectation");
    }
    if std::env::var_os(SPAWN_WRONG_EXPECTATION_ENV).is_some() {
        assert_eq!(exit_code, 8, "deliberately wrong spawned child exit expectation");
    }
}

/// Cancellation terminates a child with buffered, unread stdin and reaps the exact child.
#[test]
fn windows_spawn_kill_stops_child_with_unread_buffered_input() {
    let records = TempDir::new();
    let record = records.path().join("spawn-kill-child.txt");
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script_record = record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let mut engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    #[cfg(not(feature = "unchecked"))]
    engine.set_max_array_size(2_097_152);
    let mut scope = Scope::new();
    scope.push("input", vec![0x5au8; 1_048_576]);
    let script = format!(r#"spawn("{executable}", ["--exact", "windows_spawn_blocked_input_fixture", "--nocapture", "--quiet"], #{{
        env_clear: true, env: #{{ {SPAWN_KILL_RECORD_ENV}: "{script_record}" }}, stdin: input, max_output: 1024
    }})"#);
    let child = engine.eval_with_scope::<Dynamic>(&mut scope, &script).expect("spawn with large unread stdin must return a handle");
    scope.push_dynamic("child", child.clone());
    scope.push_dynamic("sibling", child);
    let deadline = Instant::now() + Duration::from_secs(10);
    let text = loop {
        match std::fs::read_to_string(&record) {
            Ok(text) => break text,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound && Instant::now() < deadline => thread::sleep(Duration::from_millis(10)),
            Err(error) => panic!("blocked input child readiness unavailable: {error}"),
        }
    };
    let fields: Vec<_> = text.split_whitespace().collect();
    assert_eq!(fields.len(), 3, "child readiness: {text:?}");
    let pid = fields[0].strip_prefix("pid=").unwrap().parse::<u32>().unwrap();
    assert_eq!(fields[1], "first=5a");
    let available = fields[2].strip_prefix("available=").unwrap().parse::<u32>().unwrap();
    assert!(available >= 8_191);
    let raw = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE | SYNCHRONIZE, 0, pid) };
    assert!(!raw.is_null(), "open exact blocked-input process {pid}: {}", std::io::Error::last_os_error());
    let mut guard = TimeoutChildGuard { handle: OwnedProcessHandle(raw), pid, exit_observed: false };
    assert!(engine.eval_with_scope::<Dynamic>(&mut scope, "child.try_wait()").unwrap().is_unit());
    engine.run_with_scope(&mut scope, "child.kill(); sibling.kill();").unwrap();
    let first = engine.eval_with_scope::<Map>(&mut scope, "child.wait()").expect("kill must complete without a stdin write failure");
    let second = engine.eval_with_scope::<Map>(&mut scope, "sibling.wait()").unwrap();
    assert_eq!(unsafe { WaitForSingleObject(guard.handle.0, 10_000) }, WAIT_OBJECT_0, "exact blocked-input child did not exit");
    let mut exit_code = u32::MAX;
    assert_ne!(unsafe { GetExitCodeProcess(guard.handle.0, &mut exit_code) }, 0);
    guard.exit_observed = true;
    assert_eq!(first["code"].as_int().unwrap() as u32, exit_code);
    assert_eq!(second["code"].as_int().unwrap() as u32, exit_code);
    assert!(!first["success"].as_bool().unwrap());
    engine.run_with_scope(&mut scope, "child.kill();").unwrap();
    eprintln!("windows_spawn_kill_os_readback pid={pid} exit={exit_code} available={available} exact_handle_signaled=true");
    if std::env::var_os(SPAWN_KILL_WRONG_EXPECTATION_ENV).is_some() {
        assert_eq!(exit_code, 0, "deliberately wrong killed child exit expectation");
    }
}

/// Nonfinal clones preserve the child; the final drop follows the host policy.
#[test]
fn windows_spawn_child_drop_follows_host_policy() {
    for kill_on_drop in [true, false] {
        let mode = if kill_on_drop { "kill" } else { "retain" };
        let engine = engine(SysConfig::default().programs(ProgramPolicy::Any).kill_on_drop(kill_on_drop));
        let records = TempDir::new();
        let record = records.path().join("drop-child.txt");
        let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let script_record = record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let script = format!(r#"spawn("{executable}", ["--exact", "windows_child_drop_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true, env: #{{ {CHILD_DROP_RECORD_ENV}: "{script_record}" }}, max_output: 1024
        }})"#);
        let child = engine.eval::<Dynamic>(&script).expect("spawn drop fixture");
        let sibling = child.clone();
        let deadline = Instant::now() + Duration::from_secs(5);
        let text = loop {
            match std::fs::read_to_string(&record) {
                Ok(text) => break text,
                Err(error) if error.kind() == std::io::ErrorKind::NotFound && Instant::now() < deadline => thread::sleep(Duration::from_millis(10)),
                Err(error) => panic!("drop child readiness unavailable: {error}"),
            }
        };
        let pid = text.split_whitespace().next().unwrap().strip_prefix("pid=").unwrap().parse::<u32>().unwrap();
        let raw = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE | SYNCHRONIZE, 0, pid) };
        assert!(!raw.is_null(), "open exact drop child {pid}: {}", std::io::Error::last_os_error());
        let mut guard = TimeoutChildGuard { handle: OwnedProcessHandle(raw), pid, exit_observed: false };
        let challenge = |phase: &str| {
            std::fs::write(record.with_extension(format!("{phase}-challenge")), b"challenge\n").unwrap();
            let deadline = Instant::now() + Duration::from_secs(4);
            loop {
                if std::fs::read(record.with_extension(format!("{phase}-ack"))).is_ok_and(|bytes| bytes == b"alive\n") { break; }
                assert!(Instant::now() < deadline, "child did not acknowledge {phase} challenge");
                thread::sleep(Duration::from_millis(10));
            }
        };
        drop(child);
        let nonfinal_wait = unsafe { WaitForSingleObject(guard.handle.0, 0) };
        assert_eq!(nonfinal_wait, WAIT_TIMEOUT, "nonfinal clone drop must preserve child");
        challenge("nonfinal");
        drop(sibling);
        if !kill_on_drop {
            assert_eq!(unsafe { WaitForSingleObject(guard.handle.0, 0) }, WAIT_TIMEOUT, "false policy must preserve child after final drop");
            challenge("final");
            std::fs::write(record.with_extension("release"), b"release\n").unwrap();
        }
        assert_eq!(unsafe { WaitForSingleObject(guard.handle.0, 10_000) }, WAIT_OBJECT_0, "exact child did not exit after final drop");
        let mut exit_code = u32::MAX;
        assert_ne!(unsafe { GetExitCodeProcess(guard.handle.0, &mut exit_code) }, 0);
        guard.exit_observed = true;
        assert_eq!(exit_code == 0, !kill_on_drop, "exact child exit must follow final-drop policy");
        eprintln!("windows_child_drop_os_readback mode={mode} pid={pid} exit={exit_code} nonfinal_ack=true final_ack={} exact_handle_signaled=true", !kill_on_drop);
        if std::env::var(CHILD_DROP_WRONG_EXPECTATION_ENV).as_deref() == Ok(mode) {
            assert!(!record.with_extension(if kill_on_drop { "nonfinal-ack" } else { "final-ack" }).exists(), "deliberately wrong child drop {mode} survival expectation");
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

/// A leaf owned by either the managed task or the independently launched sentinel.
#[test]
fn windows_managed_leaf_fixture() {
    let Ok(record) = std::env::var(MANAGED_LEAF_ENV) else { return; };
    let record = std::path::Path::new(&record);
    let temporary = record.with_extension("tmp");
    std::fs::write(&temporary, format!("{}\n", process::id())).unwrap();
    std::fs::rename(temporary, record).unwrap();
    let deadline = Instant::now() + Duration::from_secs(25);
    while Instant::now() < deadline {
        if record.with_extension("stop").exists() { process::exit(0); }
        for phase in ["nonfinal", "final"] {
            let challenge = record.with_extension(format!("{phase}-challenge"));
            let ack = record.with_extension(format!("{phase}-ack"));
            if challenge.exists() && !ack.exists() {
                std::fs::write(ack, b"alive\n").unwrap();
            }
        }
        thread::sleep(Duration::from_millis(10));
    }
    panic!("managed leaf exceeded its safety deadline");
}

/// The owner may opt in to batch execution; Managed must still launch it inside
/// its owned scope, and the host independently reads the child's output file.
#[test]
fn windows_managed_run_executes_explicitly_allowed_batch() {
    let records = TempDir::new();
    let batch = records.path().join("allowed fixture.cmd");
    let record = records.path().join("batch-record.txt");
    std::fs::write(&batch, b"@echo off\r\n>\"%RHAI_WINDOWS_BATCH_RECORD%\" echo managed-batch-ok\r\n")
        .expect("write own batch fixture");
    let program = batch.to_string_lossy().into_owned();
    let mut scope = Scope::new();
    scope.push("program", program.clone());
    scope.push("record", record.to_string_lossy().into_owned());
    let denied_config = SysConfig::default()
        .programs(ProgramPolicy::AllowList(vec![program.clone()]))
        .process_scope(ProcessScope::Managed);
    let script = r#"run_raw(program, #{ env: #{ RHAI_WINDOWS_BATCH_RECORD: record }, timeout: 15 })"#;
    let denied = engine(denied_config).eval_with_scope::<Map>(&mut scope, script)
        .expect_err("batch execution is denied by default");
    match *denied {
        EvalAltResult::ErrorRuntime(value, _) => match value.try_cast::<SysError>() {
            Some(SysError::Denied(reason)) => assert_eq!(reason, "batch files are not allowed by host configuration"),
            other => panic!("expected batch-specific denial: {other:?}"),
        },
        other => panic!("expected typed batch denial: {other:?}"),
    }
    assert!(!record.exists(), "denied batch must not start");
    eprintln!("windows_managed_batch_denial_readback batch_denied=true child_file_absent=true");
    let config = SysConfig::default()
        .programs(ProgramPolicy::AllowList(vec![program]))
        .process_scope(ProcessScope::Managed)
        .allow_batch_files(true);
    let result = engine(config).eval_with_scope::<Map>(
        &mut scope,
        script,
    );
    let observed = std::fs::read_to_string(&record).ok();
    assert!(result.is_ok(), "allowed managed batch must run: {result:?}; record={observed:?}");
    let report = result.unwrap();
    assert_eq!(report["code"].as_int().unwrap(), 0);
    assert_eq!(observed.as_deref().map(str::trim), Some("managed-batch-ok"));
    eprintln!("windows_managed_batch_readback allowed=true child_file=managed-batch-ok");
    if std::env::var_os(MANAGED_BATCH_WRONG_ENV).is_some() {
        assert_ne!(observed.as_deref().map(str::trim), Some("managed-batch-ok"),
            "deliberately wrong managed batch expectation");
    }
}

/// A script-supplied argument must not become an additional command when a host
/// explicitly permits a managed batch file. All effects stay in this fixture root.
#[test]
fn windows_managed_batch_argument_cannot_create_an_extra_file() {
    let records = TempDir::new();
    let batch = records.path().join("safe-batch.cmd");
    let record = records.path().join("expected.txt");
    let injected = records.path().join("injected.txt");
    assert!(injected.to_string_lossy().chars().all(|ch| ch.is_ascii_alphanumeric()
        || matches!(ch, '\\' | ':' | '_' | '-' | '.')),
        "fixture path must contain only safe ASCII path characters");
    std::fs::write(&batch, b"@echo off\r\n>\"%RHAI_WINDOWS_BATCH_RECORD%\" echo batch-started\r\n")
        .expect("write own batch fixture");
    let program = batch.to_string_lossy().into_owned();
    let mut scope = Scope::new();
    scope.push("program", program.clone());
    scope.push("record", record.to_string_lossy().into_owned());
    scope.push("injected", injected.to_string_lossy().into_owned());
    scope.push("argument", "safe&echo(INJECTED>%RHAI_WINDOWS_BATCH_INJECT%".to_owned());
    let config = SysConfig::default().programs(ProgramPolicy::AllowList(vec![program]))
        .process_scope(ProcessScope::Managed).allow_batch_files(true);
    let result = engine(config).eval_with_scope::<Map>(
        &mut scope,
        r#"run_raw(program, [argument], #{ env: #{ RHAI_WINDOWS_BATCH_RECORD: record, RHAI_WINDOWS_BATCH_INJECT: injected }, timeout: 15 })"#,
    );
    let injected_exists = injected.exists();
    eprintln!("windows_managed_batch_argument_readback injected={injected_exists} child_record={:?} result={result:?}", std::fs::read_to_string(&record).ok());
    assert!(!injected_exists, "batch argument must not execute an extra command");
    let report = result.expect("the allowed batch with this argument must run safely");
    assert_eq!(report["code"].as_int().unwrap(), 0);
    assert_eq!(std::fs::read_to_string(&record).unwrap().trim(), "batch-started");
    if std::env::var_os("RHAI_WINDOWS_BATCH_INJECTION_WRONG_EXPECTATION").is_some() {
        assert!(injected_exists, "deliberately wrong batch injection expectation");
    }
}

/// The direct managed child starts a leaf, records both identities, and exits on release.
#[test]
fn windows_managed_parent_fixture() {
    let Ok(root) = std::env::var(MANAGED_ROOT_ENV) else { return; };
    let root = std::path::Path::new(&root);
    let leaf_record = root.join("worker.pid");
    let _leaf = OwnedFixture(Some(process::Command::new(std::env::current_exe().unwrap())
        .args(["--exact", "windows_managed_leaf_fixture", "--nocapture", "--quiet"])
        .env_clear().env(MANAGED_LEAF_ENV, &leaf_record)
        .stdin(process::Stdio::null()).stdout(process::Stdio::null()).stderr(process::Stdio::null())
        .spawn().expect("start managed descendant")));
    let deadline = Instant::now() + Duration::from_secs(20);
    while !leaf_record.exists() {
        assert!(Instant::now() < deadline, "managed descendant did not become ready");
        thread::sleep(Duration::from_millis(10));
    }
    if std::env::var_os("RHAI_DEBUG_JOB_MEMBERS").is_some() {
        #[repr(C)]
        struct ProcessList { assigned: u32, listed: u32, ids: [usize; 32] }
        let mut members = ProcessList { assigned: 0, listed: 0, ids: [0; 32] };
        // SAFETY: NULL selects this fixture's immediate job; the buffer is writable and aligned.
        let ok = unsafe { QueryInformationJobObject(std::ptr::null_mut(), 3, &mut members as *mut _ as *mut c_void,
            std::mem::size_of_val(&members) as u32, std::ptr::null_mut()) };
        let detail = if ok == 0 {
            format!("query_failed={} assigned={} listed={}", std::io::Error::last_os_error(), members.assigned, members.listed)
        } else if members.listed <= members.ids.len() as u32 {
            format!("complete={} assigned={} listed={} ids={:?}", members.assigned == members.listed,
                members.assigned, members.listed, &members.ids[..members.listed as usize])
        } else {
            format!("inconsistent_counts assigned={} listed={}", members.assigned, members.listed)
        };
        std::fs::write(root.join("job-members.txt"), detail).unwrap();
    }
    let temporary = root.join("parent.tmp");
    std::fs::write(&temporary, format!("{}\n", process::id())).unwrap();
    std::fs::rename(temporary, root.join("parent.pid")).unwrap();
    while Instant::now() < deadline {
        if root.join("release").exists() { process::exit(0); }
        for phase in ["nonfinal", "final"] {
            let challenge = root.join(format!("parent-{phase}-challenge"));
            let ack = root.join(format!("parent-{phase}-ack"));
            if challenge.exists() && !ack.exists() {
                std::fs::write(ack, b"alive\n").unwrap();
            }
        }
        thread::sleep(Duration::from_millis(10));
    }
    panic!("managed parent was not released");
}

struct OwnedFixture(Option<process::Child>);
impl OwnedFixture {
    fn wait_bounded(&mut self) -> Option<process::ExitStatus> {
        let child = self.0.as_mut()?;
        let raw = child.as_raw_handle() as Handle;
        if unsafe { WaitForSingleObject(raw, 10_000) } != WAIT_OBJECT_0 { return None; }
        child.wait().ok()
    }
}
impl Drop for OwnedFixture {
    fn drop(&mut self) {
        let Some(child) = self.0.as_ref() else { return; };
        let raw = child.as_raw_handle() as Handle;
        let pid = child.id();
        if unsafe { WaitForSingleObject(raw, 0) } != WAIT_OBJECT_0 {
            if unsafe { TerminateProcess(raw, 1) } == 0 {
                eprintln!("failed to terminate exact fixture {pid}: {}", std::io::Error::last_os_error());
            }
        }
        if self.wait_bounded().is_none() {
            eprintln!("exact fixture {pid} exit remains unconfirmed; retaining handle for outer job cleanup");
            if let Some(child) = self.0.take() { std::mem::forget(child); }
        }
    }
}

fn wait_for_pid(path: &std::path::Path, deadline: Instant) -> Option<u32> {
    loop {
        match std::fs::read_to_string(path) {
            Ok(value) => return Some(value.trim().parse().expect("fixture PID")),
            Err(error) if error.kind() == std::io::ErrorKind::NotFound && Instant::now() < deadline => thread::sleep(Duration::from_millis(10)),
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => return None,
            Err(error) => panic!("fixture record {}: {error}", path.display()),
        }
    }
}

struct ManagedFixtureGuard { handle: Option<OwnedProcessHandle>, pid: u32, exit_observed: bool }
impl ManagedFixtureGuard {
    fn handle(&self) -> Handle { self.handle.as_ref().expect("owned fixture handle").0 }
}
impl Drop for ManagedFixtureGuard {
    fn drop(&mut self) {
        if self.exit_observed { return; }
        let raw = self.handle();
        if unsafe { WaitForSingleObject(raw, 0) } != WAIT_OBJECT_0 && unsafe { TerminateProcess(raw, 1) } == 0 {
            eprintln!("failed to terminate exact managed fixture {}: {}", self.pid, std::io::Error::last_os_error());
        }
        if unsafe { WaitForSingleObject(raw, 10_000) } != WAIT_OBJECT_0 {
            eprintln!("managed fixture {} exit remains unconfirmed; retaining handle for outer job cleanup", self.pid);
            if let Some(handle) = self.handle.take() { std::mem::forget(handle); }
        }
    }
}
struct ManagedRecords { directory: Option<TempDir>, safe_to_remove: bool }
impl Drop for ManagedRecords {
    fn drop(&mut self) {
        if !self.safe_to_remove {
            if let Some(directory) = self.directory.take() {
                eprintln!("preserving managed fixture directory {} for outer job cleanup", directory.path().display());
                std::mem::forget(directory);
            }
        }
    }
}

fn open_fixture_guard(pid: u32) -> ManagedFixtureGuard {
    let raw = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE | SYNCHRONIZE, 0, pid) };
    assert!(!raw.is_null(), "open exact fixture {pid}: {}", std::io::Error::last_os_error());
    ManagedFixtureGuard { handle: Some(OwnedProcessHandle(raw)), pid, exit_observed: false }
}

/// A normal managed run closes the descendant job before success, without touching a sentinel.
#[test]
fn windows_managed_run_closes_descendant_on_normal_parent_exit() {
    let mut records = ManagedRecords { directory: Some(TempDir::new()), safe_to_remove: false };
    let record_root = records.directory.as_ref().unwrap().path().to_path_buf();
    let sentinel_record = record_root.join("sentinel.pid");
    let sentinel = process::Command::new(std::env::current_exe().unwrap())
        .args(["--exact", "windows_managed_leaf_fixture", "--nocapture", "--quiet"])
        .env_clear().env(MANAGED_LEAF_ENV, &sentinel_record)
        .stdin(process::Stdio::null()).stdout(process::Stdio::null()).stderr(process::Stdio::null())
        .spawn().expect("start independent sentinel");
    let mut sentinel = OwnedFixture(Some(sentinel));
    let sentinel_pid = wait_for_pid(&sentinel_record, Instant::now() + Duration::from_secs(5)).expect("sentinel ready");
    assert_eq!(sentinel_pid, sentinel.0.as_ref().unwrap().id());
    let (sender, receiver) = std::sync::mpsc::sync_channel(1);
    let observer = thread::spawn({
        let root = record_root.clone();
        move || {
            let deadline = Instant::now() + Duration::from_secs(5);
            let worker_pid = wait_for_pid(&root.join("worker.pid"), deadline)?;
            let worker = open_fixture_guard(worker_pid);
            let parent_pid = wait_for_pid(&root.join("parent.pid"), deadline)?;
            assert_ne!(parent_pid, worker_pid);
            let parent = open_fixture_guard(parent_pid);
            assert_eq!(unsafe { WaitForSingleObject(parent.handle(), 0) }, WAIT_TIMEOUT);
            assert_eq!(unsafe { WaitForSingleObject(worker.handle(), 0) }, WAIT_TIMEOUT);
            sender.send((parent, worker)).expect("deliver exact fixture handles");
            std::fs::write(root.join("release"), b"release\n").unwrap();
            Some(())
        }
    });
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let root = record_root.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script = format!(r#"run_raw("{executable}", ["--exact", "windows_managed_parent_fixture", "--nocapture", "--quiet"], #{{
        env_clear: true, env: #{{ {MANAGED_ROOT_ENV}: "{root}" }}, max_output: 1024, timeout: 15
    }})"#);
    let result = engine(SysConfig::default().programs(ProgramPolicy::Any).process_scope(ProcessScope::Managed)).eval::<Map>(&script);
    let mut handles = receiver.try_recv().ok();
    let observed_closed_at_return = handles.as_ref().map(|(_, worker)| unsafe { WaitForSingleObject(worker.handle(), 0) == WAIT_OBJECT_0 }).unwrap_or(false);
    if handles.is_none() { handles = receiver.recv_timeout(Duration::from_secs(6)).ok(); }
    let observation = observer.join().expect("join managed process observer");
    let sentinel_alive = sentinel.0.as_mut().unwrap().try_wait().unwrap().is_none();
    std::fs::write(sentinel_record.with_extension("stop"), b"stop\n").unwrap();
    let sentinel_exit = sentinel.wait_bounded().expect("sentinel must exit within its bound");
    if let Err(ref error) = result {
        if matches!(&**error, EvalAltResult::ErrorRuntime(value, _) if matches!(value.clone().try_cast::<SysError>(), Some(SysError::Denied(_)))) {
            eprintln!("windows_managed_contract_denied_before_launch observation={}", observation.is_some());
        }
    }
    let result = result.unwrap_or_else(|error| panic!("Windows managed run must execute and close its descendant scope: {error:?}"));
    observation.expect("observe exact managed child and descendant");
    let (mut parent, mut worker) = handles.expect("retain exact managed child and descendant handles");
    assert!(observed_closed_at_return, "managed descendant must be stopped when run returns");
    assert_eq!(unsafe { WaitForSingleObject(parent.handle(), 0) }, WAIT_OBJECT_0);
    parent.exit_observed = true;
    worker.exit_observed = true;
    let (parent_pid, worker_pid) = (parent.pid, worker.pid);
    let mut parent_exit = u32::MAX;
    assert_ne!(unsafe { GetExitCodeProcess(parent.handle(), &mut parent_exit) }, 0);
    assert_eq!(parent_exit, 0);
    assert_eq!(result["code"].as_int().unwrap(), 0);
    assert!(result["success"].as_bool().unwrap());
    assert!(sentinel_alive && sentinel_exit.success(), "managed closure must preserve the independent sentinel");
    records.safe_to_remove = true;
    eprintln!("windows_managed_os_readback parent={parent_pid} worker={worker_pid} parent_exit={parent_exit} sentinel={sentinel_pid} sentinel_alive=true");
    if std::env::var_os(MANAGED_WRONG_ENV).is_some() {
        assert!(!sentinel_alive, "deliberately wrong managed sentinel expectation");
    }
    if std::env::var_os(MANAGED_RUN_CLOSURE_WRONG_ENV).is_some() {
        assert!(!observed_closed_at_return,
            "deliberately wrong managed run descendant closure expectation");
    }
}

/// Waiting on a managed spawned child must not publish success while its leaf lives.
#[test]
fn windows_managed_spawn_wait_closes_descendant_on_parent_exit() {
    let mut records = ManagedRecords { directory: Some(TempDir::new()), safe_to_remove: false };
    let record_root = records.directory.as_ref().unwrap().path().to_path_buf();
    let (sender, receiver) = std::sync::mpsc::sync_channel(1);
    let observer = thread::spawn({
        let root = record_root.clone();
        move || {
            let deadline = Instant::now() + Duration::from_secs(5);
            let worker_pid = wait_for_pid(&root.join("worker.pid"), deadline)?;
            let worker = open_fixture_guard(worker_pid);
            let parent_pid = wait_for_pid(&root.join("parent.pid"), deadline)?;
            assert_ne!(parent_pid, worker_pid);
            let parent = open_fixture_guard(parent_pid);
            assert_eq!(unsafe { WaitForSingleObject(parent.handle(), 0) }, WAIT_TIMEOUT);
            assert_eq!(unsafe { WaitForSingleObject(worker.handle(), 0) }, WAIT_TIMEOUT);
            sender.send((parent, worker)).expect("deliver exact fixture handles");
            std::fs::write(root.join("release"), b"release\n").unwrap();
            Some(())
        }
    });
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let root = record_root.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script = format!(r#"let child = spawn("{executable}", ["--exact", "windows_managed_parent_fixture", "--nocapture", "--quiet"], #{{
        env_clear: true, env: #{{ {MANAGED_ROOT_ENV}: "{root}" }}, max_output: 1024
    }}); child.wait()"#);
    let result = engine(SysConfig::default().programs(ProgramPolicy::Any).process_scope(ProcessScope::Managed)).eval::<Map>(&script);
    let mut handles = receiver.try_recv().ok();
    let observed_closed_at_return = handles.as_ref().map(|(_, worker)| unsafe { WaitForSingleObject(worker.handle(), 0) == WAIT_OBJECT_0 }).unwrap_or(false);
    if handles.is_none() { handles = receiver.recv_timeout(Duration::from_secs(6)).ok(); }
    let observation = observer.join().expect("join managed spawn observer");
    if let Err(ref error) = result {
        if matches!(&**error, EvalAltResult::ErrorRuntime(value, _) if matches!(value.clone().try_cast::<SysError>(), Some(SysError::Denied(_)))) {
            eprintln!("windows_managed_spawn_denied_before_launch observation={}", observation.is_some());
        }
    }
    let result = result.unwrap_or_else(|error| panic!("Windows managed spawn must execute and close its descendant scope: {error:?}"));
    observation.expect("observe exact managed spawn parent and descendant");
    let (mut parent, mut worker) = handles.expect("retain exact managed spawn handles");
    assert!(observed_closed_at_return, "managed descendant must stop before wait returns");
    assert_eq!(unsafe { WaitForSingleObject(parent.handle(), 0) }, WAIT_OBJECT_0);
    parent.exit_observed = true;
    worker.exit_observed = true;
    let mut parent_exit = u32::MAX;
    assert_ne!(unsafe { GetExitCodeProcess(parent.handle(), &mut parent_exit) }, 0);
    assert_eq!(parent_exit, 0);
    assert_eq!(result["code"].as_int().unwrap(), 0);
    assert!(result["success"].as_bool().unwrap());
    records.safe_to_remove = true;
    eprintln!("windows_managed_spawn_os_readback parent={} worker={} parent_exit={parent_exit}", parent.pid, worker.pid);
    if std::env::var_os(MANAGED_WRONG_ENV).is_some() {
        assert!(!observed_closed_at_return, "deliberately wrong managed spawn closure expectation");
    }
}

/// An explicit script kill closes the managed scope and preserves an unrelated process.
#[test]
fn windows_managed_spawn_kill_closes_descendant_and_preserves_sentinel() {
    let mut records = ManagedRecords { directory: Some(TempDir::new()), safe_to_remove: false };
    let root = records.directory.as_ref().unwrap().path().to_path_buf();
    let sentinel_record = root.join("sentinel.pid");
    let sentinel = process::Command::new(std::env::current_exe().unwrap())
        .args(["--exact", "windows_managed_leaf_fixture", "--nocapture", "--quiet"])
        .env_clear().env(MANAGED_LEAF_ENV, &sentinel_record)
        .stdin(process::Stdio::null()).stdout(process::Stdio::null()).stderr(process::Stdio::null())
        .spawn().expect("start independent sentinel");
    let mut sentinel = OwnedFixture(Some(sentinel));
    let sentinel_pid = wait_for_pid(&sentinel_record, Instant::now() + Duration::from_secs(5)).expect("sentinel ready");
    assert_eq!(sentinel_pid, sentinel.0.as_ref().unwrap().id());
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script_root = root.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let debug_env = if std::env::var_os("RHAI_DEBUG_JOB_MEMBERS").is_some() { ", RHAI_DEBUG_JOB_MEMBERS: \"1\"" } else { "" };
    let script = format!(r#"spawn("{executable}", ["--exact", "windows_managed_parent_fixture", "--nocapture", "--quiet"], #{{
        env_clear: true, env: #{{ {MANAGED_ROOT_ENV}: "{script_root}" {debug_env} }}, max_output: 1024
    }})"#);
    let engine = engine(SysConfig::default().programs(ProgramPolicy::Any).process_scope(ProcessScope::Managed));
    let child = engine.eval::<Dynamic>(&script).expect("start managed child");
    let deadline = Instant::now() + Duration::from_secs(5);
    let worker_pid = wait_for_pid(&root.join("worker.pid"), deadline).expect("worker ready");
    let mut worker = open_fixture_guard(worker_pid);
    let parent_pid = wait_for_pid(&root.join("parent.pid"), deadline).expect("parent ready");
    let mut parent = open_fixture_guard(parent_pid);
    if !debug_env.is_empty() {
        eprintln!("[DEBUG-kill36] membership parent={parent_pid} worker={worker_pid} {}", std::fs::read_to_string(root.join("job-members.txt")).expect("job membership diagnostic"));
    }
    assert_ne!(parent_pid, worker_pid);
    assert_eq!(unsafe { WaitForSingleObject(parent.handle(), 0) }, WAIT_TIMEOUT);
    assert_eq!(unsafe { WaitForSingleObject(worker.handle(), 0) }, WAIT_TIMEOUT);
    let mut scope = Scope::new();
    scope.push_dynamic("child", child);
    engine.run_with_scope(&mut scope, "child.kill();").expect("request managed kill");
    let result = engine.eval_with_scope::<Map>(&mut scope, "child.wait()").expect("managed kill cleanup");
    let parent_wait = unsafe { WaitForSingleObject(parent.handle(), 0) };
    let parent_error = (parent_wait == u32::MAX).then(std::io::Error::last_os_error);
    let worker_wait = unsafe { WaitForSingleObject(worker.handle(), 0) };
    let worker_error = (worker_wait == u32::MAX).then(std::io::Error::last_os_error);
    let parent_stopped = parent_wait == WAIT_OBJECT_0;
    let worker_stopped = worker_wait == WAIT_OBJECT_0;
    eprintln!("[DEBUG-kill36] parent={parent_pid} wait={parent_wait:#x} error={parent_error:?} worker={worker_pid} wait={worker_wait:#x} error={worker_error:?}");
    let sentinel_alive = sentinel.0.as_mut().unwrap().try_wait().unwrap().is_none();
    std::fs::write(sentinel_record.with_extension("stop"), b"stop\n").unwrap();
    let sentinel_exit = sentinel.wait_bounded().expect("sentinel exits within bound");
    assert!(parent_stopped && worker_stopped,
        "managed kill must stop both exact process handles before wait returns: parent_stopped={parent_stopped}, worker_stopped={worker_stopped}");
    parent.exit_observed = true;
    worker.exit_observed = true;
    let mut parent_exit = u32::MAX;
    assert_ne!(unsafe { GetExitCodeProcess(parent.handle(), &mut parent_exit) }, 0);
    assert_eq!(result["code"].as_int().unwrap() as u32, parent_exit);
    assert!(!result["success"].as_bool().unwrap());
    assert!(sentinel_alive && sentinel_exit.success(), "managed kill must preserve the sentinel");
    records.safe_to_remove = true;
    eprintln!("windows_managed_kill_os_readback parent={parent_pid} worker={worker_pid} sentinel={sentinel_pid} sentinel_alive=true");
    if std::env::var_os("RHAI_WINDOWS_MANAGED_KILL_WRONG_EXPECTATION").is_some() {
        assert!(!worker_stopped, "deliberately wrong managed kill closure expectation");
    }
}

/// A managed run deadline ends both owned processes and leaves the sentinel alive.
#[test]
fn windows_managed_timeout_closes_descendant_and_preserves_sentinel() {
    let mut records = ManagedRecords { directory: Some(TempDir::new()), safe_to_remove: false };
    let root = records.directory.as_ref().unwrap().path().to_path_buf();
    let sentinel_record = root.join("sentinel.pid");
    let sentinel = process::Command::new(std::env::current_exe().unwrap())
        .args(["--exact", "windows_managed_leaf_fixture", "--nocapture", "--quiet"])
        .env_clear().env(MANAGED_LEAF_ENV, &sentinel_record)
        .stdin(process::Stdio::null()).stdout(process::Stdio::null()).stderr(process::Stdio::null())
        .spawn().expect("start independent sentinel");
    let mut sentinel = OwnedFixture(Some(sentinel));
    let sentinel_pid = wait_for_pid(&sentinel_record, Instant::now() + Duration::from_secs(5)).expect("sentinel ready");
    assert_eq!(sentinel_pid, sentinel.0.as_ref().unwrap().id());
    let (sender, receiver) = std::sync::mpsc::sync_channel(1);
    let observer = thread::spawn({
        let root = root.clone();
        move || {
            let deadline = Instant::now() + Duration::from_secs(5);
            let worker_pid = wait_for_pid(&root.join("worker.pid"), deadline)?;
            let worker = open_fixture_guard(worker_pid);
            let parent_pid = wait_for_pid(&root.join("parent.pid"), deadline)?;
            let parent = open_fixture_guard(parent_pid);
            assert_ne!(parent_pid, worker_pid);
            assert_eq!(unsafe { WaitForSingleObject(parent.handle(), 0) }, WAIT_TIMEOUT);
            assert_eq!(unsafe { WaitForSingleObject(worker.handle(), 0) }, WAIT_TIMEOUT);
            sender.send((parent, worker)).expect("deliver exact timeout fixture handles");
            Some(())
        }
    });
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script_root = root.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script = format!(r#"run_raw("{executable}", ["--exact", "windows_managed_parent_fixture", "--nocapture", "--quiet"], #{{
        env_clear: true, env: #{{ {MANAGED_ROOT_ENV}: "{script_root}" }}, max_output: 1024, timeout: 6.0
    }})"#);
    let result = engine(SysConfig::default().programs(ProgramPolicy::Any).process_scope(ProcessScope::Managed)).eval::<Map>(&script);
    let mut handles = receiver.try_recv().ok();
    let stopped_at_return = handles.as_ref().map(|(parent, worker)| unsafe {
        WaitForSingleObject(parent.handle(), 0) == WAIT_OBJECT_0 && WaitForSingleObject(worker.handle(), 0) == WAIT_OBJECT_0
    }).unwrap_or(false);
    if handles.is_none() { handles = receiver.recv_timeout(Duration::from_secs(6)).ok(); }
    observer.join().expect("join timeout observer").expect("observe exact managed timeout fixtures");
    let (mut parent, mut worker) = handles.expect("retain exact timeout fixture handles");
    let sentinel_alive = sentinel.0.as_mut().unwrap().try_wait().unwrap().is_none();
    std::fs::write(sentinel_record.with_extension("stop"), b"stop\n").unwrap();
    let sentinel_exit = sentinel.wait_bounded().expect("sentinel exits within bound");
    assert!(stopped_at_return, "timeout must stop both exact process handles before returning");
    parent.exit_observed = true;
    worker.exit_observed = true;
    let mut parent_exit = u32::MAX;
    assert_ne!(unsafe { GetExitCodeProcess(parent.handle(), &mut parent_exit) }, 0);
    let error = result.expect_err("managed run must report its deadline");
    let sys_error = match *error {
        EvalAltResult::ErrorRuntime(value, _) => value.try_cast::<SysError>().expect("typed process error"),
        other => panic!("unexpected managed timeout error: {other:?}"),
    };
    match sys_error {
        SysError::Process { cause: ProcessCause::Timeout(_), report } => {
            assert!(report.timed_out(), "timeout must be verified after cleanup");
            assert!(report.cleanup_diagnostics().is_empty());
            assert_eq!(report.exit_code(), Some(parent_exit as i32));
        }
        other => panic!("expected managed timeout report, got {other:?}"),
    }
    assert!(sentinel_alive && sentinel_exit.success(), "managed timeout must preserve the sentinel");
    records.safe_to_remove = true;
    eprintln!("windows_managed_timeout_os_readback parent={} worker={} sentinel={sentinel_pid} sentinel_alive=true", parent.pid, worker.pid);
    if std::env::var_os("RHAI_WINDOWS_MANAGED_TIMEOUT_WRONG_EXPECTATION").is_some() {
        assert!(!stopped_at_return, "deliberately wrong managed timeout closure expectation");
    }
}

/// Clones retain the entire managed task; final drop follows the host policy.
#[test]
fn windows_managed_spawn_final_drop_follows_host_policy() {
    for kill_on_drop in [true, false] {
        let mode = if kill_on_drop { "kill" } else { "retain" };
        let mut records = ManagedRecords { directory: Some(TempDir::new()), safe_to_remove: false };
        let root = records.directory.as_ref().unwrap().path().to_path_buf();
        let sentinel_record = root.join("sentinel.pid");
        let sentinel = process::Command::new(std::env::current_exe().unwrap())
            .args(["--exact", "windows_managed_leaf_fixture", "--nocapture", "--quiet"])
            .env_clear().env(MANAGED_LEAF_ENV, &sentinel_record)
            .stdin(process::Stdio::null()).stdout(process::Stdio::null()).stderr(process::Stdio::null())
            .spawn().expect("start independent sentinel");
        let mut sentinel = OwnedFixture(Some(sentinel));
        let sentinel_pid = wait_for_pid(&sentinel_record, Instant::now() + Duration::from_secs(5)).expect("sentinel ready");
        assert_eq!(sentinel_pid, sentinel.0.as_ref().unwrap().id());
        let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let script_root = root.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let script = format!(r#"spawn("{executable}", ["--exact", "windows_managed_parent_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true, env: #{{ {MANAGED_ROOT_ENV}: "{script_root}" }}, max_output: 1024
        }})"#);
        let engine = engine(SysConfig::default().programs(ProgramPolicy::Any).process_scope(ProcessScope::Managed).kill_on_drop(kill_on_drop));
        let child = engine.eval::<Dynamic>(&script).expect("start managed drop fixture");
        let sibling = child.clone();
        let deadline = Instant::now() + Duration::from_secs(5);
        let worker_pid = wait_for_pid(&root.join("worker.pid"), deadline).expect("worker ready");
        let mut worker = open_fixture_guard(worker_pid);
        let parent_pid = wait_for_pid(&root.join("parent.pid"), deadline).expect("parent ready");
        let mut parent = open_fixture_guard(parent_pid);
        assert_ne!(parent_pid, worker_pid);
        let challenge = |phase: &str| {
            let parent_request = root.join(format!("parent-{phase}-challenge"));
            let parent_ack = root.join(format!("parent-{phase}-ack"));
            let worker_record = root.join("worker.pid");
            let worker_request = worker_record.with_extension(format!("{phase}-challenge"));
            let worker_ack = worker_record.with_extension(format!("{phase}-ack"));
            std::fs::write(parent_request, b"challenge\n").unwrap();
            std::fs::write(worker_request, b"challenge\n").unwrap();
            let deadline = Instant::now() + Duration::from_secs(4);
            loop {
                if std::fs::read(&parent_ack).is_ok_and(|b| b == b"alive\n")
                    && std::fs::read(&worker_ack).is_ok_and(|b| b == b"alive\n") { break; }
                assert!(Instant::now() < deadline, "managed {phase} challenge not acknowledged");
                thread::sleep(Duration::from_millis(10));
            }
        };
        drop(child);
        assert_eq!(unsafe { WaitForSingleObject(parent.handle(), 0) }, WAIT_TIMEOUT);
        assert_eq!(unsafe { WaitForSingleObject(worker.handle(), 0) }, WAIT_TIMEOUT);
        challenge("nonfinal");
        drop(sibling);
        if !kill_on_drop {
            assert_eq!(unsafe { WaitForSingleObject(parent.handle(), 0) }, WAIT_TIMEOUT);
            assert_eq!(unsafe { WaitForSingleObject(worker.handle(), 0) }, WAIT_TIMEOUT);
            challenge("final");
            std::fs::write(root.join("release"), b"release\n").unwrap();
        }
        assert_eq!(unsafe { WaitForSingleObject(parent.handle(), 10_000) }, WAIT_OBJECT_0, "exact managed parent did not terminate");
        assert_eq!(unsafe { WaitForSingleObject(worker.handle(), 10_000) }, WAIT_OBJECT_0, "exact managed worker did not terminate");
        let mut exit = u32::MAX;
        assert_ne!(unsafe { GetExitCodeProcess(parent.handle(), &mut exit) }, 0);
        assert_eq!(exit == 0, !kill_on_drop);
        parent.exit_observed = true;
        worker.exit_observed = true;
        let sentinel_alive = sentinel.0.as_mut().unwrap().try_wait().unwrap().is_none();
        std::fs::write(sentinel_record.with_extension("stop"), b"stop\n").unwrap();
        let sentinel_exit = sentinel.wait_bounded().expect("sentinel exits within bound");
        assert!(sentinel_alive && sentinel_exit.success(), "managed final drop must preserve the sentinel");
        records.safe_to_remove = true;
        eprintln!("windows_managed_drop_os_readback mode={mode} parent={parent_pid} worker={worker_pid} parent_exit={exit} sentinel={sentinel_pid} sentinel_alive=true");
        if std::env::var("RHAI_WINDOWS_MANAGED_DROP_WRONG_EXPECTATION").as_deref() == Ok(mode) {
            if kill_on_drop {
                assert_ne!(unsafe { WaitForSingleObject(worker.handle(), 0) }, WAIT_OBJECT_0,
                    "deliberately wrong managed kill drop termination expectation");
            } else {
                assert!(!root.join("parent-final-ack").exists() && !root.join("worker.pid").with_extension("final-ack").exists(),
                    "deliberately wrong managed retain drop survival expectation");
            }
        }
    }
}
