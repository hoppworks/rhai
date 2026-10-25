#![cfg(all(feature = "sys", windows, not(feature = "no_index")))]
//! Minimal public process contract for native Windows.

mod sys_support;

use rhai::packages::sys::{ProgramPolicy, SysConfig};
use rhai::{Blob, Map};
use std::ffi::c_void;
use std::process;
use std::thread;
use std::time::{Duration, Instant};
use sys_support::{engine, TempDir};

const FIXTURE_CODE_ENV: &str = "RHAI_SYS_WINDOWS_PROCESS_CODE";
const FIXTURE_RECORD_ENV: &str = "RHAI_SYS_WINDOWS_PROCESS_RECORD";
const WRONG_EXPECTATION_ENV: &str = "RHAI_WINDOWS_PROCESS_WRONG_EXPECTATION";
const LIBTEST_QUIET_START: &[u8] = b"\nrunning 1 test\n";

type Handle = *mut c_void;
const PROCESS_QUERY_LIMITED_INFORMATION: u32 = 0x1000;
const SYNCHRONIZE: u32 = 0x0010_0000;
const WAIT_OBJECT_0: u32 = 0;

#[link(name = "kernel32")]
extern "system" {
    fn OpenProcess(access: u32, inherit: i32, pid: u32) -> Handle;
    fn WaitForSingleObject(handle: Handle, milliseconds: u32) -> u32;
    fn GetExitCodeProcess(handle: Handle, exit_code: *mut u32) -> i32;
    fn CloseHandle(handle: Handle) -> i32;
}

struct OwnedProcessHandle(Handle);

impl Drop for OwnedProcessHandle {
    fn drop(&mut self) {
        unsafe { CloseHandle(self.0) };
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
    std::io::Write::flush(&mut std::io::stdout()).unwrap();
    std::io::Write::write_all(&mut std::io::stderr(), &[0xfe, 0x42, 0x00]).unwrap();
    std::io::Write::flush(&mut std::io::stderr()).unwrap();
    process::exit(code);
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
        if let Err(error) = &result {
            eprintln!("windows public run_raw failed before OS observation: {error:?}");
        }
        let (observed_pid, observed_exit) = observer.join().expect("join independent OS observer");
        eprintln!("windows_process_os_readback pid={observed_pid} exit={observed_exit} exact_handle_signaled=true");
        let result = result.unwrap();
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
