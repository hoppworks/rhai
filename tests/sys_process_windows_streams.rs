#![cfg(all(feature = "sys", windows, not(feature = "no_index")))]
//! Native public process contract for large interleaved stdout and stderr.

mod sys_support;

use rhai::packages::sys::{ProcessScope, ProgramPolicy, SysConfig};
use rhai::{Blob, Dynamic, EvalAltResult, ImmutableString, Map, Scope};
use std::ffi::c_void;
use std::io::Write;
use std::path::PathBuf;
use std::thread;
use std::time::{Duration, Instant};
use sys_support::{engine, TempDir};

const STREAM_BYTES: usize = 4 * 1024 * 1024;
const CHUNK_BYTES: usize = 8192;
const QUIET_PREFIX: &[u8] = b"\nrunning 1 test\n";
type Handle = *mut c_void;
const PROCESS_QUERY_LIMITED_INFORMATION: u32 = 0x1000;
const PROCESS_TERMINATE: u32 = 1;
const SYNCHRONIZE: u32 = 0x0010_0000;
const WAIT_OBJECT_0: u32 = 0;

#[repr(C)]
#[derive(Clone, Copy, Default)]
struct FileTime {
    low: u32,
    high: u32,
}

#[link(name = "kernel32")]
extern "system" {
    fn OpenProcess(access: u32, inherit: i32, pid: u32) -> Handle;
    fn GetCurrentProcess() -> Handle;
    fn GetProcessTimes(handle: Handle, creation: *mut FileTime, exit: *mut FileTime, kernel: *mut FileTime, user: *mut FileTime) -> i32;
    fn WaitForSingleObject(handle: Handle, milliseconds: u32) -> u32;
    fn GetExitCodeProcess(handle: Handle, exit: *mut u32) -> i32;
    fn TerminateProcess(handle: Handle, exit: u32) -> i32;
    fn CloseHandle(handle: Handle) -> i32;
}

fn creation_time(handle: Handle) -> u64 {
    let (mut creation, mut exit, mut kernel, mut user) = (FileTime::default(), FileTime::default(), FileTime::default(), FileTime::default());
    assert_ne!(unsafe { GetProcessTimes(handle, &mut creation, &mut exit, &mut kernel, &mut user) }, 0, "query stream fixture identity: {}", std::io::Error::last_os_error());
    (u64::from(creation.high) << 32) | u64::from(creation.low)
}

struct ProcessGuard {
    handle: Handle,
    pid: u32,
    verified: bool,
    exited: bool,
}
impl Drop for ProcessGuard {
    fn drop(&mut self) {
        unsafe {
            if self.verified && !self.exited && WaitForSingleObject(self.handle, 0) != WAIT_OBJECT_0 {
                if TerminateProcess(self.handle, 1) == 0 {
                    eprintln!("stream fixture {} termination failed: {}", self.pid, std::io::Error::last_os_error());
                }
                if WaitForSingleObject(self.handle, 10_000) != WAIT_OBJECT_0 {
                    eprintln!("stream fixture {} exit remains unconfirmed", self.pid);
                }
            }
            CloseHandle(self.handle);
        }
    }
}

struct Records {
    directory: Option<TempDir>,
    safe: bool,
}
impl Drop for Records {
    fn drop(&mut self) {
        if !self.safe {
            if let Some(directory) = self.directory.take() {
                eprintln!("preserving stream fixture directory {} for outer custody", directory.path().display());
                std::mem::forget(directory);
            }
        }
    }
}

fn observe_child(record: PathBuf) -> Option<(u32, u32)> {
    let deadline = Instant::now() + Duration::from_secs(5);
    let identity = loop {
        match std::fs::read_to_string(&record) {
            Ok(text) => break text,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound && Instant::now() < deadline => thread::sleep(Duration::from_millis(10)),
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => return None,
            Err(error) => panic!("stream fixture readiness: {error}"),
        }
    };
    let mut fields = identity.split_whitespace();
    let pid = fields.next().expect("stream fixture PID").parse::<u32>().unwrap();
    let expected_creation = fields.next().expect("stream fixture creation time").parse::<u64>().unwrap();
    assert!(pid != 0 && expected_creation != 0 && fields.next().is_none(), "invalid stream fixture identity");
    let handle = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE | SYNCHRONIZE, 0, pid) };
    assert!(!handle.is_null(), "open stream fixture {pid}: {}", std::io::Error::last_os_error());
    let mut guard = ProcessGuard { handle, pid, verified: false, exited: false };
    assert_eq!(creation_time(handle), expected_creation, "PID reused before opening stream fixture");
    guard.verified = true;
    std::fs::write(record.with_extension("observed"), b"verified child handle\n").unwrap();
    assert_eq!(unsafe { WaitForSingleObject(handle, 30_000) }, WAIT_OBJECT_0, "stream fixture {pid} did not terminate");
    guard.exited = true;
    let mut exit = u32::MAX;
    assert_ne!(unsafe { GetExitCodeProcess(handle, &mut exit) }, 0, "query stream fixture exit");
    Some((pid, exit))
}

