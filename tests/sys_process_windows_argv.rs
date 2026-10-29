#![cfg(all(feature = "sys", windows, not(feature = "no_index")))]
//! Native argv round trips through the public process API.

mod sys_support;

use rhai::packages::sys::{ProcessScope, ProgramPolicy, SysConfig};
use rhai::{Array, Dynamic, Map, Scope};
use std::ffi::c_void;
use std::os::windows::ffi::OsStrExt;
use std::path::{Path, PathBuf};
use std::thread;
use std::time::{Duration, Instant};
use sys_support::{engine, TempDir};

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

struct ProcessGuard {
    handle: Handle,
    pid: u32,
    exited: bool,
    identity_verified: bool,
}
impl Drop for ProcessGuard {
    fn drop(&mut self) {
        unsafe {
            if self.identity_verified && !self.exited && WaitForSingleObject(self.handle, 0) != WAIT_OBJECT_0 {
                if TerminateProcess(self.handle, 1) == 0 {
                    eprintln!("failed to terminate argv fixture {}: {}", self.pid, std::io::Error::last_os_error());
                }
                if WaitForSingleObject(self.handle, 10_000) != WAIT_OBJECT_0 {
                    eprintln!("argv fixture {} exit unconfirmed", self.pid);
                }
            }
            CloseHandle(self.handle);
        }
    }
}

fn creation_time(handle: Handle) -> u64 {
    let (mut creation, mut exit, mut kernel, mut user) = (FileTime::default(), FileTime::default(), FileTime::default(), FileTime::default());
    assert_ne!(unsafe { GetProcessTimes(handle, &mut creation, &mut exit, &mut kernel, &mut user) }, 0, "query process identity: {}", std::io::Error::last_os_error());
    (u64::from(creation.high) << 32) | u64::from(creation.low)
}

/// Re-execute this test binary so no separately installed helper is required.
#[test]
fn windows_argv_child_fixture() {
    let Some(record) = std::env::var_os("RHAI_WINDOWS_ARGV_RECORD") else {
        return;
    };
    let record = PathBuf::from(record);
    let args: Vec<Vec<u16>> = std::env::args_os().skip_while(|arg| arg != "--").skip(1).map(|arg| arg.encode_wide().collect()).collect();
    let mut bytes = Vec::new();
    bytes.extend_from_slice(&(args.len() as u32).to_le_bytes());
    for arg in args {
        bytes.extend_from_slice(&(arg.len() as u32).to_le_bytes());
        for unit in arg {
            bytes.extend_from_slice(&unit.to_le_bytes());
        }
    }
    let temporary = record.with_extension("tmp");
    std::fs::write(&temporary, bytes).expect("write argv record");
    std::fs::rename(&temporary, &record).expect("publish argv record");
    let temporary = record.with_extension("pid-tmp");
    let identity = creation_time(unsafe { GetCurrentProcess() });
    std::fs::write(&temporary, format!("{} {identity}\n", std::process::id())).expect("write child identity");
    std::fs::rename(&temporary, record.with_extension("pid")).expect("publish child identity");
    let deadline = Instant::now() + Duration::from_secs(20);
    while !record.with_extension("observed").exists() {
        assert!(Instant::now() < deadline, "observer did not open the child process");
        thread::sleep(Duration::from_millis(10));
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
                eprintln!("preserving argv fixture directory {} for outer job cleanup", directory.path().display());
                std::mem::forget(directory);
            }
        }
    }
}

fn observe_child(record: PathBuf) -> Option<(u32, u32)> {
    let pid_path = record.with_extension("pid");
    let deadline = Instant::now() + Duration::from_secs(5);
    let identity = loop {
        match std::fs::read_to_string(&pid_path) {
            Ok(text) => break text,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound && Instant::now() < deadline => thread::sleep(Duration::from_millis(10)),
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => return None,
            Err(error) => panic!("argv fixture readiness: {error}"),
        }
    };
    let mut fields = identity.split_whitespace();
    let pid = fields.next().expect("fixture PID").parse::<u32>().expect("numeric fixture PID");
    let expected_creation = fields.next().expect("fixture creation time").parse::<u64>().expect("numeric fixture creation time");
    assert!(fields.next().is_none() && expected_creation != 0, "invalid fixture identity");
    let handle = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE | SYNCHRONIZE, 0, pid) };
    assert!(!handle.is_null(), "open exact argv fixture {pid}: {}", std::io::Error::last_os_error());
    let mut guard = ProcessGuard { handle, pid, exited: false, identity_verified: false };
    assert_eq!(creation_time(handle), expected_creation, "PID reused before fixture handle was acquired");
    guard.identity_verified = true;
    std::fs::write(record.with_extension("observed"), b"handle acquired\n").expect("release argv fixture");
    assert_eq!(unsafe { WaitForSingleObject(handle, 25_000) }, WAIT_OBJECT_0, "argv fixture {pid} did not exit");
    guard.exited = true;
    let mut exit = u32::MAX;
    assert_ne!(unsafe { GetExitCodeProcess(handle, &mut exit) }, 0, "query argv fixture exit");
    Some((pid, exit))
}