#[test]
fn windows_stream_fixture() {
    let Some(record) = std::env::var_os("RHAI_WINDOWS_STREAM_PID") else {
        return;
    };
    let record = PathBuf::from(record);
    let receipt = PathBuf::from(std::env::var_os("RHAI_WINDOWS_STREAM_RECEIPT").expect("stream receipt path"));
    let temporary = record.with_extension("tmp");
    let creation = creation_time(unsafe { GetCurrentProcess() });
    std::fs::write(&temporary, format!("{} {creation}\n", std::process::id())).unwrap();
    std::fs::rename(&temporary, &record).unwrap();
    let deadline = Instant::now() + Duration::from_secs(25);
    while !record.with_extension("observed").exists() {
        assert!(Instant::now() < deadline, "stream observer did not acquire the exact child handle");
        thread::sleep(Duration::from_millis(10));
    }
    let mut stdout = std::io::stdout().lock();
    let mut stderr = std::io::stderr().lock();
    let out = [b'S'; CHUNK_BYTES];
    let err = [b'E'; CHUNK_BYTES];
    for _ in 0..STREAM_BYTES / CHUNK_BYTES {
        stdout.write_all(&out).unwrap();
        stdout.flush().unwrap();
        stderr.write_all(&err).unwrap();
        stderr.flush().unwrap();
    }
    std::fs::write(receipt, b"stdout=4194304 stderr=4194304\n").expect("write independent stream receipt");
    std::process::exit(0);
}

fn exercise_streams(label: &str, supervision: ProcessScope, mode: &str) {
    let mut records = Records { directory: Some(TempDir::new()), safe: true };
    let root = records.directory.as_ref().unwrap().path().to_path_buf();
    let pid_record = root.join("child.pid");
    let receipt = root.join("receipt.txt");
    let observer = thread::spawn({
        let record = pid_record.clone();
        move || observe_child(record)
    });
    let mut scope = Scope::new();
    scope.push("program", std::env::current_exe().unwrap().to_string_lossy().into_owned());
    scope.push("pid_record", pid_record.to_string_lossy().into_owned());
    scope.push("receipt", receipt.to_string_lossy().into_owned());
    let mut engine = engine(SysConfig::default().programs(ProgramPolicy::Any).process_scope(supervision));
    #[cfg(not(feature = "unchecked"))]
    {
        // Rhai accounts the combined contents of both fields in the result map.
        engine.set_max_array_size(2 * STREAM_BYTES + 2048);
        engine.set_max_string_size(2 * STREAM_BYTES + 2048);
    }
    let script = match mode {
        "run" => r#"run(program, ["--exact", "windows_stream_fixture", "--quiet"], #{ env: #{ RHAI_WINDOWS_STREAM_PID: pid_record, RHAI_WINDOWS_STREAM_RECEIPT: receipt }, max_output: 4195328, timeout: 25 })"#,
        "raw" => r#"run_raw(program, ["--exact", "windows_stream_fixture", "--quiet"], #{ env: #{ RHAI_WINDOWS_STREAM_PID: pid_record, RHAI_WINDOWS_STREAM_RECEIPT: receipt }, max_output: 4195328, timeout: 25 })"#,
        _ => r#"spawn(program, ["--exact", "windows_stream_fixture", "--quiet"], #{ env: #{ RHAI_WINDOWS_STREAM_PID: pid_record, RHAI_WINDOWS_STREAM_RECEIPT: receipt }, max_output: 4195328 })"#,
    };
    records.safe = false;
    let started = engine.eval_with_scope::<Dynamic>(&mut scope, script);
    let result: Result<Dynamic, Box<EvalAltResult>> = if mode == "spawn" {
        match started {
            Err(error) => Err(error),
            Ok(child) => {
                scope.push_dynamic("child", child);
                let deadline = Instant::now() + Duration::from_secs(25);
                loop {
                    let result = engine.eval_with_scope::<Dynamic>(&mut scope, "child.try_wait()");
                    if !result.as_ref().is_ok_and(Dynamic::is_unit) {
                        break result;
                    }
                    if Instant::now() >= deadline {
                        let cancellation = engine.run_with_scope(&mut scope, "child.kill();");
                        eprintln!("windows_stream_timeout label={label} cancellation={cancellation:?}");
                        let wait_deadline = Instant::now() + Duration::from_secs(10);
                        loop {
                            match engine.eval_with_scope::<Dynamic>(&mut scope, "child.try_wait()") {
                                Ok(terminal) if !terminal.is_unit() => {
                                    eprintln!("windows_stream_timeout_api_terminal label={label}");
                                    break;
                                }
                                Err(error) => {
                                    eprintln!("windows_stream_timeout_api_terminal_unconfirmed label={label} error={error:?}");
                                    break;
                                }
                                _ if Instant::now() >= wait_deadline => {
                                    eprintln!("windows_stream_timeout_api_terminal_unconfirmed label={label} deadline=true");
                                    break;
                                }
                                _ => thread::sleep(Duration::from_millis(10)),
                            }
                        }
                        break result;
                    }
                    thread::sleep(Duration::from_millis(10));
                }
            }
        }
    } else {
        started
    };
    let observation = observer.join().expect("join stream child observer");
    let (pid, exit) = observation.expect("observe exact stream child exit");
    records.safe = true;
    assert_eq!(exit, 0, "stream fixture exit");
    let report = result
        .unwrap_or_else(|error| panic!("STREAM_CONTRACT {label}: {error:?}"))
        .try_cast::<Map>()
        .expect("stream child must finish before deadline");
    assert!(report["success"].as_bool().unwrap());
    assert_eq!(report["code"].as_int().unwrap(), 0);
    assert!(report["stdout_complete"].as_bool().unwrap() && report["stderr_complete"].as_bool().unwrap());
    let bytes = |field: &str| -> Vec<u8> {
        if mode == "raw" {
            report[field].clone().try_cast::<Blob>().expect("raw stream bytes")
        } else {
            report[field].clone().try_cast::<ImmutableString>().expect("text stream").as_bytes().to_vec()
        }
    };
    let stdout = bytes("stdout");
    let stderr = bytes("stderr");
    let child_receipt = std::fs::read(&receipt).expect("fresh child stream receipt");
    assert_eq!(child_receipt, b"stdout=4194304 stderr=4194304\n");
    let stdout_ok = stdout.starts_with(QUIET_PREFIX) && stdout.len() == QUIET_PREFIX.len() + STREAM_BYTES && stdout[QUIET_PREFIX.len()..].iter().all(|byte| *byte == b'S');
    let stderr_ok = stderr.len() == STREAM_BYTES && stderr.iter().all(|byte| *byte == b'E');
    eprintln!("windows_stream_readback label={label} pid={pid} exit={exit} exact_handle_signaled=true stdout_len={} stderr_len={} receipt=true", stdout.len(), stderr.len());
    match std::env::var("RHAI_WINDOWS_STREAM_WRONG_EXPECTATION").as_deref() {
        Ok("stdout") => assert!(!stdout_ok, "STREAM_WRONG_STDOUT {label}"),
        Ok("stderr") => assert!(!stderr_ok, "STREAM_WRONG_STDERR {label}"),
        _ => {}
    }
    assert!(stdout_ok, "stdout must contain the exact four MiB fixture stream");
    assert!(stderr_ok, "stderr must contain the exact four MiB fixture stream");
}

#[test]
fn windows_stream_direct_run() {
    exercise_streams("direct-run", ProcessScope::DirectChild, "run");
}
#[test]
fn windows_stream_direct_raw() {
    exercise_streams("direct-raw", ProcessScope::DirectChild, "raw");
}
#[test]
fn windows_stream_direct_spawn() {
    exercise_streams("direct-spawn", ProcessScope::DirectChild, "spawn");
}
#[test]
fn windows_stream_managed_run() {
    exercise_streams("managed-run", ProcessScope::Managed, "run");
}
#[test]
fn windows_stream_managed_raw() {
    exercise_streams("managed-raw", ProcessScope::Managed, "raw");
}
#[test]
fn windows_stream_managed_spawn() {
    exercise_streams("managed-spawn", ProcessScope::Managed, "spawn");
}