fn read_args(path: &Path) -> Vec<String> {
    let data = std::fs::read(path).expect("fresh child argv record");
    let mut offset = 0;
    let read_u32 = |offset: &mut usize| {
        let bytes: [u8; 4] = data.get(*offset..*offset + 4).expect("argv record header").try_into().unwrap();
        *offset += 4;
        u32::from_le_bytes(bytes) as usize
    };
    let count = read_u32(&mut offset);
    assert!(count <= 64, "unexpected argv count {count}");
    let mut args = Vec::with_capacity(count);
    for _ in 0..count {
        let length = read_u32(&mut offset);
        assert!(length <= 4096, "unexpected argv length {length}");
        let end = offset + length * 2;
        let units: Vec<u16> = data
            .get(offset..end)
            .expect("complete UTF-16 argv")
            .chunks_exact(2)
            .map(|bytes| u16::from_le_bytes([bytes[0], bytes[1]]))
            .collect();
        args.push(String::from_utf16(&units).expect("valid UTF-16 fixture argument"));
        offset = end;
    }
    assert_eq!(offset, data.len(), "unexpected trailing argv record data");
    args
}

#[test]
fn windows_process_arguments_reach_the_child_without_shell_interpretation() {
    let probe = std::env::current_exe().expect("current test executable");
    let mut records = Records { directory: Some(TempDir::new()), safe: true };
    let marker = records.directory.as_ref().unwrap().path().join("shell-injection-marker");
    let expected = vec![
        "plain".to_owned(),
        "two words".to_owned(),
        "quote\"inside".to_owned(),
        "trailing slash\\".to_owned(),
        "\\\"".to_owned(),
        "$HOME".to_owned(),
        "|".to_owned(),
        ";".to_owned(),
        "&&".to_owned(),
        format!("& echo injected > \"{}\"", marker.display()),
        "ümlaut 東京".to_owned(),
        String::new(),
    ];
    for (label, supervision, mode) in [
        ("direct-run", ProcessScope::DirectChild, "run"),
        ("direct-raw", ProcessScope::DirectChild, "raw"),
        ("direct-spawn", ProcessScope::DirectChild, "spawn"),
        ("managed-run", ProcessScope::Managed, "run"),
        ("managed-raw", ProcessScope::Managed, "raw"),
        ("managed-spawn", ProcessScope::Managed, "spawn"),
    ] {
        records.safe = false;
        let record = records.directory.as_ref().unwrap().path().join(format!("{label}.argv"));
        let observer = thread::spawn({
            let record = record.clone();
            move || observe_child(record)
        });
        let mut scope = Scope::new();
        scope.push("program", probe.to_string_lossy().into_owned());
        scope.push("record", record.to_string_lossy().into_owned());
        let arguments = ["--exact", "windows_argv_child_fixture", "--quiet", "--"]
            .iter()
            .map(|arg| Dynamic::from(*arg))
            .chain(expected.iter().map(|arg| Dynamic::from(arg.clone())))
            .collect::<Array>();
        scope.push("arguments", arguments);
        let engine = engine(SysConfig::default().programs(ProgramPolicy::Any).process_scope(supervision));
        let script = match mode {
            "run" => r#"run(program, arguments, #{ env: #{ RHAI_WINDOWS_ARGV_RECORD: record }, timeout: 15 })"#,
            "raw" => r#"run_raw(program, arguments, #{ env: #{ RHAI_WINDOWS_ARGV_RECORD: record }, timeout: 15 })"#,
            _ => r#"spawn(program, arguments, #{ env: #{ RHAI_WINDOWS_ARGV_RECORD: record } })"#,
        };
        let started = engine.eval_with_scope::<Dynamic>(&mut scope, script);
        let result = if mode == "spawn" {
            match started {
                Err(error) => Err(error),
                Ok(child) => {
                    scope.push_dynamic("argv_child", child);
                    let deadline = Instant::now() + Duration::from_secs(15);
                    loop {
                        let result = engine.eval_with_scope::<Dynamic>(&mut scope, "argv_child.try_wait()");
                        if !result.as_ref().is_ok_and(Dynamic::is_unit) {
                            break result;
                        }
                        if Instant::now() >= deadline {
                            let _ = engine.run_with_scope(&mut scope, "argv_child.kill();");
                            break result;
                        }
                        thread::sleep(Duration::from_millis(10));
                    }
                }
            }
        } else {
            started
        };
        let observation = observer.join().expect("join argv observer");
        let (pid, exit) = observation.expect("observe exact argv child exit");
        assert_eq!(exit, 0, "argv child {pid} exited unsuccessfully");
        records.safe = true;
        let report = result
            .unwrap_or_else(|error| panic!("ARGV_CONTRACT {label}: {error:?}"))
            .try_cast::<Map>()
            .expect("argv child must finish before deadline");
        assert!(report.get("success").expect("success field").clone_cast::<bool>(), "public child result {label}");
        let actual = read_args(&record);
        eprintln!("windows_argv_readback label={label} pid={pid} exit={exit} exact_handle_signaled=true arguments={actual:?}");
        assert!(!marker.exists(), "{label}: shell injection marker must remain absent");
        if std::env::var("RHAI_WINDOWS_ARGV_WRONG_EXPECTATION").as_deref() == Ok(label) {
            assert_ne!(actual, expected, "ARGV_WRONG_EXPECTATION {label}");
        }
        assert_eq!(actual, expected, "ARGV_CONTRACT {label}: exact argument boundaries");
    }
}
