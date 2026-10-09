#![cfg(all(feature = "sys", unix))]
//! Public process execution contracts (Unix slice).

mod sys_support;

#[cfg(not(feature = "no_index"))]
#[path = "fixtures/sys_process_shared_child_contract.rs"]
mod shared_child_contract;

use rhai::packages::sys::{FsAccess, ProcessCause, ProcessScope, ProgramPolicy, SysConfig, SysError};
#[cfg(not(feature = "no_index"))]
use rhai::Blob;
use rhai::{Dynamic, Engine, EvalAltResult, Map, Scope};
#[cfg(not(feature = "no_index"))]
use std::io::{Read, Write};
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
use std::os::unix::process::CommandExt;
#[cfg(not(feature = "no_index"))]
use std::process;
#[cfg(not(feature = "no_index"))]
use std::process::{Child, Command, Stdio};
#[cfg(not(feature = "no_index"))]
use std::time::{Duration, Instant};
use sys_support::engine;
use sys_support::TempDir;

const FIXTURE_ENV: &str = "RHAI_SYS_PROCESS_FIXTURE";
const FIXTURE_RECORD_ENV: &str = "RHAI_SYS_PROCESS_FIXTURE_RECORD";
const FIXTURE_ENV_QUERY: &str = "RHAI_SYS_PROCESS_FIXTURE_ENV_QUERY";
const FIXTURE_ENV_QUERY_RECORD: &str = "RHAI_SYS_PROCESS_FIXTURE_ENV_QUERY_RECORD";
const LIBTEST_QUIET_START: &[u8] = b"\nrunning 1 test\n";
const ACTIVE_STDERR_MARKER: &str = "stderr-active-marker\n";
const ACTIVE_STDERR_OUTPUT: &str = "stderr-active-marker\n";
const MANAGED_SPAWN_HOLD_ENV: &str = "RHAI_SYS_MANAGED_SPAWN_HOLD";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_FALSE_DROP_ENV: &str = "RHAI_SYS_MANAGED_FALSE_DROP";
#[cfg(all(unix, not(feature = "no_index")))]
const DIRECT_DROP_ENV: &str = "RHAI_SYS_DIRECT_DROP";
#[cfg(all(unix, not(feature = "no_index")))]
const DIRECT_DROP_RECORD_ENV: &str = "RHAI_SYS_DIRECT_DROP_RECORD";
#[cfg(all(unix, not(feature = "no_index")))]
const DIRECT_DROP_RELEASE_ENV: &str = "RHAI_SYS_DIRECT_DROP_RELEASE";
#[cfg(all(unix, not(feature = "no_index")))]
const DIRECT_DROP_CHALLENGE_ENV: &str = "RHAI_SYS_DIRECT_DROP_CHALLENGE";

/// The process API re-executes this test binary so stdout/stderr and exit status come from
/// an independently supervised OS process rather than a mocked command implementation.
#[test]
#[cfg(not(feature = "no_index"))]
fn process_fixture() {
    #[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
    if let Ok(role) = std::env::var(MANAGED_ZOMBIE_ROLE_ENV) {
        match role.as_str() {
            "reaper" => managed_zombie_reaper_process(),
            "host" => managed_zombie_host_process(),
            other => panic!("unknown managed zombie fixture role {other}"),
        }
        return;
    }
    if let Ok(code) = std::env::var(FIXTURE_ENV) {
        let record = std::env::var_os(FIXTURE_RECORD_ENV).expect("fixture record path");
        if std::env::var_os("RHAI_SYS_PROCESS_RESOURCE_HOLD").is_some() {
            std::fs::write(record, format!("child-pid={} child-ready=1\n", process::id())).unwrap();
            let release = std::env::var_os("RHAI_SYS_PROCESS_RESOURCE_RELEASE").map(std::path::PathBuf::from);
            let deadline = std::time::Instant::now() + std::time::Duration::from_secs(20);
            while std::time::Instant::now() < deadline && !release.as_ref().is_some_and(|path| path.exists()) {
                std::thread::sleep(std::time::Duration::from_millis(10));
            }
            process::exit(code.parse().unwrap());
        }
        #[cfg(target_os = "linux")]
        if std::env::var_os("RHAI_SYS_PROCESS_CLOSE_STDIN").is_some() {
            let pid = process::id();
            let pipe_capacity = unsafe { libc::fcntl(libc::STDIN_FILENO, libc::F_GETPIPE_SZ) };
            assert!(pipe_capacity > 0, "query actual child stdin pipe capacity: {}", std::io::Error::last_os_error());
            let start_ticks = resource_census_start_ticks(pid as i32)
                .expect("read early-close fixture start ticks")
                .expect("early-close fixture identity exists");
            let process_group = unsafe { libc::getpgid(0) };
            assert!(process_group > 0, "read early-close fixture process group: {}", std::io::Error::last_os_error());
            let temporary = std::path::PathBuf::from(&record).with_extension("ready-tmp");
            std::fs::write(&temporary, format!("child-pid={pid} child-start={start_ticks} child-pgid={process_group} pipe-capacity={pipe_capacity} ready=true\n")).unwrap();
            std::fs::rename(temporary, &record).unwrap();
            let ack = std::path::PathBuf::from(std::env::var_os("RHAI_SYS_PROCESS_CLOSE_STDIN_ACK").expect("observer acknowledgement path"));
            let watchdog = std::time::Instant::now() + std::time::Duration::from_secs(10);
            while !ack.exists() && std::time::Instant::now() < watchdog {
                std::thread::sleep(std::time::Duration::from_millis(1));
            }
            assert!(ack.exists(), "independent observer did not acknowledge the live fixture before its watchdog");
            std::io::stdout().write_all(b"early-close-stdout\n").unwrap();
            std::io::stdout().flush().unwrap();
            std::io::stderr().write_all(b"early-close-stderr\n").unwrap();
            std::io::stderr().flush().unwrap();
            let prefill_path = std::env::var_os("RHAI_SYS_PROCESS_CLOSE_STDIN_PREFILL");
            let close_ack_path = std::env::var_os("RHAI_SYS_PROCESS_CLOSE_STDIN_CLOSE_ACK");
            let input_bytes_raw = std::env::var_os("RHAI_SYS_PROCESS_CLOSE_STDIN_INPUT_BYTES");
            let input_bytes = input_bytes_raw.as_ref().and_then(|raw| raw.to_str()).and_then(|value| value.parse::<usize>().ok());
            let configured = [prefill_path.is_some(), close_ack_path.is_some(), input_bytes_raw.is_some()]
                .into_iter()
                .filter(|present| *present)
                .count();
            assert!(configured == 0 || configured == 3, "all optional pre-close observation variables must be configured together");
            if configured == 3 {
                let prefill = prefill_path.expect("prefill path");
                let close_ack = close_ack_path.expect("close acknowledgement path");
                let input_bytes = input_bytes.expect("positive numeric input byte count");
                let prefill = std::path::PathBuf::from(prefill);
                let close_ack = std::path::PathBuf::from(close_ack);
                let prefill_deadline = std::time::Instant::now() + std::time::Duration::from_secs(4);
                let unread = loop {
                    let mut unread = 0i32;
                    let result = unsafe { libc::ioctl(libc::STDIN_FILENO, libc::FIONREAD, &mut unread) };
                    assert_eq!(result, 0, "observe unread child stdin bytes: {}", std::io::Error::last_os_error());
                    assert!(unread >= 0, "kernel reported negative unread stdin bytes: {unread}");
                    if unread as usize == pipe_capacity as usize {
                        break unread;
                    }
                    assert!(std::time::Instant::now() < prefill_deadline, "stdin pipe did not fill before the bounded pre-close deadline: unread={unread} capacity={pipe_capacity}");
                    std::thread::sleep(std::time::Duration::from_millis(2));
                };
                let temporary = prefill.with_extension("prefill-tmp");
                std::fs::write(
                    &temporary,
                    format!("child-pid={pid} child-start={start_ticks} child-pgid={process_group} stdin-prefill-bytes={unread} pipe-capacity={pipe_capacity} input-bytes={input_bytes} ready-to-close=true\n"),
                )
                .unwrap();
                std::fs::rename(temporary, &prefill).unwrap();
                let close_watchdog = std::time::Instant::now() + std::time::Duration::from_secs(10);
                while !close_ack.exists() && std::time::Instant::now() < close_watchdog {
                    std::thread::sleep(std::time::Duration::from_millis(1));
                }
                assert!(close_ack.exists(), "independent observer did not acknowledge the full open stdin pipe before its watchdog");
            }
            let intent = std::path::PathBuf::from(std::env::var_os("RHAI_SYS_PROCESS_CLOSE_STDIN_INTENT").expect("close intent path"));
            let temporary = intent.with_extension("intent-tmp");
            std::fs::write(&temporary, format!("child-pid={pid} child-start={start_ticks} child-pgid={process_group} stdin-close-intent=true\n")).unwrap();
            std::fs::rename(temporary, intent).unwrap();
            assert_eq!(unsafe { libc::close(libc::STDIN_FILENO) }, 0, "close actual child fd 0: {}", std::io::Error::last_os_error());
            // The bounded parent run deadline is only a safety net. Normal completion
            // requires the owning process runner to terminate this still-live child.
            loop {
                std::thread::sleep(std::time::Duration::from_secs(1));
            }
        }
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
        if std::env::var_os("RHAI_SYS_PROCESS_IO_STRESS").is_some() {
            let expected = std::env::var("RHAI_SYS_PROCESS_IO_BYTES").unwrap().parse::<usize>().unwrap();
            let out_bytes = std::env::var("RHAI_SYS_PROCESS_STDOUT_BYTES").unwrap().parse::<usize>().unwrap();
            let err_bytes = std::env::var("RHAI_SYS_PROCESS_STDERR_BYTES").unwrap().parse::<usize>().unwrap();
            let expected_input = std::env::var_os("RHAI_SYS_PROCESS_IO_EXPECTED").map(std::path::PathBuf::from);
            let received_input = std::env::var_os("RHAI_SYS_PROCESS_IO_RECEIVED").map(std::path::PathBuf::from);
            let echo_input = std::env::var_os("RHAI_SYS_PROCESS_IO_ECHO").is_some();
            let child_pid = process::id();
            let record_path = std::path::PathBuf::from(record);
            std::fs::write(&record_path, format!("child-pid={child_pid} child-ready=1\n")).unwrap();
            let stdout_writer = std::thread::spawn(move || {
                std::io::stdout().write_all(&vec![b'o'; out_bytes]).unwrap();
                std::io::stdout().flush().unwrap();
            });
            let stderr_writer = std::thread::spawn(move || {
                std::io::stderr().write_all(&vec![b'e'; err_bytes]).unwrap();
                std::io::stderr().flush().unwrap();
            });
            let mut input = Vec::new();
            std::io::stdin().read_to_end(&mut input).unwrap();
            assert_eq!(input.len(), expected);
            let input_valid = if let Some(path) = expected_input {
                std::fs::read(path).map(|expected| expected == input).unwrap_or(false)
            } else {
                input.iter().all(|byte| *byte == b'i')
            };
            assert!(input_valid, "stress child input differs from its expected bytes");
            if let Some(path) = received_input {
                std::fs::write(path, &input).unwrap();
            }
            let complete_record = record_path.with_extension("complete");
            std::fs::write(&complete_record, format!("child-pid={child_pid} input-bytes={} input-valid=true\n", input.len())).unwrap();
            std::fs::rename(complete_record, record_path).unwrap();
            stdout_writer.join().unwrap();
            stderr_writer.join().unwrap();
            if echo_input {
                std::io::stdout().write_all(&input).unwrap();
            }
            process::exit(code.parse().unwrap());
        }
        if std::env::var_os("RHAI_SYS_PROCESS_DEADLINE_IO").is_some() {
            std::fs::write(record, format!("child-pid={} child-ready=1\n", process::id())).unwrap();
            let stdout_started = std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false));
            let stdout_ready = std::sync::Arc::clone(&stdout_started);
            std::thread::spawn(move || {
                let mut stdout = std::io::stdout().lock();
                if stdout.write_all(b"stdout-ready\n").is_err() || stdout.flush().is_err() {
                    return;
                }
                stdout_ready.store(true, std::sync::atomic::Ordering::Release);
                let chunk = vec![b'o'; 4096];
                loop {
                    if stdout.write_all(&chunk).is_err() || stdout.flush().is_err() {
                        break;
                    }
                    std::thread::sleep(std::time::Duration::from_micros(200));
                }
            });
            let stderr_ready = std::sync::Arc::clone(&stdout_started);
            std::thread::spawn(move || {
                while !stderr_ready.load(std::sync::atomic::Ordering::Acquire) {
                    std::thread::yield_now();
                }
                let mut stderr = std::io::stderr().lock();
                if stderr.write_all(ACTIVE_STDERR_OUTPUT.as_bytes()).is_err() || stderr.flush().is_err() {
                    return;
                }
                let chunk = vec![b'e'; 1024];
                loop {
                    if stderr.write_all(&chunk).is_err() || stderr.flush().is_err() {
                        break;
                    }
                    std::thread::sleep(std::time::Duration::from_micros(500));
                }
            });
            loop {
                std::thread::sleep(std::time::Duration::from_millis(10));
            }
        }
        if std::env::var_os(DIRECT_DROP_ENV).is_some() {
            let record = std::path::PathBuf::from(record);
            let release = std::path::PathBuf::from(std::env::var_os(DIRECT_DROP_RELEASE_ENV).unwrap());
            let challenge = std::path::PathBuf::from(std::env::var_os(DIRECT_DROP_CHALLENGE_ENV).unwrap());
            let pid = process::id();
            let ready = record.with_extension("ready-tmp");
            std::fs::write(&ready, format!("pid={pid} ready=true\n")).unwrap();
            std::fs::rename(ready, &record).unwrap();
            std::io::stdout().write_all(b"direct-drop-ready-stdout\n").unwrap();
            std::io::stdout().flush().unwrap();
            std::io::stderr().write_all(b"direct-drop-ready-stderr\n").unwrap();
            std::io::stderr().flush().unwrap();
            let deadline = std::time::Instant::now() + std::time::Duration::from_secs(20);
            while !release.exists() && std::time::Instant::now() < deadline {
                let ack = record.with_extension("challenge-ack");
                if challenge.exists() && !ack.exists() {
                    let temporary = ack.with_extension("tmp");
                    std::fs::write(&temporary, format!("pid={pid} alive=true\n")).unwrap();
                    std::fs::rename(temporary, ack).unwrap();
                }
                std::thread::sleep(std::time::Duration::from_millis(5));
            }
            assert!(release.exists(), "direct-drop fixture release watchdog expired");
            // Exceed ordinary pipe capacity so completion proves the retained owner kept both
            // captured streams drainable after the final public client was dropped.
            let payload = vec![b'o'; 512 * 1024];
            std::io::stdout().write_all(&payload).unwrap();
            std::io::stdout().flush().unwrap();
            let payload = vec![b'e'; 512 * 1024];
            std::io::stderr().write_all(&payload).unwrap();
            std::io::stderr().flush().unwrap();
            let complete = record.with_extension("complete");
            let complete_temporary = record.with_extension("complete-tmp");
            std::fs::write(&complete_temporary, format!("pid={pid} stdout_bytes=524288 stderr_bytes=524288 complete=true\n")).unwrap();
            std::fs::rename(complete_temporary, complete).unwrap();
            process::exit(0);
        }
        let child_id = process::id();
        #[cfg(target_os = "linux")]
        let census_identity = if std::env::var_os("RHAI_SYS_PROCESS_RESOURCE_CENSUS").is_some() {
            format!(
                " child-start={}",
                resource_census_start_ticks(child_id as i32)
                    .expect("read fixture start ticks")
                    .expect("fixture process identity exists")
            )
        } else {
            String::new()
        };
        #[cfg(not(target_os = "linux"))]
        let census_identity = String::new();
        std::fs::write(record, format!("child-pid={child_id} child-exit={code}{census_identity}\n")).unwrap();
        if let Ok(name) = std::env::var(FIXTURE_ENV_QUERY) {
            let query_record = std::env::var_os(FIXTURE_ENV_QUERY_RECORD).expect("fixture environment query record path");
            let present = std::env::var_os(&name).is_some();
            std::fs::write(query_record, format!("variable={name} present={present}\n")).unwrap();
        }
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

#[cfg(all(target_os = "linux", not(feature = "no_index")))]
fn resource_census_parse_start_ticks(stat: &str) -> std::io::Result<u64> {
    let tail = stat
        .rsplit_once(')')
        .ok_or_else(|| std::io::Error::new(std::io::ErrorKind::InvalidData, "missing /proc stat command terminator"))?
        .1;
    tail.split_whitespace()
        .nth(19)
        .ok_or_else(|| std::io::Error::new(std::io::ErrorKind::InvalidData, "missing /proc stat start time"))?
        .parse()
        .map_err(|error| std::io::Error::new(std::io::ErrorKind::InvalidData, error))
}

#[cfg(all(target_os = "linux", not(feature = "no_index")))]
fn resource_census_start_ticks(pid: i32) -> std::io::Result<Option<u64>> {
    let stat = match std::fs::read_to_string(format!("/proc/{pid}/stat")) {
        Ok(stat) => stat,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(error) => return Err(error),
    };
    resource_census_parse_start_ticks(&stat).map(Some)
}

#[cfg(all(target_os = "linux", not(feature = "no_index")))]
fn resource_census_assert_gone(pid: i32, start: u64) {
    assert_ne!(resource_census_start_ticks(pid).expect("read exact process identity"), Some(start), "process identity {pid}/{start} remains present");
}

#[cfg(all(target_os = "linux", not(feature = "no_index")))]
fn resource_census_snapshot() -> (usize, usize, usize) {
    let deadline = Instant::now() + Duration::from_millis(100);
    loop {
        let tasks = std::fs::read_dir("/proc/self/task").expect("read current task list");
        let mut task_count = 0;
        let mut cleanup_workers = 0;
        let mut retry = false;
        for task in tasks {
            let task = task.expect("read current task entry");
            task_count += 1;
            let comm = match std::fs::read_to_string(task.path().join("comm")) {
                Ok(comm) => comm,
                Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                    retry = true;
                    break;
                }
                Err(error) => panic!("read task comm: {error}"),
            };
            if comm.trim() == "rhai-sys-proces" {
                cleanup_workers += 1;
            }
        }
        if !retry {
            let fd_count = std::fs::read_dir("/proc/self/fd")
                .expect("read current descriptor list")
                .map(|entry| entry.expect("read descriptor entry"))
                .count();
            return (task_count, fd_count, cleanup_workers);
        }
        assert!(Instant::now() < deadline, "task snapshot stayed ambiguous through bounded retry");
        std::thread::yield_now();
    }
}

#[cfg(all(target_os = "linux", not(feature = "no_index")))]
fn resource_census_wait_for_baseline(expected: (usize, usize, usize)) -> (usize, usize, usize) {
    let deadline = Instant::now() + Duration::from_secs(2);
    loop {
        let observed = resource_census_snapshot();
        if observed == expected || Instant::now() >= deadline {
            return observed;
        }
        std::thread::sleep(Duration::from_millis(5));
    }
}

#[cfg(all(target_os = "linux", not(feature = "no_index")))]
fn resource_census_fields(path: &std::path::Path) -> Option<std::collections::HashMap<String, u64>> {
    Some(
        std::fs::read_to_string(path)
            .ok()?
            .split_whitespace()
            .filter_map(|field| {
                let (key, value) = field.split_once('=')?;
                Some((key.to_owned(), value.parse().ok()?))
            })
            .collect(),
    )
}

#[cfg(all(target_os = "linux", not(feature = "no_index")))]
fn resource_census_wait_for_pid(path: &std::path::Path) -> i32 {
    let deadline = Instant::now() + Duration::from_secs(2);
    loop {
        if let Some(pid) = resource_census_fields(path).and_then(|fields| fields.get("child-pid").copied()) {
            return pid as i32;
        }
        assert!(Instant::now() < deadline, "fixture did not publish its PID before the bounded watchdog");
        std::thread::sleep(Duration::from_millis(5));
    }
}

#[cfg(all(target_os = "linux", not(feature = "no_index")))]
struct ResourceCensusRelease(std::path::PathBuf);

#[cfg(all(target_os = "linux", not(feature = "no_index")))]
impl Drop for ResourceCensusRelease {
    fn drop(&mut self) {
        let _ = std::fs::write(&self.0, b"release\n");
    }
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
struct DirectDropFixture {
    root: TempDir,
    pid: Option<i32>,
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
impl DirectDropFixture {
    fn new() -> Self {
        Self { root: TempDir::new(), pid: None }
    }

    fn path(&self, name: &str) -> std::path::PathBuf {
        self.root.path().join(name)
    }

    fn await_record(&self, path: &str) -> Option<String> {
        let deadline = Instant::now() + Duration::from_secs(5);
        loop {
            if let Ok(record) = std::fs::read_to_string(self.path(path)) {
                return Some(record);
            }
            if Instant::now() >= deadline {
                return None;
            }
            std::thread::sleep(Duration::from_millis(5));
        }
    }

    fn release_and_wait(&mut self) -> bool {
        let _ = std::fs::write(self.path("release"), b"release\n");
        let deadline = Instant::now() + Duration::from_secs(6);
        while let Some(pid) = self.pid {
            if pid_is_absent(pid) {
                eprintln!("direct_drop_fixture_cleanup root={} pid={pid} esrch=true", self.root.path().display());
                return true;
            }
            if Instant::now() >= deadline {
                eprintln!("direct_drop_fixture_cleanup root={} pid={pid} esrch=false", self.root.path().display());
                return false;
            }
            std::thread::sleep(Duration::from_millis(10));
        }
        eprintln!("direct_drop_fixture_cleanup root={} pid=missing esrch=false", self.root.path().display());
        false
    }
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
impl Drop for DirectDropFixture {
    fn drop(&mut self) {
        let _ = self.release_and_wait();
    }
}

/// Public false-policy final-drop contract: the retained owner must leave the OS child alive,
/// continue draining its captured pipes, and eventually reap it after the child exits.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn direct_spawn_kill_on_drop_false_preserves_child_and_capture() {
    let mut fixture = DirectDropFixture::new();
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let record = fixture.path("record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let release = fixture.path("release").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let challenge = fixture.path("challenge").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let config = SysConfig::default()
        .programs(ProgramPolicy::AllowList(vec![executable.clone()]))
        .max_output(2 * 1024 * 1024)
        .kill_on_drop(false);
    let engine = engine(config);
    let script = format!(
        r#"spawn("{executable}", ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {DIRECT_DROP_ENV}: "1", {FIXTURE_ENV}: "0", {FIXTURE_RECORD_ENV}: "{record}", {DIRECT_DROP_RELEASE_ENV}: "{release}", {DIRECT_DROP_CHALLENGE_ENV}: "{challenge}" }}
        }})"#
    );
    let child = engine.eval::<Dynamic>(&script).expect("public spawn should return a child handle");
    let ready = fixture.await_record("record").expect("child readiness record");
    let fields = managed_record_fields(&ready);
    let pid = *fields.get("pid").expect("ready record PID");
    assert!(ready.contains("ready=true"), "fixture must publish complete readiness atomically");
    fixture.pid = Some(pid);
    eprintln!("direct_drop_fixture_started root={} test_pid={} child_pid={pid}", fixture.root.path().display(), std::process::id());
    drop(child); // The only public client lease is gone here.
    drop(engine); // The retained service must outlive the package owner while it drains/reaps.

    std::fs::write(fixture.path("challenge"), b"probe\n").unwrap();
    let ack = fixture.await_record("record.challenge-ack");
    let ack_matches = ack.as_deref().is_some_and(|record| record.trim() == format!("pid={pid} alive=true"));
    let alive_after_drop = pid_is_running(pid);
    eprintln!("direct_drop_after_final_client_drop pid={pid} alive={alive_after_drop} challenge_ack={ack_matches} completion_exists={}", fixture.path("record.complete").exists());
    assert!(alive_after_drop && ack_matches, "kill_on_drop(false) must preserve the child after final handle drop");
    assert!(!fixture.path("record.complete").exists(), "child must still be blocked before fixture release");

    std::fs::write(fixture.path("release"), b"release\n").unwrap();
    let complete = fixture.await_record("record.complete").expect("child completion record after pipe writes");
    eprintln!("direct_drop_completion pid={pid} record={complete:?}");
    assert!(complete.contains(&format!("pid={pid} stdout_bytes=524288 stderr_bytes=524288 complete=true")));
    let deadline = Instant::now() + Duration::from_secs(5);
    while !pid_is_absent(pid) && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(10));
    }
    let child_esrch = pid_is_absent(pid);
    eprintln!("direct_drop_terminal pid={pid} esrch={child_esrch}");
    assert!(child_esrch, "retained owner must reap the child after natural exit");
    assert!(fixture.release_and_wait(), "fixture-owned child cleanup must be exact and bounded");
}

/// A running public Child has no exit snapshot yet; after natural exit, try_wait returns it.
#[test]
#[cfg(all(unix, not(feature = "no_index")))]
fn direct_spawn_try_wait_returns_unit_until_child_exits() {
    let root = TempDir::new();
    let record_path = root.path().join("ready");
    let release_path = root.path().join("release");
    let path_literal = |path: &std::path::Path| path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let executable = path_literal(&std::env::current_exe().expect("current test executable"));
    let record = path_literal(&record_path);
    let release = path_literal(&release_path);
    struct ReleaseChild(std::path::PathBuf);
    impl Drop for ReleaseChild {
        fn drop(&mut self) {
            let _ = std::fs::write(&self.0, b"release\n");
        }
    }
    let _release = ReleaseChild(release_path.clone());

    let config = SysConfig::default().programs(ProgramPolicy::AllowList(vec![executable.clone()])).max_output(4096);
    let engine = engine(config);
    let script = format!(
        r#"spawn("{executable}", ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {FIXTURE_ENV}: "0", {FIXTURE_RECORD_ENV}: "{record}", RHAI_SYS_PROCESS_RESOURCE_HOLD: "1", RHAI_SYS_PROCESS_RESOURCE_RELEASE: "{release}" }}
        }})"#
    );
    let child = engine.eval::<Dynamic>(&script).expect("public spawn returns a Child handle");
    let mut scope = Scope::new();
    scope.push_dynamic("child", child);
    let handle_pid = engine.eval_with_scope::<rhai::INT>(&mut scope, "child.id").unwrap() as i32;

    let deadline = Instant::now() + Duration::from_secs(5);
    let ready = loop {
        if let Ok(ready) = std::fs::read_to_string(&record_path) {
            if ready.contains("child-ready=1") {
                break ready;
            }
        }
        assert!(Instant::now() < deadline, "child did not publish readiness before the bounded watchdog");
        std::thread::sleep(Duration::from_millis(5));
    };
    let fixture_pid = ready
        .split_whitespace()
        .find_map(|field| field.strip_prefix("child-pid=").and_then(|value| value.parse::<i32>().ok()))
        .expect("fixture readiness record includes its PID");
    assert_eq!(handle_pid, fixture_pid, "public Child ID matches independent fixture PID");
    assert!(ready.contains("child-ready=1"), "fixture published a complete ready record: {ready:?}");
    assert!(!release_path.exists(), "positive control child remains behind the release gate");
    assert_eq!(unsafe { libc::kill(fixture_pid, 0) }, 0, "OS confirms the held child is alive before try_wait");

    let pending = engine.eval_with_scope::<Dynamic>(&mut scope, "child.try_wait()").unwrap();
    assert!(pending.is_unit(), "try_wait on a running child must return unit, got {pending:?}");
    assert_eq!(unsafe { libc::kill(fixture_pid, 0) }, 0, "try_wait leaves the independently observed child alive");
    eprintln!("x24_running pid={fixture_pid} alive_before_try_wait=true result_is_unit={}", pending.is_unit());

    std::fs::write(&release_path, b"release\n").expect("release held fixture");
    let terminal_deadline = Instant::now() + Duration::from_secs(5);
    let terminal = loop {
        let result = engine.eval_with_scope::<Dynamic>(&mut scope, "child.try_wait()").unwrap();
        if !result.is_unit() {
            break result;
        }
        assert!(Instant::now() < terminal_deadline, "try_wait did not observe natural child exit before the bounded watchdog");
        std::thread::sleep(Duration::from_millis(5));
    };
    assert!(!terminal.is_unit(), "try_wait after child exit must return a result, got ()");
    let terminal = terminal.try_cast::<Map>().expect("try_wait returns the exit result directly after natural child exit");
    let terminal_code = terminal["code"].as_int().unwrap();
    assert_eq!(terminal_code, 0, "try_wait directly observes the natural exit result");
    assert!(terminal["success"].as_bool().unwrap());
    eprintln!("x24_post_exit_try_wait pid={fixture_pid} result_observed_before_wait=true code={terminal_code} success=true");

    let completed = engine.eval_with_scope::<Map>(&mut scope, "child.wait()").unwrap();
    let wait_code = completed["code"].as_int().unwrap();
    assert_eq!(wait_code, 0, "wait returns the result cached by the earlier terminal try_wait");
    assert!(completed["success"].as_bool().unwrap());
    let gone_deadline = Instant::now() + Duration::from_secs(5);
    loop {
        let result = unsafe { libc::kill(fixture_pid, 0) };
        if result == -1 && std::io::Error::last_os_error().raw_os_error() == Some(libc::ESRCH) {
            break;
        }
        assert!(Instant::now() < gone_deadline, "public wait did not reap exact fixture PID {fixture_pid}");
        std::thread::sleep(Duration::from_millis(5));
    }
    eprintln!("x24_finished pid={fixture_pid} wait_code={wait_code} try_wait_code={terminal_code} success=true reaped_esrch=true");
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_FIXTURE_ENV: &str = "RHAI_SYS_MANAGED_FIXTURE";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_ROOT_ENV: &str = "RHAI_SYS_MANAGED_ROOT";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_WORKER_ENV: &str = "RHAI_SYS_MANAGED_WORKER";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_LEAF_ENV: &str = "RHAI_SYS_MANAGED_LEAF";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_RELEASE_ENV: &str = "RHAI_SYS_MANAGED_RELEASE";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_PIDFD_ACK_ENV: &str = "RHAI_SYS_MANAGED_PIDFD_ACK";
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_ZOMBIE_ROLE_ENV: &str = "RHAI_SYS_MANAGED_ZOMBIE_ROLE";
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_ZOMBIE_ROOT_ENV: &str = "RHAI_SYS_MANAGED_ZOMBIE_ROOT";
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_ZOMBIE_DEADLINE_ENV: &str = "RHAI_SYS_MANAGED_ZOMBIE_DEADLINE_NS";
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_ZOMBIE_REAP_MODE_ENV: &str = "RHAI_SYS_MANAGED_ZOMBIE_REAP_MODE";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_ESCAPE_FIXTURE_ENV: &str = "RHAI_SYS_MANAGED_ESCAPE_FIXTURE";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_ESCAPE_RECORD_ENV: &str = "RHAI_SYS_MANAGED_ESCAPE_RECORD";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_ESCAPE_RELEASE_ENV: &str = "RHAI_SYS_MANAGED_ESCAPE_RELEASE";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_ESCAPE_GROUP_ENV: &str = "RHAI_SYS_MANAGED_ESCAPE_GROUP";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_PIPE_FIXTURE_ENV: &str = "RHAI_SYS_MANAGED_PIPE_FIXTURE";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_PIPE_ROOT_ENV: &str = "RHAI_SYS_MANAGED_PIPE_ROOT";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_PIPE_HOLDER_RECORD_ENV: &str = "RHAI_SYS_MANAGED_PIPE_HOLDER_RECORD";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_PIPE_HOLDER_RELEASE_ENV: &str = "RHAI_SYS_MANAGED_PIPE_HOLDER_RELEASE";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_PIPE_HOLDER_CHALLENGE_ENV: &str = "RHAI_SYS_MANAGED_PIPE_HOLDER_CHALLENGE";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_PIPE_HOLDER_ACK_ENV: &str = "RHAI_SYS_MANAGED_PIPE_HOLDER_ACK";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_PIPE_SENTINEL_GROUP_ENV: &str = "RHAI_SYS_MANAGED_PIPE_SENTINEL_GROUP";
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
const MANAGED_PIPE_LEADER_RECORD_ENV: &str = "RHAI_SYS_MANAGED_PIPE_LEADER_RECORD";

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_atomic_record(path: &std::path::Path, contents: &str) {
    let temporary = path.with_extension(format!("tmp-{}", std::process::id()));
    std::fs::write(&temporary, contents).unwrap();
    std::fs::rename(temporary, path).unwrap();
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_pipe_start_ticks(pid: i32) -> u64 {
    #[cfg(target_os = "linux")]
    {
        return managed_proc_identity(pid).expect("read escaped-pipe process start time").3;
    }
    #[cfg(not(target_os = "linux"))]
    {
        let _ = pid;
        0
    }
}

/// Re-exec fixture moves the managed leader into a separate same-session group, then waits for
/// fixture-owned release. This exercises exact direct-child cancellation independently of the
/// original process-group signal.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_scope_escape_fixture() {
    if std::env::var_os(MANAGED_ESCAPE_FIXTURE_ENV).is_none() {
        return;
    }
    let record = std::path::PathBuf::from(std::env::var_os(MANAGED_ESCAPE_RECORD_ENV).unwrap());
    let release = std::path::PathBuf::from(std::env::var_os(MANAGED_ESCAPE_RELEASE_ENV).unwrap());
    let escaped_pgid = std::env::var(MANAGED_ESCAPE_GROUP_ENV).unwrap().parse::<i32>().unwrap();
    let pid = std::process::id() as i32;
    let original_pgid = unsafe { libc::getpgrp() };
    // SAFETY: this fixture is a child in the same session as the fixture-owned target group.
    assert_eq!(unsafe { libc::setpgid(0, escaped_pgid) }, 0, "move leader into fixture-owned group");
    assert_eq!(unsafe { libc::getpgrp() }, escaped_pgid);
    managed_atomic_record(&record, &format!("pid={pid} original_pgid={original_pgid} escaped_pgid={escaped_pgid}\n"));
    let deadline = Instant::now() + Duration::from_secs(10);
    while !release.exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
}

/// Re-exec fixture leader: start a worker that inherits the captured pipes, publish both
/// process-group identities, then exit successfully while the worker remains alive.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_scope_leader_fixture() {
    if std::env::var_os(MANAGED_FIXTURE_ENV).is_none() {
        return;
    }
    let root = std::path::PathBuf::from(std::env::var_os(MANAGED_ROOT_ENV).unwrap());
    let worker_record = std::path::PathBuf::from(std::env::var_os(MANAGED_WORKER_ENV).unwrap());
    let leaf_record = std::path::PathBuf::from(std::env::var_os(MANAGED_LEAF_ENV).unwrap());
    let release = std::env::var_os(MANAGED_RELEASE_ENV).unwrap();
    let fixture_mode = std::env::var(MANAGED_FIXTURE_ENV).unwrap_or_default();
    let closed_io_probe = matches!(fixture_mode.as_str(), "leader-closed-io" | "leader-held-zombie" | "leader-managed-deadline" | "leader-managed-output-limit");
    #[cfg(target_os = "linux")]
    if fixture_mode == "leader-held-zombie" {
        let pid = std::process::id() as i32;
        let (_, parent, pgid, start) = managed_proc_identity(pid).expect("anchor held-zombie leader at entry");
        managed_atomic_record(&root.join("leader-identity"), &format!("pid={pid} parent={parent} pgid={pgid} start={start}\n"));
    }
    let worker = Command::new(std::env::current_exe().unwrap())
        .args(["--exact", "managed_scope_worker_fixture", "--nocapture", "--quiet"])
        .env_clear()
        .env(MANAGED_FIXTURE_ENV, if closed_io_probe { "worker-closed-io" } else { "worker" })
        .env(MANAGED_WORKER_ENV, &worker_record)
        .env(MANAGED_LEAF_ENV, &leaf_record)
        .env(MANAGED_RELEASE_ENV, &release)
        .stdin(Stdio::null())
        .stdout(if closed_io_probe { Stdio::null() } else { Stdio::inherit() })
        .stderr(if closed_io_probe { Stdio::null() } else { Stdio::inherit() })
        .spawn()
        .expect("start managed worker fixture");
    let worker_pid = worker.id();
    #[cfg(target_os = "linux")]
    let worker_start_field = format!("worker_start={}", managed_proc_identity(worker_pid as i32).expect("read managed worker start ticks").3);
    #[cfg(not(target_os = "linux"))]
    let worker_start_field = String::new();
    let deadline = Instant::now() + Duration::from_secs(5);
    while !worker_record.exists() || !leaf_record.exists() {
        assert!(Instant::now() < deadline, "worker and leaf readiness records were not published");
        std::thread::sleep(Duration::from_millis(5));
    }
    let worker_text = std::fs::read_to_string(&worker_record).unwrap();
    let worker_fields = managed_record_fields(&worker_text);
    let leader_pid = std::process::id();
    let leader_pgid = unsafe { libc::getpgrp() };
    let leaf_text = std::fs::read_to_string(&leaf_record).unwrap();
    let leaf_fields = managed_record_fields(&leaf_text);
    #[cfg(target_os = "linux")]
    let leader_start_field = format!("start={}", managed_proc_identity(leader_pid as i32).expect("read leader start ticks").3);
    #[cfg(not(target_os = "linux"))]
    let leader_start_field = String::new();
    #[cfg(target_os = "linux")]
    let leaf_start_field = format!("leaf_start={}", managed_zombie_u64(&leaf_text, "start").unwrap_or(0));
    #[cfg(not(target_os = "linux"))]
    let leaf_start_field = String::new();
    managed_atomic_record(
        &root.join("leader-record"),
        &format!(
            "pid={leader_pid} {leader_start_field} pgid={leader_pgid} worker={worker_pid} {worker_start_field} worker-pgid={} leaf={} {leaf_start_field} leaf-pgid={}\n",
            worker_fields["pgid"], leaf_fields["pid"], leaf_fields["pgid"]
        ),
    );
    if closed_io_probe {
        let ack = std::path::PathBuf::from(std::env::var_os(MANAGED_PIDFD_ACK_ENV).unwrap());
        let deadline = Instant::now() + Duration::from_secs(5);
        while !ack.exists() {
            assert!(Instant::now() < deadline, "PID/start-time observer did not acknowledge live members");
            std::thread::sleep(Duration::from_millis(2));
        }
    }
    if fixture_mode == "leader-managed-deadline" {
        use std::io::Write;
        let mut stdout = std::io::stdout().lock();
        let mut stderr = std::io::stderr().lock();
        stdout.write_all(b"managed-deadline-stdout\n").unwrap();
        stderr.write_all(b"managed-deadline-stderr\n").unwrap();
        stdout.flush().unwrap();
        stderr.flush().unwrap();
        let deadline = Instant::now() + Duration::from_secs(15);
        while !std::path::Path::new(&release).exists() && Instant::now() < deadline {
            std::thread::sleep(Duration::from_millis(5));
        }
        return;
    }
    if fixture_mode == "leader-managed-output-limit" {
        use std::io::Write;
        let mut stdout = std::io::stdout().lock();
        stdout.write_all(&vec![b'X'; 8192]).unwrap();
        stdout.flush().unwrap();
        let fallback = Instant::now() + Duration::from_secs(10);
        while !std::path::Path::new(&release).exists() && Instant::now() < fallback {
            std::thread::sleep(Duration::from_millis(5));
        }
        return;
    }
    // Dropping Child intentionally leaves the worker for the process-scope owner to close.
    drop(worker);
}

/// Re-exec fixture worker: remain alive with inherited stdout/stderr until the fixture guard
/// releases it, or until its bounded fallback expires after a failed assertion.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_scope_worker_fixture() {
    if !matches!(std::env::var(MANAGED_FIXTURE_ENV).as_deref(), Ok("worker") | Ok("worker-closed-io")) {
        return;
    }
    let record = std::path::PathBuf::from(std::env::var_os(MANAGED_WORKER_ENV).unwrap());
    let leaf_record = std::path::PathBuf::from(std::env::var_os(MANAGED_LEAF_ENV).unwrap());
    let release = std::path::PathBuf::from(std::env::var_os(MANAGED_RELEASE_ENV).unwrap());
    let pid = std::process::id();
    let pgid = unsafe { libc::getpgrp() };
    #[cfg(target_os = "linux")]
    let start_field = format!("start={}", managed_proc_identity(pid as i32).expect("read worker start ticks").3);
    #[cfg(not(target_os = "linux"))]
    let start_field = String::new();
    managed_atomic_record(&record, &format!("pid={pid} {start_field} pgid={pgid} ready=true\n"));
    let leaf = Command::new(std::env::current_exe().unwrap())
        .args(["--exact", "managed_scope_leaf_fixture", "--nocapture", "--quiet"])
        .env_clear()
        .env(MANAGED_FIXTURE_ENV, "leaf")
        .env(MANAGED_LEAF_ENV, &leaf_record)
        .env(MANAGED_RELEASE_ENV, &release)
        .stdin(Stdio::null())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .spawn()
        .expect("start managed leaf fixture");
    let leaf_pid = leaf.id();
    let leaf_deadline = Instant::now() + Duration::from_secs(5);
    while !leaf_record.exists() {
        assert!(Instant::now() < leaf_deadline, "leaf readiness record was not published");
        std::thread::sleep(Duration::from_millis(5));
    }
    managed_atomic_record(&record.with_extension("child"), &format!("pid={pid} leaf={leaf_pid}\n"));
    let deadline = Instant::now() + Duration::from_secs(15);
    while !release.exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
    let mut leaf = leaf;
    if leaf.try_wait().ok().flatten().is_none() {
        let _ = leaf.kill();
        let _ = leaf.wait();
    }
    managed_atomic_record(&record.with_extension("exited"), &format!("pid={pid} released={} leaf={}\n", release.exists(), leaf_pid));
}

/// Re-exec fixture leaf: retain the managed process-group membership after both ancestors exit.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_scope_leaf_fixture() {
    if std::env::var(MANAGED_FIXTURE_ENV).as_deref() != Ok("leaf") {
        return;
    }
    let record = std::path::PathBuf::from(std::env::var_os(MANAGED_LEAF_ENV).unwrap());
    let release = std::path::PathBuf::from(std::env::var_os(MANAGED_RELEASE_ENV).unwrap());
    let pid = std::process::id();
    let pgid = unsafe { libc::getpgrp() };
    #[cfg(target_os = "linux")]
    let start_field = format!("start={}", managed_proc_identity(pid as i32).expect("read leaf start ticks").3);
    #[cfg(not(target_os = "linux"))]
    let start_field = String::new();
    managed_atomic_record(&record, &format!("pid={pid} {start_field} pgid={pgid} ready=true\n"));
    let deadline = Instant::now() + Duration::from_secs(15);
    while !release.exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
}

/// Re-exec fixture for public `spawn` cancellation/drop cases. Unlike the normal-exit fixture,
/// the direct leader stays alive until the fixture-owned release marker is published.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_scope_spawn_leader_fixture() {
    if std::env::var_os(MANAGED_SPAWN_HOLD_ENV).is_none() {
        return;
    }
    let root = std::path::PathBuf::from(std::env::var_os(MANAGED_ROOT_ENV).unwrap());
    let worker_record = std::path::PathBuf::from(std::env::var_os(MANAGED_WORKER_ENV).unwrap());
    let leaf_record = std::path::PathBuf::from(std::env::var_os(MANAGED_LEAF_ENV).unwrap());
    let release = std::env::var_os(MANAGED_RELEASE_ENV).unwrap();
    let exit_record = root.join("leader-exit-record");
    let worker = Command::new(std::env::current_exe().unwrap())
        .args(["--exact", "managed_scope_worker_fixture", "--nocapture", "--quiet"])
        .env_clear()
        .env(MANAGED_FIXTURE_ENV, "worker")
        .env(MANAGED_WORKER_ENV, &worker_record)
        .env(MANAGED_LEAF_ENV, &leaf_record)
        .env(MANAGED_RELEASE_ENV, &release)
        .stdin(Stdio::null())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .spawn()
        .expect("start managed spawn worker fixture");
    let worker_pid = worker.id();
    let deadline = Instant::now() + Duration::from_secs(5);
    while !worker_record.exists() || !leaf_record.exists() {
        assert!(Instant::now() < deadline, "managed spawn worker/leaf readiness timed out");
        std::thread::sleep(Duration::from_millis(5));
    }
    let worker_fields = managed_record_fields(&std::fs::read_to_string(&worker_record).unwrap());
    let leaf_fields = managed_record_fields(&std::fs::read_to_string(&leaf_record).unwrap());
    let leader_pid = std::process::id() as i32;
    let leader_pgid = unsafe { libc::getpgrp() };
    #[cfg(target_os = "linux")]
    let leader_start_field = format!("start={}", managed_proc_identity(leader_pid).expect("read managed spawn leader start ticks").3);
    #[cfg(not(target_os = "linux"))]
    let leader_start_field = String::new();
    managed_atomic_record(
        &root.join("leader-record"),
        &format!(
            "pid={leader_pid} {leader_start_field} pgid={leader_pgid} worker={worker_pid} worker_pgid={} leaf={} leaf_pgid={}\n",
            worker_fields["pgid"], leaf_fields["pid"], leaf_fields["pgid"]
        ),
    );
    let deadline = Instant::now() + Duration::from_secs(15);
    while !std::path::Path::new(&release).exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
    // On fixture cleanup the worker and leaf observe the same release marker. Reap the exact
    // worker handle if it has not exited yet; this is fixture custody, not product cleanup.
    let mut worker = worker;
    let worker_status = match worker.try_wait().ok().flatten() {
        Some(status) => Some(status),
        None => {
            let _ = worker.kill();
            worker.wait().ok()
        }
    };
    managed_atomic_record(&exit_record, &format!("leader_pid={leader_pid} worker_pid={worker_pid} worker_status={worker_status:?}\n"));
}

/// Public managed false-policy fixture: the leader exits on its own release while its worker
/// and leaf remain blocked, so successful scope closure must stop those exact descendants.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_false_drop_leader_fixture() {
    if std::env::var_os(MANAGED_FALSE_DROP_ENV).is_none() {
        return;
    }
    let root = std::path::PathBuf::from(std::env::var_os(MANAGED_ROOT_ENV).unwrap());
    let worker_record = std::path::PathBuf::from(std::env::var_os(MANAGED_WORKER_ENV).unwrap());
    let leaf_record = std::path::PathBuf::from(std::env::var_os(MANAGED_LEAF_ENV).unwrap());
    let release_worker = std::env::var_os(MANAGED_RELEASE_ENV).unwrap();
    let release_leader = std::env::var_os("RHAI_SYS_MANAGED_FALSE_DROP_LEADER_RELEASE").unwrap();
    let challenge = root.join("challenge");
    let executable = std::env::current_exe().unwrap();
    let worker = Command::new(&executable)
        .args(["--exact", "managed_false_drop_worker_fixture", "--nocapture", "--quiet"])
        .env_clear()
        .env(MANAGED_FALSE_DROP_ENV, "worker")
        .env(MANAGED_ROOT_ENV, &root)
        .env(MANAGED_WORKER_ENV, &worker_record)
        .env(MANAGED_LEAF_ENV, &leaf_record)
        .env(MANAGED_RELEASE_ENV, &release_worker)
        .stdin(Stdio::null())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .spawn()
        .expect("start managed false-policy worker");
    let worker_pid = worker.id();
    let deadline = Instant::now() + Duration::from_secs(5);
    while !worker_record.exists() || !leaf_record.exists() {
        assert!(Instant::now() < deadline, "managed false-policy readiness timed out");
        std::thread::sleep(Duration::from_millis(5));
    }
    let worker_fields = managed_record_fields(&std::fs::read_to_string(&worker_record).unwrap());
    let leaf_fields = managed_record_fields(&std::fs::read_to_string(&leaf_record).unwrap());
    let pid = std::process::id() as i32;
    let pgid = unsafe { libc::getpgrp() };
    managed_atomic_record(&root.join("leader-record"), &format!("pid={pid} pgid={pgid} worker={worker_pid} leaf={} ready=true\n", leaf_fields["pid"]));
    managed_atomic_record(&root.join("worker-link-record"), &format!("worker={} pgid={} leaf={} leaf_pgid={}\n", worker_fields["pid"], worker_fields["pgid"], leaf_fields["pid"], leaf_fields["pgid"]));
    let deadline = Instant::now() + Duration::from_secs(15);
    while !std::path::Path::new(&release_leader).exists() && Instant::now() < deadline {
        let ack = root.join("ack-leader");
        if challenge.exists() && !ack.exists() {
            managed_atomic_record(&ack, &format!("pid={pid} pgid={pgid} role=leader\n"));
        }
        std::thread::sleep(Duration::from_millis(5));
    }
}

#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_false_drop_worker_fixture() {
    if std::env::var(MANAGED_FALSE_DROP_ENV).as_deref() != Ok("worker") {
        return;
    }
    let worker_record = std::path::PathBuf::from(std::env::var_os(MANAGED_WORKER_ENV).unwrap());
    let leaf_record = std::path::PathBuf::from(std::env::var_os(MANAGED_LEAF_ENV).unwrap());
    let root = std::path::PathBuf::from(std::env::var_os(MANAGED_ROOT_ENV).unwrap());
    let release = std::path::PathBuf::from(std::env::var_os(MANAGED_RELEASE_ENV).unwrap());
    let leaf = Command::new(std::env::current_exe().unwrap())
        .args(["--exact", "managed_false_drop_leaf_fixture", "--nocapture", "--quiet"])
        .env_clear()
        .env(MANAGED_FALSE_DROP_ENV, "leaf")
        .env(MANAGED_ROOT_ENV, &root)
        .env(MANAGED_LEAF_ENV, &leaf_record)
        .env(MANAGED_RELEASE_ENV, &release)
        .stdin(Stdio::null())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .spawn()
        .expect("start managed false-policy leaf");
    let pid = std::process::id() as i32;
    let pgid = unsafe { libc::getpgrp() };
    let leaf_pid = leaf.id();
    managed_atomic_record(&worker_record, &format!("pid={pid} pgid={pgid} leaf={leaf_pid} ready=true\n"));
    let deadline = Instant::now() + Duration::from_secs(15);
    while !release.exists() && Instant::now() < deadline {
        let challenge = root.join("challenge");
        let ack = root.join("ack-worker");
        if challenge.exists() && !ack.exists() {
            managed_atomic_record(&ack, &format!("pid={pid} pgid={pgid} role=worker\n"));
        }
        std::thread::sleep(Duration::from_millis(5));
    }
    let mut leaf = leaf;
    if leaf.try_wait().ok().flatten().is_none() {
        let _ = leaf.kill();
        let _ = leaf.wait();
    }
}

#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_false_drop_leaf_fixture() {
    if std::env::var(MANAGED_FALSE_DROP_ENV).as_deref() != Ok("leaf") {
        return;
    }
    let record = std::path::PathBuf::from(std::env::var_os(MANAGED_LEAF_ENV).unwrap());
    let release = std::path::PathBuf::from(std::env::var_os(MANAGED_RELEASE_ENV).unwrap());
    let root = std::path::PathBuf::from(std::env::var_os(MANAGED_ROOT_ENV).unwrap());
    let pid = std::process::id() as i32;
    let pgid = unsafe { libc::getpgrp() };
    managed_atomic_record(&record, &format!("pid={pid} pgid={pgid} ready=true\n"));
    let deadline = Instant::now() + Duration::from_secs(15);
    while !release.exists() && Instant::now() < deadline {
        let challenge = root.join("challenge");
        let ack = root.join("ack-leaf");
        if challenge.exists() && !ack.exists() {
            managed_atomic_record(&ack, &format!("pid={pid} pgid={pgid} role=leaf\n"));
        }
        std::thread::sleep(Duration::from_millis(5));
    }
}

/// Managed direct child starts an escaped holder that inherits both capture writers. The test
/// parent releases and reaps that exact holder through fixture-owned files after checking the API.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_scope_retained_pipe_leader_fixture() {
    if std::env::var_os(MANAGED_PIPE_FIXTURE_ENV).is_none() {
        return;
    }
    let root = std::path::PathBuf::from(std::env::var_os(MANAGED_PIPE_ROOT_ENV).unwrap());
    let holder_record = std::path::PathBuf::from(std::env::var_os(MANAGED_PIPE_HOLDER_RECORD_ENV).unwrap());
    let holder_release = std::path::PathBuf::from(std::env::var_os(MANAGED_PIPE_HOLDER_RELEASE_ENV).unwrap());
    let holder_challenge = std::path::PathBuf::from(std::env::var_os(MANAGED_PIPE_HOLDER_CHALLENGE_ENV).unwrap());
    let holder_ack = std::path::PathBuf::from(std::env::var_os(MANAGED_PIPE_HOLDER_ACK_ENV).unwrap());
    let leader_record = std::path::PathBuf::from(std::env::var_os(MANAGED_PIPE_LEADER_RECORD_ENV).unwrap());
    let sentinel_pgid = std::env::var(MANAGED_PIPE_SENTINEL_GROUP_ENV).unwrap().parse::<i32>().unwrap();
    let executable = std::env::current_exe().unwrap();
    let mut command = Command::new(executable);
    command
        .args(["--exact", "managed_scope_retained_pipe_holder_fixture", "--nocapture", "--quiet"])
        .env_clear()
        .env(MANAGED_PIPE_FIXTURE_ENV, "holder")
        .env(MANAGED_PIPE_HOLDER_RECORD_ENV, &holder_record)
        .env(MANAGED_PIPE_HOLDER_RELEASE_ENV, &holder_release)
        .env(MANAGED_PIPE_HOLDER_CHALLENGE_ENV, &holder_challenge)
        .env(MANAGED_PIPE_HOLDER_ACK_ENV, &holder_ack)
        .stdin(Stdio::null())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit());
    // SAFETY: the holder joins the separately owned sentinel's same-session process group.
    unsafe {
        command.pre_exec(move || {
            if libc::setpgid(0, sentinel_pgid) < 0 {
                return Err(std::io::Error::last_os_error());
            }
            Ok(())
        });
    }
    let mut holder = command.spawn().expect("start escaped captured-pipe holder");
    let holder_pid = holder.id() as i32;
    let leader_pid = std::process::id() as i32;
    let leader_pgid = unsafe { libc::getpgrp() };
    let deadline = Instant::now() + Duration::from_secs(3);
    while !holder_record.exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
    let holder_fields = managed_record_fields(&std::fs::read_to_string(&holder_record).expect("holder readiness record"));
    assert_eq!(holder_fields.get("pid"), Some(&holder_pid));
    assert_eq!(holder_fields.get("pgid"), Some(&sentinel_pgid));
    let leader_start = managed_pipe_start_ticks(leader_pid);
    let holder_start = managed_pipe_start_ticks(holder_pid);
    managed_atomic_record(
        &leader_record,
        &format!("pid={leader_pid} start={leader_start} pgid={leader_pgid} holder={holder_pid} holder_start={holder_start} holder_pgid={sentinel_pgid} sentinel_pgid={sentinel_pgid}\n"),
    );
    let deadline = Instant::now() + Duration::from_secs(15);
    while !root.join("release-leader").exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
    managed_atomic_record(&root.join("leader-exit-record"), &format!("pid={} release_seen={} exit_intent=true\n", std::process::id(), root.join("release-leader").exists()));
    // The direct leader may be terminated by the public API before fixture release. The outer
    // owner releases the escaped holder and independently observes its PID become ESRCH.
    drop(holder);
}

/// Escaped holder keeps both inherited capture writers open, but can be challenged and released
/// through independent fixture files. Probe results are written outside captured stdout/stderr.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_scope_retained_pipe_holder_fixture() {
    if std::env::var(MANAGED_PIPE_FIXTURE_ENV).as_deref() != Ok("holder") {
        return;
    }
    let record = std::path::PathBuf::from(std::env::var_os(MANAGED_PIPE_HOLDER_RECORD_ENV).unwrap());
    let release = std::path::PathBuf::from(std::env::var_os(MANAGED_PIPE_HOLDER_RELEASE_ENV).unwrap());
    let challenge = std::path::PathBuf::from(std::env::var_os(MANAGED_PIPE_HOLDER_CHALLENGE_ENV).unwrap());
    let ack = std::path::PathBuf::from(std::env::var_os(MANAGED_PIPE_HOLDER_ACK_ENV).unwrap());
    let pid = std::process::id() as i32;
    let pgid = unsafe { libc::getpgrp() };
    let mut stdout = std::io::stdout().lock();
    let mut stderr = std::io::stderr().lock();
    stdout.write_all(b"escaped-holder-stdout-ready\n").unwrap();
    stdout.flush().unwrap();
    stderr.write_all(b"escaped-holder-stderr-ready\n").unwrap();
    stderr.flush().unwrap();
    drop(stdout);
    drop(stderr);
    let start = managed_pipe_start_ticks(pid);
    managed_atomic_record(&record, &format!("pid={pid} start={start} pgid={pgid} ready=true\n"));
    // Keep the holder alive after endpoint closure so raw writes can report EPIPE instead of
    // terminating it with SIGPIPE. It remains an independently owned fixture process.
    unsafe {
        libc::signal(libc::SIGPIPE, libc::SIG_IGN);
    }
    let deadline = Instant::now() + Duration::from_secs(15);
    while !release.exists() && Instant::now() < deadline {
        if challenge.exists() && !ack.exists() {
            let stdout_probe = b"escaped-holder-post-return-stdout\n";
            let stderr_probe = b"escaped-holder-post-return-stderr\n";
            let stdout_result = unsafe { libc::write(libc::STDOUT_FILENO, stdout_probe.as_ptr().cast(), stdout_probe.len()) };
            let stdout_error = if stdout_result < 0 { std::io::Error::last_os_error().raw_os_error().unwrap_or(0) } else { 0 };
            let stderr_result = unsafe { libc::write(libc::STDERR_FILENO, stderr_probe.as_ptr().cast(), stderr_probe.len()) };
            let stderr_error = if stderr_result < 0 { std::io::Error::last_os_error().raw_os_error().unwrap_or(0) } else { 0 };
            managed_atomic_record(&ack, &format!("pid={pid} stdout_result={stdout_result} stdout_error={stdout_error} stderr_result={stderr_result} stderr_error={stderr_error}\n"));
        }
        std::thread::sleep(Duration::from_millis(5));
    }
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
struct ManagedFixture {
    root: TempDir,
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
impl ManagedFixture {
    fn new() -> Self {
        Self { root: TempDir::new() }
    }

    fn path(&self, name: &str) -> std::path::PathBuf {
        self.root.path().join(name)
    }
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
impl Drop for ManagedFixture {
    fn drop(&mut self) {
        // The marker is fixture-owned cleanup, never a process-name or numeric-PID signal.
        let _ = std::fs::write(self.path("release-worker"), b"release\n");
        let _ = std::fs::write(self.path("release-leader"), b"release\n");
        let deadline = Instant::now() + Duration::from_secs(3);
        let mut worker_pid = None;
        let mut leaf_pid = None;
        let mut leader_pid = None;
        while Instant::now() < deadline {
            let worker = std::fs::read_to_string(self.path("worker-record")).ok().map(|record| managed_record_fields(&record));
            let leaf = std::fs::read_to_string(self.path("leaf-record")).ok().map(|record| managed_record_fields(&record));
            worker_pid = worker.as_ref().and_then(|record| record.get("pid")).copied();
            leaf_pid = leaf.as_ref().and_then(|record| record.get("pid")).copied();
            leader_pid = std::fs::read_to_string(self.path("leader-record"))
                .ok()
                .map(|record| managed_record_fields(&record))
                .and_then(|record| record.get("pid").copied());
            let worker_gone = worker.as_ref().and_then(|record| record.get("pid")).map_or(false, |pid| pid_is_absent(*pid));
            let leaf_gone = leaf.as_ref().and_then(|record| record.get("pid")).map_or(true, |pid| pid_is_absent(*pid));
            let leader_gone = leader_pid.map_or(true, pid_is_absent);
            if worker_gone && leaf_gone && leader_gone {
                break;
            }
            std::thread::sleep(Duration::from_millis(10));
        }
        eprintln!(
            "managed_fixture_cleanup worker_pid={worker_pid:?} worker_esrch={} leaf_pid={leaf_pid:?} leaf_esrch={}",
            worker_pid.map_or(false, pid_is_absent),
            leaf_pid.map_or(true, pid_is_absent)
        );
        eprintln!("managed_spawn_fixture_leader_cleanup leader_pid={leader_pid:?} leader_esrch={}", leader_pid.map_or(true, pid_is_absent),);
    }
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
struct ManagedEscapedPipeFixture {
    root: TempDir,
    released: bool,
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
impl ManagedEscapedPipeFixture {
    fn new() -> Self {
        Self { root: TempDir::new(), released: false }
    }

    fn path(&self, name: &str) -> std::path::PathBuf {
        self.root.path().join(name)
    }

    fn release_leader(&self) {
        std::fs::write(self.path("release-leader"), b"release\n").expect("release fixture leader");
    }

    fn release_and_wait(&mut self) -> (Option<i32>, Option<i32>, bool, bool) {
        if !self.released {
            let _ = std::fs::write(self.path("release-leader"), b"release\n");
            let _ = std::fs::write(self.path("release-holder"), b"release\n");
            self.released = true;
        }
        let leader_pid = std::fs::read_to_string(self.path("leader-record"))
            .ok()
            .and_then(|record| managed_record_fields(&record).get("pid").copied());
        let holder_pid = std::fs::read_to_string(self.path("holder-record"))
            .ok()
            .and_then(|record| managed_record_fields(&record).get("pid").copied());
        let deadline = Instant::now() + Duration::from_secs(5);
        while Instant::now() < deadline && (leader_pid.is_some_and(|pid| !pid_is_absent(pid)) || holder_pid.is_some_and(|pid| !pid_is_absent(pid))) {
            std::thread::sleep(Duration::from_millis(10));
        }
        let leader_esrch = leader_pid.map_or(false, pid_is_absent);
        let holder_esrch = holder_pid.map_or(false, pid_is_absent);
        eprintln!("managed_escaped_pipe_cleanup root={} leader={leader_pid:?} leader_esrch={leader_esrch} holder={holder_pid:?} holder_esrch={holder_esrch}", self.root.path().display());
        (leader_pid, holder_pid, leader_esrch, holder_esrch)
    }
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
impl Drop for ManagedEscapedPipeFixture {
    fn drop(&mut self) {
        let _ = self.release_and_wait();
    }
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
struct Sentinel(Child);

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
impl Drop for Sentinel {
    fn drop(&mut self) {
        let pid = self.0.id();
        if self.0.try_wait().ok().flatten().is_none() {
            let _ = self.0.kill();
            let status = self.0.wait().ok();
            eprintln!("managed-scope sentinel_cleanup pid={pid} status={status:?} esrch={}", pid_is_absent(pid as i32));
        } else {
            eprintln!("managed-scope sentinel_cleanup pid={pid} status=already-exited esrch={}", pid_is_absent(pid as i32));
        }
    }
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn pid_is_absent(pid: i32) -> bool {
    if unsafe { libc::kill(pid, 0) } == -1 {
        std::io::Error::last_os_error().raw_os_error() == Some(libc::ESRCH)
    } else {
        false
    }
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn pid_is_alive(pid: i32) -> bool {
    (unsafe { libc::kill(pid, 0) }) == 0
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn pid_is_running(pid: i32) -> bool {
    Command::new("/bin/ps")
        .args(["-o", "stat=", "-p", &pid.to_string()])
        .output()
        .ok()
        .filter(|output| output.status.success())
        .map(|output| !String::from_utf8_lossy(&output.stdout).trim().starts_with('Z'))
        .unwrap_or(false)
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_record_fields(record: &str) -> std::collections::HashMap<String, i32> {
    record
        .split_whitespace()
        .filter_map(|field| {
            let (key, value) = field.split_once('=')?;
            Some((key.to_owned(), value.parse().ok()?))
        })
        .collect()
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
struct ManagedPidfds(Vec<(i32, i32, u64)>);

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
impl Drop for ManagedPidfds {
    fn drop(&mut self) {
        for (_, fd, _) in self.0.drain(..) {
            unsafe { libc::close(fd) };
        }
    }
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_proc_identity(pid: i32) -> Option<(char, i32, i32, u64)> {
    let stat = std::fs::read_to_string(format!("/proc/{pid}/stat")).ok()?;
    let fields = stat.rsplit_once(')')?.1.split_whitespace().collect::<Vec<_>>();
    Some((fields.first()?.chars().next()?, fields.get(1)?.parse().ok()?, fields.get(2)?.parse().ok()?, fields.get(19)?.parse().ok()?))
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_proc_identity_checked(pid: i32) -> std::io::Result<Option<(char, i32, i32, u64)>> {
    let stat = match std::fs::read_to_string(format!("/proc/{pid}/stat")) {
        Ok(stat) => stat,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(error) => return Err(error),
    };
    let fields = stat
        .rsplit_once(')')
        .ok_or_else(|| std::io::Error::new(std::io::ErrorKind::InvalidData, "malformed proc stat command"))?
        .1
        .split_whitespace()
        .collect::<Vec<_>>();
    let field = |index: usize| fields.get(index).copied().ok_or_else(|| std::io::Error::new(std::io::ErrorKind::InvalidData, "short proc stat"));
    let state = fields
        .first()
        .and_then(|field| field.chars().next())
        .ok_or_else(|| std::io::Error::new(std::io::ErrorKind::InvalidData, "missing proc state"))?;
    let parent = field(1)?.parse::<i32>().map_err(|error| std::io::Error::new(std::io::ErrorKind::InvalidData, error))?;
    let group = field(2)?.parse::<i32>().map_err(|error| std::io::Error::new(std::io::ErrorKind::InvalidData, error))?;
    let start = field(19)?.parse::<u64>().map_err(|error| std::io::Error::new(std::io::ErrorKind::InvalidData, error))?;
    Ok(Some((state, parent, group, start)))
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_zombie_wait_for(path: &std::path::Path, deadline: Instant) -> bool {
    while Instant::now() < deadline {
        if path.exists() {
            return true;
        }
        std::thread::sleep(Duration::from_millis(5));
    }
    path.exists()
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_zombie_monotonic_ns() -> u64 {
    let mut now = libc::timespec { tv_sec: 0, tv_nsec: 0 };
    let result = unsafe { libc::clock_gettime(libc::CLOCK_MONOTONIC, &mut now) };
    assert_eq!(result, 0, "read shared fixture monotonic clock");
    (now.tv_sec as u64) * 1_000_000_000 + now.tv_nsec as u64
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_zombie_deadline() -> (u64, Instant) {
    let deadline_ns = std::env::var(MANAGED_ZOMBIE_DEADLINE_ENV)
        .expect("shared fixture deadline")
        .parse::<u64>()
        .expect("valid shared fixture monotonic deadline");
    let remaining = deadline_ns.saturating_sub(managed_zombie_monotonic_ns());
    let instant = Instant::now() + Duration::from_nanos(remaining);
    (deadline_ns, instant)
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_zombie_u64(fields: &str, key: &str) -> Option<u64> {
    fields.split_whitespace().find_map(|field| {
        let (name, value) = field.split_once('=')?;
        (name == key).then(|| value.parse().ok()).flatten()
    })
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_zombie_prompt_reap_members(root: &std::path::Path, reaper_pid: i32) -> Result<bool, String> {
    let ids_path = root.join("pidfd-identities");
    let Ok(ids) = std::fs::read_to_string(&ids_path) else { return Ok(false) };
    let Some(group) = managed_zombie_u64(&ids, "pgid").and_then(|value| i32::try_from(value).ok()) else {
        return Err("missing managed process-group identity".to_owned());
    };
    let mut receipts = Vec::new();
    for (label, record_name, start_key, expected_parent_key) in [("worker", "worker-record", "worker_start", "leader"), ("leaf", "leaf-record", "leaf_start", "worker")] {
        let receipt_path = root.join(format!("prompt-{label}-reaped"));
        if let Ok(receipt) = std::fs::read_to_string(&receipt_path) {
            let expected_start = managed_zombie_u64(&ids, start_key).ok_or_else(|| format!("missing {label} start identity"))?;
            let expected_pid = std::fs::read_to_string(root.join(record_name))
                .ok()
                .and_then(|record| managed_record_fields(&record).get("pid").copied())
                .ok_or_else(|| format!("missing {label} PID identity"))?;
            if !receipt.contains(&format!("{label}={expected_pid} start={expected_start} pgid={group} reaped=true")) {
                return Err(format!("{label} prior reap receipt does not match exact identity: {receipt}"));
            }
            if managed_proc_identity(expected_pid).is_some() {
                return Err(format!("{label} PID became visible again after its exact wait receipt"));
            }
            receipts.push(receipt.trim().to_owned());
            continue;
        }
        let record = match std::fs::read_to_string(root.join(record_name)) {
            Ok(record) => record,
            Err(_) => return Ok(false),
        };
        let pid = managed_record_fields(&record).get("pid").copied().ok_or_else(|| format!("missing {label} PID"))?;
        let start = managed_zombie_u64(&ids, start_key).ok_or_else(|| format!("missing {label} start identity"))?;
        let expected_parent = std::fs::read_to_string(root.join(format!("{expected_parent_key}-record")))
            .ok()
            .and_then(|record| managed_record_fields(&record).get("pid").copied())
            .ok_or_else(|| format!("missing expected {label} parent identity"))?;
        match managed_proc_identity(pid) {
            None => return Err(format!("{label} disappeared without this reaper's exact wait receipt")),
            Some((state, parent, process_group, observed_start)) if observed_start == start && process_group == group && state == 'Z' && parent == reaper_pid => {
                let mut status = 0;
                let waited = unsafe { libc::waitpid(pid, &mut status, libc::WNOHANG) };
                if waited == pid {
                    if managed_proc_identity(pid).is_some() {
                        return Err(format!("{label} pid={pid} remained visible after exact waitpid"));
                    }
                    let receipt = format!("{label}={pid} start={start} pgid={group} reaped=true wait_status={status}");
                    managed_atomic_record(&receipt_path, &(receipt.clone() + "\n"));
                    receipts.push(receipt);
                } else if waited == 0 {
                    return Ok(false);
                } else {
                    return Err(format!("{label} waitpid failed: {:?}", std::io::Error::last_os_error()));
                }
            }
            Some((state, parent, process_group, observed_start)) if observed_start == start && process_group == group && parent == expected_parent && state != 'Z' => {
                return Ok(false);
            }
            Some((state, parent, process_group, observed_start)) if observed_start == start && process_group == group && parent == expected_parent && state == 'Z' => {
                return Ok(false);
            }
            Some((_, parent, process_group, observed_start)) if observed_start == start && process_group == group && parent == reaper_pid => {
                return Ok(false);
            }
            Some(identity) => return Err(format!("{label} identity left its owned lifecycle: {identity:?}")),
        }
    }
    if receipts.len() != 2 {
        return Ok(false);
    }
    managed_atomic_record(&root.join("prompt-reaper-cleanup"), &(receipts.join(" ") + " complete=true\n"));
    Ok(true)
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
struct ManagedZombieReaperGuard {
    root: std::path::PathBuf,
    child: Child,
    launched: bool,
    deadline: Instant,
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
struct ManagedZombieHostGuard {
    root: std::path::PathBuf,
    child: Option<Child>,
    deadline: Instant,
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
struct ManagedZombieDrainGuard {
    root: std::path::PathBuf,
    reaper_pid: i32,
    deadline: Instant,
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
impl Drop for ManagedZombieDrainGuard {
    fn drop(&mut self) {
        let launched = self.root.join("begin-run").exists() || self.root.join("leader-record").exists();
        if !launched {
            let _ = std::fs::write(self.root.join("cancel-before-run"), b"cancel before workload\n");
            return;
        }
        for name in ["pidfd-ack", "release-worker", "release-leader", "holder-release", "kill-request", "host-exit-release", "reap-release"] {
            let _ = std::fs::write(self.root.join(name), b"exact fixture drain on exceptional exit\n");
        }
        let mut signaled = std::collections::HashSet::new();
        let mut failures = Vec::new();
        let mut incomplete = false;
        loop {
            let mut pending = false;
            let escaped_pipe = std::env::var(MANAGED_ZOMBIE_REAP_MODE_ENV).as_deref() == Ok("deadline-pipe");
            let owned_records = if escaped_pipe {
                vec![("leader-record", None, "leader"), ("holder-record", None, "holder")]
            } else {
                vec![("leader-identity", Some("leader-record"), "leader"), ("worker-record", None, "worker"), ("leaf-record", None, "leaf")]
            };
            for (file, fallback, label) in owned_records {
                // The kill-mode fixture publishes the leader's exact PID/start identity in
                // leader-record; leader-identity is only emitted by the held-zombie modes.
                let path = self.root.join(file);
                let path = if path.exists() {
                    path
                } else if let Some(fallback) = fallback {
                    self.root.join(fallback)
                } else {
                    path
                };
                let Ok(text) = std::fs::read_to_string(path) else {
                    pending = true;
                    continue;
                };
                let fields = managed_record_fields(&text);
                let Some(pid) = fields.get("pid").copied() else {
                    pending = true;
                    continue;
                };
                let Some(start) = managed_zombie_u64(&text, "start") else {
                    pending = true;
                    continue;
                };
                match managed_proc_identity(pid) {
                    None => {}
                    Some((_, _, _, observed_start)) if observed_start != start => failures.push(format!("{label}={pid} start_tick_mismatch=true")),
                    Some((state, parent, _, _)) if parent == self.reaper_pid && state == 'Z' => {
                        let mut status = 0;
                        let waited = unsafe { libc::waitpid(pid, &mut status, libc::WNOHANG) };
                        if waited == pid {
                            failures.push(format!("{label}={pid} reaped=true status={status}"));
                        } else if waited == 0 {
                            pending = true;
                        } else {
                            failures.push(format!("{label}={pid} waitpid_error={:?}", std::io::Error::last_os_error().raw_os_error()));
                        }
                    }
                    Some((_, parent, _, _)) if parent == self.reaper_pid => {
                        pending = true;
                        if signaled.insert((pid, start)) {
                            let fd = unsafe { libc::syscall(libc::SYS_pidfd_open, pid, 0) as i32 };
                            if fd >= 0 {
                                let exact = managed_proc_identity(pid).is_some_and(|(_, current_parent, _, current_start)| current_parent == self.reaper_pid && current_start == start);
                                if exact {
                                    let result = unsafe { libc::syscall(libc::SYS_pidfd_send_signal, fd, libc::SIGKILL, std::ptr::null::<libc::siginfo_t>(), 0) };
                                    if result != 0 {
                                        failures.push(format!("{label}={pid} pidfd_signal_error={:?}", std::io::Error::last_os_error().raw_os_error()));
                                    }
                                }
                                unsafe { libc::close(fd) };
                            } else {
                                failures.push(format!("{label}={pid} pidfd_open_error={:?}", std::io::Error::last_os_error().raw_os_error()));
                            }
                        }
                    }
                    Some(_) => pending = true,
                }
            }
            if !pending || Instant::now() >= self.deadline {
                incomplete = pending;
                break;
            }
            std::thread::sleep(Duration::from_millis(5));
        }
        let receipt = format!("reaper={} complete={} details={:?}\n", self.reaper_pid, !incomplete && !failures.iter().any(|line| line.contains("error") || line.contains("mismatch")), failures);
        let _ = std::fs::write(self.root.join("reaper-exception-cleanup"), receipt);
    }
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
impl Drop for ManagedZombieHostGuard {
    fn drop(&mut self) {
        let Some(child) = self.child.as_mut() else { return };
        if self.root.join("begin-run").exists() {
            for name in ["pidfd-ack", "release-worker", "release-leader", "holder-release", "kill-request", "host-exit-release"] {
                let _ = std::fs::write(self.root.join(name), b"owned host cleanup\n");
            }
        } else {
            let _ = std::fs::write(self.root.join("cancel-before-run"), b"cancel before workload\n");
        }
        while Instant::now() < self.deadline {
            match child.try_wait() {
                Ok(Some(_)) => return,
                Ok(None) => std::thread::sleep(Duration::from_millis(5)),
                Err(_) => break,
            }
        }
        if child.try_wait().ok().flatten().is_none() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
impl Drop for ManagedZombieReaperGuard {
    fn drop(&mut self) {
        if !self.launched {
            let _ = std::fs::write(self.root.join("cancel-before-run"), b"cancel before workload\n");
            let _ = std::fs::write(self.root.join("reap-release"), b"drain only pre-run fixture children\n");
        } else {
            // Release only the exact fixture's existing ACKs and wait gates. This never creates
            // begin-run, so failure before launch cannot accidentally start an Engine operation.
            for name in ["pidfd-ack", "release-worker", "release-leader", "holder-release", "kill-request", "host-exit-release", "reap-release"] {
                let _ = std::fs::write(self.root.join(name), b"owned fixture cleanup\n");
            }
        }
        while Instant::now() < self.deadline {
            match self.child.try_wait() {
                Ok(Some(_)) => return,
                Ok(None) => std::thread::sleep(Duration::from_millis(5)),
                Err(_) => break,
            }
        }
        if self.child.try_wait().ok().flatten().is_none() {
            let _ = self.child.kill();
            let _ = self.child.wait();
        }
    }
}

/// Fixture-only subreaper. Its Engine host is a separate child and never changes its own
/// subreaper policy. The reaper releases only the exact adopted worker/leaf PIDs after O's ACK.
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_zombie_reaper_process() {
    let root = std::path::PathBuf::from(std::env::var_os(MANAGED_ZOMBIE_ROOT_ENV).expect("held-zombie root"));
    let (deadline_ns, deadline) = managed_zombie_deadline();
    let work_deadline = Instant::now() + Duration::from_nanos(deadline_ns.saturating_sub(managed_zombie_monotonic_ns()).saturating_sub(7_000_000_000));
    let reaper_pid = std::process::id() as i32;
    let reap_mode = std::env::var(MANAGED_ZOMBIE_REAP_MODE_ENV).unwrap_or_default();
    let prompt_reap = reap_mode == "prompt" || reap_mode == "kill" || reap_mode == "drop" || reap_mode == "deadline" || reap_mode == "output-limit";
    let reaper_start = managed_proc_identity(reaper_pid).expect("read reaper start ticks").3;
    let prctl_result = unsafe { libc::prctl(libc::PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) };
    assert_eq!(prctl_result, 0, "set fixture-local subreaper policy");
    managed_atomic_record(&root.join("reaper-ready"), &format!("pid={reaper_pid} start={reaper_start} enabled=true\n"));
    let drain_deadline = deadline.checked_sub(Duration::from_secs(2)).unwrap_or(deadline);
    let _drain = ManagedZombieDrainGuard {
        root: root.clone(),
        reaper_pid,
        deadline: drain_deadline,
    };

    let executable = std::env::current_exe().expect("test executable");
    let mut host_command = Command::new(executable);
    host_command
        .args(["--exact", "process_fixture", "--nocapture", "--quiet"])
        .env_clear()
        .env(MANAGED_ZOMBIE_ROLE_ENV, "host")
        .env(MANAGED_ZOMBIE_REAP_MODE_ENV, &reap_mode)
        .env(MANAGED_ZOMBIE_ROOT_ENV, &root)
        .env(MANAGED_ZOMBIE_DEADLINE_ENV, deadline_ns.to_string())
        .env(MANAGED_ROOT_ENV, &root)
        .env(MANAGED_WORKER_ENV, root.join("worker-record"))
        .env(MANAGED_LEAF_ENV, root.join("leaf-record"))
        .env(MANAGED_RELEASE_ENV, root.join("release-worker"))
        .env(MANAGED_PIDFD_ACK_ENV, root.join("pidfd-ack"));
    if let Some(sentinel_group) = std::env::var_os(MANAGED_PIPE_SENTINEL_GROUP_ENV) {
        host_command.env(MANAGED_PIPE_SENTINEL_GROUP_ENV, sentinel_group);
    }
    let host = host_command.spawn().expect("start isolated Engine host");
    let host_deadline = Instant::now() + Duration::from_nanos(deadline_ns.saturating_sub(managed_zombie_monotonic_ns()).saturating_sub(6_000_000_000));
    let mut host = ManagedZombieHostGuard {
        root: root.clone(),
        child: Some(host),
        deadline: host_deadline,
    };
    let mut host_status = None;
    let api_result_path = root.join("api-result");
    while Instant::now() < work_deadline {
        if prompt_reap {
            match managed_zombie_prompt_reap_members(&root, reaper_pid) {
                Ok(_) => {}
                Err(error) => panic!("prompt fixture reaper rejected lifecycle identity: {error}"),
            }
            if api_result_path.exists() {
                break;
            }
        }
        if let Some(status) = host.child.as_mut().unwrap().try_wait().expect("observe exact Engine host") {
            host_status = Some(status);
            break;
        }
        if root.join("cancel-before-run").exists() {
            break;
        }
        std::thread::sleep(Duration::from_millis(5));
    }

    let host_exit_path = root.join("host-exit-release");
    if host_status.is_none() && api_result_path.exists() {
        while !host_exit_path.exists() && Instant::now() < work_deadline {
            if prompt_reap {
                match managed_zombie_prompt_reap_members(&root, reaper_pid) {
                    Ok(_) => {}
                    Err(error) => panic!("prompt fixture reaper rejected lifecycle identity: {error}"),
                }
            }
            if let Some(status) = host.child.as_mut().unwrap().try_wait().expect("observe Engine host exit") {
                host_status = Some(status);
                break;
            }
            std::thread::sleep(Duration::from_millis(5));
        }
        // The release marker means the parent finished its API-boundary readback; it does
        // not prove that the exact Engine host has exited. Observe that owned child normally
        // before classifying a still-running host as a watchdog case. In particular, do not
        // turn the marker/try_wait race into a false exceptional-cleanup receipt.
        while host_status.is_none() && Instant::now() < work_deadline {
            if prompt_reap {
                match managed_zombie_prompt_reap_members(&root, reaper_pid) {
                    Ok(_) => {}
                    Err(error) => panic!("prompt fixture reaper rejected lifecycle identity: {error}"),
                }
            }
            host_status = host.child.as_mut().unwrap().try_wait().expect("observe exact Engine host after release");
            if host_status.is_none() {
                std::thread::sleep(Duration::from_millis(5));
            }
        }
    }
    if host_status.is_none() {
        // This is a fixture-owned watchdog path: release only the already-created fixture's
        // exact readiness markers, then terminate/reap the exact direct Engine-host child.
        managed_atomic_record(&root.join("exceptional-cleanup-started"), "kind=fixture-watchdog\n");
        if root.join("begin-run").exists() || root.join("leader-record").exists() {
            let _ = std::fs::write(root.join("pidfd-ack"), b"watchdog cleanup\n");
            let _ = std::fs::write(root.join("release-worker"), b"watchdog cleanup\n");
            let _ = std::fs::write(root.join("release-leader"), b"watchdog cleanup\n");
            let _ = std::fs::write(&host_exit_path, b"watchdog cleanup\n");
        } else {
            let _ = std::fs::write(root.join("cancel-before-run"), b"cancel\n");
        }
        if let Some(child) = host.child.as_mut() {
            while Instant::now() < host.deadline {
                if let Some(status) = child.try_wait().expect("observe fixture host during cleanup") {
                    host_status = Some(status);
                    break;
                }
                std::thread::sleep(Duration::from_millis(5));
            }
            if host_status.is_none() {
                child.kill().expect("terminate exact fixture Engine host after watchdog");
                host_status = Some(child.wait().expect("reap exact fixture Engine host"));
            }
        }
    }

    if prompt_reap {
        let status_code = host_status.and_then(|status| status.code()).unwrap_or(-1);
        let cleanup = std::fs::read_to_string(root.join("prompt-reaper-cleanup")).expect("prompt reaper must independently record both exact descendants");
        assert!(cleanup.contains("complete=true"), "prompt reaper cleanup receipt incomplete: {cleanup}");
        assert_eq!(status_code, 0, "Engine host must remain successful through fixture cleanup");
        managed_atomic_record(&root.join("reaper-cleanup"), &format!("pid={reaper_pid} prompt=true host_status={status_code} {cleanup}"));
        return;
    }

    if reap_mode == "deadline-pipe" {
        let status_code = host_status.and_then(|status| status.code()).unwrap_or(-1);
        let leader_text = std::fs::read_to_string(root.join("leader-record")).expect("escaped-pipe leader identity record");
        let leader_pid = managed_record_fields(&leader_text).get("pid").copied().expect("escaped leader PID");
        let leader_start = managed_zombie_u64(&leader_text, "start").expect("escaped leader start time");
        let holder_text = std::fs::read_to_string(root.join("holder-record")).expect("escaped holder identity record");
        let holder_fields = managed_record_fields(&holder_text);
        let holder_pid = holder_fields.get("pid").copied().expect("escaped holder PID");
        let holder_start = managed_zombie_u64(&holder_text, "start").expect("escaped holder start time");
        let holder_group = holder_fields.get("pgid").copied().expect("escaped holder group");
        let expected_group = std::env::var(MANAGED_PIPE_SENTINEL_GROUP_ENV)
            .expect("sentinel process-group identity")
            .parse::<i32>()
            .expect("valid sentinel process-group identity");
        let mut holder_receipt = None;
        let mut holder_error = None;
        if holder_group != expected_group {
            holder_error = Some(format!("holder group {holder_group} did not match sentinel group {expected_group}"));
        }
        if holder_error.is_none() && !managed_zombie_wait_for(&root.join("holder-release"), drain_deadline) {
            holder_error = Some("holder release marker missed fixture cleanup deadline".to_owned());
        }
        while holder_receipt.is_none() && holder_error.is_none() && Instant::now() < drain_deadline {
            match managed_proc_identity_checked(holder_pid) {
                Ok(Some(('Z', parent, group, start))) if parent == reaper_pid && group == holder_group && start == holder_start => {
                    let mut status = 0;
                    let waited = unsafe { libc::waitpid(holder_pid, &mut status, libc::WNOHANG) };
                    if waited == holder_pid {
                        match managed_proc_identity_checked(holder_pid) {
                            Ok(None) => holder_receipt = Some(format!("holder={holder_pid} start={holder_start} pgid={holder_group} reaped=true wait_status={status}")),
                            Ok(Some(identity)) => holder_error = Some(format!("holder remained visible after exact waitpid: {identity:?}")),
                            Err(error) => holder_error = Some(format!("could not verify holder absence after exact waitpid: {error}")),
                        }
                    } else if waited < 0 {
                        holder_error = Some(format!("exact holder waitpid failed: {:?}", std::io::Error::last_os_error().raw_os_error()));
                    } else {
                        std::thread::sleep(Duration::from_millis(5));
                    }
                }
                Ok(Some((state, parent, group, start)))
                    if start == holder_start && group == holder_group && (parent == reaper_pid || (parent == leader_pid && managed_proc_identity_checked(leader_pid).is_ok_and(|identity| identity.is_some_and(|(_, _, _, current_start)| current_start == leader_start)))) =>
                {
                    // The leader may still own the live holder, or the holder may have
                    // become a zombie immediately before orphan adoption. Wait for the
                    // exact parent transition; only the reaper may waitpid it.
                    std::thread::sleep(Duration::from_millis(5));
                }
                Ok(Some((state, parent, group, start))) => {
                    holder_error = Some(format!("escaped holder identity changed: state={state} parent={parent} pgid={group} start={start}"));
                }
                Ok(None) => holder_error = Some("escaped holder disappeared without this reaper's exact waitpid".to_owned()),
                Err(error) => holder_error = Some(format!("could not read escaped holder identity: {error}")),
            }
        }
        let holder_reaped = holder_receipt.is_some();
        let receipt = holder_receipt.unwrap_or_else(|| format!("holder={holder_pid} start={holder_start} pgid={holder_group} reaped=false error={:?}", holder_error.as_deref().unwrap_or("cleanup deadline")));
        managed_atomic_record(&root.join("escaped-holder-reaped"), &format!("{receipt}\n"));
        managed_atomic_record(&root.join("reaper-cleanup"), &format!("pid={reaper_pid} start={reaper_start} host_status={status_code} complete={} {receipt}\n", status_code == 0 && holder_error.is_none()));
        assert_eq!(status_code, 0, "deadline host must exit successfully after API-boundary readback");
        assert!(holder_reaped, "fixture reaper did not reap the exact escaped holder: {receipt}");
        return;
    }

    let worker_text = std::fs::read_to_string(root.join("worker-record")).ok();
    let leaf_text = std::fs::read_to_string(root.join("leaf-record")).ok();
    let leader_text = std::fs::read_to_string(root.join("leader-record")).ok();
    let worker = worker_text.as_deref().and_then(|v| managed_record_fields(v).get("pid").copied());
    let leaf = leaf_text.as_deref().and_then(|v| managed_record_fields(v).get("pid").copied());
    let exact_ids = std::fs::read_to_string(root.join("pidfd-identities")).ok();
    let worker_start = exact_ids
        .as_deref()
        .and_then(|v| managed_zombie_u64(v, "worker_start"))
        .or_else(|| worker_text.as_deref().and_then(|v| managed_zombie_u64(v, "start")));
    let leaf_start = exact_ids
        .as_deref()
        .and_then(|v| managed_zombie_u64(v, "leaf_start"))
        .or_else(|| leaf_text.as_deref().and_then(|v| managed_zombie_u64(v, "start")));
    let original_group = exact_ids
        .as_deref()
        .and_then(|v| managed_zombie_u64(v, "pgid"))
        .or_else(|| leader_text.as_deref().and_then(|v| managed_zombie_u64(v, "pgid")))
        .and_then(|value| i32::try_from(value).ok());
    let mut held_ok = false;
    if let (Some(worker), Some(leaf), Ok(host_text)) = (worker, leaf, std::fs::read_to_string(root.join("host-ready"))) {
        let expected_host = managed_record_fields(&host_text).get("pid").copied();
        let expected_host_start = managed_zombie_u64(&host_text, "start");
        let identity_deadline = (Instant::now() + Duration::from_secs(3)).min(drain_deadline);
        while Instant::now() < identity_deadline {
            let worker_identity = managed_proc_identity(worker);
            let leaf_identity = managed_proc_identity(leaf);
            if let (Some(worker_start), Some(leaf_start), Some(original_group)) = (worker_start, leaf_start, original_group) {
                let worker_held = matches!(worker_identity, Some(('Z', parent, group, start)) if parent == reaper_pid && group == original_group && start == worker_start);
                let leaf_held = matches!(leaf_identity, Some(('Z', parent, group, start)) if parent == reaper_pid && group == original_group && start == leaf_start);
                if worker_held && leaf_held && expected_host.is_some_and(|pid| pid != reaper_pid) && expected_host_start.is_some_and(|start| start > 0) {
                    held_ok = true;
                    break;
                }
            }
            std::thread::sleep(Duration::from_millis(5));
        }
    }
    let status_code = host_status.and_then(|status| status.code()).unwrap_or(-1);
    managed_atomic_record(
        &root.join("reaper-held"),
        &format!("pid={reaper_pid} start={reaper_start} host_status={status_code} worker={worker:?} worker_start={worker_start:?} leaf={leaf:?} leaf_start={leaf_start:?} held_zombies={held_ok}\n"),
    );

    // Normal path reaps only after O has independently read the API result and zero-time
    // pidfd/state observations. The watchdog path still drains only validated fixture children.
    if !managed_zombie_wait_for(&root.join("reap-release"), drain_deadline) {
        let _ = std::fs::write(root.join("release-worker"), b"reaper watchdog cleanup\n");
        let _ = std::fs::write(root.join("release-leader"), b"reaper watchdog cleanup\n");
    }
    let mut cleanup = Vec::new();
    for (label, pid, expected_start) in [("worker", worker, worker_start), ("leaf", leaf, leaf_start)] {
        let Some(pid) = pid else { continue };
        let Some(expected_start) = expected_start else {
            cleanup.push(format!("{label}={pid} missing_start_identity=true"));
            continue;
        };
        loop {
            match managed_proc_identity(pid) {
                None => {
                    cleanup.push(format!("{label}={pid} absent=true"));
                    break;
                }
                Some((state, parent, group, start)) if parent == reaper_pid && Some(group) == original_group && start == expected_start && state == 'Z' => {
                    let mut status = 0;
                    let waited = unsafe { libc::waitpid(pid, &mut status, libc::WNOHANG) };
                    if waited == pid {
                        cleanup.push(format!("{label}={pid} reaped=true wait_status={status}"));
                        break;
                    }
                    if waited < 0 && std::io::Error::last_os_error().raw_os_error() == Some(libc::ECHILD) {
                        cleanup.push(format!("{label}={pid} waitpid_error=ECHILD"));
                        break;
                    }
                }
                Some((state, parent, _group, start)) if start != expected_start => {
                    cleanup.push(format!("{label}={pid} identity_mismatch=true state={state} parent={parent}"));
                    break;
                }
                _ => {}
            }
            if Instant::now() >= drain_deadline {
                cleanup.push(format!("{label}={pid} cleanup_deadline=true"));
                break;
            }
            std::thread::sleep(Duration::from_millis(5));
        }
    }
    managed_atomic_record(&root.join("reaper-cleanup"), &format!("pid={reaper_pid} held_zombies={held_ok} host_status={status_code} {}\n", cleanup.join(" ")));
    if !held_ok
        || status_code != 0
        || cleanup
            .iter()
            .any(|line| line.contains("identity_mismatch") || line.contains("cleanup_deadline") || line.contains("waitpid_error") || line.contains("missing_start_identity"))
    {
        panic!("held-zombie fixture cleanup/boundary failed: held={held_ok} host_status={status_code} cleanup={cleanup:?}");
    }
}

/// Separate process API host. It returns its result to O and waits for O's receipt ACK before
/// exiting, so direct-leader custody is checked before R waits/reaps this Engine host.
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_zombie_host_process() {
    let root = std::path::PathBuf::from(std::env::var_os(MANAGED_ZOMBIE_ROOT_ENV).expect("held-zombie root"));
    let (_, deadline) = managed_zombie_deadline();
    let host_pid = std::process::id() as i32;
    let host_start = managed_proc_identity(host_pid).expect("read Engine host start ticks").3;
    managed_atomic_record(&root.join("host-ready"), &format!("pid={host_pid} start={host_start}\n"));
    while !root.join("begin-run").exists() {
        if root.join("cancel-before-run").exists() {
            managed_atomic_record(&root.join("host-cancelled"), &format!("pid={host_pid} start={host_start} ran=false\n"));
            return;
        }
        assert!(Instant::now() < deadline, "held-zombie host did not receive bounded begin/cancel");
        std::thread::sleep(Duration::from_millis(5));
    }

    if std::env::var(MANAGED_ZOMBIE_REAP_MODE_ENV).as_deref() == Ok("kill") {
        managed_zombie_host_child_kill(&root, host_pid, host_start, deadline);
        return;
    }
    if std::env::var(MANAGED_ZOMBIE_REAP_MODE_ENV).as_deref() == Ok("drop") {
        managed_zombie_host_final_drop(&root, host_pid, host_start, deadline);
        return;
    }
    if std::env::var(MANAGED_ZOMBIE_REAP_MODE_ENV).as_deref() == Ok("deadline") {
        managed_zombie_host_deadline(&root, host_pid, host_start, deadline);
        return;
    }
    if std::env::var(MANAGED_ZOMBIE_REAP_MODE_ENV).as_deref() == Ok("deadline-pipe") {
        managed_zombie_host_escaped_pipe_deadline(&root, host_pid, host_start, deadline);
        return;
    }
    if std::env::var(MANAGED_ZOMBIE_REAP_MODE_ENV).as_deref() == Ok("output-limit") {
        managed_zombie_host_output_limit(&root, host_pid, host_start, deadline);
        return;
    }

    let executable = std::env::current_exe().expect("test executable");
    let executable_text = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let root_literal = root.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let worker_literal = root.join("worker-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let leaf_literal = root.join("leaf-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let release_literal = root.join("release-worker").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let ack_literal = root.join("pidfd-ack").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let config = SysConfig::default()
        .programs(ProgramPolicy::AllowList(vec![executable_text.clone()]))
        .process_scope(ProcessScope::Managed);
    let engine = engine(config);
    let script = format!(
        r#"run("{executable_text}", ["--exact", "managed_scope_leader_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {MANAGED_FIXTURE_ENV}: "leader-held-zombie", {MANAGED_ROOT_ENV}: "{root_literal}", {MANAGED_WORKER_ENV}: "{worker_literal}", {MANAGED_LEAF_ENV}: "{leaf_literal}", {MANAGED_RELEASE_ENV}: "{release_literal}", {MANAGED_PIDFD_ACK_ENV}: "{ack_literal}" }},
            timeout: 4.0
        }})"#
    );
    let outcome = match engine.eval::<Map>(&script) {
        Ok(report) => {
            let code = report.get("code").and_then(|v| v.as_int().ok()).unwrap_or(-999);
            let success = report.get("success").and_then(|v| v.as_bool().ok()).unwrap_or(false);
            let stdout_complete = report.get("stdout_complete").and_then(|v| v.as_bool().ok()).unwrap_or(false);
            let stderr_complete = report.get("stderr_complete").and_then(|v| v.as_bool().ok()).unwrap_or(false);
            format!("api_success={success} api_outcome=success_report code={code} exit=Some({code}) stdout_complete={stdout_complete} stderr_complete={stderr_complete} cause=none diagnostic=none")
        }
        Err(error) => {
            let sys_error = match error.as_ref() {
                rhai::EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>(),
                _ => None,
            };
            match sys_error {
                Some(SysError::Process { cause: ProcessCause::Io { op, kind, .. }, report }) => {
                    let cause_op_matches = op == "observe process group closure";
                    let diagnostic = report.cleanup_diagnostics().iter().any(|item| item.operation() == "observe process group closure");
                    format!(
                        "api_success=false api_outcome=typed_process_io cause_op={} cause_op_matches={cause_op_matches} kind={kind:?} exit={:?} stdout_complete={} stderr_complete={} diagnostic={diagnostic} cause_details={:?} cleanup_diagnostics={:?}",
                        op.replace(' ', "_"),
                        report.exit_code(),
                        report.stdout_complete(),
                        report.stderr_complete(),
                        match error.as_ref() {
                            rhai::EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>(),
                            _ => None,
                        },
                        report.cleanup_diagnostics()
                    )
                }
                Some(other) => format!("api_success=false api_outcome=typed_non_process_error kind={} diagnostic=none error={other:?}", other.kind()),
                None => format!("api_success=false api_outcome=non_sys_error diagnostic=none error={error:?}"),
            }
        }
    };
    managed_atomic_record(&root.join("api-result"), &format!("host={host_pid} host_start={host_start} {outcome}\n"));
    while !root.join("host-exit-release").exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_zombie_host_deadline(root: &std::path::Path, host_pid: i32, host_start: u64, deadline: Instant) {
    let executable = std::env::current_exe().expect("test executable");
    let executable_text = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let root_literal = root.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let worker = root.join("worker-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let leaf = root.join("leaf-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let release = root.join("release-worker").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let ack = root.join("pidfd-ack").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let config = SysConfig::default()
        .programs(ProgramPolicy::AllowList(vec![executable_text.clone()]))
        .process_scope(ProcessScope::Managed)
        .max_output(4096);
    let engine = engine(config);
    let script = format!(
        r#"run("{executable_text}", ["--exact", "managed_scope_leader_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {MANAGED_FIXTURE_ENV}: "leader-managed-deadline", {MANAGED_ROOT_ENV}: "{root_literal}", {MANAGED_WORKER_ENV}: "{worker}", {MANAGED_LEAF_ENV}: "{leaf}", {MANAGED_RELEASE_ENV}: "{release}", {MANAGED_PIDFD_ACK_ENV}: "{ack}" }},
            timeout: 0.75,
            max_output: 4096
        }})"#
    );
    let result = match engine.eval::<Map>(&script) {
        Ok(report) => {
            let bool_field = |key: &str| report.get(key).and_then(|value| value.as_bool().ok());
            let stdout_marker = report
                .get("stdout")
                .and_then(|value| value.as_immutable_string_ref().ok())
                .is_some_and(|value| value.contains("managed-deadline-stdout\n"));
            let stderr_marker = report
                .get("stderr")
                .and_then(|value| value.as_immutable_string_ref().ok())
                .is_some_and(|value| value.contains("managed-deadline-stderr\n"));
            format!(
                "api_success=true api_outcome=timeout_report success={:?} timed_out={:?} stdout_complete={:?} stderr_complete={:?} stdout_marker={stdout_marker} stderr_marker={stderr_marker}",
                bool_field("success"),
                bool_field("timed_out"),
                bool_field("stdout_complete"),
                bool_field("stderr_complete")
            )
        }
        Err(error) => {
            let sys_error = match error.as_ref() {
                rhai::EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>(),
                _ => None,
            };
            match sys_error {
                Some(SysError::Process { cause: ProcessCause::Timeout(_), report }) => format!(
                    "api_success=false api_outcome=typed_timeout_error timed_out={} stdout_complete={} stderr_complete={} exit={:?} diagnostics={:?}",
                    report.timed_out(),
                    report.stdout_complete(),
                    report.stderr_complete(),
                    report.exit_code(),
                    report.cleanup_diagnostics()
                ),
                Some(other) => format!("api_success=false api_outcome=typed_non_timeout_error kind={}", other.kind()),
                None => format!("api_success=false api_outcome=non_sys_error error={error:?}"),
            }
        }
    };
    managed_atomic_record(&root.join("api-result"), &format!("host={host_pid} host_start={host_start} {result}\n"));
    while !root.join("host-exit-release").exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_zombie_host_escaped_pipe_deadline(root: &std::path::Path, host_pid: i32, host_start: u64, deadline: Instant) {
    let executable = std::env::current_exe().expect("test executable");
    let executable_text = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let root_literal = root.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let holder_record = root.join("holder-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let holder_release = root.join("holder-release").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let holder_challenge = root.join("holder-challenge").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let holder_ack = root.join("holder-ack").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let leader_record = root.join("leader-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let sentinel_group = std::env::var(MANAGED_PIPE_SENTINEL_GROUP_ENV).expect("sentinel process group");
    let config = SysConfig::default()
        .programs(ProgramPolicy::AllowList(vec![executable_text.clone()]))
        .process_scope(ProcessScope::Managed)
        .max_output(4096);
    let engine = engine(config);
    let script = format!(
        r#"run("{executable_text}", ["--exact", "managed_scope_retained_pipe_leader_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {MANAGED_PIPE_FIXTURE_ENV}: "leader", {MANAGED_PIPE_ROOT_ENV}: "{root_literal}", {MANAGED_PIPE_HOLDER_RECORD_ENV}: "{holder_record}", {MANAGED_PIPE_HOLDER_RELEASE_ENV}: "{holder_release}", {MANAGED_PIPE_HOLDER_CHALLENGE_ENV}: "{holder_challenge}", {MANAGED_PIPE_HOLDER_ACK_ENV}: "{holder_ack}", {MANAGED_PIPE_SENTINEL_GROUP_ENV}: "{sentinel_group}", {MANAGED_PIPE_LEADER_RECORD_ENV}: "{leader_record}" }},
            timeout: 1.0,
            max_output: 4096
        }})"#
    );
    let outcome = match engine.eval::<Map>(&script) {
        Ok(report) => {
            let bool_field = |key: &str| report.get(key).and_then(|value| value.as_bool().ok());
            let stdout_marker = report
                .get("stdout")
                .and_then(|value| value.as_immutable_string_ref().ok())
                .is_some_and(|value| value.contains("escaped-holder-stdout-ready\n"));
            let stderr_marker = report
                .get("stderr")
                .and_then(|value| value.as_immutable_string_ref().ok())
                .is_some_and(|value| value.contains("escaped-holder-stderr-ready\n"));
            format!(
                "api_success=true api_outcome=timeout_report success={:?} timed_out={:?} stdout_complete={:?} stderr_complete={:?} stdout_marker={stdout_marker} stderr_marker={stderr_marker}",
                bool_field("success"),
                bool_field("timed_out"),
                bool_field("stdout_complete"),
                bool_field("stderr_complete")
            )
        }
        Err(error) => {
            let sys_error = match error.as_ref() {
                rhai::EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>(),
                _ => None,
            };
            match sys_error {
                Some(SysError::Process { cause: ProcessCause::Timeout(_), report }) => format!(
                    "api_success=false api_outcome=typed_timeout_error timed_out={} stdout_complete={} stderr_complete={} stdout_marker={} stderr_marker={}",
                    report.timed_out(),
                    report.stdout_complete(),
                    report.stderr_complete(),
                    report
                        .stdout_bytes()
                        .windows(b"escaped-holder-stdout-ready\n".len())
                        .any(|part| part == b"escaped-holder-stdout-ready\n"),
                    report
                        .stderr_bytes()
                        .windows(b"escaped-holder-stderr-ready\n".len())
                        .any(|part| part == b"escaped-holder-stderr-ready\n")
                ),
                Some(other) => format!("api_success=false api_outcome=typed_non_timeout_error kind={}", other.kind()),
                None => format!("api_success=false api_outcome=non_sys_error error={error:?}"),
            }
        }
    };
    managed_atomic_record(&root.join("api-result"), &format!("host={host_pid} host_start={host_start} {outcome}\n"));
    while !root.join("host-exit-release").exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_zombie_host_output_limit(root: &std::path::Path, host_pid: i32, host_start: u64, deadline: Instant) {
    const CAP: usize = 4096;
    let executable = std::env::current_exe().expect("test executable");
    let executable_text = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let root_literal = root.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let worker = root.join("worker-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let leaf = root.join("leaf-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let release = root.join("release-worker").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let ack = root.join("pidfd-ack").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let config = SysConfig::default()
        .programs(ProgramPolicy::AllowList(vec![executable_text.clone()]))
        .process_scope(ProcessScope::Managed)
        .max_output(CAP);
    let engine = engine(config);
    let script = format!(
        r#"run("{executable_text}", ["--exact", "managed_scope_leader_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {MANAGED_FIXTURE_ENV}: "leader-managed-output-limit", {MANAGED_ROOT_ENV}: "{root_literal}", {MANAGED_WORKER_ENV}: "{worker}", {MANAGED_LEAF_ENV}: "{leaf}", {MANAGED_RELEASE_ENV}: "{release}", {MANAGED_PIDFD_ACK_ENV}: "{ack}" }},
            timeout: 8.0
        }})"#
    );
    let result = match engine.eval::<Map>(&script) {
        Ok(report) => {
            let stdout_len = report.get("stdout").and_then(|value| value.as_immutable_string_ref().ok()).map(|value| value.as_bytes().len());
            let stderr_complete = report.get("stderr_complete").and_then(|value| value.as_bool().ok());
            format!("api_success=true api_outcome=unexpected_success stdout_len={stdout_len:?} stderr_complete={stderr_complete:?}")
        }
        Err(error) => {
            let sys_error = match error.as_ref() {
                rhai::EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>(),
                _ => None,
            };
            match sys_error {
                Some(SysError::Process { cause: ProcessCause::OutputLimit(_), report }) => {
                    let stdout = report.stdout_bytes();
                    let prefix_exact = stdout.len() == CAP && stdout.starts_with(LIBTEST_QUIET_START) && stdout[LIBTEST_QUIET_START.len()..].iter().all(|byte| *byte == b'X');
                    format!(
                        "api_success=false api_outcome=typed_output_limit stdout_len={} stdout_prefix_exact={prefix_exact} stdout_complete={} stderr_len={} stderr_complete={} timed_out={} exit={:?}",
                        stdout.len(),
                        report.stdout_complete(),
                        report.stderr_bytes().len(),
                        report.stderr_complete(),
                        report.timed_out(),
                        report.exit_code()
                    )
                }
                Some(other) => format!("api_success=false api_outcome=typed_other_error kind={}", other.kind()),
                None => format!("api_success=false api_outcome=non_sys_error error={error:?}"),
            }
        }
    };
    managed_atomic_record(&root.join("api-result"), &format!("host={host_pid} host_start={host_start} {result}\n"));
    while !root.join("host-exit-release").exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_zombie_host_child_kill(root: &std::path::Path, host_pid: i32, host_start: u64, deadline: Instant) {
    let executable = std::env::current_exe().expect("test executable");
    let executable_text = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let root_literal = root.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let worker_literal = root.join("worker-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let leaf_literal = root.join("leaf-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let release_literal = root.join("release-worker").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let config = SysConfig::default()
        .programs(ProgramPolicy::AllowList(vec![executable_text.clone()]))
        .process_scope(ProcessScope::Managed);
    let engine = engine(config);
    let script = format!(
        r#"spawn("{executable_text}", ["--exact", "managed_scope_spawn_leader_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {MANAGED_SPAWN_HOLD_ENV}: "child-kill", {MANAGED_ROOT_ENV}: "{root_literal}", {MANAGED_WORKER_ENV}: "{worker_literal}", {MANAGED_LEAF_ENV}: "{leaf_literal}", {MANAGED_RELEASE_ENV}: "{release_literal}" }},
        }})"#
    );
    let child = engine.eval::<Dynamic>(&script).expect("public managed spawn");
    let mut scope = Scope::new();
    scope.push_dynamic("child", child);
    managed_atomic_record(&root.join("child-ready"), &format!("host={host_pid} host_start={host_start}\n"));
    while !root.join("kill-request").exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(2));
    }
    assert!(root.join("kill-request").exists(), "outer observer did not authorize public Child.kill");
    let api_result = match engine.eval_with_scope::<Map>(&mut scope, "child.kill(); child.wait(5.0)") {
        Ok(report) => {
            let success = report.get("success").and_then(|value| value.as_bool().ok()).expect("Child.wait report success must be a boolean");
            let code = report.get("code").and_then(|value| value.as_int().ok());
            let signal = report.get("signal").and_then(|value| value.as_int().ok());
            let stdout_complete = report.get("stdout_complete").and_then(|value| value.as_bool().ok()).unwrap_or(false);
            let stderr_complete = report.get("stderr_complete").and_then(|value| value.as_bool().ok()).unwrap_or(false);
            format!("api_success=true api_outcome=child_report success={success} code={code:?} signal={signal:?} stdout_complete={stdout_complete} stderr_complete={stderr_complete} cause=none diagnostic=none")
        }
        Err(error) => format!("api_success=false api_outcome=child_error error={error:?}"),
    };
    managed_atomic_record(&root.join("api-result"), &format!("host={host_pid} host_start={host_start} {api_result}\n"));
    while !root.join("host-exit-release").exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_zombie_host_final_drop(root: &std::path::Path, host_pid: i32, host_start: u64, deadline: Instant) {
    let executable = std::env::current_exe().expect("test executable");
    let executable_text = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let root_literal = root.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let worker_literal = root.join("worker-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let leaf_literal = root.join("leaf-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let release_literal = root.join("release-worker").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let config = SysConfig::default()
        .programs(ProgramPolicy::AllowList(vec![executable_text.clone()]))
        .process_scope(ProcessScope::Managed);
    let engine = engine(config);
    let script = format!(
        r#"spawn("{executable_text}", ["--exact", "managed_scope_spawn_leader_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {MANAGED_SPAWN_HOLD_ENV}: "child-kill", {MANAGED_ROOT_ENV}: "{root_literal}", {MANAGED_WORKER_ENV}: "{worker_literal}", {MANAGED_LEAF_ENV}: "{leaf_literal}", {MANAGED_RELEASE_ENV}: "{release_literal}" }},
        }})"#
    );
    let original = engine.eval::<Dynamic>(&script).expect("public managed spawn");
    let mut scope = Scope::new();
    scope.push_dynamic("nonfinal", original.clone());
    scope.push_dynamic("final", original.clone());
    drop(original);
    managed_atomic_record(&root.join("child-ready"), &format!("host={host_pid} host_start={host_start}\n"));

    drop(scope.remove::<Dynamic>("nonfinal"));
    let nonfinal_wait_unit = engine.eval_with_scope::<Dynamic>(&mut scope, "final.wait(0.1)").is_ok_and(|result| result.is_unit());
    managed_atomic_record(&root.join("nonfinal-drop-done"), &format!("host={host_pid} host_start={host_start} wait_unit={nonfinal_wait_unit}\n"));
    while !root.join("kill-request").exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(2));
    }
    assert!(root.join("kill-request").exists(), "outer observer did not authorize final managed lease drop");
    drop(scope.remove::<Dynamic>("final"));
    managed_atomic_record(&root.join("api-result"), &format!("host={host_pid} host_start={host_start} final_drop_returned=true nonfinal_wait_unit={nonfinal_wait_unit}\n"));
    while !root.join("host-exit-release").exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
}

/// Fixture-local subreaper control holds adopted, already-stopped descendants until the outer
/// observer records the public API return boundary and explicitly permits exact-PID reaping.
#[test]
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_run_reports_while_fixture_reaper_holds_stopped_zombies() {
    const WATCHDOG: Duration = Duration::from_secs(20);
    let fixture = ManagedFixture::new();
    let root = fixture.root.path().to_path_buf();
    let deadline_ns = managed_zombie_monotonic_ns() + WATCHDOG.as_nanos() as u64;
    let deadline = Instant::now() + WATCHDOG;
    let mut command = Command::new(std::env::current_exe().expect("test executable"));
    command
        .args(["--exact", "process_fixture", "--nocapture", "--quiet"])
        .env_clear()
        .env(MANAGED_ZOMBIE_ROLE_ENV, "reaper")
        .env(MANAGED_ZOMBIE_ROOT_ENV, &root)
        .env(MANAGED_ZOMBIE_DEADLINE_ENV, deadline_ns.to_string());
    let reaper = command.spawn().expect("start fixture-owned reaper");
    let reaper_pid = reaper.id() as i32;
    let mut reaper = ManagedZombieReaperGuard {
        root: root.clone(),
        child: reaper,
        launched: false,
        deadline,
    };
    let reaper_ready = fixture.path("reaper-ready");
    let host_ready = fixture.path("host-ready");
    while (!reaper_ready.exists() || !host_ready.exists()) && Instant::now() < deadline {
        assert!(reaper.child.try_wait().unwrap().is_none(), "fixture reaper exited before readiness");
        std::thread::sleep(Duration::from_millis(5));
    }
    assert!(reaper_ready.exists() && host_ready.exists(), "reaper/host readiness exceeded fixture watchdog");
    let reaper_receipt = std::fs::read_to_string(reaper_ready).unwrap();
    let host_receipt = std::fs::read_to_string(host_ready).unwrap();
    let reaper_fields = managed_record_fields(&reaper_receipt);
    let host_fields = managed_record_fields(&host_receipt);
    let host_pid = *host_fields.get("pid").expect("host PID receipt");
    assert_eq!(reaper_fields.get("pid"), Some(&reaper_pid), "reaper PID receipt must match owned child");
    let Some((_, host_parent, _, host_start)) = managed_proc_identity(host_pid) else { panic!("host identity unavailable before begin") };
    let Some((_, reaper_parent, _, reaper_start)) = managed_proc_identity(reaper_pid) else { panic!("reaper identity unavailable before begin") };
    assert_eq!(host_parent, reaper_pid, "Engine host must be a direct child of fixture reaper");
    assert_eq!(reaper_parent, std::process::id() as i32, "reaper must be owned by outer test");
    assert_eq!(managed_zombie_u64(&host_receipt, "start"), Some(host_start));
    assert_eq!(managed_zombie_u64(&reaper_receipt, "start"), Some(reaper_start));
    reaper.launched = true;
    std::fs::write(fixture.path("begin-run"), b"begin\n").unwrap();

    let pidfds = acquire_managed_pidfds(root.clone(), host_pid);
    let leader = std::fs::read_to_string(fixture.path("leader-record")).unwrap();
    let worker = std::fs::read_to_string(fixture.path("worker-record")).unwrap();
    let leaf = std::fs::read_to_string(fixture.path("leaf-record")).unwrap();
    let leader_fields = managed_record_fields(&leader);
    let worker_fields = managed_record_fields(&worker);
    let leaf_fields = managed_record_fields(&leaf);
    let leader_start = pidfds.0.iter().find(|member| member.0 == leader_fields["pid"]).unwrap().2;
    let worker_start = pidfds.0.iter().find(|member| member.0 == worker_fields["pid"]).unwrap().2;
    let leaf_start = pidfds.0.iter().find(|member| member.0 == leaf_fields["pid"]).unwrap().2;
    std::fs::write(fixture.path("pidfd-identities"), format!("leader_start={leader_start} worker_start={worker_start} leaf_start={leaf_start} pgid={}\n", leader_fields["pgid"])).unwrap();
    std::fs::write(fixture.path("pidfd-ack"), b"observer holds exact live pidfds\n").unwrap();

    let api_result_path = fixture.path("api-result");
    while !api_result_path.exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(2));
    }
    assert!(api_result_path.exists(), "Engine host did not publish API result in watchdog");
    let api_result = std::fs::read_to_string(api_result_path).unwrap();
    assert!(api_result.contains(&format!("host={host_pid} host_start={host_start}")), "API result belongs to unexpected host: {api_result}");
    assert!(api_result.contains("success=true") || api_result.contains("success=false"), "API outcome receipt is malformed: {api_result}");
    let recognized_api_outcome = api_result.contains("api_success=true api_outcome=success_report") || (api_result.contains("api_success=false api_outcome=typed_process_io cause_op=observe_process_group_closure cause_op_matches=true") && api_result.contains("diagnostic=true"));
    assert!(recognized_api_outcome, "API result must be a successful report or the typed managed group-closure error with its matching diagnostic: {api_result}");
    assert!(api_result.contains("exit=Some("), "API result must retain the exact direct leader's exit status: {api_result}");
    assert!(api_result.contains("stdout_complete=true stderr_complete=true"), "API return must include complete local capture facts: {api_result}");
    assert_managed_pidfds_exited(&pidfds);
    let leader_now = managed_proc_identity(leader_fields["pid"]);
    assert!(leader_now.is_none(), "direct leader must be reaped before H publishes the API result: {leader_now:?}");
    let host_now = managed_proc_identity(host_pid).expect("Engine host must remain live until boundary ACK");
    assert_ne!(host_now.0, 'Z', "Engine host exited before O observed its result");
    assert_eq!(host_now.1, reaper_pid, "Engine host parent changed before boundary ACK");
    assert_eq!(host_now.3, host_start, "Engine host PID was reused before boundary ACK");
    let group = leader_fields["pgid"];
    // Observe the original group at this same API-return boundary. The result and errno are
    // evidence only; signal zero is never used to infer permission to send a termination signal.
    let group_result = unsafe { libc::kill(-group, 0) };
    let group_errno = if group_result == -1 { std::io::Error::last_os_error().raw_os_error().unwrap_or(0) } else { 0 };
    let worker_now = managed_proc_identity(worker_fields["pid"]).expect("worker state at API boundary");
    let leaf_now = managed_proc_identity(leaf_fields["pid"]).expect("leaf state at API boundary");
    assert_eq!(worker_now, ('Z', reaper_pid, group, worker_start), "worker must be a stopped zombie held by R at the API boundary");
    assert_eq!(leaf_now, ('Z', reaper_pid, group, leaf_start), "leaf must be a stopped zombie held by R at the API boundary");
    let boundary = format!("host={host_pid} host_start={host_start} leader={} leader_reaped=true worker={} worker_state={} worker_start={worker_start} worker_ppid={} worker_pgid={} leaf={} leaf_state={} leaf_start={leaf_start} leaf_ppid={} leaf_pgid={} group={group} kill_zero_result={group_result} kill_zero_errno={group_errno} stdout_complete=true stderr_complete=true\n", leader_fields["pid"], worker_fields["pid"], worker_now.0, worker_now.1, worker_now.2, leaf_fields["pid"], leaf_now.0, leaf_now.1, leaf_now.2);
    std::fs::write(fixture.path("api-boundary"), &boundary).unwrap();
    std::fs::write(fixture.path("host-exit-release"), b"API boundary read back\n").unwrap();

    let held_path = fixture.path("reaper-held");
    while !held_path.exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(2));
    }
    assert!(held_path.exists(), "reaper did not publish its held-zombie observation");
    let held = std::fs::read_to_string(held_path).unwrap();
    assert!(held.contains("held_zombies=true"), "fixture did not hold exact adopted zombies: {held}");
    assert!(managed_proc_identity(worker_fields["pid"]).is_some_and(|(state, parent, group, start)| state == 'Z' && parent == reaper_pid && group == leader_fields["pgid"] && start == worker_start));
    assert!(managed_proc_identity(leaf_fields["pid"]).is_some_and(|(state, parent, group, start)| state == 'Z' && parent == reaper_pid && group == leader_fields["pgid"] && start == leaf_start));
    std::fs::write(fixture.path("reap-release"), b"outer recorded stopped members\n").unwrap();
    // Keep the final two seconds for Drop guards to release owned gates and drain exact children.
    let reaper_observation_deadline = deadline.checked_sub(Duration::from_secs(2)).unwrap_or(deadline);
    let mut status = None;
    while status.is_none() && Instant::now() < reaper_observation_deadline {
        status = reaper.child.try_wait().expect("observe exact fixture reaper");
        if status.is_none() {
            std::thread::sleep(Duration::from_millis(5));
        }
    }
    let status = status.expect("fixture reaper cleanup exceeded shared watchdog");
    assert!(status.success(), "fixture reaper reports invalid custody or incomplete exact cleanup");
    let cleanup = std::fs::read_to_string(fixture.path("reaper-cleanup")).unwrap();
    assert!(cleanup.contains("held_zombies=true"));
    assert!(cleanup.contains(&format!("worker={} reaped=true", worker_fields["pid"])), "worker was not reaped by the fixture-owned reaper: {cleanup}");
    assert!(cleanup.contains(&format!("leaf={} reaped=true", leaf_fields["pid"])), "leaf was not reaped by the fixture-owned reaper: {cleanup}");
    eprintln!("managed_held_zombie_boundary host_live_at_return=true leader={} leader_start={leader_start} leader_reaped=true worker={} worker_start={worker_start} worker_state=Z worker_pgid={} leaf={} leaf_start={leaf_start} leaf_state=Z leaf_pgid={} group={group} kill_zero_result={group_result} kill_zero_errno={group_errno} capture_complete=true {api_result} held={held:?} reaper_status={status:?}", leader_fields["pid"], worker_fields["pid"], worker_now.2, leaf_fields["pid"], leaf_now.2);
    eprintln!("managed_held_zombie_cleanup worker={} reaped=true leaf={} reaped=true", worker_fields["pid"], leaf_fields["pid"]);
}

/// Public Child.kill returns a failed child report after exact managed-group closure.
#[test]
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_child_kill_reports_group_closed_under_fixture_reaper() {
    const WATCHDOG: Duration = Duration::from_secs(20);
    let fixture = ManagedFixture::new();
    let root = fixture.root.path().to_path_buf();
    let deadline_ns = managed_zombie_monotonic_ns() + WATCHDOG.as_nanos() as u64;
    let deadline = Instant::now() + WATCHDOG;
    let mut sentinel = managed_spawn_sentinel();
    let sentinel_pid = sentinel.0.id() as i32;
    let sentinel_start = managed_proc_identity(sentinel_pid).expect("sentinel start").3;
    let sentinel_pgid = unsafe { libc::getpgid(sentinel_pid) };
    assert_eq!(sentinel_pgid, sentinel_pid);
    let mut command = Command::new(std::env::current_exe().expect("test executable"));
    command
        .args(["--exact", "process_fixture", "--nocapture", "--quiet"])
        .env_clear()
        .env(MANAGED_ZOMBIE_ROLE_ENV, "reaper")
        .env(MANAGED_ZOMBIE_REAP_MODE_ENV, "kill")
        .env(MANAGED_ZOMBIE_ROOT_ENV, &root)
        .env(MANAGED_ZOMBIE_DEADLINE_ENV, deadline_ns.to_string());
    let child = command.spawn().expect("fixture reaper");
    let reaper_pid = child.id() as i32;
    let mut reaper = ManagedZombieReaperGuard { root: root.clone(), child, launched: false, deadline };
    while (!fixture.path("reaper-ready").exists() || !fixture.path("host-ready").exists()) && Instant::now() < deadline {
        assert!(reaper.child.try_wait().unwrap().is_none(), "reaper exited before readiness");
        std::thread::sleep(Duration::from_millis(5));
    }
    let reaper_fields = managed_record_fields(&std::fs::read_to_string(fixture.path("reaper-ready")).expect("reaper readiness"));
    let host_fields = managed_record_fields(&std::fs::read_to_string(fixture.path("host-ready")).expect("host readiness"));
    let host_pid = host_fields["pid"];
    let reaper_start = managed_proc_identity(reaper_pid).expect("reaper identity").3;
    let host_start = managed_proc_identity(host_pid).expect("host identity").3;
    assert_eq!(reaper_fields["pid"], reaper_pid);
    assert_eq!(managed_proc_identity(host_pid).unwrap().1, reaper_pid);
    assert_eq!(managed_proc_identity(reaper_pid).unwrap().1, std::process::id() as i32);
    reaper.launched = true;
    std::fs::write(fixture.path("begin-run"), b"begin\n").unwrap();
    while !fixture.path("child-ready").exists() && Instant::now() < deadline {
        assert!(reaper.child.try_wait().unwrap().is_none(), "reaper exited before Child readiness");
        std::thread::sleep(Duration::from_millis(3));
    }
    assert!(fixture.path("child-ready").exists(), "Engine host did not publish Child readiness");
    while (!fixture.path("leader-record").exists() || !fixture.path("worker-record").exists() || !fixture.path("leaf-record").exists()) && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(3));
    }
    let pidfds = acquire_managed_pidfds(root.clone(), host_pid);
    let leader_record_text = std::fs::read_to_string(fixture.path("leader-record")).unwrap();
    let leader_record_start = managed_zombie_u64(&leader_record_text, "start").expect("spawn leader record must include its Linux start ticks");
    let leader = managed_record_fields(&leader_record_text);
    let worker = managed_record_fields(&std::fs::read_to_string(fixture.path("worker-record")).unwrap());
    let leaf = managed_record_fields(&std::fs::read_to_string(fixture.path("leaf-record")).unwrap());
    let start = |pid| pidfds.0.iter().find(|entry| entry.0 == pid).unwrap().2;
    let leader_start = start(leader["pid"]);
    let leader_record_start_matches_pidfd = leader_record_start == leader_start;
    let worker_start = start(worker["pid"]);
    let leaf_start = start(leaf["pid"]);
    let group = leader["pgid"];
    std::fs::write(fixture.path("pidfd-identities"), format!("leader_start={leader_start} worker_start={worker_start} leaf_start={leaf_start} pgid={group}\n")).unwrap();
    eprintln!("managed_child_kill_live reaper={reaper_pid} reaper_start={reaper_start} host={host_pid} host_start={host_start} leader={} leader_start={leader_start} worker={} worker_start={worker_start} leaf={} leaf_start={leaf_start} group={group} sentinel={sentinel_pid} sentinel_start={sentinel_start} sentinel_pgid={sentinel_pgid}", leader["pid"], worker["pid"], leaf["pid"]);
    std::fs::write(fixture.path("kill-request"), b"exact member PIDFDs acquired\n").unwrap();
    while !fixture.path("api-result").exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(2));
    }
    let api = std::fs::read_to_string(fixture.path("api-result")).unwrap_or_default();
    let api_bound = api.contains(&format!("host={host_pid} host_start={host_start}"));
    let report_returned = api.contains("api_success=true api_outcome=child_report");
    let killed_report = api.contains("success=false");
    let capture_complete = api.contains("stdout_complete=true stderr_complete=true");
    let pidfds_exited = pidfds.0.iter().all(|(pid, fd, _)| {
        let mut pollfd = libc::pollfd { fd: *fd, events: libc::POLLIN, revents: 0 };
        (unsafe { libc::poll(&mut pollfd, 1, 0) }) == 1 && pollfd.revents & libc::POLLIN != 0 && *pid > 0
    });
    let leader_absent = managed_proc_identity(leader["pid"]).is_none();
    let worker_absent = managed_proc_identity(worker["pid"]).is_none();
    let leaf_absent = managed_proc_identity(leaf["pid"]).is_none();
    let reaped = std::fs::read_to_string(fixture.path("prompt-reaper-cleanup")).unwrap_or_default();
    let exact_reaped = reaped.contains(&format!("worker={} start={worker_start} pgid={group} reaped=true wait_status=", worker["pid"])) && reaped.contains(&format!("leaf={} start={leaf_start} pgid={group} reaped=true wait_status=", leaf["pid"])) && reaped.contains("complete=true");
    let host_live = matches!(managed_proc_identity(host_pid), Some((state, parent, _, start)) if state != 'Z' && parent == reaper_pid && start == host_start);
    let reaper_live = matches!(managed_proc_identity(reaper_pid), Some((state, parent, _, start)) if state != 'Z' && parent == std::process::id() as i32 && start == reaper_start);
    let sentinel_live = matches!(managed_proc_identity(sentinel_pid), Some((state, parent, pgid, start)) if state != 'Z' && parent == std::process::id() as i32 && pgid == sentinel_pgid && start == sentinel_start);
    std::fs::write(fixture.path("host-exit-release"), b"API boundary observed\n").unwrap();
    let stop = deadline.checked_sub(Duration::from_secs(2)).unwrap_or(deadline);
    let mut status = None;
    while status.is_none() && Instant::now() < stop {
        status = reaper.child.try_wait().unwrap();
        if status.is_none() {
            std::thread::sleep(Duration::from_millis(5));
        }
    }
    let reaper_ok = status.is_some_and(|status| status.success());
    let host_absent_after_cleanup = managed_proc_identity(host_pid).is_none();
    let cleanup = std::fs::read_to_string(fixture.path("reaper-cleanup")).unwrap_or_default();
    drop(sentinel);
    let sentinel_reaped = pid_is_absent(sentinel_pid);
    let group_empty = unsafe { libc::kill(-group, 0) } == -1 && std::io::Error::last_os_error().raw_os_error() == Some(libc::ESRCH);
    eprintln!("managed_child_kill_boundary host_live_at_return={host_live} reaper_live_at_return={reaper_live} leader={} leader_start={leader_start} leader_record_start_matches_pidfd={leader_record_start_matches_pidfd} leader_absent={leader_absent} worker={} worker_start={worker_start} worker_absent={worker_absent} leaf={} leaf_start={leaf_start} leaf_absent={leaf_absent} group={group} exact_descendants_reaped={exact_reaped} sentinel={sentinel_pid} sentinel_start={sentinel_start} sentinel_pgid={sentinel_pgid} sentinel_live_at_return={sentinel_live} sentinel_reaped_after_return={sentinel_reaped} api_bound={api_bound} report_returned={report_returned} killed_report={killed_report} capture_complete={capture_complete} pidfds_exited={pidfds_exited} reaper_ok={reaper_ok} host_absent_after_cleanup={host_absent_after_cleanup} group_empty={group_empty} api={api:?} reaped={reaped:?} cleanup={cleanup:?}", leader["pid"], worker["pid"], leaf["pid"]);
    assert!(leader_record_start_matches_pidfd, "spawn leader record start must match exact acquired PIDFD identity");
    assert!(api_bound && report_returned, "public wait must return the exact host-bound Child report: {api}");
    assert!(killed_report, "public Child.kill report must record the killed child as unsuccessful");
    assert!(capture_complete, "public kill report must contain complete streams: {api}");
    assert!(pidfds_exited && leader_absent && worker_absent && leaf_absent && exact_reaped, "all exact managed members must be closed and reaped");
    assert!(host_live && reaper_live, "host and independent reaper must remain live at API return");
    assert!(sentinel_live, "public Child.kill must preserve the unrelated sentinel at API return");
    assert!(reaper_ok && cleanup.contains("complete=true") && host_absent_after_cleanup && sentinel_reaped && group_empty, "exact fixture cleanup must finish: {cleanup}");
}

/// Dropping a nonfinal Rhai handle preserves the managed group; dropping the final lease closes it.
#[test]
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_spawn_final_clone_drop_closes_group_under_fixture_reaper() {
    const WATCHDOG: Duration = Duration::from_secs(20);
    let fixture = ManagedFixture::new();
    let root = fixture.root.path().to_path_buf();
    let deadline_ns = managed_zombie_monotonic_ns() + WATCHDOG.as_nanos() as u64;
    let deadline = Instant::now() + WATCHDOG;
    let mut sentinel = managed_spawn_sentinel();
    let sentinel_pid = sentinel.0.id() as i32;
    let sentinel_start = managed_proc_identity(sentinel_pid).expect("sentinel start").3;
    let sentinel_pgid = unsafe { libc::getpgid(sentinel_pid) };
    assert_eq!(sentinel_pgid, sentinel_pid);

    let mut command = Command::new(std::env::current_exe().expect("test executable"));
    command
        .args(["--exact", "process_fixture", "--nocapture", "--quiet"])
        .env_clear()
        .env(MANAGED_ZOMBIE_ROLE_ENV, "reaper")
        .env(MANAGED_ZOMBIE_REAP_MODE_ENV, "drop")
        .env(MANAGED_ZOMBIE_ROOT_ENV, &root)
        .env(MANAGED_ZOMBIE_DEADLINE_ENV, deadline_ns.to_string());
    let child = command.spawn().expect("fixture reaper");
    let reaper_pid = child.id() as i32;
    let mut reaper = ManagedZombieReaperGuard { root: root.clone(), child, launched: false, deadline };
    while (!fixture.path("reaper-ready").exists() || !fixture.path("host-ready").exists()) && Instant::now() < deadline {
        assert!(reaper.child.try_wait().unwrap().is_none(), "reaper exited before readiness");
        std::thread::sleep(Duration::from_millis(5));
    }
    let reaper_fields = managed_record_fields(&std::fs::read_to_string(fixture.path("reaper-ready")).expect("reaper readiness"));
    let host_fields = managed_record_fields(&std::fs::read_to_string(fixture.path("host-ready")).expect("host readiness"));
    let host_pid = host_fields["pid"];
    let reaper_start = managed_proc_identity(reaper_pid).expect("reaper identity").3;
    let host_start = managed_proc_identity(host_pid).expect("host identity").3;
    assert_eq!(reaper_fields["pid"], reaper_pid);
    assert_eq!(managed_proc_identity(host_pid).unwrap().1, reaper_pid);
    assert_eq!(managed_proc_identity(reaper_pid).unwrap().1, std::process::id() as i32);
    reaper.launched = true;
    std::fs::write(fixture.path("begin-run"), b"begin final-drop fixture\n").unwrap();

    while !fixture.path("nonfinal-drop-done").exists() && Instant::now() < deadline {
        assert!(reaper.child.try_wait().unwrap().is_none(), "reaper exited before nonfinal-drop observation");
        std::thread::sleep(Duration::from_millis(3));
    }
    let nonfinal = managed_record_fields(&std::fs::read_to_string(fixture.path("nonfinal-drop-done")).expect("nonfinal-drop observation"));
    while (!fixture.path("leader-record").exists() || !fixture.path("worker-record").exists() || !fixture.path("leaf-record").exists()) && Instant::now() < deadline {
        assert!(reaper.child.try_wait().unwrap().is_none(), "reaper exited before all managed members were ready");
        std::thread::sleep(Duration::from_millis(3));
    }
    let leader_record_text = std::fs::read_to_string(fixture.path("leader-record")).expect("leader readiness");
    let leader_record_start = managed_zombie_u64(&leader_record_text, "start").expect("leader start ticks");
    let leader = managed_record_fields(&leader_record_text);
    let worker = managed_record_fields(&std::fs::read_to_string(fixture.path("worker-record")).expect("worker readiness"));
    let leaf = managed_record_fields(&std::fs::read_to_string(fixture.path("leaf-record")).expect("leaf readiness"));
    let pidfds = acquire_managed_pidfds(root.clone(), host_pid);
    let pidfd_start = |pid| pidfds.0.iter().find(|entry| entry.0 == pid).unwrap().2;
    let leader_start = pidfd_start(leader["pid"]);
    let worker_start = pidfd_start(worker["pid"]);
    let leaf_start = pidfd_start(leaf["pid"]);
    let group = leader["pgid"];
    let leader_record_start_matches_pidfd = leader_record_start == leader_start;
    let worker_record_group_matches = worker.get("pgid") == Some(&group);
    let leaf_record_group_matches = leaf.get("pgid") == Some(&group);
    let worker_record_start_matches_pidfd = managed_zombie_u64(&std::fs::read_to_string(fixture.path("worker-record")).unwrap(), "start") == Some(worker_start);
    let leaf_record_start_matches_pidfd = managed_zombie_u64(&std::fs::read_to_string(fixture.path("leaf-record")).unwrap(), "start") == Some(leaf_start);
    std::fs::write(fixture.path("pidfd-identities"), format!("leader_start={leader_start} worker_start={worker_start} leaf_start={leaf_start} pgid={group}\n")).unwrap();
    eprintln!("managed_final_drop_live reaper={reaper_pid} reaper_start={reaper_start} host={host_pid} host_start={host_start} leader={} leader_start={leader_start} worker={} worker_start={worker_start} leaf={} leaf_start={leaf_start} group={group} sentinel={sentinel_pid} sentinel_start={sentinel_start} sentinel_pgid={sentinel_pgid}", leader["pid"], worker["pid"], leaf["pid"]);

    let parent = std::process::id() as i32;
    let reaper_live_before_drop = matches!(managed_proc_identity(reaper_pid), Some((state, actual_parent, _, start)) if state != 'Z' && actual_parent == parent && start == reaper_start);
    let host_live_before_drop = matches!(managed_proc_identity(host_pid), Some((state, actual_parent, _, start)) if state != 'Z' && actual_parent == reaper_pid && start == host_start);
    let sentinel_live_before_drop = matches!(managed_proc_identity(sentinel_pid), Some((state, actual_parent, pgid, start)) if state != 'Z' && actual_parent == parent && pgid == sentinel_pgid && start == sentinel_start);
    let nonfinal_members_live = [leader["pid"], worker["pid"], leaf["pid"]]
        .into_iter()
        .all(|pid| managed_proc_identity(pid).is_some_and(|(state, _, observed_group, start)| state != 'Z' && observed_group == group && start == pidfd_start(pid)));
    let nonfinal_drop_preserved_group = nonfinal.get("host") == Some(&host_pid) && nonfinal_members_live && std::fs::read_to_string(fixture.path("nonfinal-drop-done")).is_ok_and(|receipt| receipt.contains("wait_unit=true"));
    std::fs::write(fixture.path("kill-request"), b"exact live identities recorded; authorize final lease drop\n").unwrap();
    while !fixture.path("api-result").exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(2));
    }
    let api = std::fs::read_to_string(fixture.path("api-result")).unwrap_or_default();
    let api_bound = api.contains(&format!("host={host_pid} host_start={host_start} final_drop_returned=true nonfinal_wait_unit=true"));
    let mut pidfds_exited = false;
    let mut leader_absent = false;
    let mut worker_absent = false;
    let mut leaf_absent = false;
    let mut exact_reaped = false;
    let mut host_live_during_closure = false;
    let mut reaper_live_during_closure = false;
    let mut sentinel_live_during_closure = false;
    let mut group_empty_after_closure = false;
    let mut final_members_live = true;
    let mut reaped = String::new();
    let observation_deadline = deadline.checked_sub(Duration::from_secs(8)).unwrap_or(deadline);
    let mut observation_error = None;
    while Instant::now() < observation_deadline {
        if fixture.path("exceptional-cleanup-started").exists() {
            observation_error = Some("fixture watchdog exceptional cleanup started before observed closure".to_owned());
            break;
        }
        let read_identity = |pid| managed_proc_identity_checked(pid);
        let host_identity = read_identity(host_pid);
        let reaper_identity = read_identity(reaper_pid);
        let sentinel_identity = read_identity(sentinel_pid);
        let member_identities = [leader["pid"], worker["pid"], leaf["pid"]].map(read_identity);
        if host_identity.is_err() || reaper_identity.is_err() || sentinel_identity.is_err() || member_identities.iter().any(Result::is_err) {
            observation_error = Some("permission or malformed proc identity during closure observation".to_owned());
            break;
        }
        let host_identity = host_identity.unwrap();
        let reaper_identity = reaper_identity.unwrap();
        let sentinel_identity = sentinel_identity.unwrap();
        let member_identities = member_identities.map(Result::unwrap);
        host_live_during_closure = matches!(host_identity, Some((state, parent, _, start)) if state != 'Z' && parent == reaper_pid && start == host_start);
        reaper_live_during_closure = matches!(reaper_identity, Some((state, parent, _, start)) if state != 'Z' && parent == std::process::id() as i32 && start == reaper_start);
        sentinel_live_during_closure = matches!(sentinel_identity, Some((state, parent, pgid, start)) if state != 'Z' && parent == std::process::id() as i32 && pgid == sentinel_pgid && start == sentinel_start);
        if !host_live_during_closure || !reaper_live_during_closure || !sentinel_live_during_closure {
            observation_error = Some("host, reaper, or sentinel identity did not remain live during closure observation".to_owned());
            break;
        }
        pidfds_exited = pidfds.0.iter().all(|(pid, fd, _)| {
            let mut pollfd = libc::pollfd { fd: *fd, events: libc::POLLIN, revents: 0 };
            (unsafe { libc::poll(&mut pollfd, 1, 0) }) == 1 && pollfd.revents & libc::POLLIN != 0 && *pid > 0
        });
        let expected = [(leader["pid"], leader_start), (worker["pid"], worker_start), (leaf["pid"], leaf_start)];
        let absent = expected
            .iter()
            .zip(member_identities.iter())
            .map(|((pid, start), identity)| match identity.as_ref() {
                None => true,
                Some((_, _, _, observed_start)) => observed_start != start || *pid <= 0,
            })
            .collect::<Vec<_>>();
        [leader_absent, worker_absent, leaf_absent] = [absent[0], absent[1], absent[2]];
        reaped = std::fs::read_to_string(fixture.path("prompt-reaper-cleanup")).unwrap_or_default();
        exact_reaped = reaped.contains(&format!("worker={} start={worker_start} pgid={group} reaped=true wait_status=", worker["pid"])) && reaped.contains(&format!("leaf={} start={leaf_start} pgid={group} reaped=true wait_status=", leaf["pid"])) && reaped.contains("complete=true");
        let group_result = unsafe { libc::kill(-group, 0) };
        let group_error = if group_result == -1 { std::io::Error::last_os_error().raw_os_error() } else { None };
        group_empty_after_closure = group_result == -1 && group_error == Some(libc::ESRCH);
        final_members_live = member_identities.iter().zip(expected.iter()).any(|(identity, (pid, start))| match identity {
            Some((state, _, observed_group, observed_start)) => *state != 'Z' && *observed_group == group && observed_start == start && *pid > 0,
            None => false,
        });
        if pidfds_exited && leader_absent && worker_absent && leaf_absent && exact_reaped && group_empty_after_closure {
            break;
        }
        std::thread::sleep(Duration::from_millis(5));
    }
    let exceptional_cleanup_not_started = !fixture.path("exceptional-cleanup-started").exists();
    let closure_observed = pidfds_exited && leader_absent && worker_absent && leaf_absent && exact_reaped && group_empty_after_closure && exceptional_cleanup_not_started && observation_error.is_none();
    let host_live_at_drop_return = host_live_during_closure;
    let reaper_live_at_drop_return = reaper_live_during_closure;
    let sentinel_live_at_drop_return = sentinel_live_during_closure;
    managed_atomic_record(&root.join("final-drop-closure-observed"), &format!(
        "host={host_pid} host_start={host_start} reaper={reaper_pid} reaper_start={reaper_start} leader={} leader_start={leader_start} worker={} worker_start={worker_start} leaf={} leaf_start={leaf_start} group={group} observed={closure_observed} pidfds_exited={pidfds_exited} exact_reaped={exact_reaped} group_empty={group_empty_after_closure}\n",
        leader["pid"], worker["pid"], leaf["pid"]));

    std::fs::write(fixture.path("host-exit-release"), b"final-drop boundary observed\n").unwrap();
    let stop = deadline.checked_sub(Duration::from_secs(2)).unwrap_or(deadline);
    let mut status = None;
    while status.is_none() && Instant::now() < stop {
        status = reaper.child.try_wait().unwrap();
        if status.is_none() {
            std::thread::sleep(Duration::from_millis(5));
        }
    }
    let reaper_ok = status.is_some_and(|status| status.success());
    let host_absent_after_cleanup = managed_proc_identity(host_pid).is_none();
    let cleanup = std::fs::read_to_string(fixture.path("reaper-cleanup")).unwrap_or_default();
    drop(sentinel);
    let sentinel_reaped = pid_is_absent(sentinel_pid);
    let group_empty = unsafe { libc::kill(-group, 0) } == -1 && std::io::Error::last_os_error().raw_os_error() == Some(libc::ESRCH);
    eprintln!("managed_final_drop_boundary nonfinal_preserved={nonfinal_drop_preserved_group} leader={} leader_start={leader_start} leader_record_start_matches_pidfd={leader_record_start_matches_pidfd} worker={} worker_start={worker_start} worker_record_start_matches_pidfd={worker_record_start_matches_pidfd} leaf={} leaf_start={leaf_start} leaf_record_start_matches_pidfd={leaf_record_start_matches_pidfd} worker_record_group_matches={worker_record_group_matches} leaf_record_group_matches={leaf_record_group_matches} group={group} drop_return_recorded={api_bound} closure_observed={closure_observed} exceptional_cleanup_not_started={exceptional_cleanup_not_started} leader_absent={leader_absent} worker_absent={worker_absent} leaf_absent={leaf_absent} exact_reaped={exact_reaped} host_live_before_drop={host_live_before_drop} reaper_live_before_drop={reaper_live_before_drop} sentinel_live_before_drop={sentinel_live_before_drop} host_live_through_closure={host_live_at_drop_return} reaper_live_through_closure={reaper_live_at_drop_return} sentinel_live_through_closure={sentinel_live_at_drop_return} pidfds_exited={pidfds_exited} final_members_live={final_members_live} reaper_ok={reaper_ok} reaper_status={status:?} host_absent_after_cleanup={host_absent_after_cleanup} sentinel_reaped={sentinel_reaped} group_empty_after_closure={group_empty_after_closure} observation_error={observation_error:?} api={api:?} reaped={reaped:?} cleanup={cleanup:?}", leader["pid"], worker["pid"], leaf["pid"]);

    assert!(
        leader_record_start_matches_pidfd && worker_record_start_matches_pidfd && leaf_record_start_matches_pidfd && worker_record_group_matches && leaf_record_group_matches,
        "fixture records must match exact acquired PIDFD identities and managed group"
    );
    assert!(host_live_before_drop && reaper_live_before_drop && sentinel_live_before_drop, "host, fixture reaper, and sentinel must be live before final drop");
    assert!(nonfinal_drop_preserved_group, "dropping a nonfinal managed Child clone terminated its live group");
    assert!(api_bound, "host did not record the authorized final managed lease drop: {api}");
    assert!(
        closure_observed && pidfds_exited && leader_absent && worker_absent && leaf_absent && exact_reaped && group_empty_after_closure,
        "final managed lease drop must be followed by independently observed exact group closure"
    );
    assert!(host_live_at_drop_return && reaper_live_at_drop_return && sentinel_live_at_drop_return, "host, fixture reaper, and sentinel must remain live at the final-drop boundary");
    assert!(reaper_ok && cleanup.contains("complete=true") && host_absent_after_cleanup && sentinel_reaped && group_empty, "exact final-drop fixture cleanup must finish: {cleanup}");
    assert!(!final_members_live, "final managed Child lease drop left an exact process-group member live");
}

/// A real managed deadline kills its full process group; the fixture reaper independently waits
/// exact descendants while the host and unrelated sentinel remain live for readback.
#[test]
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_run_deadline_reaps_group_under_fixture_reaper() {
    const WATCHDOG: Duration = Duration::from_secs(20);
    let fixture = ManagedFixture::new();
    let root = fixture.root.path().to_path_buf();
    let deadline_ns = managed_zombie_monotonic_ns() + WATCHDOG.as_nanos() as u64;
    let deadline = Instant::now() + WATCHDOG;
    let mut sentinel = Sentinel(
        Command::new("/bin/sleep")
            .arg("30")
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("start unrelated sentinel"),
    );
    let sentinel_pid = sentinel.0.id() as i32;
    let sentinel_start = managed_proc_identity(sentinel_pid).expect("read unrelated sentinel identity").3;
    let mut command = Command::new(std::env::current_exe().expect("test executable"));
    command
        .args(["--exact", "process_fixture", "--nocapture", "--quiet"])
        .env_clear()
        .env(MANAGED_ZOMBIE_ROLE_ENV, "reaper")
        .env(MANAGED_ZOMBIE_REAP_MODE_ENV, "deadline")
        .env(MANAGED_ZOMBIE_ROOT_ENV, &root)
        .env(MANAGED_ZOMBIE_DEADLINE_ENV, deadline_ns.to_string());
    let reaper_child = command.spawn().expect("start fixture-owned reaper");
    let reaper_pid = reaper_child.id() as i32;
    let mut reaper = ManagedZombieReaperGuard {
        root: root.clone(),
        child: reaper_child,
        launched: false,
        deadline,
    };
    let reaper_ready = fixture.path("reaper-ready");
    let host_ready = fixture.path("host-ready");
    while (!reaper_ready.exists() || !host_ready.exists()) && Instant::now() < deadline {
        assert!(reaper.child.try_wait().unwrap().is_none(), "fixture reaper exited before readiness");
        std::thread::sleep(Duration::from_millis(5));
    }
    assert!(reaper_ready.exists() && host_ready.exists(), "reaper/host readiness exceeded watchdog");
    let reaper_receipt = std::fs::read_to_string(&reaper_ready).unwrap();
    let reaper_fields = managed_record_fields(&reaper_receipt);
    let host_receipt = std::fs::read_to_string(host_ready).unwrap();
    let host_fields = managed_record_fields(&host_receipt);
    let host_pid = host_fields["pid"];
    let Some((_, host_parent, _, host_start)) = managed_proc_identity(host_pid) else { panic!("host identity unavailable before begin") };
    let Some((_, reaper_parent, _, reaper_start)) = managed_proc_identity(reaper_pid) else { panic!("reaper identity unavailable before begin") };
    assert_eq!(reaper_fields.get("pid"), Some(&reaper_pid));
    assert_eq!(managed_zombie_u64(&host_receipt, "start"), Some(host_start));
    assert_eq!(managed_zombie_u64(&reaper_receipt, "start"), Some(reaper_start));
    assert_eq!((host_parent, reaper_parent), (reaper_pid, std::process::id() as i32));
    reaper.launched = true;
    std::fs::write(fixture.path("begin-run"), b"begin\n").unwrap();

    let pidfds = acquire_managed_pidfds(root.clone(), host_pid);
    let leader = std::fs::read_to_string(fixture.path("leader-record")).unwrap();
    let worker = std::fs::read_to_string(fixture.path("worker-record")).unwrap();
    let leaf = std::fs::read_to_string(fixture.path("leaf-record")).unwrap();
    let leader_fields = managed_record_fields(&leader);
    let worker_fields = managed_record_fields(&worker);
    let leaf_fields = managed_record_fields(&leaf);
    let identity = |pid: i32| pidfds.0.iter().find(|member| member.0 == pid).map(|member| member.2).expect("PIDFD start identity");
    let leader_start = identity(leader_fields["pid"]);
    let worker_start = identity(worker_fields["pid"]);
    let leaf_start = identity(leaf_fields["pid"]);
    let group = leader_fields["pgid"];
    assert_eq!((worker_fields["pgid"], leaf_fields["pgid"]), (group, group), "all fixture members must share the managed process group");
    std::fs::write(fixture.path("pidfd-identities"), format!("leader_start={leader_start} worker_start={worker_start} leaf_start={leaf_start} pgid={group}\n")).unwrap();
    std::fs::write(fixture.path("pidfd-ack"), b"observer holds exact live pidfds\n").unwrap();

    let normal_observation_deadline = deadline.checked_sub(Duration::from_secs(8)).unwrap_or(deadline);
    let api_path = fixture.path("api-result");
    while !api_path.exists() && Instant::now() < normal_observation_deadline {
        std::thread::sleep(Duration::from_millis(2));
    }
    let api_result = std::fs::read_to_string(&api_path).unwrap_or_default();
    let api_is_timed_out = api_result.contains("api_success=true api_outcome=timeout_report success=Some(false) timed_out=Some(true)");
    let captures_incomplete = api_result.contains("stdout_complete=Some(false) stderr_complete=Some(false)");
    let partial_output_preserved = api_result.contains("stdout_marker=true stderr_marker=true");
    let api_is_not_cleanup_error = !api_result.contains("typed_timeout_error") && !api_result.contains("observe_process_group_closure");
    let api_belongs_to_host = api_result.contains(&format!("host={host_pid} host_start={host_start}"));
    let no_watchdog_cleanup_at_return = !fixture.path("exceptional-cleanup-started").exists();
    let leader_absent = managed_proc_identity(leader_fields["pid"]).map_or(true, |identity| identity.3 != leader_start);
    let worker_absent = managed_proc_identity(worker_fields["pid"]).map_or(true, |identity| identity.3 != worker_start);
    let leaf_absent = managed_proc_identity(leaf_fields["pid"]).map_or(true, |identity| identity.3 != leaf_start);
    let pidfds_exited = pidfds.0.iter().all(|(pid, fd, start)| {
        let mut pollfd = libc::pollfd { fd: *fd, events: libc::POLLIN, revents: 0 };
        (unsafe { libc::poll(&mut pollfd, 1, 0) }) == 1 && pollfd.revents & libc::POLLIN != 0 && managed_proc_identity(*pid).map_or(true, |identity| identity.3 != *start)
    });
    let host_live_at_return = matches!(managed_proc_identity(host_pid), Some((state, parent, _, start)) if state != 'Z' && parent == reaper_pid && start == host_start);
    let reaper_live_at_return = matches!(managed_proc_identity(reaper_pid), Some((state, parent, _, start)) if state != 'Z' && parent == std::process::id() as i32 && start == reaper_start);
    let sentinel_live_at_return = matches!(managed_proc_identity(sentinel_pid), Some((state, parent, _, start)) if state != 'Z' && parent == std::process::id() as i32 && start == sentinel_start);
    let group_probe = unsafe { libc::kill(-group, 0) };
    let group_errno = if group_probe == -1 { std::io::Error::last_os_error().raw_os_error().unwrap_or(0) } else { 0 };
    let cleanup_path = fixture.path("prompt-reaper-cleanup");
    while !cleanup_path.exists() && Instant::now() < normal_observation_deadline {
        std::thread::sleep(Duration::from_millis(2));
    }
    let cleanup_text = std::fs::read_to_string(cleanup_path).unwrap_or_default();
    let cleanup_exact =
        cleanup_text.contains(&format!("worker={} start={worker_start} pgid={group} reaped=true", worker_fields["pid"])) && cleanup_text.contains(&format!("leaf={} start={leaf_start} pgid={group} reaped=true", leaf_fields["pid"])) && cleanup_text.contains("complete=true");
    let no_watchdog_cleanup_through_boundary = no_watchdog_cleanup_at_return && !fixture.path("exceptional-cleanup-started").exists();
    let boundary = format!("host={host_pid} host_start={host_start} reaper={reaper_pid} reaper_start={reaper_start} leader={} leader_start={leader_start} leader_absent={leader_absent} worker={} worker_start={worker_start} worker_absent={worker_absent} leaf={} leaf_start={leaf_start} leaf_absent={leaf_absent} group={group} group_probe={group_probe} group_errno={group_errno} host_live={host_live_at_return} reaper_live={reaper_live_at_return} sentinel={sentinel_pid} sentinel_start={sentinel_start} sentinel_live={sentinel_live_at_return} timed_out={api_is_timed_out} captures_incomplete={captures_incomplete} partial_output={partial_output_preserved} pidfds_exited={pidfds_exited} cleanup_exact={cleanup_exact} no_watchdog_cleanup_through_boundary={no_watchdog_cleanup_through_boundary}\n", leader_fields["pid"], worker_fields["pid"], leaf_fields["pid"]);
    std::fs::write(fixture.path("api-boundary"), &boundary).unwrap();
    std::fs::write(fixture.path("host-exit-release"), b"deadline boundary recorded\n").unwrap();
    std::fs::write(fixture.path("reap-release"), b"deadline closure recorded\n").unwrap();
    let observation_deadline = normal_observation_deadline;
    let mut reaper_status = None;
    while reaper_status.is_none() && Instant::now() < observation_deadline {
        reaper_status = reaper.child.try_wait().expect("observe exact fixture reaper");
        if reaper_status.is_none() {
            std::thread::sleep(Duration::from_millis(5));
        }
    }
    let reaper_ok = reaper_status.is_some_and(|status| status.success());
    let no_watchdog_cleanup_after_reap = !fixture.path("exceptional-cleanup-started").exists();
    drop(sentinel);
    let sentinel_reaped = pid_is_absent(sentinel_pid);
    eprintln!("managed_deadline_group_boundary {boundary} api={api_result:?} cleanup={cleanup_text:?} reaper_ok={reaper_ok} sentinel_reaped={sentinel_reaped} no_watchdog_cleanup_after_reap={no_watchdog_cleanup_after_reap}");

    assert!(reaper_ok, "fixture reaper failed its bounded exact cleanup");
    assert!(no_watchdog_cleanup_through_boundary && no_watchdog_cleanup_after_reap, "fixture watchdog cleanup participated in the deadline result or closure observation");
    assert!(api_belongs_to_host, "deadline result belongs to an unexpected Engine host: {api_result}");
    assert!(api_is_timed_out, "managed public run did not return its deadline report after exact group closure: {api_result}");
    assert!(api_is_not_cleanup_error, "managed run reported timeout cleanup failure instead of a closed scope: {api_result}");
    assert!(captures_incomplete && partial_output_preserved, "deadline report must preserve both marker streams and honestly report their still-open captures: {api_result}");
    assert!(leader_absent && worker_absent && leaf_absent && pidfds_exited, "managed member identity remained live after deadline cleanup: {boundary}");
    assert!(group_probe == -1 && group_errno == libc::ESRCH, "original managed group remained present after closure: {boundary}");
    assert!(host_live_at_return && reaper_live_at_return && sentinel_live_at_return && sentinel_reaped, "host/reaper/sentinel custody boundary was invalid: {boundary}");
    assert!(cleanup_exact, "fixture reaper did not independently wait for exact worker and leaf identities: {cleanup_text}");
}

/// A managed run deadline cancels capture readers while an escaped descendant remains owned by
/// the fixture subreaper and still holds both inherited pipe writers.
#[test]
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_run_deadline_cancels_escaped_pipe_holder_under_fixture_reaper() {
    const WATCHDOG: Duration = Duration::from_secs(20);
    let fixture = ManagedFixture::new();
    let root = fixture.root.path().to_path_buf();
    let deadline_ns = managed_zombie_monotonic_ns() + WATCHDOG.as_nanos() as u64;
    let deadline = Instant::now() + WATCHDOG;
    let mut sentinel = managed_spawn_sentinel();
    let sentinel_pid = sentinel.0.id() as i32;
    let sentinel_start = managed_proc_identity(sentinel_pid).expect("read sentinel identity").3;
    let sentinel_group = unsafe { libc::getpgid(sentinel_pid) };
    assert_eq!(sentinel_group, sentinel_pid, "fixture sentinel must own a separate process group");

    let mut command = Command::new(std::env::current_exe().expect("test executable"));
    command
        .args(["--exact", "process_fixture", "--nocapture", "--quiet"])
        .env_clear()
        .env(MANAGED_ZOMBIE_ROLE_ENV, "reaper")
        .env(MANAGED_ZOMBIE_REAP_MODE_ENV, "deadline-pipe")
        .env(MANAGED_ZOMBIE_ROOT_ENV, &root)
        .env(MANAGED_ZOMBIE_DEADLINE_ENV, deadline_ns.to_string())
        .env(MANAGED_PIPE_SENTINEL_GROUP_ENV, sentinel_group.to_string());
    let reaper_child = command.spawn().expect("start fixture-owned subreaper");
    let reaper_pid = reaper_child.id() as i32;
    let mut reaper = ManagedZombieReaperGuard {
        root: root.clone(),
        child: reaper_child,
        launched: false,
        deadline,
    };
    let reaper_ready = fixture.path("reaper-ready");
    let host_ready = fixture.path("host-ready");
    while (!reaper_ready.exists() || !host_ready.exists()) && Instant::now() < deadline {
        assert!(reaper.child.try_wait().unwrap().is_none(), "fixture subreaper exited before readiness");
        std::thread::sleep(Duration::from_millis(5));
    }
    assert!(reaper_ready.exists() && host_ready.exists(), "subreaper/Engine host readiness exceeded watchdog");
    let reaper_receipt = std::fs::read_to_string(&reaper_ready).unwrap();
    let reaper_start = managed_zombie_u64(&reaper_receipt, "start").expect("subreaper start time");
    let host_receipt = std::fs::read_to_string(&host_ready).unwrap();
    let host_pid = managed_record_fields(&host_receipt)["pid"];
    let host_start = managed_zombie_u64(&host_receipt, "start").expect("host start time");
    assert!(matches!(managed_proc_identity(reaper_pid), Some((state, parent, _, start)) if state != 'Z' && parent == std::process::id() as i32 && start == reaper_start));
    assert!(matches!(managed_proc_identity(host_pid), Some((state, parent, _, start)) if state != 'Z' && parent == reaper_pid && start == host_start));
    reaper.launched = true;
    std::fs::write(fixture.path("begin-run"), b"start escaped-pipe deadline fixture\n").unwrap();

    let readiness_deadline = Instant::now() + Duration::from_secs(4);
    while (!fixture.path("leader-record").exists() || !fixture.path("holder-record").exists()) && Instant::now() < readiness_deadline {
        std::thread::sleep(Duration::from_millis(2));
    }
    let leader_text = std::fs::read_to_string(fixture.path("leader-record")).expect("escaped-pipe leader record");
    let holder_text = std::fs::read_to_string(fixture.path("holder-record")).expect("escaped-pipe holder record");
    let leader_fields = managed_record_fields(&leader_text);
    let holder_fields = managed_record_fields(&holder_text);
    let leader_pid = leader_fields["pid"];
    let leader_group = leader_fields["pgid"];
    let leader_start = managed_zombie_u64(&leader_text, "start").expect("leader start time");
    let holder_pid = holder_fields["pid"];
    let holder_group = holder_fields["pgid"];
    let holder_start = managed_zombie_u64(&holder_text, "start").expect("holder start time");
    assert_eq!(leader_pid, leader_group, "managed leader must own its group");
    assert_eq!(leader_fields.get("holder"), Some(&holder_pid));
    assert_eq!(managed_zombie_u64(&leader_text, "holder_start"), Some(holder_start));
    assert_eq!(holder_group, sentinel_group, "holder must live in the fixture sentinel's group");
    assert_ne!(holder_group, leader_group, "holder must escape the managed group");
    let (leader_pidfd, acquired_leader_start) = acquire_managed_pidfd_for_exact_parent_group(leader_pid, host_pid, leader_group);
    let (holder_pidfd, acquired_holder_start) = acquire_managed_pidfd_for_exact_parent_group(holder_pid, leader_pid, holder_group);
    let pidfds = ManagedPidfds(vec![(leader_pid, leader_pidfd, acquired_leader_start), (holder_pid, holder_pidfd, acquired_holder_start)]);
    let leader_pidfd = pidfds.0[0].1;
    let holder_pidfd = pidfds.0[1].1;
    assert_eq!((leader_start, holder_start), (acquired_leader_start, acquired_holder_start));
    std::fs::write(
        fixture.path("escaped-pipe-pidfd-identities"),
        format!("leader={leader_pid} leader_start={leader_start} leader_group={leader_group} holder={holder_pid} holder_start={holder_start} holder_group={holder_group} sentinel={sentinel_pid} sentinel_start={sentinel_start} sentinel_group={sentinel_group}\n"),
    )
    .unwrap();

    let normal_observation_deadline = deadline.checked_sub(Duration::from_secs(8)).unwrap_or(deadline);
    let api_path = fixture.path("api-result");
    while !api_path.exists() && Instant::now() < normal_observation_deadline {
        assert!(!fixture.path("exceptional-cleanup-started").exists(), "fixture watchdog started before the API boundary");
        std::thread::sleep(Duration::from_millis(2));
    }
    let api_result = std::fs::read_to_string(&api_path).unwrap_or_default();
    let timeout_report = api_result.contains("api_success=true api_outcome=timeout_report success=Some(false) timed_out=Some(true)");
    let partial_capture = api_result.contains("stdout_complete=Some(false) stderr_complete=Some(false) stdout_marker=true stderr_marker=true");
    let api_for_host = api_result.contains(&format!("host={host_pid} host_start={host_start}"));
    let leader_live = matches!(managed_proc_identity(leader_pid), Some((state, _, group, start)) if state != 'Z' && group == leader_group && start == leader_start);
    let holder_boundary = matches!(managed_proc_identity(holder_pid), Some((state, parent, group, start)) if state != 'Z' && parent == reaper_pid && group == holder_group && start == holder_start);
    let host_live = matches!(managed_proc_identity(host_pid), Some((state, parent, _, start)) if state != 'Z' && parent == reaper_pid && start == host_start);
    let reaper_live = matches!(managed_proc_identity(reaper_pid), Some((state, parent, _, start)) if state != 'Z' && parent == std::process::id() as i32 && start == reaper_start);
    let sentinel_live = matches!(managed_proc_identity(sentinel_pid), Some((state, parent, group, start)) if state != 'Z' && parent == std::process::id() as i32 && group == sentinel_group && start == sentinel_start);
    let pidfd_is_live = |fd: i32| {
        let mut pollfd = libc::pollfd { fd, events: libc::POLLIN, revents: 0 };
        (unsafe { libc::poll(&mut pollfd, 1, 0) }) == 0
    };
    let leader_pidfd_exited = {
        let mut pollfd = libc::pollfd { fd: leader_pidfd, events: libc::POLLIN, revents: 0 };
        (unsafe { libc::poll(&mut pollfd, 1, 0) }) == 1 && pollfd.revents & libc::POLLIN != 0
    };
    let holder_pidfd_live = pidfd_is_live(holder_pidfd);
    let group_probe = unsafe { libc::kill(-leader_group, 0) };
    let group_errno = if group_probe < 0 { std::io::Error::last_os_error().raw_os_error().unwrap_or(0) } else { 0 };
    let no_watchdog = !fixture.path("exceptional-cleanup-started").exists();
    let boundary = format!("host={host_pid} host_start={host_start} reaper={reaper_pid} reaper_start={reaper_start} leader={leader_pid} leader_start={leader_start} leader_live={leader_live} leader_pidfd_exited={leader_pidfd_exited} managed_group={leader_group} group_probe={group_probe} group_errno={group_errno} holder={holder_pid} holder_start={holder_start} holder_group={holder_group} holder_live={holder_boundary} holder_pidfd_live={holder_pidfd_live} host_live={host_live} reaper_live={reaper_live} sentinel={sentinel_pid} sentinel_start={sentinel_start} sentinel_group={sentinel_group} sentinel_live={sentinel_live} timeout_report={timeout_report} partial_capture={partial_capture} no_watchdog={no_watchdog}\n");
    std::fs::write(fixture.path("api-boundary"), &boundary).unwrap();

    std::fs::write(fixture.path("holder-challenge"), b"probe after timeout return\n").unwrap();
    let challenge_deadline = (Instant::now() + Duration::from_secs(2)).min(normal_observation_deadline);
    while !fixture.path("holder-ack").exists() && Instant::now() < challenge_deadline {
        assert!(!fixture.path("exceptional-cleanup-started").exists(), "fixture watchdog started before the escaped-pipe challenge");
        std::thread::sleep(Duration::from_millis(2));
    }
    let ack = std::fs::read_to_string(fixture.path("holder-ack")).unwrap_or_default();
    let no_watchdog_through_challenge = !fixture.path("exceptional-cleanup-started").exists();
    let holder_fields = managed_record_fields(&ack);
    let epiprobe = holder_fields.get("pid") == Some(&holder_pid) && holder_fields.get("stdout_result") == Some(&-1) && holder_fields.get("stdout_error") == Some(&libc::EPIPE) && holder_fields.get("stderr_result") == Some(&-1) && holder_fields.get("stderr_error") == Some(&libc::EPIPE);
    std::fs::write(fixture.path("holder-release"), b"release exact escaped holder\n").unwrap();
    std::fs::write(fixture.path("release-leader"), b"release if still running\n").unwrap();
    std::fs::write(fixture.path("host-exit-release"), b"API boundary and challenge recorded\n").unwrap();
    let cleanup_deadline = deadline.checked_sub(Duration::from_secs(2)).unwrap_or(deadline);
    while !fixture.path("escaped-holder-reaped").exists() && Instant::now() < cleanup_deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
    let holder_reap = std::fs::read_to_string(fixture.path("escaped-holder-reaped")).unwrap_or_default();
    let reaper_status = loop {
        match reaper.child.try_wait().expect("observe exact fixture subreaper") {
            Some(status) => break Some(status),
            None if Instant::now() < cleanup_deadline => std::thread::sleep(Duration::from_millis(5)),
            None => break None,
        }
    };
    let reaper_cleanup = if reaper_status.as_ref().is_some_and(|status| status.success()) {
        std::fs::read_to_string(fixture.path("reaper-cleanup")).unwrap_or_default()
    } else {
        String::new()
    };
    let holder_reaped_exactly = holder_reap.contains(&format!("holder={holder_pid} start={holder_start} pgid={holder_group} reaped=true"));
    let identity_absent = |pid, expected_start| match managed_proc_identity_checked(pid) {
        Ok(None) => (true, "not found".to_owned()),
        Ok(Some((_, _, _, actual_start))) if actual_start != expected_start => (true, format!("PID reused at start={actual_start}")),
        Ok(Some(identity)) => (false, format!("same start still visible: {identity:?}")),
        Err(error) => (false, format!("identity read failed: {error}")),
    };
    let (host_absent, host_absence) = identity_absent(host_pid, host_start);
    let (leader_absent, leader_absence) = identity_absent(leader_pid, leader_start);
    let (holder_absent, holder_absence) = identity_absent(holder_pid, holder_start);
    let reaper_ok = reaper_status.as_ref().is_some_and(|status| status.success()) && reaper_cleanup.contains("complete=true");
    drop(sentinel);
    let (sentinel_absent, sentinel_absence) = identity_absent(sentinel_pid, sentinel_start);
    let sentinel_group_probe = unsafe { libc::kill(-sentinel_group, 0) };
    let sentinel_group_errno = if sentinel_group_probe < 0 { std::io::Error::last_os_error().raw_os_error().unwrap_or(0) } else { 0 };
    eprintln!("managed_deadline_escaped_pipe_boundary {boundary} api={api_result:?} challenge={ack:?} no_watchdog_through_challenge={no_watchdog_through_challenge} holder_reap={holder_reap:?} reaper_cleanup={reaper_cleanup:?} reaper_ok={reaper_ok} host_absent={host_absent} host_absence={host_absence:?} leader_absent={leader_absent} leader_absence={leader_absence:?} holder_absent={holder_absent} holder_absence={holder_absence:?} sentinel_absent={sentinel_absent} sentinel_absence={sentinel_absence:?} sentinel_group_probe={sentinel_group_probe} sentinel_group_errno={sentinel_group_errno}");

    assert!(reaper_ok, "fixture subreaper did not complete exact holder cleanup: {reaper_cleanup}");
    assert!(host_absent && leader_absent && holder_absent && sentinel_absent, "an exact fixture identity remained live after cleanup: {boundary}");
    assert!(sentinel_group_probe == -1 && sentinel_group_errno == libc::ESRCH, "sentinel group remained after exact sentinel cleanup");
    assert!(api_for_host, "timeout report belonged to an unexpected Engine host: {api_result}");
    assert!(timeout_report && partial_capture, "managed run must return its bounded deadline report with partial incomplete captures: {api_result}");
    assert!(!leader_live && leader_pidfd_exited && group_probe == -1 && group_errno == libc::ESRCH, "deadline did not close the exact managed group: {boundary}");
    assert!(
        holder_boundary && holder_pidfd_live && host_live && reaper_live && sentinel_live && no_watchdog && no_watchdog_through_challenge,
        "escaped holder custody/live boundary was invalid: {boundary}"
    );
    assert!(epiprobe, "escaped holder did not observe EPIPE on both closed capture writers after return: {ack}");
    assert!(holder_reaped_exactly, "fixture reaper did not exact-wait the escaped holder: {holder_reap}");
}

/// A managed output cap preserves the configured prefix and closes its full process group.
#[test]
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_run_output_limit_reaps_group_under_fixture_reaper() {
    const WATCHDOG: Duration = Duration::from_secs(20);
    const CAP: usize = 4096;
    let fixture = ManagedFixture::new();
    let root = fixture.root.path().to_path_buf();
    let deadline_ns = managed_zombie_monotonic_ns() + WATCHDOG.as_nanos() as u64;
    let deadline = Instant::now() + WATCHDOG;
    let mut sentinel = Sentinel(
        Command::new("/bin/sleep")
            .arg("30")
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("start unrelated sentinel"),
    );
    let sentinel_pid = sentinel.0.id() as i32;
    let sentinel_start = managed_proc_identity(sentinel_pid).expect("read unrelated sentinel identity").3;
    let mut command = Command::new(std::env::current_exe().expect("test executable"));
    command
        .args(["--exact", "process_fixture", "--nocapture", "--quiet"])
        .env_clear()
        .env(MANAGED_ZOMBIE_ROLE_ENV, "reaper")
        .env(MANAGED_ZOMBIE_REAP_MODE_ENV, "output-limit")
        .env(MANAGED_ZOMBIE_ROOT_ENV, &root)
        .env(MANAGED_ZOMBIE_DEADLINE_ENV, deadline_ns.to_string());
    let reaper_child = command.spawn().expect("start fixture-owned reaper");
    let reaper_pid = reaper_child.id() as i32;
    let mut reaper = ManagedZombieReaperGuard {
        root: root.clone(),
        child: reaper_child,
        launched: false,
        deadline,
    };
    let reaper_ready = fixture.path("reaper-ready");
    let host_ready = fixture.path("host-ready");
    while (!reaper_ready.exists() || !host_ready.exists()) && Instant::now() < deadline {
        assert!(reaper.child.try_wait().unwrap().is_none(), "fixture reaper exited before readiness");
        std::thread::sleep(Duration::from_millis(5));
    }
    assert!(reaper_ready.exists() && host_ready.exists(), "reaper/host readiness exceeded watchdog");
    let reaper_receipt = std::fs::read_to_string(&reaper_ready).unwrap();
    let reaper_fields = managed_record_fields(&reaper_receipt);
    let host_receipt = std::fs::read_to_string(host_ready).unwrap();
    let host_fields = managed_record_fields(&host_receipt);
    let host_pid = host_fields["pid"];
    let Some((_, host_parent, _, host_start)) = managed_proc_identity(host_pid) else { panic!("host identity unavailable before begin") };
    let Some((_, reaper_parent, _, reaper_start)) = managed_proc_identity(reaper_pid) else { panic!("reaper identity unavailable before begin") };
    assert_eq!(reaper_fields.get("pid"), Some(&reaper_pid));
    assert_eq!(managed_zombie_u64(&host_receipt, "start"), Some(host_start));
    assert_eq!(managed_zombie_u64(&reaper_receipt, "start"), Some(reaper_start));
    assert_eq!((host_parent, reaper_parent), (reaper_pid, std::process::id() as i32));
    reaper.launched = true;
    std::fs::write(fixture.path("begin-run"), b"begin output-limit fixture\n").unwrap();

    let pidfds = acquire_managed_pidfds(root.clone(), host_pid);
    let leader = std::fs::read_to_string(fixture.path("leader-record")).unwrap();
    let worker = std::fs::read_to_string(fixture.path("worker-record")).unwrap();
    let leaf = std::fs::read_to_string(fixture.path("leaf-record")).unwrap();
    let leader_fields = managed_record_fields(&leader);
    let worker_fields = managed_record_fields(&worker);
    let leaf_fields = managed_record_fields(&leaf);
    let identity = |pid: i32| pidfds.0.iter().find(|member| member.0 == pid).map(|member| member.2).expect("PIDFD start identity");
    let leader_start = identity(leader_fields["pid"]);
    let worker_start = identity(worker_fields["pid"]);
    let leaf_start = identity(leaf_fields["pid"]);
    let group = leader_fields["pgid"];
    assert_eq!((worker_fields["pgid"], leaf_fields["pgid"]), (group, group), "all fixture members must share the managed process group");
    std::fs::write(fixture.path("pidfd-identities"), format!("leader_start={leader_start} worker_start={worker_start} leaf_start={leaf_start} pgid={group}\n")).unwrap();
    std::fs::write(fixture.path("pidfd-ack"), b"observer holds exact live pidfds\n").unwrap();

    let observation_deadline = deadline.checked_sub(Duration::from_secs(8)).unwrap_or(deadline);
    let api_path = fixture.path("api-result");
    while !api_path.exists() && Instant::now() < observation_deadline {
        std::thread::sleep(Duration::from_millis(2));
    }
    let api_result = std::fs::read_to_string(&api_path).unwrap_or_default();
    let api_is_output_limit = api_result.contains("api_success=false api_outcome=typed_output_limit");
    let api_belongs_to_host = api_result.contains(&format!("host={host_pid} host_start={host_start}"));
    let prefix_preserved = api_result.contains(&format!("stdout_len={CAP} stdout_prefix_exact=true"));
    let captures_honest = api_result.contains("stdout_complete=false") && api_result.contains("stderr_complete=false") && api_result.contains("timed_out=false");
    let no_watchdog_cleanup_at_return = !fixture.path("exceptional-cleanup-started").exists();
    let cleanup_path = fixture.path("prompt-reaper-cleanup");
    while !cleanup_path.exists() && Instant::now() < observation_deadline {
        std::thread::sleep(Duration::from_millis(2));
    }
    let cleanup_text = std::fs::read_to_string(cleanup_path).unwrap_or_default();
    let absent_or_reused = |pid, expected_start| match managed_proc_identity_checked(pid).expect("read exact managed member identity after OutputLimit") {
        None => true,
        Some(identity) => identity.3 != expected_start,
    };
    let leader_absent = absent_or_reused(leader_fields["pid"], leader_start);
    let worker_absent = absent_or_reused(worker_fields["pid"], worker_start);
    let leaf_absent = absent_or_reused(leaf_fields["pid"], leaf_start);
    let pidfds_exited = pidfds.0.iter().all(|(pid, fd, start)| {
        let mut pollfd = libc::pollfd { fd: *fd, events: libc::POLLIN, revents: 0 };
        (unsafe { libc::poll(&mut pollfd, 1, 0) }) == 1 && pollfd.revents & libc::POLLIN != 0 && absent_or_reused(*pid, *start)
    });
    let host_live_at_return = matches!(managed_proc_identity_checked(host_pid).expect("read host identity at OutputLimit return"), Some((state, parent, _, start)) if state != 'Z' && parent == reaper_pid && start == host_start);
    let reaper_live_at_return = matches!(managed_proc_identity_checked(reaper_pid).expect("read reaper identity at OutputLimit return"), Some((state, parent, _, start)) if state != 'Z' && parent == std::process::id() as i32 && start == reaper_start);
    let sentinel_live_at_return = matches!(managed_proc_identity_checked(sentinel_pid).expect("read sentinel identity at OutputLimit return"), Some((state, parent, _, start)) if state != 'Z' && parent == std::process::id() as i32 && start == sentinel_start);
    let group_probe = unsafe { libc::kill(-group, 0) };
    let group_errno = if group_probe == -1 { std::io::Error::last_os_error().raw_os_error().unwrap_or(0) } else { 0 };
    let cleanup_exact = cleanup_text.contains(&format!("worker={} start={worker_start} pgid={group} reaped=true wait_status=", worker_fields["pid"]))
        && cleanup_text.contains(&format!("leaf={} start={leaf_start} pgid={group} reaped=true wait_status=", leaf_fields["pid"]))
        && cleanup_text.contains("complete=true");
    let no_watchdog_cleanup_through_boundary = no_watchdog_cleanup_at_return && !fixture.path("exceptional-cleanup-started").exists();
    let boundary = format!("host={host_pid} host_start={host_start} reaper={reaper_pid} reaper_start={reaper_start} leader={} leader_start={leader_start} leader_absent={leader_absent} worker={} worker_start={worker_start} worker_absent={worker_absent} leaf={} leaf_start={leaf_start} leaf_absent={leaf_absent} group={group} group_probe={group_probe} group_errno={group_errno} host_live={host_live_at_return} reaper_live={reaper_live_at_return} sentinel={sentinel_pid} sentinel_start={sentinel_start} sentinel_live={sentinel_live_at_return} output_limit={api_is_output_limit} prefix_preserved={prefix_preserved} captures_honest={captures_honest} pidfds_exited={pidfds_exited} cleanup_exact={cleanup_exact} no_watchdog_cleanup_through_boundary={no_watchdog_cleanup_through_boundary}\n", leader_fields["pid"], worker_fields["pid"], leaf_fields["pid"]);
    std::fs::write(fixture.path("api-boundary"), &boundary).unwrap();
    std::fs::write(fixture.path("host-exit-release"), b"output-limit boundary recorded\n").unwrap();
    std::fs::write(fixture.path("reap-release"), b"output-limit closure recorded\n").unwrap();
    let mut reaper_status = None;
    while reaper_status.is_none() && Instant::now() < observation_deadline {
        reaper_status = reaper.child.try_wait().expect("observe exact fixture reaper");
        if reaper_status.is_none() {
            std::thread::sleep(Duration::from_millis(5));
        }
    }
    let reaper_ok = reaper_status.is_some_and(|status| status.success());
    let no_watchdog_cleanup_after_reap = !fixture.path("exceptional-cleanup-started").exists();
    drop(sentinel);
    let sentinel_reaped = pid_is_absent(sentinel_pid);
    eprintln!("managed_output_limit_group_boundary {boundary} api={api_result:?} cleanup={cleanup_text:?} reaper_ok={reaper_ok} sentinel_reaped={sentinel_reaped} no_watchdog_cleanup_after_reap={no_watchdog_cleanup_after_reap}");

    assert!(reaper_ok, "fixture reaper failed its bounded exact cleanup");
    assert!(no_watchdog_cleanup_through_boundary && no_watchdog_cleanup_after_reap, "fixture watchdog cleanup participated in output-limit closure observation");
    assert!(api_belongs_to_host, "output-limit result belongs to an unexpected Engine host: {api_result}");
    assert!(api_is_output_limit, "managed public run did not return an OutputLimit process result: {api_result}");
    assert!(prefix_preserved, "managed OutputLimit did not preserve exactly the configured stdout prefix: {api_result}");
    assert!(captures_honest, "managed OutputLimit must report both still-open captures as incomplete: {api_result}");
    assert!(leader_absent && worker_absent && leaf_absent && pidfds_exited, "managed member identity remained live after output-limit cleanup: {boundary}");
    assert!(group_probe == -1 && group_errno == libc::ESRCH, "original managed group remained present after OutputLimit closure: {boundary}");
    assert!(host_live_at_return && reaper_live_at_return && sentinel_live_at_return && sentinel_reaped, "host/reaper/sentinel custody boundary was invalid: {boundary}");
    assert!(cleanup_exact, "fixture reaper did not independently wait for exact worker and leaf identities: {cleanup_text}");
}

/// A fixture-owned subreaper reaps only the exact stopped descendants before the managed run
/// publishes success, while the separate Engine host remains alive for independent readback.
#[test]
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_run_succeeds_after_fixture_reaper_reaps_descendants() {
    const WATCHDOG: Duration = Duration::from_secs(20);
    let fixture = ManagedFixture::new();
    let root = fixture.root.path().to_path_buf();
    let deadline_ns = managed_zombie_monotonic_ns() + WATCHDOG.as_nanos() as u64;
    let deadline = Instant::now() + WATCHDOG;
    let mut sentinel = Sentinel(
        Command::new("/bin/sleep")
            .arg("30")
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("start unrelated sentinel"),
    );
    let sentinel_pid = sentinel.0.id() as i32;
    let sentinel_start = managed_proc_identity(sentinel_pid).expect("read unrelated sentinel identity").3;
    let mut command = Command::new(std::env::current_exe().expect("test executable"));
    command
        .args(["--exact", "process_fixture", "--nocapture", "--quiet"])
        .env_clear()
        .env(MANAGED_ZOMBIE_ROLE_ENV, "reaper")
        .env("RHAI_SYS_MANAGED_ZOMBIE_REAP_MODE", "prompt")
        .env(MANAGED_ZOMBIE_ROOT_ENV, &root)
        .env(MANAGED_ZOMBIE_DEADLINE_ENV, deadline_ns.to_string());
    let reaper = command.spawn().expect("start fixture-owned reaper");
    let reaper_pid = reaper.id() as i32;
    let mut reaper = ManagedZombieReaperGuard {
        root: root.clone(),
        child: reaper,
        launched: false,
        deadline,
    };
    let reaper_ready = fixture.path("reaper-ready");
    let host_ready = fixture.path("host-ready");
    while (!reaper_ready.exists() || !host_ready.exists()) && Instant::now() < deadline {
        assert!(reaper.child.try_wait().unwrap().is_none(), "fixture reaper exited before readiness");
        std::thread::sleep(Duration::from_millis(5));
    }
    assert!(reaper_ready.exists() && host_ready.exists(), "reaper/host readiness exceeded fixture watchdog");
    let reaper_receipt = std::fs::read_to_string(reaper_ready).unwrap();
    let host_receipt = std::fs::read_to_string(host_ready).unwrap();
    let reaper_fields = managed_record_fields(&reaper_receipt);
    let host_fields = managed_record_fields(&host_receipt);
    let host_pid = *host_fields.get("pid").expect("host PID receipt");
    assert_eq!(reaper_fields.get("pid"), Some(&reaper_pid), "reaper PID receipt must match owned child");
    let Some((_, host_parent, _, host_start)) = managed_proc_identity(host_pid) else { panic!("host identity unavailable before begin") };
    let Some((_, reaper_parent, _, reaper_start)) = managed_proc_identity(reaper_pid) else { panic!("reaper identity unavailable before begin") };
    assert_eq!(host_parent, reaper_pid, "Engine host must be a direct child of fixture reaper");
    assert_eq!(reaper_parent, std::process::id() as i32, "reaper must be owned by outer test");
    assert_eq!(managed_zombie_u64(&host_receipt, "start"), Some(host_start));
    assert_eq!(managed_zombie_u64(&reaper_receipt, "start"), Some(reaper_start));
    reaper.launched = true;
    std::fs::write(fixture.path("begin-run"), b"begin\n").unwrap();

    let pidfds = acquire_managed_pidfds(root.clone(), host_pid);
    let leader = std::fs::read_to_string(fixture.path("leader-record")).unwrap();
    let worker = std::fs::read_to_string(fixture.path("worker-record")).unwrap();
    let leaf = std::fs::read_to_string(fixture.path("leaf-record")).unwrap();
    let leader_fields = managed_record_fields(&leader);
    let worker_fields = managed_record_fields(&worker);
    let leaf_fields = managed_record_fields(&leaf);
    let leader_start = pidfds.0.iter().find(|member| member.0 == leader_fields["pid"]).unwrap().2;
    let worker_start = pidfds.0.iter().find(|member| member.0 == worker_fields["pid"]).unwrap().2;
    let leaf_start = pidfds.0.iter().find(|member| member.0 == leaf_fields["pid"]).unwrap().2;
    std::fs::write(fixture.path("pidfd-identities"), format!("leader_start={leader_start} worker_start={worker_start} leaf_start={leaf_start} pgid={}\n", leader_fields["pgid"])).unwrap();
    eprintln!("managed_prompt_reap_live_boundary reaper={reaper_pid} reaper_start={reaper_start} host={host_pid} host_start={host_start} leader={} leader_start={leader_start} worker={} worker_start={worker_start} leaf={} leaf_start={leaf_start} group={} sentinel={sentinel_pid} sentinel_start={sentinel_start}", leader_fields["pid"], worker_fields["pid"], leaf_fields["pid"], leader_fields["pgid"]);
    std::fs::write(fixture.path("pidfd-ack"), b"observer holds exact live pidfds\n").unwrap();

    let api_result_path = fixture.path("api-result");
    while !api_result_path.exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(2));
    }
    assert!(api_result_path.exists(), "Engine host did not publish API result in watchdog");
    let api_result = std::fs::read_to_string(api_result_path).unwrap();
    assert!(api_result.contains(&format!("host={host_pid} host_start={host_start}")), "API result belongs to unexpected host: {api_result}");
    let api_exit_zero_at_return = api_result.contains("api_success=true api_outcome=success_report code=0 exit=Some(0)");
    assert!(api_exit_zero_at_return, "managed run must return a successful zero-exit report after exact foreign reaping: {api_result}");
    let captures_complete_at_return = api_result.contains("stdout_complete=true stderr_complete=true");
    assert!(captures_complete_at_return, "successful result must preserve complete captures: {api_result}");
    assert_managed_pidfds_exited(&pidfds);

    for (label, fields, expected_start) in [("leader", &leader_fields, leader_start), ("worker", &worker_fields, worker_start), ("leaf", &leaf_fields, leaf_start)] {
        let pid = fields["pid"];
        assert!(managed_proc_identity(pid).is_none(), "{label} pid={pid} start={expected_start} must be absent at API return");
    }
    let host_now = managed_proc_identity(host_pid).expect("Engine host remains live while parent verifies closure");
    assert_ne!(host_now.0, 'Z', "Engine host exited before independent closure readback");
    assert_eq!((host_now.1, host_now.3), (reaper_pid, host_start), "Engine host identity or parent changed");
    let reaper_now = managed_proc_identity(reaper_pid).expect("fixture reaper remains live through API boundary");
    assert_eq!((reaper_now.1, reaper_now.3), (std::process::id() as i32, reaper_start), "fixture reaper identity or parent changed");
    let reaped = std::fs::read_to_string(fixture.path("prompt-reaper-cleanup")).expect("prompt reaper cleanup receipt");
    for (label, fields, start) in [("worker", &worker_fields, worker_start), ("leaf", &leaf_fields, leaf_start)] {
        assert!(reaped.contains(&format!("{label}={} start={start} pgid={} reaped=true", fields["pid"], leader_fields["pgid"])), "reaper did not prove exact {label} wait: {reaped}");
    }
    let sentinel_live_at_return = matches!(
        managed_proc_identity(sentinel_pid),
        Some((state, parent, _, start)) if state != 'Z' && parent == std::process::id() as i32 && start == sentinel_start
    );
    assert!(sentinel_live_at_return, "managed group cleanup terminated or replaced the unrelated sentinel");
    std::fs::write(fixture.path("host-exit-release"), b"API success and exact closure recorded\n").unwrap();
    let observation_deadline = deadline.checked_sub(Duration::from_secs(2)).unwrap_or(deadline);
    let mut status = None;
    while status.is_none() && Instant::now() < observation_deadline {
        status = reaper.child.try_wait().expect("observe exact fixture reaper");
        if status.is_none() {
            std::thread::sleep(Duration::from_millis(5));
        }
    }
    assert!(status.is_some_and(|status| status.success()), "fixture reaper did not finish exact cleanup");
    drop(sentinel);
    assert!(pid_is_absent(sentinel_pid), "fixture-owned sentinel cleanup must reap its exact child");
    eprintln!("managed_prompt_reap_success host={host_pid} host_start={host_start} leader={} leader_start={leader_start} leader_absent=true worker={} worker_start={worker_start} worker_absent=true leaf={} leaf_start={leaf_start} leaf_absent=true sentinel={sentinel_pid} sentinel_start={sentinel_start} sentinel_live_at_return={sentinel_live_at_return} sentinel_reaped_after_return=true api_exit_zero_at_return={api_exit_zero_at_return} captures_complete_at_return={captures_complete_at_return} api={api_result} cleanup={reaped:?}", leader_fields["pid"], worker_fields["pid"], leaf_fields["pid"]);
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn acquire_managed_pidfds(root: std::path::PathBuf, runner_pid: i32) -> ManagedPidfds {
    let deadline = Instant::now() + Duration::from_secs(5);
    loop {
        let leader_path = root.join("leader-record");
        let worker_path = root.join("worker-record");
        let leaf_path = root.join("leaf-record");
        if leader_path.exists() && worker_path.exists() && leaf_path.exists() {
            let leader = managed_record_fields(&std::fs::read_to_string(leader_path).unwrap());
            let worker = managed_record_fields(&std::fs::read_to_string(worker_path).unwrap());
            let leaf = managed_record_fields(&std::fs::read_to_string(leaf_path).unwrap());
            let leader_pid = leader["pid"];
            let worker_pid = worker["pid"];
            let leaf_pid = leaf["pid"];
            let group = leader["pgid"];
            let identities = [(leader_pid, runner_pid), (worker_pid, leader_pid), (leaf_pid, worker_pid)];
            let mut held = Vec::new();
            let mut ready = true;
            for (pid, expected_parent) in identities {
                let Some((state, parent, pgid, start)) = managed_proc_identity(pid) else {
                    ready = false;
                    break;
                };
                if state == 'Z' || pgid != group || parent != expected_parent {
                    ready = false;
                    break;
                }
                let fd = unsafe { libc::syscall(libc::SYS_pidfd_open, pid, 0) as i32 };
                if fd < 0 {
                    ready = false;
                    break;
                }
                match managed_proc_identity(pid) {
                    Some((after, after_parent, after_group, after_start)) if after != 'Z' && after_parent == parent && after_group == pgid && after_start == start => {
                        eprintln!("managed_pidfd_acquired pid={pid} start={start} ppid={parent} pgid={pgid}");
                        held.push((pid, fd, start));
                    }
                    _ => {
                        unsafe { libc::close(fd) };
                        ready = false;
                        break;
                    }
                }
            }
            if ready && held.len() == identities.len() {
                return ManagedPidfds(held);
            }
            for (_, fd, _) in held {
                unsafe { libc::close(fd) };
            }
        }
        assert!(Instant::now() < deadline, "fixture members were not simultaneously live for pidfd acquisition");
        std::thread::sleep(Duration::from_millis(2));
    }
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn assert_managed_pidfds_exited(pidfds: &ManagedPidfds) {
    for (pid, fd, start) in &pidfds.0 {
        let mut pollfd = libc::pollfd { fd: *fd, events: libc::POLLIN, revents: 0 };
        let result = unsafe { libc::poll(&mut pollfd, 1, 0) };
        assert_eq!(result, 1, "managed member pid={pid} start={start} remained live at API return");
        assert_ne!(pollfd.revents & libc::POLLIN, 0, "pidfd did not report process exit for pid={pid}");
    }
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn assert_managed_pidfd_exited(member: &(i32, i32, u64)) {
    let (pid, fd, start) = member;
    let mut pollfd = libc::pollfd { fd: *fd, events: libc::POLLIN, revents: 0 };
    let result = unsafe { libc::poll(&mut pollfd, 1, 0) };
    assert_eq!(result, 1, "managed member pid={pid} start={start} had not exited at API return");
    assert_ne!(pollfd.revents & libc::POLLIN, 0, "pidfd did not report process exit for pid={pid}");
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn assert_managed_pidfds_live(pidfds: &ManagedPidfds) {
    for (pid, fd, start) in pidfds.0.iter().skip(1) {
        let mut pollfd = libc::pollfd { fd: *fd, events: libc::POLLIN, revents: 0 };
        let result = unsafe { libc::poll(&mut pollfd, 1, 0) };
        assert_eq!(result, 0, "control member pid={pid} start={start} unexpectedly exited before API return");
    }
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn acquire_managed_pidfd_for_exact_parent_group(pid: i32, expected_parent: i32, expected_group: i32) -> (i32, u64) {
    let deadline = Instant::now() + Duration::from_secs(4);
    loop {
        if let Some((state, parent, group, start)) = managed_proc_identity(pid) {
            if state != 'Z' && parent == expected_parent && group == expected_group {
                let fd = unsafe { libc::syscall(libc::SYS_pidfd_open, pid, 0) as i32 };
                if fd >= 0 {
                    if matches!(managed_proc_identity(pid), Some((current_state, current_parent, current_group, current_start)) if current_state != 'Z' && current_parent == expected_parent && current_group == expected_group && current_start == start) {
                        eprintln!("managed_pipe_pidfd_acquired pid={pid} start={start} ppid={expected_parent} pgid={expected_group}");
                        return (fd, start);
                    }
                    unsafe { libc::close(fd) };
                }
            }
        }
        assert!(Instant::now() < deadline, "escaped-pipe PID {pid} did not reach the exact live parent/group identity");
        std::thread::sleep(Duration::from_millis(2));
    }
}

/// Host-selected managed scope closes workers that outlive a successful leader without touching
/// an unrelated process in the runner's inherited group.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_run_closes_worker_after_leader_exit_and_preserves_sentinel() {
    let fixture = ManagedFixture::new();
    let mut sentinel = Sentinel(
        Command::new("/bin/sleep")
            .arg("30")
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("start unrelated sentinel"),
    );
    let sentinel_pid = sentinel.0.id() as i32;
    eprintln!("managed_fixture_started root={} test_pid={} sentinel_pid={sentinel_pid}", fixture.root.path().display(), std::process::id());
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let root = fixture.root.as_script_path();
    let worker_record = fixture.path("worker-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let leaf_record = fixture.path("leaf-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let release = fixture.path("release-worker").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let configured = SysConfig::default().programs(ProgramPolicy::AllowList(vec![executable.clone()])).process_scope(ProcessScope::Managed);
    let engine = engine(configured);
    let script = format!(
        r#"run("{executable}", ["--exact", "managed_scope_leader_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {MANAGED_FIXTURE_ENV}: "leader", {MANAGED_ROOT_ENV}: "{root}", {MANAGED_WORKER_ENV}: "{worker_record}", {MANAGED_LEAF_ENV}: "{leaf_record}", {MANAGED_RELEASE_ENV}: "{release}" }},
            timeout: 4.0
        }})"#
    );

    let result = engine.eval::<Map>(&script).unwrap_or_else(|error| {
        if let rhai::EvalAltResult::ErrorRuntime(value, _) = error.as_ref() {
            if let Some(SysError::Denied(message)) = value.clone().try_cast::<SysError>() {
                panic!("managed run returned SysError::Denied: {message}");
            }
        }
        let diagnostic = match error.as_ref() {
            rhai::EvalAltResult::ErrorRuntime(value, _) => match value.clone().try_cast::<SysError>() {
                Some(SysError::Process { cause, report }) => format!("SysError::Process cause={cause:?} report={report:?} cleanup_diagnostics={:?}", report.cleanup_diagnostics()),
                Some(other) => format!("SysError={other:?}"),
                None => format!("non-SysError runtime payload={value:?}"),
            },
            other => format!("non-runtime error={other:?}"),
        };
        panic!("managed run returned an unexpected error: {diagnostic}");
    });
    assert_eq!(result["success"].as_bool().unwrap(), true);
    assert_eq!(result["code"].as_int().unwrap(), 0);
    assert_eq!(result["timed_out"].as_bool().unwrap(), false);
    assert_eq!(result["stdout_complete"].as_bool().unwrap(), true);
    assert_eq!(result["stderr_complete"].as_bool().unwrap(), true);

    let leader = std::fs::read_to_string(fixture.path("leader-record")).unwrap();
    let worker = std::fs::read_to_string(fixture.path("worker-record")).unwrap();
    let leaf = std::fs::read_to_string(fixture.path("leaf-record")).unwrap();
    let leader = managed_record_fields(&leader);
    let worker = managed_record_fields(&worker);
    let leaf = managed_record_fields(&leaf);
    let leader_gone = pid_is_absent(*leader.get("pid").unwrap());
    let worker_gone = pid_is_absent(*worker.get("pid").unwrap());
    let leaf_gone = pid_is_absent(*leaf.get("pid").unwrap());
    let sentinel_live = sentinel.0.try_wait().unwrap().is_none();
    eprintln!("managed_normal_leader pid={} pgid={} esrch={leader_gone}", leader["pid"], leader["pgid"]);
    eprintln!("managed_normal_worker_leaf worker_pid={} worker_esrch={worker_gone} leaf_pid={} leaf_esrch={leaf_gone}", worker["pid"], leaf["pid"]);
    eprintln!("managed_normal_sentinel pid={sentinel_pid} live={sentinel_live}");
    assert_eq!(leader.get("pgid"), leader.get("pid"), "leader must own a new process group");
    assert_eq!(worker.get("pgid"), leader.get("pgid"), "worker must inherit managed group");
    assert_eq!(leaf.get("pgid"), leader.get("pgid"), "grandchild must inherit managed group");
    assert_eq!(leader.get("worker"), worker.get("pid"), "leader and worker receipts must identify the same child");
    assert_eq!(leader.get("leaf"), leaf.get("pid"), "leader receipt must identify the same grandchild");
    assert!(leader_gone, "leader must be reaped before run returns");
    assert!(worker_gone, "managed worker must be gone before run returns");
    assert!(leaf_gone, "managed grandchild must be gone before run returns");
    assert!(sentinel_live, "managed cleanup terminated unrelated sentinel");
    drop(sentinel);
    assert!(pid_is_absent(sentinel_pid), "fixture-owned sentinel cleanup must reap its exact child");
}

/// Pipe closure cannot stand in for member termination: the worker deliberately redirects its
/// captured descriptors, while this observer acquires exact PID/start-time pidfds before return.
#[test]
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn managed_run_closes_pipe_closed_worker_before_return() {
    let fixture = ManagedFixture::new();
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let root = fixture.root.as_script_path();
    let worker_record = fixture.path("worker-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let leaf_record = fixture.path("leaf-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let release = fixture.path("release-worker").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let ack = fixture.path("pidfd-ack");
    let observed = std::sync::Arc::new(std::sync::Mutex::new(None));
    let observer = std::thread::spawn({
        let root = fixture.root.path().to_path_buf();
        let runner_pid = std::process::id() as i32;
        let ack = ack.clone();
        let observed = observed.clone();
        move || {
            let pidfds = acquire_managed_pidfds(root, runner_pid);
            *observed.lock().unwrap() = Some(pidfds);
            std::fs::write(ack, "live identities validated and pidfds acquired\n").unwrap();
        }
    });
    let configured = SysConfig::default().programs(ProgramPolicy::AllowList(vec![executable.clone()])).process_scope(ProcessScope::Managed);
    let engine = engine(configured);
    let script = format!(
        r#"run("{executable}", ["--exact", "managed_scope_leader_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {MANAGED_FIXTURE_ENV}: "leader-closed-io", {MANAGED_ROOT_ENV}: "{root}", {MANAGED_WORKER_ENV}: "{worker_record}", {MANAGED_LEAF_ENV}: "{leaf_record}", {MANAGED_RELEASE_ENV}: "{release}", {MANAGED_PIDFD_ACK_ENV}: "{}" }},
            timeout: 4.0
        }})"#,
        ack.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"")
    );
    let result = engine.eval::<Map>(&script).unwrap_or_else(|error| {
        panic!("managed run with closed-pipe worker failed before scope closure: {error:?}");
    });
    assert_eq!(result["success"].as_bool().unwrap(), true);
    assert_eq!(result["code"].as_int().unwrap(), 0);
    let pidfds = observed.lock().unwrap().take().expect("live PIDfd proof was published before the fixture leader exited");
    assert_managed_pidfds_exited(&pidfds);
    observer.join().expect("PIDfd observer completed");
}

/// Direct scope is the omitted-group-termination control; pipe closure alone leaves both exact
/// recorded descendants live at API return.
#[test]
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn direct_run_returns_with_pipe_closed_worker_live_control() {
    let fixture = ManagedFixture::new();
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let root = fixture.root.as_script_path();
    let worker_record = fixture.path("worker-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let leaf_record = fixture.path("leaf-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let release = fixture.path("release-worker").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let ack = fixture.path("pidfd-ack");
    let observed = std::sync::Arc::new(std::sync::Mutex::new(None));
    let observer = std::thread::spawn({
        let root = fixture.root.path().to_path_buf();
        let runner_pid = std::process::id() as i32;
        let ack = ack.clone();
        let observed = observed.clone();
        move || {
            let pidfds = acquire_managed_pidfds(root, runner_pid);
            *observed.lock().unwrap() = Some(pidfds);
            std::fs::write(ack, "live identities validated and pidfds acquired\n").unwrap();
        }
    });
    let configured = SysConfig::default()
        .programs(ProgramPolicy::AllowList(vec![executable.clone()]))
        .process_scope(ProcessScope::DirectChild);
    let engine = engine(configured);
    let script = format!(
        r#"run("{executable}", ["--exact", "managed_scope_leader_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {MANAGED_FIXTURE_ENV}: "leader-closed-io", {MANAGED_ROOT_ENV}: "{root}", {MANAGED_WORKER_ENV}: "{worker_record}", {MANAGED_LEAF_ENV}: "{leaf_record}", {MANAGED_RELEASE_ENV}: "{release}", {MANAGED_PIDFD_ACK_ENV}: "{}" }},
            timeout: 4.0
        }})"#,
        ack.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"")
    );
    let result = engine.eval::<Map>(&script).expect("direct process run completes after captured pipes close");
    assert_eq!(result["success"].as_bool().unwrap(), true);
    let pidfds = observed.lock().unwrap().take().expect("live PIDfd proof was published before the fixture leader exited");
    assert_managed_pidfd_exited(&pidfds.0[0]);
    assert_managed_pidfds_live(&pidfds);
    observer.join().expect("PIDfd observer completed");
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
struct ManagedEscapeFixture {
    root: TempDir,
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
impl ManagedEscapeFixture {
    fn new() -> Self {
        Self { root: TempDir::new() }
    }

    fn path(&self, name: &str) -> std::path::PathBuf {
        self.root.path().join(name)
    }
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
impl Drop for ManagedEscapeFixture {
    fn drop(&mut self) {
        let _ = std::fs::write(self.path("release"), b"release\n");
        let record = std::fs::read_to_string(self.path("leader-record")).ok();
        let pid = record.as_deref().and_then(|value| managed_record_fields(value).get("pid").copied());
        let deadline = Instant::now() + Duration::from_secs(2);
        while pid.is_some_and(|pid| !pid_is_absent(pid)) && Instant::now() < deadline {
            std::thread::sleep(Duration::from_millis(10));
        }
        eprintln!("managed_escape_fixture_cleanup pid={pid:?} esrch={}", pid.map_or(true, pid_is_absent));
    }
}

/// Timeout closes the original group and separately stops its direct leader even when that
/// leader moved into another fixture-owned same-session group. The unrelated group member lives.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_timeout_kills_leader_after_it_changes_process_group() {
    let mut sentinel = Sentinel({
        let mut command = Command::new("/bin/sleep");
        command.arg("30").stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null());
        // SAFETY: the fixture sentinel creates a separate process group in the inherited session.
        unsafe {
            command.pre_exec(|| {
                if libc::setpgid(0, 0) < 0 {
                    return Err(std::io::Error::last_os_error());
                }
                Ok(())
            });
        }
        command.spawn().expect("start managed-scope sentinel")
    });
    let sentinel_pid = sentinel.0.id() as i32;
    let sentinel_pgid = unsafe { libc::getpgid(sentinel_pid) };
    assert_eq!(sentinel_pgid, sentinel_pid, "sentinel must own its fixture process group");
    let fixture = ManagedEscapeFixture::new();
    eprintln!("managed_escape_started root={} test_pid={} sentinel_pid={} sentinel_pgid={}", fixture.root.path().display(), std::process::id(), sentinel_pid, sentinel_pgid);
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let record = fixture.path("leader-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let release = fixture.path("release").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let config = SysConfig::default().programs(ProgramPolicy::AllowList(vec![executable.clone()])).process_scope(ProcessScope::Managed);
    let engine = engine(config);
    let script = format!(
        r#"run("{executable}", ["--exact", "managed_scope_escape_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {MANAGED_ESCAPE_FIXTURE_ENV}: "1", {MANAGED_ESCAPE_RECORD_ENV}: "{record}", {MANAGED_ESCAPE_RELEASE_ENV}: "{release}", {MANAGED_ESCAPE_GROUP_ENV}: "{sentinel_pgid}" }},
            timeout: 0.5,
            max_output: 4096
        }})"#
    );
    let result = engine.eval::<Map>(&script);
    let child_record = std::fs::read_to_string(fixture.path("leader-record")).unwrap();
    let child = managed_record_fields(&child_record);
    assert_eq!(child.get("pid"), child.get("original_pgid"));
    assert_eq!(child.get("escaped_pgid"), Some(&sentinel_pgid));
    assert_ne!(child.get("original_pgid"), child.get("escaped_pgid"));
    let sentinel_live = sentinel.0.try_wait().unwrap().is_none();
    eprintln!("managed_escape_sentinel_live pid={sentinel_pid} live={sentinel_live}");
    assert!(sentinel_live, "cleanup signaled the escaped child's unrelated group");
    eprintln!("managed_escape_leader pid={} original_pgid={} escaped_pgid={} esrch={}", child["pid"], child["original_pgid"], child["escaped_pgid"], pid_is_absent(child["pid"]));
    assert!(pid_is_absent(*child.get("pid").unwrap()), "managed direct leader must be gone before return");
    let result = result.unwrap_or_else(|error| panic!("managed timeout did not return its report: {error:?}"));
    assert_eq!(result["timed_out"].as_bool().unwrap(), true);
    drop(fixture);
    drop(sentinel);
    assert!(pid_is_absent(sentinel_pid), "fixture must reap the exact sentinel");
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_spawn_script(fixture: &ManagedFixture, kill_on_drop: bool) -> (Engine, String) {
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let root = fixture.root.as_script_path();
    let worker = fixture.path("worker-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let leaf = fixture.path("leaf-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let release = fixture.path("release-worker").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let config = SysConfig::default()
        .programs(ProgramPolicy::AllowList(vec![executable.clone()]))
        .process_scope(ProcessScope::Managed)
        .max_output(4096)
        .kill_on_drop(kill_on_drop);
    let engine = engine(config);
    let script = format!(
        r#"spawn("{executable}", ["--exact", "managed_scope_spawn_leader_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {MANAGED_SPAWN_HOLD_ENV}: "1", {MANAGED_ROOT_ENV}: "{root}", {MANAGED_WORKER_ENV}: "{worker}", {MANAGED_LEAF_ENV}: "{leaf}", {MANAGED_RELEASE_ENV}: "{release}" }}
        }})"#
    );
    (engine, script)
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_false_drop_spawn_script(fixture: &ManagedFixture) -> (Engine, String) {
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let root = fixture.root.as_script_path();
    let worker = fixture.path("worker-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let leaf = fixture.path("leaf-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let release_worker = fixture.path("release-worker").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let release_leader = fixture.path("release-leader").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let config = SysConfig::default()
        .programs(ProgramPolicy::AllowList(vec![executable.clone()]))
        .process_scope(ProcessScope::Managed)
        .max_output(4096)
        .kill_on_drop(false);
    let engine = engine(config);
    let script = format!(
        r#"spawn("{executable}", ["--exact", "managed_false_drop_leader_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {MANAGED_FALSE_DROP_ENV}: "leader", {MANAGED_ROOT_ENV}: "{root}", {MANAGED_WORKER_ENV}: "{worker}", {MANAGED_LEAF_ENV}: "{leaf}", {MANAGED_RELEASE_ENV}: "{release_worker}", "RHAI_SYS_MANAGED_FALSE_DROP_LEADER_RELEASE": "{release_leader}" }}
        }})"#
    );
    (engine, script)
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_escaped_pipe_spawn_script(fixture: &ManagedEscapedPipeFixture, sentinel_pgid: i32) -> (Engine, String) {
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let root = fixture.root.path().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let holder_record = fixture.path("holder-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let holder_release = fixture.path("release-holder").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let holder_challenge = fixture.path("holder-challenge").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let holder_ack = fixture.path("holder-ack").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let leader_record = fixture.path("leader-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let config = SysConfig::default()
        .programs(ProgramPolicy::AllowList(vec![executable.clone()]))
        .process_scope(ProcessScope::Managed)
        .max_output(4096)
        .kill_on_drop(true);
    let engine = engine(config);
    let script = format!(
        r#"spawn("{executable}", ["--exact", "managed_scope_retained_pipe_leader_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {MANAGED_PIPE_FIXTURE_ENV}: "leader", {MANAGED_PIPE_ROOT_ENV}: "{root}", {MANAGED_PIPE_HOLDER_RECORD_ENV}: "{holder_record}", {MANAGED_PIPE_HOLDER_RELEASE_ENV}: "{holder_release}", {MANAGED_PIPE_HOLDER_CHALLENGE_ENV}: "{holder_challenge}", {MANAGED_PIPE_HOLDER_ACK_ENV}: "{holder_ack}", {MANAGED_PIPE_SENTINEL_GROUP_ENV}: "{sentinel_pgid}", {MANAGED_PIPE_LEADER_RECORD_ENV}: "{leader_record}" }}
        }})"#
    );
    (engine, script)
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_fixture_member_pids(fixture: &ManagedFixture) -> (i32, i32, i32, i32) {
    let deadline = Instant::now() + Duration::from_secs(5);
    loop {
        let leader = std::fs::read_to_string(fixture.path("leader-record")).ok();
        let worker = std::fs::read_to_string(fixture.path("worker-record")).ok();
        let leaf = std::fs::read_to_string(fixture.path("leaf-record")).ok();
        if let (Some(leader), Some(worker), Some(leaf)) = (leader, worker, leaf) {
            let leader = managed_record_fields(&leader);
            let worker = managed_record_fields(&worker);
            let leaf = managed_record_fields(&leaf);
            let pids = (leader["pid"], worker["pid"], leaf["pid"], leader["pgid"]);
            assert_eq!(pids.0, pids.3, "managed spawned leader owns its process group");
            assert_eq!(worker["pgid"], pids.3, "worker inherited the managed group");
            assert_eq!(leaf["pgid"], pids.3, "leaf inherited the managed group");
            assert_eq!(leader["worker"], pids.1, "leader record identifies the worker");
            assert_eq!(leader["leaf"], pids.2, "leader record identifies the leaf");
            return pids;
        }
        assert!(Instant::now() < deadline, "managed spawn fixture readiness timed out");
        std::thread::sleep(Duration::from_millis(5));
    }
}

/// Public managed false-policy contract: dropping the final script client leaves the running
/// scope owned, then a naturally exiting leader closes only its recorded group.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit() {
    let fixture = ManagedFixture::new();
    let mut sentinel = managed_spawn_sentinel();
    let sentinel_pid = sentinel.0.id() as i32;
    let sentinel_pgid = unsafe { libc::getpgid(sentinel_pid) };
    let (engine, script) = managed_false_drop_spawn_script(&fixture);
    let child = engine.eval::<Dynamic>(&script).expect("public managed false-policy spawn");
    let (leader, worker, leaf, group) = managed_fixture_member_pids(&fixture);
    assert_eq!(sentinel_pgid, sentinel_pid);
    assert_ne!(group, sentinel_pgid);
    eprintln!(
        "managed_false_drop_started root={} test_pid={} sentinel_pid={} sentinel_pgid={} leader={} worker={} leaf={} group={}",
        fixture.root.as_script_path(),
        std::process::id(),
        sentinel_pid,
        sentinel_pgid,
        leader,
        worker,
        leaf,
        group
    );

    drop(child);
    drop(engine);
    let observation_deadline = Instant::now() + Duration::from_millis(250);
    let mut members_live = [leader, worker, leaf].into_iter().all(pid_is_running);
    while members_live && Instant::now() < observation_deadline {
        std::thread::sleep(Duration::from_millis(10));
        members_live = [leader, worker, leaf].into_iter().all(pid_is_running);
    }
    let sentinel_live = sentinel.0.try_wait().unwrap().is_none();
    eprintln!(
        "managed_false_drop_after_final_client_drop leader={leader} leader_live={} worker={worker} worker_live={} leaf={leaf} leaf_live={} sentinel={sentinel_pid} sentinel_live={sentinel_live}",
        pid_is_running(leader),
        pid_is_running(worker),
        pid_is_running(leaf)
    );
    assert!(members_live, "kill_on_drop(false) must preserve managed members after final handle drop");
    assert!(sentinel_live, "false-policy drop must preserve the unrelated sentinel");

    std::fs::write(fixture.path("challenge"), b"challenge\n").unwrap();
    let challenge_deadline = Instant::now() + Duration::from_secs(3);
    while !["ack-leader", "ack-worker", "ack-leaf"].into_iter().all(|name| fixture.path(name).exists()) && Instant::now() < challenge_deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
    let ack_records: Vec<_> = ["ack-leader", "ack-worker", "ack-leaf"]
        .into_iter()
        .map(|name| std::fs::read_to_string(fixture.path(name)).ok())
        .collect();
    let acks: Vec<_> = ack_records.iter().filter_map(|record| record.as_deref().map(managed_record_fields)).collect();
    let challenge_ok = acks.len() == 3 && acks.iter().map(|ack| ack.get("pid").copied()).collect::<Vec<_>>() == [Some(leader), Some(worker), Some(leaf)] && acks.iter().all(|ack| ack.get("pgid") == Some(&group));
    eprintln!(
        "managed_false_drop_live_challenge leader={leader} worker={worker} leaf={leaf} group={group} ack_count={} ack_pids={:?} ack_groups={:?}",
        acks.len(),
        acks.iter().map(|ack| ack.get("pid").copied()).collect::<Vec<_>>(),
        acks.iter().map(|ack| ack.get("pgid").copied()).collect::<Vec<_>>()
    );
    assert!(members_live && challenge_ok, "kill_on_drop(false) must preserve all managed members after final handle drop");

    std::fs::write(fixture.path("release-leader"), b"release\n").unwrap();
    let deadline = Instant::now() + Duration::from_secs(5);
    while [leader, worker, leaf].into_iter().any(|pid| !pid_is_absent(pid)) && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(10));
    }
    let leader_esrch = pid_is_absent(leader);
    let worker_esrch = pid_is_absent(worker);
    let leaf_esrch = pid_is_absent(leaf);
    let sentinel_live_after = sentinel.0.try_wait().unwrap().is_none();
    eprintln!("managed_false_drop_after_leader_exit leader={leader} leader_esrch={leader_esrch} worker={worker} worker_esrch={worker_esrch} leaf={leaf} leaf_esrch={leaf_esrch} sentinel={sentinel_pid} sentinel_live={sentinel_live_after}");
    assert!(leader_esrch && worker_esrch && leaf_esrch, "natural leader exit must close its managed group");
    assert!(sentinel_live_after, "managed natural exit must preserve unrelated sentinel");
    drop(sentinel);
    assert!(pid_is_absent(sentinel_pid), "fixture must reap its exact sentinel");
}

#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_spawn_sentinel() -> Sentinel {
    let mut command = Command::new("/bin/sleep");
    command.arg("30").stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null());
    // SAFETY: the fixture sentinel creates a separate process group in the inherited session.
    unsafe {
        command.pre_exec(|| {
            if libc::setpgid(0, 0) < 0 {
                return Err(std::io::Error::last_os_error());
            }
            Ok(())
        });
    }
    Sentinel(command.spawn().expect("start unrelated managed-scope sentinel"))
}

/// Public spawn cancellation terminates the direct leader and all recorded group members while
/// preserving an unrelated process group.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel() {
    let fixture = ManagedFixture::new();
    let mut sentinel = managed_spawn_sentinel();
    let sentinel_pid = sentinel.0.id() as i32;
    let sentinel_pgid = unsafe { libc::getpgid(sentinel_pid) };
    assert_eq!(sentinel_pgid, sentinel_pid);
    let (engine, script) = managed_spawn_script(&fixture, true);
    let child = engine.eval::<Dynamic>(&script).expect("public managed spawn");
    let pids = managed_fixture_member_pids(&fixture);
    assert!(pids.0 != sentinel_pid && pids.3 != sentinel_pgid);
    eprintln!(
        "managed_spawn_kill_started root={} test_pid={} sentinel_pid={} sentinel_pgid={} leader={} worker={} leaf={} group={}",
        fixture.root.as_script_path(),
        std::process::id(),
        sentinel_pid,
        sentinel_pgid,
        pids.0,
        pids.1,
        pids.2,
        pids.3
    );
    let mut scope = Scope::new();
    scope.push_dynamic("child", child);
    let timed_wait = engine.eval_with_scope::<Dynamic>(&mut scope, "child.kill(); child.wait(0.5)");
    let leader_esrch = pid_is_absent(pids.0);
    let worker_esrch = pid_is_absent(pids.1);
    let leaf_esrch = pid_is_absent(pids.2);
    let members_gone = leader_esrch && worker_esrch && leaf_esrch;
    let sentinel_live = sentinel.0.try_wait().unwrap().is_none();
    eprintln!(
        "managed_spawn_kill leader={} leader_esrch={leader_esrch} worker={} worker_esrch={worker_esrch} leaf={} leaf_esrch={leaf_esrch} all_esrch={members_gone} sentinel={sentinel_pid} live={sentinel_live} wait_returned={}",
        pids.0,
        pids.1,
        pids.2,
        timed_wait.is_ok()
    );
    assert!(members_gone, "managed spawned members must be gone after public kill");
    assert!(sentinel_live, "managed spawn kill terminated the unrelated sentinel");
    let timed_wait = timed_wait.expect("public kill followed by bounded wait");
    assert!(!timed_wait.is_unit(), "public child.wait must publish the killed child's report");
    let result = timed_wait.cast::<Map>();
    assert!(!result["success"].as_bool().unwrap());
    drop(sentinel);
    assert!(pid_is_absent(sentinel_pid), "fixture must reap its exact sentinel");
}

/// Killing a managed child whose escaped descendant holds capture pipes must still publish a
/// bounded final report with incomplete streams. The fixture, not the process API, releases the
/// escaped holder after proving it remained live and could still answer a fresh challenge.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes() {
    let mut fixture = ManagedEscapedPipeFixture::new();
    let mut sentinel = managed_spawn_sentinel();
    let sentinel_pid = sentinel.0.id() as i32;
    let sentinel_pgid = unsafe { libc::getpgid(sentinel_pid) };
    assert_eq!(sentinel_pgid, sentinel_pid, "fixture sentinel owns its group");
    let (engine, script) = managed_escaped_pipe_spawn_script(&fixture, sentinel_pgid);
    let child = engine.eval::<Dynamic>(&script).expect("public managed spawn");

    let deadline = Instant::now() + Duration::from_secs(5);
    while (!fixture.path("leader-record").exists() || !fixture.path("holder-record").exists()) && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
    let leader = managed_record_fields(&std::fs::read_to_string(fixture.path("leader-record")).expect("leader readiness"));
    let holder = managed_record_fields(&std::fs::read_to_string(fixture.path("holder-record")).expect("holder readiness"));
    let leader_pid = leader["pid"];
    let leader_pgid = leader["pgid"];
    let holder_pid = holder["pid"];
    let holder_pgid = holder["pgid"];
    assert_eq!(leader_pid, leader_pgid, "managed leader owns its process group");
    assert_eq!(holder_pgid, sentinel_pgid, "pipe holder escaped into the fixture sentinel group");
    assert_ne!(holder_pgid, leader_pgid, "pipe holder must escape the managed group");
    assert!(pid_is_alive(holder_pid), "escaped holder must be alive before cancellation");
    assert!(sentinel.0.try_wait().unwrap().is_none(), "fixture sentinel exited before the test");

    let mut scope = Scope::new();
    scope.push_dynamic("child", child);
    let wait_result = engine.eval_with_scope::<Dynamic>(&mut scope, "child.kill(); child.wait(2.0)");
    let leader_esrch_before_cleanup = pid_is_absent(leader_pid);
    let holder_live_after_wait = pid_is_alive(holder_pid);
    let sentinel_live_after_wait = sentinel.0.try_wait().unwrap().is_none();
    std::fs::write(fixture.path("holder-challenge"), b"probe\n").unwrap();
    let ack_deadline = Instant::now() + Duration::from_secs(2);
    while !fixture.path("holder-ack").exists() && Instant::now() < ack_deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
    let probe = std::fs::read_to_string(fixture.path("holder-ack")).expect("escaped holder answered post-return challenge");
    let probe_fields = managed_record_fields(&probe);
    let sentinel_pgid_matches = probe_fields.get("pid") == Some(&holder_pid) && holder_live_after_wait && sentinel_live_after_wait && holder_pgid == sentinel_pgid;
    eprintln!(
        "managed_escaped_pipe_wait root={} test_pid={} leader={} leader_pgid={} leader_esrch={leader_esrch_before_cleanup} holder={} holder_pgid={} holder_live_after_wait={holder_live_after_wait} sentinel={} sentinel_pgid={} sentinel_live_after_wait={sentinel_live_after_wait} wait_unit={} probe={probe:?} identity_ok={sentinel_pgid_matches}",
        fixture.root.path().display(),
        std::process::id(),
        leader_pid,
        leader_pgid,
        holder_pid,
        holder_pgid,
        sentinel_pid,
        sentinel_pgid,
        wait_result.as_ref().is_ok_and(|value| value.is_unit()),
    );
    let (cleanup_leader, cleanup_holder, leader_esrch, holder_esrch) = fixture.release_and_wait();
    drop(sentinel);
    let sentinel_esrch = pid_is_absent(sentinel_pid);
    eprintln!("managed_escaped_pipe_terminal leader={cleanup_leader:?} leader_esrch={leader_esrch} holder={cleanup_holder:?} holder_esrch={holder_esrch} sentinel={sentinel_pid} sentinel_esrch={sentinel_esrch}");
    assert_eq!(cleanup_leader, Some(leader_pid));
    assert_eq!(cleanup_holder, Some(holder_pid));
    assert!(leader_esrch && holder_esrch && sentinel_esrch, "fixture must release and reap exact PIDs");
    assert!(leader_esrch_before_cleanup, "public kill must terminate the direct managed leader");
    assert!(holder_live_after_wait && sentinel_live_after_wait && sentinel_pgid_matches, "fixture must prove the escaped holder remains operational in the unrelated sentinel group");

    let result = wait_result.expect("public wait must finish capture after cancellation even when an escaped holder retains pipes");
    assert!(!result.is_unit(), "public wait must return the final process report");
    let result = result.cast::<Map>();
    assert_eq!(result["stdout_complete"].as_bool().unwrap(), false);
    assert_eq!(result["stderr_complete"].as_bool().unwrap(), false);
    assert!(result["stdout"].as_immutable_string_ref().unwrap().contains("escaped-holder-stdout-ready"));
    assert!(result["stderr"].as_immutable_string_ref().unwrap().contains("escaped-holder-stderr-ready"));
    assert_eq!(probe_fields.get("stdout_result"), Some(&-1), "closed stdout capture endpoint must reject the post-return write");
    assert_eq!(probe_fields.get("stdout_error"), Some(&libc::EPIPE));
    assert_eq!(probe_fields.get("stderr_result"), Some(&-1), "closed stderr capture endpoint must reject the post-return write");
    assert_eq!(probe_fields.get("stderr_error"), Some(&libc::EPIPE));
}

/// An uncancelled timed wait remains pending while an escaped holder owns capture writers.
/// After the direct leader exits naturally, public kill cancels capture collection without
/// signaling the reaped PID and still publishes an incomplete report.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_spawn_post_reap_cancel_bounds_escaped_capture() {
    let mut fixture = ManagedEscapedPipeFixture::new();
    let mut sentinel = managed_spawn_sentinel();
    let sentinel_pid = sentinel.0.id() as i32;
    let sentinel_pgid = unsafe { libc::getpgid(sentinel_pid) };
    assert_eq!(sentinel_pgid, sentinel_pid, "fixture sentinel owns its group");
    let (engine, script) = managed_escaped_pipe_spawn_script(&fixture, sentinel_pgid);
    let child = engine.eval::<Dynamic>(&script).expect("public managed spawn");

    let deadline = Instant::now() + Duration::from_secs(5);
    while (!fixture.path("leader-record").exists() || !fixture.path("holder-record").exists()) && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
    let leader = managed_record_fields(&std::fs::read_to_string(fixture.path("leader-record")).expect("leader readiness"));
    let holder = managed_record_fields(&std::fs::read_to_string(fixture.path("holder-record")).expect("holder readiness"));
    let leader_pid = leader["pid"];
    let holder_pid = holder["pid"];
    assert_eq!(leader_pid, leader["pgid"]);
    assert_eq!(holder["pgid"], sentinel_pgid);
    assert_ne!(leader_pid, holder_pid);
    assert!(pid_is_alive(holder_pid));

    let mut scope = Scope::new();
    scope.push_dynamic("child", child);
    let ordinary_wait = engine.eval_with_scope::<Dynamic>(&mut scope, "child.wait(0.05)");
    let ordinary_wait_unit = ordinary_wait.as_ref().is_ok_and(Dynamic::is_unit);
    let holder_live_after_ordinary_wait = pid_is_alive(holder_pid);
    eprintln!(
        "managed_post_reap_ordinary_wait root={} test_pid={} leader={} holder={} sentinel={} wait_unit={ordinary_wait_unit} holder_live={holder_live_after_ordinary_wait}",
        fixture.root.path().display(),
        std::process::id(),
        leader_pid,
        holder_pid,
        sentinel_pid
    );
    assert!(ordinary_wait_unit, "uncancelled timed wait must remain pending while escaped writers hold capture pipes");
    assert!(holder_live_after_ordinary_wait, "uncancelled timed wait must not terminate the holder");

    fixture.release_leader();
    let reap_deadline = Instant::now() + Duration::from_secs(3);
    while !pid_is_absent(leader_pid) && Instant::now() < reap_deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
    let exit_record = std::fs::read_to_string(fixture.path("leader-exit-record"));
    let exit_record_matches = exit_record
        .as_deref()
        .is_ok_and(|record| record.contains(&format!("pid={leader_pid} release_seen=true exit_intent=true")));
    let leader_try_wait = engine.eval_with_scope::<Dynamic>(&mut scope, "child.try_wait()");
    let leader_try_wait_typed_error = leader_try_wait.as_ref().err().and_then(|error| match error.as_ref() {
        EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>(),
        _ => None,
    });
    if let Some(SysError::Process { cause, report }) = &leader_try_wait_typed_error {
        eprintln!(
            "managed_post_reap_typed_error cause={cause:?} exit_code={:?} exit_signal={:?} stdout_complete={} stderr_complete={} timed_out={} stdout_bytes={:?} stderr_bytes={:?} cleanup_diagnostics={:?}",
            report.exit_code(),
            report.exit_signal(),
            report.stdout_complete(),
            report.stderr_complete(),
            report.timed_out(),
            report.stdout_bytes(),
            report.stderr_bytes(),
            report.cleanup_diagnostics(),
        );
    } else {
        eprintln!("managed_post_reap_typed_error unexpected={leader_try_wait_typed_error:?}");
    }
    let leader_ps = Command::new("/bin/ps").args(["-o", "stat=", "-p", &leader_pid.to_string()]).output();
    let leader_ps_text = leader_ps.as_ref().map(|output| String::from_utf8_lossy(&output.stdout).trim().to_owned());
    let leader_esrch_before_kill = pid_is_absent(leader_pid);
    let holder_live_after_leader_exit = pid_is_alive(holder_pid);
    eprintln!(
        "managed_post_reap_leader leader={leader_pid} exit_record_matches={exit_record_matches} exit_record={:?} try_wait_unit={} try_wait_error={:?} ps_status={:?} leader_esrch={leader_esrch_before_kill} holder={holder_pid} holder_live={holder_live_after_leader_exit}",
        exit_record.as_deref().unwrap_or("<missing>"),
        leader_try_wait.as_ref().is_ok_and(Dynamic::is_unit),
        leader_try_wait.as_ref().err().map(ToString::to_string),
        leader_ps_text
    );
    assert!(exit_record_matches, "leader fixture must observe the release before exiting");
    assert!(leader_try_wait.is_ok(), "natural leader exit with only its zombie remaining must not fail group closure");
    assert!(leader_esrch_before_kill, "direct leader must exit before public cancellation");
    assert!(holder_live_after_leader_exit, "escaped holder must survive direct leader exit");

    let post_reap_wait = engine.eval_with_scope::<Dynamic>(&mut scope, "child.wait(0.3)");
    let post_reap_wait_unit = post_reap_wait.as_ref().is_ok_and(Dynamic::is_unit);
    let holder_live_after_post_reap_wait = pid_is_alive(holder_pid);
    let sentinel_live_after_post_reap_wait = sentinel.0.try_wait().unwrap().is_none();
    eprintln!("managed_post_reap_uncancelled_wait leader={leader_pid} wait_unit={post_reap_wait_unit} holder={holder_pid} holder_live={holder_live_after_post_reap_wait} sentinel={sentinel_pid} sentinel_live={sentinel_live_after_post_reap_wait}");
    assert!(post_reap_wait_unit, "uncancelled wait after direct-child reap must remain pending while writers remain open");
    assert!(holder_live_after_post_reap_wait && sentinel_live_after_post_reap_wait, "uncancelled post-reap wait must preserve escaped holder and sentinel");

    let wait_result = engine.eval_with_scope::<Dynamic>(&mut scope, "child.kill(); child.wait(2.0)");
    let holder_live_after_cancel = pid_is_alive(holder_pid);
    std::fs::write(fixture.path("holder-challenge"), b"post-reap-probe\n").unwrap();
    let ack_deadline = Instant::now() + Duration::from_secs(2);
    while !fixture.path("holder-ack").exists() && Instant::now() < ack_deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
    let probe_text = std::fs::read_to_string(fixture.path("holder-ack")).expect("post-reap holder challenge");
    let probe = managed_record_fields(&probe_text);
    let (cleanup_leader, cleanup_holder, leader_esrch, holder_esrch) = fixture.release_and_wait();
    drop(sentinel);
    let sentinel_esrch = pid_is_absent(sentinel_pid);
    eprintln!("managed_escaped_pipe_terminal leader={cleanup_leader:?} leader_esrch={leader_esrch} holder={cleanup_holder:?} holder_esrch={holder_esrch} sentinel={sentinel_pid} sentinel_esrch={sentinel_esrch}");
    eprintln!("managed_post_reap_cancel root={} test_pid={} leader={} leader_esrch_before_kill={leader_esrch_before_kill} leader_esrch={leader_esrch} holder={} holder_live_after_cancel={holder_live_after_cancel} holder_esrch={holder_esrch} sentinel={sentinel_pid} sentinel_esrch={sentinel_esrch} probe={probe_text:?} wait_unit={}", fixture.root.path().display(), std::process::id(), leader_pid, holder_pid, wait_result.as_ref().is_ok_and(Dynamic::is_unit));
    assert_eq!(cleanup_leader, Some(leader_pid));
    assert_eq!(cleanup_holder, Some(holder_pid));
    assert!(leader_esrch_before_kill && leader_esrch && holder_esrch && sentinel_esrch, "fixture must observe exact process identities absent after cleanup");
    assert!(holder_live_after_cancel, "public post-reap kill must not signal the escaped holder group");
    assert_eq!(probe.get("pid"), Some(&holder_pid));

    let result = wait_result.expect("post-reap cancellation must publish the retained process report");
    assert!(!result.is_unit(), "post-reap cancellation must return a report");
    let result = result.cast::<Map>();
    assert_eq!(result["stdout_complete"].as_bool().unwrap(), false);
    assert_eq!(result["stderr_complete"].as_bool().unwrap(), false);
    assert_eq!(result["success"].as_bool().unwrap(), true);
    assert_eq!(probe.get("stdout_result"), Some(&-1), "post-reap cancellation must close the stdout capture endpoint");
    assert_eq!(probe.get("stdout_error"), Some(&libc::EPIPE));
    assert_eq!(probe.get("stderr_result"), Some(&-1), "post-reap cancellation must close the stderr capture endpoint");
    assert_eq!(probe.get("stderr_error"), Some(&libc::EPIPE));
    assert!(result["stdout"].as_immutable_string_ref().unwrap().contains("escaped-holder-stdout-ready"));
    assert!(result["stderr"].as_immutable_string_ref().unwrap().contains("escaped-holder-stderr-ready"));
}

/// Dropping a nonfinal shared Child clone preserves the running group; dropping the final
/// script-client handle applies `kill_on_drop` to its leader and descendants.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not() {
    let fixture = ManagedFixture::new();
    let mut sentinel = managed_spawn_sentinel();
    let sentinel_pid = sentinel.0.id() as i32;
    let (engine, script) = managed_spawn_script(&fixture, true);
    let original = engine.eval::<Dynamic>(&script).expect("public managed spawn");
    let pids = managed_fixture_member_pids(&fixture);
    let sentinel_pgid = unsafe { libc::getpgid(sentinel_pid) };
    assert_eq!(sentinel_pgid, sentinel_pid);
    assert!(pids.0 != sentinel_pid && pids.3 != sentinel_pgid);
    eprintln!(
        "managed_spawn_drop_started root={} test_pid={} sentinel_pid={} sentinel_pgid={} leader={} worker={} leaf={} group={}",
        fixture.root.as_script_path(),
        std::process::id(),
        sentinel_pid,
        sentinel_pgid,
        pids.0,
        pids.1,
        pids.2,
        pids.3
    );
    let mut scope = Scope::new();
    scope.push_dynamic("nonfinal", original.clone());
    scope.push_dynamic("final", original.clone());
    drop(original);

    drop(scope.remove::<Dynamic>("nonfinal"));
    let still_running = engine
        .eval_with_scope::<Dynamic>(&mut scope, "final.wait(0.1)")
        .expect("remaining shared handle performs a bounded wait");
    assert!(still_running.is_unit(), "nonfinal clone drop cancelled the live managed child");
    let all_live = [pids.0, pids.1, pids.2].into_iter().all(pid_is_alive);
    let leader_live = pid_is_alive(pids.0);
    let worker_live = pid_is_alive(pids.1);
    let leaf_live = pid_is_alive(pids.2);
    eprintln!(
        "managed_spawn_nonfinal_drop leader={} leader_live={leader_live} worker={} worker_live={worker_live} leaf={} leaf_live={leaf_live} all_live={all_live}",
        pids.0, pids.1, pids.2
    );
    assert!(all_live, "dropping a nonfinal Child clone terminated the managed group");

    drop(scope.remove::<Dynamic>("final"));
    let deadline = Instant::now() + Duration::from_secs(5);
    while [pids.0, pids.1, pids.2].into_iter().any(|pid| !pid_is_absent(pid)) && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
    let leader_esrch = pid_is_absent(pids.0);
    let worker_esrch = pid_is_absent(pids.1);
    let leaf_esrch = pid_is_absent(pids.2);
    let all_gone = leader_esrch && worker_esrch && leaf_esrch;
    let sentinel_live = sentinel.0.try_wait().unwrap().is_none();
    eprintln!(
        "managed_spawn_final_drop leader={} leader_esrch={leader_esrch} worker={} worker_esrch={worker_esrch} leaf={} leaf_esrch={leaf_esrch} all_esrch={all_gone} sentinel={sentinel_pid} live={sentinel_live}",
        pids.0, pids.1, pids.2,
    );
    assert!(all_gone, "dropping final Child clone did not terminate the managed group");
    assert!(sentinel_live, "final Child drop terminated the unrelated sentinel");
    drop(sentinel);
    assert!(pid_is_absent(sentinel_pid), "fixture must reap its exact sentinel");
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
                timeout: 5
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

#[test]
#[cfg(not(feature = "no_index"))]
fn run_preserves_argv_boundaries_without_shell_interpolation() {
    let engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    let records = TempDir::new();
    let argument_record = records.path().join("argv.bin");
    let child_record = records.path().join("child-record.txt");
    let marker = records.path().join("shell-expanded-marker");
    let arguments = vec![
        "value with spaces".to_owned(),
        "double \"quotes\" and 'single quotes'".to_owned(),
        "$HOME".to_owned(),
        "literal|pipe".to_owned(),
        "literal;semicolon".to_owned(),
        "literal&&and".to_owned(),
        format!("$(touch {})", marker.display()),
        String::new(),
    ];
    let argument_literals = arguments.iter().map(|argument| format!("{argument:?}")).collect::<Vec<_>>().join(", ");
    let shell_script = r#"argument_record=$1; child_record=$2; shift 2; printf '%s\0' "$@" > "$argument_record"; printf 'child-pid=%s child-exit=0\n' "$$" > "$child_record""#;
    let script = format!(
        r#"run("/bin/sh", ["-c", {shell_script:?}, "rhai-argv-fixture", {argument_record:?}, {child_record:?}, {argument_literals}], #{{ timeout: 5 }})"#,
        shell_script = shell_script,
        argument_record = argument_record.to_string_lossy(),
        child_record = child_record.to_string_lossy(),
    );

    let result = engine.eval::<Map>(&script).expect("public run should execute the argv fixture");
    assert_eq!(result["success"].as_bool(), Ok(true));
    assert_eq!(result["code"].as_int(), Ok(0));
    assert!(result["stdout_complete"].as_bool().unwrap());
    assert!(result["stderr_complete"].as_bool().unwrap());

    let observed = std::fs::read(&argument_record).expect("child argv readback");
    let mut expected = Vec::new();
    for argument in &arguments {
        expected.extend_from_slice(argument.as_bytes());
        expected.push(0);
    }
    assert_child_record(&child_record, 0);
    assert!(!marker.exists(), "shell interpreted an argv value as command text");
    assert_eq!(observed, expected, "child received different argv boundaries or bytes");
}

#[test]
#[cfg(not(feature = "no_index"))]
fn run_removes_inherited_environment_variable_from_public_child() {
    const REMOVED_VARIABLE: &str = "PATH";
    assert!(std::env::var_os(REMOVED_VARIABLE).is_some(), "test requires an inherited PATH value");

    let engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    let executable = std::env::current_exe().expect("test executable");
    let executable = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let records = TempDir::new();
    let invoke = |label: &str, remove_path: bool| {
        let child_record = records.path().join(format!("{label}-child.txt"));
        let query_record = records.path().join(format!("{label}-environment.txt"));
        let child_record = child_record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let query_record = query_record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let remove_option = if remove_path { r#"env_remove: ["PATH"],"# } else { "" };
        format!(
            r#"run("{executable}", ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
                env: #{{ {FIXTURE_ENV}: "0", {FIXTURE_RECORD_ENV}: "{child_record}", {FIXTURE_ENV_QUERY}: "{REMOVED_VARIABLE}", {FIXTURE_ENV_QUERY_RECORD}: "{query_record}" }},
                {remove_option}
                timeout: 5,
                max_output: 1024
            }})"#,
            executable = executable,
            child_record = child_record,
            query_record = query_record,
            remove_option = remove_option,
        )
    };

    let removed_result = engine.eval::<Map>(&invoke("removed", true)).expect("public run should start the fixture with PATH removed");
    assert_eq!(removed_result["success"].as_bool(), Ok(true));
    assert_eq!(removed_result["code"].as_int(), Ok(0));
    assert_child_record(&records.path().join("removed-child.txt"), 0);
    let removed_record = std::fs::read_to_string(records.path().join("removed-environment.txt")).expect("independent child environment readback");
    assert_eq!(removed_record, "variable=PATH present=false\n");

    let control_result = engine.eval::<Map>(&invoke("control", false)).expect("public run should start the inherited-environment control");
    assert_eq!(control_result["success"].as_bool(), Ok(true));
    assert_eq!(control_result["code"].as_int(), Ok(0));
    assert_child_record(&records.path().join("control-child.txt"), 0);
    let control_record = std::fs::read_to_string(records.path().join("control-environment.txt")).expect("independent control environment readback");
    assert_eq!(control_record, "variable=PATH present=true\n");
    eprintln!(
        "x11_env_remove removed_child={:?} removed_readback={:?} control_child={:?} control_readback={:?} direct_children_reaped=ESRCH",
        std::fs::read_to_string(records.path().join("removed-child.txt")).unwrap().trim(),
        removed_record.trim(),
        std::fs::read_to_string(records.path().join("control-child.txt")).unwrap().trim(),
        control_record.trim(),
    );
}

#[test]
#[cfg(not(feature = "no_index"))]
fn default_and_nonmatching_process_policies_deny_public_run_without_starting_child() {
    let records = TempDir::new();
    let executable = std::env::current_exe().expect("test executable");
    let executable_value = executable.to_string_lossy().into_owned();
    let executable_script = executable_value.replace('\\', "\\\\").replace('"', "\\\"");
    let invocation = |record: &std::path::Path| {
        let record = record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        format!(
            r#"run("{executable_script}", ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
                env_clear: true,
                env: #{{ {FIXTURE_ENV}: "0", {FIXTURE_RECORD_ENV}: "{record}" }},
                timeout: 5
            }})"#
        )
    };

    let default_record = records.path().join("default-policy-child.txt");
    let default_engine = engine(SysConfig::default());
    let default_error = sys_support::sys_err(&default_engine, &invocation(&default_record));
    assert!(matches!(&default_error, SysError::Denied(_)), "default process policy returned {default_error:?}");
    assert!(!default_record.exists(), "default-denied Engine run started the child");

    let mismatch_record = records.path().join("allowlist-mismatch-child.txt");
    let executable_parent = executable.parent().expect("test executable parent").to_string_lossy().into_owned();
    let mismatch_engine = engine(SysConfig::default().programs(ProgramPolicy::AllowList(vec![executable_parent])));
    let mismatch_error = sys_support::sys_err(&mismatch_engine, &invocation(&mismatch_record));
    assert!(matches!(&mismatch_error, SysError::Denied(_)), "nonmatching allowlist returned {mismatch_error:?}");
    assert!(!mismatch_record.exists(), "nonmatching allowlist started the child");

    let control_record = records.path().join("allowlist-control-child.txt");
    let control_engine = engine(SysConfig::default().programs(ProgramPolicy::AllowList(vec![executable_value])));
    let control_result = control_engine.eval::<Map>(&invocation(&control_record)).expect("matching allowlist should run the fixture");
    assert_eq!(control_result["success"].as_bool(), Ok(true));
    assert_child_record(&control_record, 0);
    let control_record_contents = std::fs::read_to_string(&control_record).unwrap();
    eprintln!(
        "denied child markers absent: default={}, allowlist-mismatch={}; allowed child record: {}",
        !default_record.exists(),
        !mismatch_record.exists(),
        control_record_contents.trim()
    );
}

#[test]
#[cfg(not(feature = "no_index"))]
fn missing_program_and_cwd_report_not_found_without_starting_child() {
    let records = TempDir::new();
    let executable = std::env::current_exe().expect("test executable");
    let engine = engine(SysConfig::default().fs_unrestricted(FsAccess::Read).programs(ProgramPolicy::Any));
    let script_path = |path: &std::path::Path| path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let invocation = |program: &str, record: &std::path::Path, cwd: Option<&std::path::Path>| {
        let program = program.replace('\\', "\\\\").replace('"', "\\\"");
        let record = script_path(record);
        let cwd_option = cwd.map(|path| format!("cwd: \"{}\",", script_path(path))).unwrap_or_default();
        format!(
            r#"run("{program}", ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
                env_clear: true,
                env: #{{ {FIXTURE_ENV}: "0", {FIXTURE_RECORD_ENV}: "{record}" }},
                {cwd_option}
                timeout: 5,
                max_output: 1024
            }})"#
        )
    };

    // Confirm the independent marker works before using its absence to prove failed starts.
    let control_record = records.path().join("control-child.txt");
    let control = engine
        .eval::<Map>(&invocation(&executable.to_string_lossy(), &control_record, None))
        .expect("valid executable should start the process fixture");
    assert!(control["success"].as_bool().unwrap());
    assert_child_record(&control_record, 0);
    eprintln!("x2_x8_valid_control child_record={:?} reap=ESRCH", std::fs::read_to_string(&control_record).unwrap().trim());

    let missing_program = records.path().join("missing-program");
    assert!(!missing_program.exists());
    let missing_program_record = records.path().join("missing-program-child.txt");
    let error = sys_support::sys_err(&engine, &invocation(&missing_program.to_string_lossy(), &missing_program_record, None));
    match error {
        SysError::Io { op, target, kind, .. } => {
            assert_eq!(op, "spawn process");
            assert_eq!(kind, std::io::ErrorKind::NotFound);
            assert_eq!(target, missing_program.to_string_lossy());
        }
        other => panic!("missing program returned {other:?}"),
    }
    assert!(!missing_program_record.exists(), "missing program started the child fixture");
    eprintln!("x2_missing_program io_kind=NotFound child_record_absent=true");

    let missing_cwd = records.path().join("missing-working-directory");
    assert!(!missing_cwd.exists());
    let missing_cwd_record = records.path().join("missing-cwd-child.txt");
    let error = sys_support::sys_err(&engine, &invocation(&executable.to_string_lossy(), &missing_cwd_record, Some(&missing_cwd)));
    match error {
        SysError::Io { op, target, kind, .. } => {
            assert_eq!(op, "open process working directory");
            assert_eq!(kind, std::io::ErrorKind::NotFound);
            assert_eq!(target, missing_cwd.to_string_lossy());
        }
        other => panic!("missing working directory returned {other:?}"),
    }
    assert!(!missing_cwd_record.exists(), "missing working directory started the child fixture");
    eprintln!("x8_missing_cwd io_kind=NotFound child_record_absent=true");
}

#[cfg(not(feature = "no_index"))]
fn assert_child_record(path: &std::path::Path, code: rhai::INT) {
    let record = std::fs::read_to_string(path).unwrap();
    let fields: Vec<_> = record.split_whitespace().collect();
    assert_eq!(fields.len(), 2, "child record: {record:?}");
    let pid: libc::pid_t = fields[0].strip_prefix("child-pid=").unwrap().parse().unwrap();
    assert_eq!(fields[1], format!("child-exit={code}"));
    // The API must return only after its owned direct child has been reaped.
    assert_eq!(unsafe { libc::kill(pid, 0) }, -1, "child {pid} is still present");
    assert_eq!(std::io::Error::last_os_error().raw_os_error(), Some(libc::ESRCH));
}

#[cfg(not(feature = "no_index"))]
fn assert_io_stress_record(path: &std::path::Path, expected_input: usize, complete_input: bool) {
    let record = std::fs::read_to_string(path).unwrap();
    let fields: Vec<_> = record.split_whitespace().collect();
    assert!(fields.len() == 2 || fields.len() == 3, "stress child record: {record:?}");
    let pid: libc::pid_t = fields[0].strip_prefix("child-pid=").unwrap().parse().unwrap();
    if fields.len() == 3 {
        assert_eq!(fields[1], format!("input-bytes={expected_input}"));
        assert_eq!(fields[2], "input-valid=true");
    } else {
        assert_eq!(fields[1], "child-ready=1");
    }
    if complete_input {
        assert_eq!(fields.len(), 3, "stress child did not validate complete input: {record:?}");
    }
    assert_eq!(unsafe { libc::kill(pid, 0) }, -1, "stress child {pid} is still present");
    assert_eq!(std::io::Error::last_os_error().raw_os_error(), Some(libc::ESRCH));
}

#[cfg(not(feature = "no_index"))]
fn io_stress_script(executable: &str, record_path: &str, input_bytes: usize, stdout_bytes: usize, stderr_bytes: usize, limit: usize, timeout_secs: f64) -> String {
    let input = "i".repeat(input_bytes);
    format!(
        r#"run_raw("{executable}", ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {FIXTURE_ENV}: "0", {FIXTURE_RECORD_ENV}: "{record_path}", RHAI_SYS_PROCESS_IO_STRESS: "1", RHAI_SYS_PROCESS_IO_BYTES: "{input_bytes}", RHAI_SYS_PROCESS_STDOUT_BYTES: "{stdout_bytes}", RHAI_SYS_PROCESS_STDERR_BYTES: "{stderr_bytes}" }},
            stdin: "{input}", max_output: {limit}, timeout: {timeout_secs}
        }})"#
    )
}

/// Bounded, opt-in DirectChild/Managed overhead measurements for POSIX hosts.
/// This is intentionally ignored by normal suites; the measurement driver runs it once.
#[test]
#[cfg(not(feature = "no_index"))]
#[ignore = "bounded POSIX process-scope overhead measurement; invoke with the dedicated driver"]
fn process_scope_overhead_measurement() {
    const PAIRS: usize = 30;
    const STREAM_BYTES: usize = 8 * 1024 * 1024;
    const OUTPUT_LIMIT: usize = STREAM_BYTES;
    const TRUE_TIMEOUT_SECS: f64 = 2.0;
    const CAPTURE_TIMEOUT_SECS: f64 = 6.0;

    let true_program = if cfg!(target_os = "macos") { "/usr/bin/true" } else { "/bin/true" };
    let fixture_executable = std::env::current_exe().unwrap().to_string_lossy().into_owned();
    let records = TempDir::new();
    let record_path_buf = records.path().join("capture-record.txt");
    let complete_record_path = record_path_buf.with_extension("complete");
    let record_path = record_path_buf.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let capture_script = io_stress_script(&fixture_executable.replace('\\', "\\\\").replace('"', "\\\""), &record_path, 0, STREAM_BYTES - LIBTEST_QUIET_START.len(), STREAM_BYTES, OUTPUT_LIMIT, CAPTURE_TIMEOUT_SECS);
    let true_script = format!("run_raw({true_program:?})");

    let mut modes = [ProcessScope::DirectChild, ProcessScope::Managed]
        .into_iter()
        .map(|scope| {
            let config = SysConfig::default()
                .programs(ProgramPolicy::AllowList(vec![true_program.into(), fixture_executable.clone()]))
                .max_output(OUTPUT_LIMIT)
                .default_timeout(Some(TRUE_TIMEOUT_SECS))
                .process_scope(scope);
            let engine = engine(config);
            let true_ast = engine.compile(&true_script).unwrap();
            let capture_ast = engine.compile(&capture_script).unwrap();
            let name = match scope {
                ProcessScope::DirectChild => "DirectChild",
                ProcessScope::Managed => "Managed",
            };
            (name, engine, true_ast, capture_ast)
        })
        .collect::<Vec<_>>();

    for pair in 0..PAIRS {
        let mode_order = if pair % 2 == 0 { [0, 1] } else { [1, 0] };
        for mode_index in mode_order {
            let workload_order = if pair % 2 == 0 { ["true", "capture"] } else { ["capture", "true"] };
            for workload in workload_order {
                let (name, engine, true_ast, capture_ast) = &mut modes[mode_index];
                let (ast, expected_out, expected_err, record) = if workload == "true" {
                    (true_ast, 0, 0, false)
                } else {
                    let _ = std::fs::remove_file(&record_path_buf);
                    let _ = std::fs::remove_file(&complete_record_path);
                    (capture_ast, STREAM_BYTES, STREAM_BYTES, true)
                };

                let started = Instant::now();
                let result = engine
                    .eval_ast::<Map>(ast)
                    .unwrap_or_else(|error| panic!("measurement pair={pair} scope={name} workload={workload} failed: {error:?}"));
                let latency_ns = started.elapsed().as_nanos();

                assert!(result["success"].as_bool().unwrap(), "measurement child failed");
                assert_eq!(result["code"].as_int().unwrap(), 0);
                assert!(result["stdout_complete"].as_bool().unwrap());
                assert!(result["stderr_complete"].as_bool().unwrap());
                let stdout = result["stdout"].clone().try_cast::<Blob>().unwrap();
                let stderr = result["stderr"].clone().try_cast::<Blob>().unwrap();
                assert_eq!(stdout.len(), expected_out, "stdout byte count for {name}/{workload}");
                assert_eq!(stderr.len(), expected_err, "stderr byte count for {name}/{workload}");
                if record {
                    assert!(stdout.starts_with(LIBTEST_QUIET_START));
                    assert!(stdout[LIBTEST_QUIET_START.len()..].iter().all(|byte| *byte == b'o'));
                    assert!(stderr.iter().all(|byte| *byte == b'e'));
                    assert_io_stress_record(&record_path_buf, 0, true);
                }
                eprintln!("PROCESS_SCOPE_SAMPLE,{pair},{name},{workload},{latency_ns},{},{},0", stdout.len(), stderr.len());
            }
        }
    }
}

/// Separately measures Linux retained process/thread/descriptor counts at public API return
/// and after the owning Engine is dropped. The held-child case is an observer control: it must
/// see the exact live fixture identity and increased host resources before public-handle cleanup.
#[test]
#[cfg(target_os = "linux")]
#[cfg(not(feature = "no_index"))]
#[cfg(not(feature = "no_float"))]
#[ignore = "bounded Linux retained-resource census; invoke with the dedicated resource driver"]
fn process_scope_retained_resource_census() {
    let synthetic = format!("42 (fixture with ) chars) S {} 987654321", vec!["0"; 18].join(" "));
    assert_eq!(resource_census_parse_start_ticks(&synthetic).unwrap(), 987_654_321);
    assert_eq!(resource_census_parse_start_ticks("42 (malformed) S 0").unwrap_err().kind(), std::io::ErrorKind::InvalidData);
    const CASES: [(&str, ProcessScope); 2] = [("DirectChild", ProcessScope::DirectChild), ("Managed", ProcessScope::Managed)];
    let executable = std::env::current_exe().unwrap().to_string_lossy().into_owned();

    for (scope_name, scope) in CASES {
        for (case_name, api_expression) in [("run", "run_raw"), ("spawn_wait", "spawn_wait"), ("shared_child", "shared_child")] {
            let records = TempDir::new();
            let record = records.path().join("resource-child.txt");
            let record_script = record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
            let executable_script = executable.replace('\\', "\\\\").replace('"', "\\\"");
            let command = format!("\"{executable_script}\", [\"--exact\", \"process_fixture\", \"--nocapture\", \"--quiet\"], #{{ env_clear: true, env: #{{ {FIXTURE_ENV}: \"0\", {FIXTURE_RECORD_ENV}: \"{record_script}\", RHAI_SYS_PROCESS_RESOURCE_CENSUS: \"1\" }} }}");
            let script = match api_expression {
                "run_raw" => format!("run_raw({command})"),
                "spawn_wait" => format!("spawn({command}).wait(2.0)"),
                "shared_child" => format!("spawn({command})"),
                _ => unreachable!(),
            };
            let config = SysConfig::default()
                .default_timeout(Some(2.0))
                .programs(ProgramPolicy::AllowList(vec![executable.clone()]))
                .process_scope(scope)
                .max_output(4096);
            let baseline = resource_census_snapshot();
            let engine = engine(config);
            let result = if case_name == "shared_child" {
                let handle = engine
                    .eval::<Dynamic>(&script)
                    .unwrap_or_else(|error| panic!("resource census {scope_name}/{case_name} spawn failed: {error:?}"));
                let first = handle.try_cast::<rhai::packages::sys::Child>().expect("spawn result is the public Child type");
                let second = first.clone();
                let mut scope = Scope::new();
                scope.push("first", first);
                scope.push("second", second);
                engine
                    .eval_with_scope::<Map>(&mut scope, "let primary = first.wait(2.0); second.wait(2.0); primary")
                    .unwrap_or_else(|error| panic!("resource census {scope_name}/{case_name} waits failed: {error:?}"))
            } else {
                engine.eval::<Map>(&script).unwrap_or_else(|error| panic!("resource census {scope_name}/{case_name} failed: {error:?}"))
            };
            let at_return = resource_census_snapshot();
            assert!(result["success"].as_bool().unwrap(), "{scope_name}/{case_name} report: {result:?}");
            assert_eq!(result["code"].as_int().unwrap(), 0);
            let fields = resource_census_fields(&record).expect("fixture identity receipt");
            let child_pid = fields["child-pid"] as i32;
            let child_start = fields["child-start"] as u64;
            resource_census_assert_gone(child_pid, child_start);
            assert_eq!(at_return.2, baseline.2 + 1, "the lazy package cleanup worker is retained through API return");
            drop(engine);
            let after_drop = resource_census_wait_for_baseline(baseline);
            assert_eq!(after_drop, baseline, "{scope_name}/{case_name} resources did not return to the pre-package baseline");
            eprintln!(
                "PROCESS_SCOPE_RESOURCE,{scope_name},{case_name},base_tasks={},return_tasks={},base_fds={},return_fds={},cleanup_threads={},fixture_pid={child_pid},fixture_start={child_start},postdrop_tasks={},postdrop_fds={}",
                baseline.0, at_return.0, baseline.1, at_return.1, at_return.2, after_drop.0, after_drop.1
            );
        }

        // Return an owned public Child while its fixture is demonstrably alive. The observer
        // must detect the retained process, capture descriptors, and package cleanup thread;
        // cleanup then goes through that exact Child handle, never a numeric PID signal.
        let records = TempDir::new();
        let record = records.path().join("held-child.txt");
        let release = records.path().join("release-child");
        let record_script = record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let release_script = release.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let executable_script = executable.replace('\\', "\\\\").replace('"', "\\\"");
        let spawn_script = format!(
            "spawn(\"{executable_script}\", [\"--exact\", \"process_fixture\", \"--nocapture\", \"--quiet\"], #{{ env_clear: true, env: #{{ {FIXTURE_ENV}: \"0\", {FIXTURE_RECORD_ENV}: \"{record_script}\", RHAI_SYS_PROCESS_RESOURCE_CENSUS: \"1\", RHAI_SYS_PROCESS_RESOURCE_HOLD: \"1\", RHAI_SYS_PROCESS_RESOURCE_RELEASE: \"{release_script}\" }} }})"
        );
        let config = SysConfig::default()
            .default_timeout(Some(2.0))
            .programs(ProgramPolicy::AllowList(vec![executable.clone()]))
            .process_scope(scope)
            .max_output(4096);
        let baseline = resource_census_snapshot();
        let engine = engine(config);
        let _release_guard = ResourceCensusRelease(release);
        let handle = engine.eval::<Dynamic>(&spawn_script).expect("public spawn returns a Child handle");
        let at_return = resource_census_snapshot();
        let child_pid = resource_census_wait_for_pid(&record);
        let child_start = resource_census_start_ticks(child_pid).expect("read held fixture identity").expect("held child identity exists");
        assert_eq!(resource_census_start_ticks(child_pid).expect("read held child identity"), Some(child_start), "positive control child must still be live at observation");
        assert!(at_return.0 > baseline.0, "positive control must expose an additional process-owned pump/service task");
        assert!(at_return.1 > baseline.1, "positive control must expose retained capture descriptors");
        assert_eq!(at_return.2, baseline.2 + 1, "positive control retains exactly one package cleanup worker");
        let child = handle.try_cast::<rhai::packages::sys::Child>().expect("spawn result is the public Child type");
        let mut scope = Scope::new();
        scope.push("child", child);
        let stopped = engine
            .eval_with_scope::<Map>(&mut scope, "child.kill(); child.wait(2.0)")
            .expect("public Child handle cancels and reaps the positive-control fixture");
        assert!(stopped["stdout_complete"].as_bool().unwrap());
        assert!(stopped["stderr_complete"].as_bool().unwrap());
        resource_census_assert_gone(child_pid, child_start);
        drop(scope);
        drop(engine);
        let after_drop = resource_census_wait_for_baseline(baseline);
        assert_eq!(after_drop, baseline, "positive-control resources did not return to baseline after Engine drop");
        eprintln!(
            "PROCESS_SCOPE_RESOURCE,{scope_name},held_child_control,base_tasks={},return_tasks={},base_fds={},return_fds={},cleanup_threads={},fixture_pid={child_pid},fixture_start={child_start},postdrop_tasks={},postdrop_fds={}",
            baseline.0, at_return.0, baseline.1, at_return.1, at_return.2, after_drop.0, after_drop.1
        );
    }
}

#[cfg(not(feature = "no_index"))]
fn assert_output_limit_error(error: Box<rhai::EvalAltResult>, stream: &str, prefix: &[u8]) {
    let sys_error = match error.as_ref() {
        rhai::EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>().unwrap(),
        other => panic!("unexpected output-limit error: {other:?}"),
    };
    match sys_error {
        SysError::Process { cause: ProcessCause::OutputLimit(_), report } => match stream {
            "stdout" => {
                assert_eq!(report.stdout_bytes(), prefix);
                assert!(!report.stdout_complete());
            }
            "stderr" => {
                assert_eq!(report.stderr_bytes(), prefix);
                assert!(!report.stderr_complete());
            }
            other => panic!("unknown output stream {other}"),
        },
        other => panic!("expected OutputLimit as the primary process cause, got {other:?}"),
    }
}

#[test]
#[cfg(all(unix, not(feature = "no_index")))]
fn run_reports_a_real_unix_child_signal_without_an_exit_code() {
    let engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    let records = TempDir::new();
    let record_path = records.path().join("signal-child.txt");
    let record_literal = record_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let command = r#"printf 'child-pid=%s\n' "$$" > "$RECORD"; kill -KILL "$$""#.replace('\\', "\\\\").replace('"', "\\\"");
    let script = format!(
        r#"run("/bin/sh", ["-c", "{command}"], #{{
            env_clear: true,
            env: #{{ RECORD: "{record_literal}" }},
            timeout: 5,
            max_output: 1024
        }})"#
    );

    let result = engine.eval::<Map>(&script).unwrap();
    assert!(!result["success"].as_bool().unwrap());
    assert!(result["code"].is_unit(), "a signal-terminated child has no exit code");
    assert_eq!(result["signal"].as_int().unwrap(), libc::SIGKILL as rhai::INT);
    assert!(!result["timed_out"].as_bool().unwrap());
    assert!(result["stdout_complete"].as_bool().unwrap());
    assert!(result["stderr_complete"].as_bool().unwrap());

    let record = std::fs::read_to_string(record_path).unwrap();
    let pid: libc::pid_t = record
        .strip_prefix("child-pid=")
        .expect("child must record its own process id before receiving SIGKILL")
        .trim()
        .parse()
        .unwrap();
    let pid_probe = unsafe { libc::kill(pid, 0) };
    let pid_probe_errno = std::io::Error::last_os_error().raw_os_error();
    println!(
        "x22_signal_readback success={} code_unit={} signal={} timed_out={} stdout_complete={} stderr_complete={} child_record={record:?} child_pid={pid} pid_probe={pid_probe} pid_probe_errno={pid_probe_errno:?}",
        result["success"].as_bool().unwrap(),
        result["code"].is_unit(),
        result["signal"].as_int().unwrap(),
        result["timed_out"].as_bool().unwrap(),
        result["stdout_complete"].as_bool().unwrap(),
        result["stderr_complete"].as_bool().unwrap(),
    );
    assert_eq!(pid_probe, -1, "signaled child {pid} is still present");
    assert_eq!(pid_probe_errno, Some(libc::ESRCH));
}

#[test]
#[cfg(all(target_os = "linux", not(feature = "no_index")))]
fn repeated_public_run_calls_keep_fd_count_stable() {
    let executable = std::env::current_exe().expect("locate sys_process test executable");
    let output = TempDir::new();
    let stdout_path = output.path().join("isolated-x30.stdout");
    let stderr_path = output.path().join("isolated-x30.stderr");
    let stdout_file = std::fs::File::create(&stdout_path).expect("create isolated X30 stdout log");
    let stderr_file = std::fs::File::create(&stderr_path).expect("create isolated X30 stderr log");
    let mut command = Command::new(executable);
    command
        .args(["--ignored", "--exact", "repeated_public_run_calls_keep_fd_count_stable_isolated", "--nocapture", "--test-threads=1"])
        .stdin(Stdio::null())
        .stdout(Stdio::from(stdout_file))
        .stderr(Stdio::from(stderr_file));
    use std::os::unix::process::CommandExt as _;
    command.process_group(0);
    let mut child = command.spawn().expect("run the isolated X30 descriptor census test");
    let child_pgid = child.id() as libc::pid_t;
    let deadline = Instant::now() + Duration::from_secs(60);
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) if Instant::now() < deadline => std::thread::sleep(Duration::from_millis(10)),
            observed => {
                let reason = match observed {
                    Ok(None) => "timed out after 60 seconds".to_owned(),
                    Err(error) => format!("failed while waiting for isolated test child: {error}"),
                    Ok(Some(_)) => unreachable!(),
                };
                let group_signal = unsafe { libc::kill(-child_pgid, libc::SIGKILL) };
                let group_signal_error = (group_signal == -1).then(std::io::Error::last_os_error);
                let direct_child_kill = child.kill();
                let reaped = child.wait();
                let stdout = std::fs::read_to_string(&stdout_path).unwrap_or_else(|error| format!("<read failed: {error}>"));
                let stderr = std::fs::read_to_string(&stderr_path).unwrap_or_else(|error| format!("<read failed: {error}>"));
                panic!("isolated X30 census {reason}; process-group signal={group_signal} error={group_signal_error:?}; direct-child kill={direct_child_kill:?}; reap={reaped:?}\nstdout:\n{stdout}\nstderr:\n{stderr}");
            }
        }
    };
    let stdout = std::fs::read_to_string(&stdout_path).expect("read isolated X30 stdout log");
    let stderr = std::fs::read_to_string(&stderr_path).expect("read isolated X30 stderr log");
    assert!(status.success(), "isolated X30 census failed with {status}\nstdout:\n{stdout}\nstderr:\n{stderr}");
    assert!(
        stdout.contains("test repeated_public_run_calls_keep_fd_count_stable_isolated ... ok"),
        "isolated test runner did not report the exact census test as passed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    let combined = format!("{stdout}{stderr}");
    assert!(combined.contains("x30_process_run_fd_stability iterations=200"), "isolated test output lacks the 200-run descriptor read-back\nstdout:\n{stdout}\nstderr:\n{stderr}");
    eprint!("{stdout}{stderr}");
}
#[test]
#[ignore = "run by the public X30 test in a fresh process for a stable /proc census"]
#[cfg(all(target_os = "linux", not(feature = "no_index")))]
fn repeated_public_run_calls_keep_fd_count_stable_isolated() {
    let engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    let run_once = || engine.eval::<Map>(r#"run("/bin/true")"#).unwrap_or_else(|error| panic!("public Engine run failed: {error:?}"));

    // The first run may start the package's persistent cleanup worker. Establish
    // the descriptor baseline after that one-time initialization.
    let warmup = run_once();
    assert!(warmup["success"].as_bool().unwrap(), "warm-up result: {warmup:?}");
    assert_eq!(warmup["code"].as_int(), Ok(0), "warm-up result: {warmup:?}");
    let baseline = resource_census_snapshot();

    for iteration in 0..200 {
        let result = run_once();
        assert!(result["success"].as_bool().unwrap(), "iteration {iteration}: {result:?}");
        assert_eq!(result["code"].as_int(), Ok(0), "iteration {iteration}: {result:?}");
    }

    let after = resource_census_wait_for_baseline(baseline);
    assert_eq!(after.1, baseline.1, "200 sequential public run calls changed the descriptor count");
    eprintln!(
        "x30_process_run_fd_stability iterations=200 baseline_tasks={} baseline_fds={} baseline_cleanup_workers={} after_tasks={} after_fds={} after_cleanup_workers={}",
        baseline.0, baseline.1, baseline.2, after.0, after.1, after.2
    );
}

#[test]
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn run_retains_error_when_child_closes_stdin_with_unsent_input() {
    const INPUT_BYTES: usize = 4 * 1024 * 1024;
    let config = SysConfig::default().max_output(1024 * 1024).programs(ProgramPolicy::Any).process_scope(ProcessScope::Managed);
    let mut engine = engine(config);
    engine.set_max_string_size(INPUT_BYTES + 4096);

    let executable = std::env::current_exe().unwrap();
    let executable = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let records = TempDir::new();
    let record_path = records.path().join("early-close-record.txt");
    let ack_path = records.path().join("early-close-observer-ack");
    let intent_path = records.path().join("early-close-intent");
    let record_literal = record_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let ack_literal = ack_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let intent_literal = intent_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let input = "i".repeat(INPUT_BYTES);
    let script = format!(
        r#"run_raw("{executable}", ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {FIXTURE_ENV}: "0", {FIXTURE_RECORD_ENV}: "{record_literal}", RHAI_SYS_PROCESS_CLOSE_STDIN_ACK: "{ack_literal}", RHAI_SYS_PROCESS_CLOSE_STDIN_INTENT: "{intent_literal}", RHAI_SYS_PROCESS_CLOSE_STDIN: "1" }},
            stdin: "{input}", max_output: 1048576, timeout: 3.0
        }})"#
    );

    let host_pid = std::process::id() as i32;
    let host_start = resource_census_start_ticks(host_pid).unwrap().expect("test host start identity");
    let mut sentinel = Sentinel(
        Command::new("/bin/sleep")
            .arg("60")
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("spawn unrelated live sentinel"),
    );
    let sentinel_pid = sentinel.0.id() as i32;
    let (sentinel_state, sentinel_parent, sentinel_group, sentinel_start) = managed_proc_identity(sentinel_pid).expect("read exact sentinel identity");
    assert_ne!(sentinel_state, 'Z', "sentinel must be live before the API call");
    assert_eq!(sentinel_parent, host_pid, "sentinel must remain an exact child of the test host");

    let returned = std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false));
    let monitor_returned = std::sync::Arc::clone(&returned);
    let monitor_record = record_path.clone();
    let monitor = std::thread::spawn(move || {
        let deadline = Instant::now() + Duration::from_secs(4);
        while !monitor_record.exists() && Instant::now() < deadline {
            std::thread::sleep(Duration::from_millis(1));
        }
        let Ok(record) = std::fs::read_to_string(&monitor_record) else {
            return false;
        };
        let fields: std::collections::HashMap<_, _> = record.split_whitespace().filter_map(|field| field.split_once('=')).collect();
        let (Some(pid), Some(start)) = (fields.get("child-pid"), fields.get("child-start")) else {
            return false;
        };
        let (Ok(pid), Ok(start)) = (pid.parse::<i32>(), start.parse::<u64>()) else {
            return false;
        };
        let mut observed_alive = false;
        while !monitor_returned.load(std::sync::atomic::Ordering::Acquire) && Instant::now() < deadline {
            if resource_census_start_ticks(pid).ok().flatten() == Some(start) {
                observed_alive = true;
                if std::fs::write(&ack_path, b"observer confirmed live child\n").is_err() {
                    return false;
                }
                break;
            }
            std::thread::sleep(Duration::from_millis(1));
        }
        observed_alive
    });
    let result = engine.eval::<Map>(&script);
    returned.store(true, std::sync::atomic::Ordering::Release);
    let observed_alive = monitor.join().expect("fixture liveness observer");
    let record_deadline = Instant::now() + Duration::from_secs(2);
    while !record_path.exists() && Instant::now() < record_deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
    let record = std::fs::read_to_string(&record_path).expect("child readiness and capacity receipt");
    let fields: std::collections::HashMap<_, _> = record.split_whitespace().filter_map(|field| field.split_once('=')).collect();
    let pid = fields["child-pid"].parse::<i32>().unwrap();
    let start = fields["child-start"].parse::<u64>().unwrap();
    let pgid = fields["child-pgid"].parse::<i32>().unwrap();
    let capacity = fields["pipe-capacity"].parse::<usize>().unwrap();
    assert_eq!(fields["ready"], "true");
    assert!(capacity > 0 && INPUT_BYTES > capacity, "input bytes {INPUT_BYTES} must exceed actual fd 0 pipe capacity {capacity}");
    assert!(observed_alive, "independent observer must prove fixture {pid}/{start} stayed alive until runner termination");
    assert_eq!(pgid, pid, "Managed child group must be led by the exact owned direct child");
    assert_ne!(pgid, unsafe { libc::getpgrp() }, "Managed child group must be separate from the test host group");
    let child_reap_readback = resource_census_start_ticks(pid);
    assert!(matches!(child_reap_readback, Ok(None)), "exact direct child {pid}/{start} must be reaped before checking API outcome: {child_reap_readback:?}");
    let group_probe = unsafe { libc::kill(-pgid, 0) };
    assert_eq!(group_probe, -1, "owned process group {pgid} remains after cleanup");
    assert_eq!(std::io::Error::last_os_error().raw_os_error(), Some(libc::ESRCH));
    assert_ne!(pgid, sentinel_group, "sentinel must be outside the owned process group");
    assert_eq!(resource_census_start_ticks(host_pid).unwrap(), Some(host_start), "Engine host identity must remain live through API return");
    assert!(
        matches!(
            managed_proc_identity(sentinel_pid),
            Some((state, parent, group, start)) if state != 'Z' && parent == host_pid && group == sentinel_group && start == sentinel_start
        ),
        "unrelated sentinel identity must remain live at the API boundary"
    );

    let (cause, stdout, stderr, stdout_complete, stderr_complete, timed_out) = match result {
        Err(error) => match error.as_ref() {
            EvalAltResult::ErrorRuntime(value, _) => match value.clone().try_cast::<SysError>().unwrap() {
                SysError::Process { cause, report } => (Some(cause), report.stdout_bytes().to_vec(), report.stderr_bytes().to_vec(), report.stdout_complete(), report.stderr_complete(), report.timed_out()),
                other => panic!("unexpected sys error after cleanup: {other:?}"),
            },
            other => panic!("unexpected evaluation error after cleanup: {other:?}"),
        },
        Ok(result) => (
            None,
            result["stdout"].clone().try_cast::<Blob>().expect("raw stdout report"),
            result["stderr"].clone().try_cast::<Blob>().expect("raw stderr report"),
            result["stdout_complete"].as_bool().unwrap(),
            result["stderr_complete"].as_bool().unwrap(),
            result["timed_out"].as_bool().unwrap(),
        ),
    };
    let stdout_marker = stdout.windows(b"early-close-stdout\n".len()).any(|bytes| bytes == b"early-close-stdout\n");
    let stderr_marker = stderr.windows(b"early-close-stderr\n".len()).any(|bytes| bytes == b"early-close-stderr\n");
    let sentinel_kill = sentinel.0.kill();
    let sentinel_wait = sentinel.0.wait();
    let sentinel_reaped = pid_is_absent(sentinel_pid);
    eprintln!(
        "stdin-closure-boundary child={pid} child_start={start} child_pgid={pgid} capacity={capacity} input_bytes={INPUT_BYTES} live_observed={observed_alive} child_reaped=true group_empty=true host={host_pid} host_start={host_start} host_live=true sentinel={sentinel_pid} sentinel_start={sentinel_start} sentinel_pgid={sentinel_group} sentinel_live_at_return=true sentinel_kill={sentinel_kill:?} sentinel_wait={sentinel_wait:?} sentinel_reaped={sentinel_reaped} timed_out={timed_out} stdout_complete={stdout_complete} stderr_complete={stderr_complete} stdout_marker={stdout_marker} stderr_marker={stderr_marker} cause={cause:?} stdout_capture={stdout:?} stderr_capture={stderr:?}"
    );
    assert!(sentinel_kill.is_ok() && sentinel_wait.is_ok() && sentinel_reaped, "exact sentinel cleanup must finish before outcome assertions");
    assert!(
        matches!(
            cause,
            Some(ProcessCause::Io {
                op: "write process stdin",
                kind: std::io::ErrorKind::BrokenPipe,
                ..
            })
        ),
        "wrong primary process cause: {cause:?}"
    );
    assert!(!timed_out, "child stdin closure must not be reported as a deadline");
    assert!(stdout_marker && stderr_marker, "fixture output markers must be retained after child cleanup");
}

#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn valid_child_success_map(value: &Dynamic) -> bool {
    let Some(map) = value.clone().try_cast::<Map>() else {
        return false;
    };
    const KEYS: [&str; 8] = ["code", "signal", "success", "timed_out", "stdout", "stderr", "stdout_complete", "stderr_complete"];
    if map.len() != KEYS.len() || KEYS.iter().any(|key| !map.contains_key(*key)) {
        return false;
    }
    let Some(success) = map.get("success").and_then(|value| value.as_bool().ok()) else {
        return false;
    };
    let Some(timed_out) = map.get("timed_out").and_then(|value| value.as_bool().ok()) else {
        return false;
    };
    let Some(_) = map.get("stdout_complete").and_then(|value| value.as_bool().ok()) else {
        return false;
    };
    let Some(_) = map.get("stderr_complete").and_then(|value| value.as_bool().ok()) else {
        return false;
    };
    let Some(stdout) = map.get("stdout").cloned().and_then(|value| value.try_cast::<String>()) else {
        return false;
    };
    let Some(stderr) = map.get("stderr").cloned().and_then(|value| value.try_cast::<String>()) else {
        return false;
    };
    if timed_out || stdout.len() > 1024 * 1024 || stderr.len() > 1024 * 1024 {
        return false;
    }
    let exit = |key: &str| {
        let value = map.get(key)?;
        if value.is_unit() {
            Some(None)
        } else {
            value.as_int().ok().and_then(|raw| i32::try_from(raw).ok()).map(Some)
        }
    };
    let (Some(code), Some(signal)) = (exit("code"), exit("signal")) else {
        return false;
    };
    if code.is_some() == signal.is_some() {
        return false;
    }
    success == code.map(|value| value == 0).unwrap_or(false)
}

#[test]
#[cfg(all(target_os = "linux", not(feature = "no_index"), not(feature = "no_float")))]
fn spawn_retains_error_when_child_closes_stdin_with_unsent_input() {
    const INPUT_BYTES: usize = 4 * 1024 * 1024;
    let config = SysConfig::default().max_output(1024 * 1024).programs(ProgramPolicy::Any).process_scope(ProcessScope::Managed);
    let mut engine = engine(config);
    engine.set_max_string_size(INPUT_BYTES + 4096);
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let records = TempDir::new();
    let record_path = records.path().join("spawn-early-close-record.txt");
    let ack_path = records.path().join("spawn-early-close-ack");
    let prefill_path = records.path().join("spawn-early-close-prefill");
    let close_ack_path = records.path().join("spawn-early-close-close-ack");
    let intent_path = records.path().join("spawn-early-close-intent");
    let quote = |path: &std::path::Path| path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let record = quote(&record_path);
    let ack = quote(&ack_path);
    let prefill = quote(&prefill_path);
    let close_ack = quote(&close_ack_path);
    let intent = quote(&intent_path);
    let input = "i".repeat(INPUT_BYTES);
    let script = format!(
        r#"spawn("{executable}", ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {FIXTURE_ENV}: "0", {FIXTURE_RECORD_ENV}: "{record}", RHAI_SYS_PROCESS_CLOSE_STDIN_ACK: "{ack}", RHAI_SYS_PROCESS_CLOSE_STDIN_PREFILL: "{prefill}", RHAI_SYS_PROCESS_CLOSE_STDIN_CLOSE_ACK: "{close_ack}", RHAI_SYS_PROCESS_CLOSE_STDIN_INPUT_BYTES: "{INPUT_BYTES}", RHAI_SYS_PROCESS_CLOSE_STDIN_INTENT: "{intent}", RHAI_SYS_PROCESS_CLOSE_STDIN: "1" }},
            stdin: "{input}", max_output: 1048576
        }})"#
    );

    let host_pid = std::process::id() as i32;
    let mut sentinel = Sentinel(
        Command::new("/bin/sleep")
            .arg("60")
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("spawn unrelated sentinel"),
    );
    let sentinel_pid = sentinel.0.id() as i32;
    let mut scope = Scope::new();
    let mut original_handle: Option<Dynamic> = None;
    let mut original_host_identity = None;
    let mut original_sentinel_identity = None;
    let mut observed_child: Option<(i32, u64)> = None;
    let mut observed_group: Option<i32> = None;
    let mut custody_validated = false;
    let partial = std::cell::RefCell::new(String::new());
    let guarded = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let host_identity = managed_proc_identity_checked(host_pid).expect("read exact host identity").expect("host identity exists");
        original_host_identity = Some(host_identity);
        let host_start = host_identity.3;
        let sentinel_identity = managed_proc_identity_checked(sentinel_pid).expect("read exact sentinel identity").expect("sentinel identity exists");
        original_sentinel_identity = Some(sentinel_identity);
        let (sentinel_state, sentinel_parent, sentinel_group, sentinel_start) = sentinel_identity;
        assert_ne!(sentinel_state, 'Z', "sentinel must be a live non-zombie before spawn");
        assert_eq!(sentinel_parent, host_pid);
        let original = engine.eval::<Dynamic>(&script).expect("public spawn returns child handle");
        original_handle = Some(original.clone());
        scope.push_dynamic("child", original.clone());
        scope.push_dynamic("observer", original);
        let readiness_deadline = Instant::now() + Duration::from_secs(4);
        while !record_path.exists() && Instant::now() < readiness_deadline {
            std::thread::sleep(Duration::from_millis(2));
        }
        let ready = std::fs::read_to_string(&record_path).expect("child readiness receipt");
        let fields: std::collections::HashMap<_, _> = ready.split_whitespace().filter_map(|field| field.split_once('=')).collect();
        let pid = fields["child-pid"].parse::<i32>().unwrap();
        let start = fields["child-start"].parse::<u64>().unwrap();
        let pgid = fields["child-pgid"].parse::<i32>().unwrap();
        partial.borrow_mut().push_str(&format!("ready_child={pid}/{start}/{pgid};"));
        let capacity = fields["pipe-capacity"].parse::<usize>().unwrap();
        assert_eq!(fields["ready"], "true");
        assert!(INPUT_BYTES > capacity && capacity > 0, "input {INPUT_BYTES} must exceed actual pipe capacity {capacity}");
        assert!(pid > 0 && start > 0 && pgid > 0, "fixture identity fields must be positive");
        assert_eq!(pgid, pid, "managed group leader is the exact spawned child");
        assert_ne!(pgid, unsafe { libc::getpgrp() }, "child group is distinct from host group");
        assert_ne!(pgid, sentinel_group, "sentinel remains outside owned group");
        let public_id = engine
            .eval_with_scope::<Dynamic>(&mut scope, "child.id")
            .expect("public Child.id is available")
            .as_int()
            .expect("public Child.id is an integer");
        assert_eq!(i32::try_from(public_id).expect("child id fits platform pid"), pid, "fixture PID must match the owned public Child handle");
        let pre_ack_identity = managed_proc_identity_checked(pid);
        assert!(
            matches!(&pre_ack_identity, Ok(Some((state, parent, group, ticks))) if *state != 'Z' && *parent == host_pid && *group == pgid && *ticks == start),
            "full exact non-zombie child identity must be live before observer acknowledgement: {pre_ack_identity:?}"
        );
        observed_child = Some((pid, start));
        observed_group = Some(pgid);
        custody_validated = true;
        partial.borrow_mut().push_str(&format!("custody_validated={custody_validated};pre_ack={pre_ack_identity:?};"));
        std::fs::write(&ack_path, b"observer confirmed live child\n").unwrap();

        let prefill_deadline = Instant::now() + Duration::from_secs(4);
        while !prefill_path.exists() && Instant::now() < prefill_deadline {
            std::thread::sleep(Duration::from_millis(2));
        }
        let prefill_record = std::fs::read_to_string(&prefill_path).expect("full open stdin pipe receipt");
        let prefill_fields: std::collections::HashMap<_, _> = prefill_record.split_whitespace().filter_map(|field| field.split_once('=')).collect();
        let prefill_bytes = prefill_fields["stdin-prefill-bytes"].parse::<usize>().unwrap();
        let prefill_capacity = prefill_fields["pipe-capacity"].parse::<usize>().unwrap();
        let prefill_input_bytes = prefill_fields["input-bytes"].parse::<usize>().unwrap();
        assert_eq!(prefill_fields["child-pid"], pid.to_string());
        assert_eq!(prefill_fields["child-start"], start.to_string());
        assert_eq!(prefill_fields["child-pgid"], pgid.to_string());
        assert_eq!(prefill_fields["ready-to-close"], "true");
        assert_eq!(prefill_capacity, capacity);
        assert_eq!(prefill_bytes, capacity, "fixture must observe a full unread stdin pipe");
        assert!(prefill_input_bytes > capacity);
        let preclose_identity_before = managed_proc_identity_checked(pid);
        let preclose_fd0_before = std::fs::symlink_metadata(format!("/proc/{pid}/fd/0"));
        let preclose_wait = engine.eval_with_scope::<Dynamic>(&mut scope, "child.wait(0.1)");
        let preclose_identity_after = managed_proc_identity_checked(pid);
        let preclose_fd0_after = std::fs::symlink_metadata(format!("/proc/{pid}/fd/0"));
        let preclose_live = |identity: &std::io::Result<Option<(char, i32, i32, u64)>>| matches!(identity, Ok(Some((state, parent, group, ticks))) if *state != 'Z' && *parent == host_pid && *group == pgid && *ticks == start);
        assert!(preclose_wait.as_ref().is_ok_and(Dynamic::is_unit), "bounded wait before child closes stdin must only time out: {preclose_wait:?}");
        assert!(
            preclose_live(&preclose_identity_before) && preclose_live(&preclose_identity_after),
            "exact child must remain live through pre-close wait: before={preclose_identity_before:?} after={preclose_identity_after:?}"
        );
        assert!(
            preclose_fd0_before.is_ok() && preclose_fd0_after.is_ok(),
            "child fd 0 must remain open throughout the bounded pre-close wait: before={preclose_fd0_before:?} after={preclose_fd0_after:?}"
        );
        partial.borrow_mut().push_str(&format!(
            "prefill={prefill_record:?};preclose_wait={preclose_wait:?};preclose_identity_before_after={preclose_identity_before:?}/{preclose_identity_after:?};preclose_fd0_before_after={}/{};",
            preclose_fd0_before.is_ok(),
            preclose_fd0_after.is_ok()
        ));
        std::fs::write(&close_ack_path, b"observer confirmed full pipe and open child fd 0\n").unwrap();

        let intent_deadline = Instant::now() + Duration::from_secs(4);
        while !intent_path.exists() && Instant::now() < intent_deadline {
            std::thread::sleep(Duration::from_millis(2));
        }
        let intent_record = std::fs::read_to_string(&intent_path).expect("pre-close intent receipt");
        partial.borrow_mut().push_str(&format!("intent={intent_record:?};"));
        assert!(intent_record.contains(&format!("child-pid={pid} child-start={start} child-pgid={pgid} stdin-close-intent=true")));

        // Preserve this first bounded observation: a correct implementation reports BrokenPipe here;
        // the baseline currently returns Unit while the child remains live after closing fd 0.
        let first = engine.eval_with_scope::<Dynamic>(&mut scope, "child.wait(3.0)");
        partial.borrow_mut().push_str(&format!("first_wait={first:?};"));
        let first_cause = first.as_ref().err().and_then(|error| match error.as_ref() {
            EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>(),
            _ => None,
        });
        let was_unit = first.as_ref().is_ok_and(Dynamic::is_unit);
        let mut fd_zero_absent_while_live = false;
        let mut fd0_live_before_after = None;
        if was_unit {
            let live_before = managed_proc_identity_checked(pid);
            let fd_observation = std::fs::symlink_metadata(format!("/proc/{pid}/fd/0"));
            let fd_absent = matches!(&fd_observation, Err(error) if error.kind() == std::io::ErrorKind::NotFound);
            let live_after = managed_proc_identity_checked(pid);
            let exact_live_before_after = fd_absent
                && matches!(&live_before, Ok(Some((state, parent, group, ticks))) if *state != 'Z' && *parent == host_pid && *group == pgid && *ticks == start)
                && matches!(&live_after, Ok(Some((state, parent, group, ticks))) if *state != 'Z' && *parent == host_pid && *group == pgid && *ticks == start);
            fd0_live_before_after = Some((live_before, fd_absent, live_after));
            partial
                .borrow_mut()
                .push_str(&format!("fd0_observation={fd_observation:?};fd0_live_before_after={fd0_live_before_after:?};"));
            fd_zero_absent_while_live = exact_live_before_after;
        }

        let kill_result = engine.eval_with_scope::<Dynamic>(&mut scope, "child.kill()");
        partial.borrow_mut().push_str(&format!("kill_original={kill_result:?};"));
        let cleanup = engine.eval_with_scope::<Dynamic>(&mut scope, "observer.wait(5.0)");
        partial.borrow_mut().push_str(&format!("cleanup_original={cleanup:?};"));
        let repeated_wait = engine.eval_with_scope::<Dynamic>(&mut scope, "observer.wait(0.1)");
        partial.borrow_mut().push_str(&format!("repeated_wait_original={repeated_wait:?};"));
        let repeated_try_wait = engine.eval_with_scope::<Dynamic>(&mut scope, "child.try_wait()");
        partial.borrow_mut().push_str(&format!("repeated_try_wait_original={repeated_try_wait:?};"));
        let repeated_kill = engine.eval_with_scope::<Dynamic>(&mut scope, "observer.kill()");
        partial.borrow_mut().push_str(&format!("repeated_kill_original={repeated_kill:?};"));
        let retained_error = |error: &Box<EvalAltResult>| match error.as_ref() {
            EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>().map(|error| format!("{error:?}")),
            _ => None,
        };
        let first_error_text = first.as_ref().err().and_then(retained_error);
        let first_typed_cause = first_cause.clone();
        let repeated_error_text = repeated_wait.as_ref().err().and_then(retained_error);
        let repeated_try_error_text = repeated_try_wait.as_ref().err().and_then(retained_error);
        let cleanup_error_text = cleanup.as_ref().err().and_then(retained_error);
        let cleanup_cause = cleanup.as_ref().err().and_then(|error| match error.as_ref() {
            EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>(),
            _ => None,
        });
        let repeated_cause = repeated_wait.as_ref().err().and_then(|error| match error.as_ref() {
            EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>(),
            _ => None,
        });
        let repeated_try_cause = repeated_try_wait.as_ref().err().and_then(|error| match error.as_ref() {
            EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>(),
            _ => None,
        });
        let (cleanup_outcome, stdout, stderr, stdout_complete, stderr_complete, timed_out, exit_code, exit_signal, success, cleanup_diagnostics, raw_markers) = match cleanup {
            Ok(value) if value.is_unit() => {
                panic!("bounded final Child.wait unexpectedly returned unit: {value:?}")
            }
            Ok(value) => {
                let original_map = value.clone();
                partial
                    .borrow_mut()
                    .push_str(&format!("cleanup_original_success_map={original_map:?};capture_source=child-success-map-lossy-utf8;cleanup_diagnostics=unavailable-public-map;"));
                assert!(valid_child_success_map(&value), "terminal Child.wait success must have the exact checked public map schema: {original_map:?}");
                let report = value.try_cast::<Map>().expect("validated nonunit Child.wait result must be a report map");
                let field = |key: &str| report.get(key).cloned().unwrap_or_else(|| panic!("success map missing required field {key}"));
                let output = |key: &str| field(key).try_cast::<String>().unwrap_or_else(|| panic!("success map {key} must be a string"));
                let flag = |key: &str| field(key).as_bool().unwrap_or_else(|_| panic!("success map {key} must be a bool"));
                let optional_exit = |key: &str| {
                    let value = field(key);
                    if value.is_unit() {
                        None
                    } else {
                        Some(i32::try_from(value.as_int().unwrap_or_else(|_| panic!("success map {key} must be integer or unit"))).unwrap_or_else(|_| panic!("success map {key} does not fit i32")))
                    }
                };
                let stdout = output("stdout");
                let stderr = output("stderr");
                let stdout_complete = flag("stdout_complete");
                let stderr_complete = flag("stderr_complete");
                let timed_out = flag("timed_out");
                let success = flag("success");
                let exit_code = optional_exit("code");
                let exit_signal = optional_exit("signal");
                (format!("success-map:{original_map:?}"), stdout, stderr, stdout_complete, stderr_complete, Some(timed_out), exit_code, exit_signal, Some(success), None, None)
            }
            Err(error) => {
                partial
                    .borrow_mut()
                    .push_str(&format!("cleanup_original_error={error:?};capture_source=typed-ProcessReport-raw-bytes;"));
                let retained = match error.as_ref() {
                    EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>(),
                    _ => None,
                };
                match retained {
                    Some(SysError::Process { report, .. }) => {
                        let raw_stdout_marker = report.stdout_bytes().windows(b"early-close-stdout\n".len()).any(|bytes| bytes == b"early-close-stdout\n");
                        let raw_stderr_marker = report.stderr_bytes().windows(b"early-close-stderr\n".len()).any(|bytes| bytes == b"early-close-stderr\n");
                        (
                            format!("error:{error:?}"),
                            String::from_utf8_lossy(report.stdout_bytes()).into_owned(),
                            String::from_utf8_lossy(report.stderr_bytes()).into_owned(),
                            report.stdout_complete(),
                            report.stderr_complete(),
                            Some(report.timed_out()),
                            report.exit_code(),
                            report.exit_signal(),
                            None,
                            Some(report.cleanup_diagnostics().len()),
                            Some((raw_stdout_marker, raw_stderr_marker)),
                        )
                    }
                    _ => panic!("final Child.wait error did not contain a decodable Process report: {error:?}"),
                }
            }
        };
        partial.borrow_mut().push_str(&format!(
            "cleanup={cleanup_outcome};stdout_utf8={stdout:?};stderr_utf8={stderr:?};stdout_complete={stdout_complete};stderr_complete={stderr_complete};timed_out={timed_out:?};exit_code={exit_code:?};exit_signal={exit_signal:?};success={success:?};diagnostics={cleanup_diagnostics:?};"
        ));
        let stdout_marker = stdout.contains("early-close-stdout\n");
        let stderr_marker = stderr.contains("early-close-stderr\n");
        let child_after = managed_proc_identity_checked(pid);
        let child_reaped = matches!(&child_after, Ok(None));
        let group_probe = if custody_validated && pgid > 0 { Some(unsafe { libc::kill(-pgid, 0) }) } else { None };
        let group_errno = group_probe.filter(|result| *result == -1).map(|_| std::io::Error::last_os_error().raw_os_error());
        let group_empty = group_probe == Some(-1) && group_errno == Some(Some(libc::ESRCH));
        let host_after = managed_proc_identity_checked(host_pid);
        let host_live = matches!(&host_after, Ok(Some((state, parent, group, ticks))) if *state != 'Z' && *parent == host_identity.1 && *group == host_identity.2 && *ticks == host_start);
        let sentinel_after = managed_proc_identity_checked(sentinel_pid);
        let sentinel_live = matches!(&sentinel_after, Ok(Some((state, parent, group, ticks))) if *state != 'Z' && *parent == host_pid && *group == sentinel_group && *ticks == sentinel_start);
        partial
            .borrow_mut()
            .push_str(&format!("child_after={child_after:?};group_probe={group_probe:?}/{group_errno:?};host_after={host_after:?};sentinel_after={sentinel_after:?};"));
        let first_text = match &first {
            Ok(value) => format!("unit={} value={value:?}", value.is_unit()),
            Err(error) => format!("error={error:?}"),
        };
        eprintln!("spawn-stdin-closure child={pid} start={start} pgid={pgid} capacity={capacity} input_bytes={INPUT_BYTES} executable={executable} first={first_text} prefill={prefill_record:?} preclose_wait={preclose_wait:?} preclose_identity_before_after={preclose_identity_before:?}/{preclose_identity_after:?} preclose_fd0_before_after={}/{} intent={intent_record:?} pre_ack={pre_ack_identity:?} fd0_before_absent_after={fd0_live_before_after:?} fd0_absent_while_live={fd_zero_absent_while_live} kill={kill_result:?} cleanup={cleanup_outcome} repeated_wait={repeated_wait:?} repeated_try_wait={repeated_try_wait:?} repeated_kill={repeated_kill:?} reaped={child_reaped} group_empty={group_empty} host={host_pid}/{host_identity:?}/{host_after:?} host_live={host_live} sentinel={sentinel_pid}/{sentinel_state}/{sentinel_parent}/{sentinel_group}/{sentinel_start} sentinel_live={sentinel_live} timed_out={timed_out:?} stdout_complete={stdout_complete} stderr_complete={stderr_complete} stdout_marker={stdout_marker} stderr_marker={stderr_marker} stdout={stdout:?} stderr={stderr:?}", preclose_fd0_before.is_ok(), preclose_fd0_after.is_ok());

        let sentinel_kill = sentinel.0.kill();
        let sentinel_wait_deadline = Instant::now() + Duration::from_secs(2);
        let mut sentinel_wait = sentinel.0.try_wait();
        while matches!(&sentinel_wait, Ok(None)) && Instant::now() < sentinel_wait_deadline {
            std::thread::sleep(Duration::from_millis(10));
            sentinel_wait = sentinel.0.try_wait();
        }
        let sentinel_after = managed_proc_identity_checked(sentinel_pid);
        let sentinel_reaped = matches!(&sentinel_wait, Ok(Some(_))) && matches!(&sentinel_after, Ok(None));
        let final_host_identity = managed_proc_identity_checked(host_pid);
        let host_unchanged_after_sentinel = matches!((&final_host_identity, host_identity), (Ok(Some((state, parent, group, ticks))), (original_state, original_parent, original_group, original_ticks)) if *state != 'Z' && *state == original_state && *parent == original_parent && *group == original_group && *ticks == original_ticks);
        partial
            .borrow_mut()
            .push_str(&format!("sentinel_kill={sentinel_kill:?};sentinel_try_wait={sentinel_wait:?};sentinel_after={sentinel_after:?};final_host_identity={final_host_identity:?};"));
        eprintln!("spawn-stdin-closure-final sentinel_kill={sentinel_kill:?} sentinel_wait={sentinel_wait:?} sentinel_reaped={sentinel_reaped} child={pid}/{start}/{pgid} child_reaped={child_reaped} group_empty={group_empty} host={host_pid}/{host_start} sentinel_original={sentinel_state}/{sentinel_parent}/{sentinel_group}/{sentinel_start}");
        assert!(kill_result.is_ok(), "explicit public Child.kill must complete");
        assert!(child_reaped && group_empty && host_live && sentinel_live, "owned child/group cleanup and unrelated identities must be proven before outcome assertion");
        assert!(
            sentinel_kill.is_ok() && sentinel_reaped && host_unchanged_after_sentinel,
            "sentinel cleanup and unchanged host must be proven before outcome assertion: host={final_host_identity:?}"
        );
        assert!(!was_unit || fd_zero_absent_while_live, "Unit baseline requires exact live child identity before and after observing fd 0 absent");
        if was_unit {
            assert!(cleanup_error_text.is_none(), "baseline explicit cleanup must produce a healthy process report, not an error: {cleanup_error_text:?}");
        }
        assert_eq!(timed_out, Some(false), "Child reports must not claim a run deadline");
        assert!(exit_code.is_some() ^ exit_signal.is_some(), "final cleanup report must include exactly one exit variant: exit_code={exit_code:?}, exit_signal={exit_signal:?}");
        if cleanup_diagnostics.is_none() {
            assert_eq!(success, exit_code.map(|code| code == 0).or_else(|| exit_signal.map(|_| false)), "successful map flag must agree with the observed exit");
        }
        assert!(stdout.len() <= 1024 * 1024 && stderr.len() <= 1024 * 1024, "decoded captures must respect configured per-stream output bound");
        if cleanup_diagnostics.is_some() {
            assert_eq!(cleanup_diagnostics, Some(0), "typed ProcessReport must have no cleanup diagnostics");
        }
        assert!(stdout_marker && stderr_marker, "bounded final report must retain both pre-close markers");
        if cleanup_diagnostics.is_some() {
            assert_eq!(raw_markers, Some((true, true)), "typed GREEN ProcessReport must retain both markers in its actual raw bytes");
        }
        if first_error_text.is_some() {
            assert_eq!(cleanup_error_text, first_error_text, "cleanup wait must preserve the original process cause and report");
            assert_eq!(cleanup_cause, first_cause, "cleanup must preserve the original cause, raw bytes, flags, exit and diagnostics");
            assert_eq!(repeated_cause, first_typed_cause, "repeated wait must preserve the complete typed process report");
            assert_eq!(repeated_try_cause, first_typed_cause, "try_wait must preserve the complete typed process report");
        }
        assert!(
            matches!(first_cause, Some(SysError::Process { cause: ProcessCause::Io { op: "write child stdin", target, kind: std::io::ErrorKind::BrokenPipe, message }, .. }) if target == executable && !message.is_empty()),
            "first bounded Child.wait must retain stdin BrokenPipe with executable target and OS message; observed {first_text}; live_fd0_absence={fd_zero_absent_while_live}"
        );
        assert!(repeated_wait.is_err() && repeated_try_wait.is_err() && repeated_kill.is_ok(), "cloned handles must retain terminal error and idempotent kill");
        assert_eq!(repeated_error_text, first_error_text, "repeated bounded wait through cloned handle must preserve the original error and report");
        assert_eq!(repeated_try_error_text, first_error_text, "try_wait through the other cloned handle must preserve the original error and report");
    }));
    if let Err(payload) = guarded {
        // Keep ownership explicit when parsing or an assertion unwinds before normal cleanup.
        let fallback_kill = engine.eval_with_scope::<Dynamic>(&mut scope, "child.kill()");
        let fallback_wait = engine.eval_with_scope::<Dynamic>(&mut scope, "observer.wait(5.0)");
        let valid_terminal_process_error = |error: &Box<EvalAltResult>| match error.as_ref() {
            EvalAltResult::ErrorRuntime(value, _) => match value.clone().try_cast::<SysError>() {
                Some(SysError::Process { report, .. }) => report.timed_out() == false && (report.exit_code().is_some() ^ report.exit_signal().is_some()),
                _ => false,
            },
            _ => false,
        };
        let fallback_wait_kind = match &fallback_wait {
            Ok(value) if value.is_unit() => "unit",
            Ok(value) if valid_child_success_map(value) => "terminal-success-map",
            Ok(_) => "unexpected-value",
            Err(error) if valid_terminal_process_error(error) => "terminal-typed-process-error",
            Err(_) => "unexpected-error",
        };
        partial
            .borrow_mut()
            .push_str(&format!("fallback_kill={fallback_kill:?};fallback_wait={fallback_wait:?};fallback_wait_kind={fallback_wait_kind};"));
        let child_readback = observed_child.map(|(pid, start)| (pid, start, managed_proc_identity_checked(pid)));
        let group_readback = observed_group.map(|pgid| {
            let result = unsafe { libc::kill(-pgid, 0) };
            (pgid, result, std::io::Error::last_os_error().raw_os_error())
        });
        let original_sentinel = original_sentinel_identity;
        let sentinel_before_cleanup = managed_proc_identity_checked(sentinel_pid);
        let sentinel_probe = sentinel.0.try_wait();
        let sentinel_probe_text = format!("{sentinel_probe:?}");
        let sentinel_identity_bound = match (original_sentinel.as_ref(), &sentinel_before_cleanup, &sentinel_probe) {
            (Some((original_state, original_parent, original_group, original_start)), Ok(Some((state, parent, group, start))), _) => *original_state != 'Z' && *state != 'Z' && parent == original_parent && group == original_group && start == original_start,
            (Some((original_state, _, _, _)), Ok(None), Ok(Some(_))) => *original_state != 'Z',
            _ => false,
        };
        let sentinel_kill = if !matches!(&sentinel_probe, Ok(Some(_))) { Some(sentinel.0.kill()) } else { None };
        let sentinel_deadline = Instant::now() + Duration::from_secs(2);
        let mut sentinel_wait = sentinel_probe;
        while matches!(&sentinel_wait, Ok(None)) && Instant::now() < sentinel_deadline {
            std::thread::sleep(Duration::from_millis(10));
            sentinel_wait = sentinel.0.try_wait();
        }
        let sentinel_after = managed_proc_identity_checked(sentinel_pid);
        let host_after = managed_proc_identity_checked(host_pid);
        let sentinel_reaped = matches!(&sentinel_wait, Ok(Some(_))) && matches!(&sentinel_after, Ok(None));
        let host_unchanged = matches!((&original_host_identity, &host_after), (Some((_, parent, group, start)), Ok(Some((state, now_parent, now_group, now_start)))) if *state != 'Z' && parent == now_parent && group == now_group && start == now_start);
        let child_absent = matches!(&child_readback, Some((_, _, Ok(None))));
        let group_absent = custody_validated && group_readback.is_some_and(|(_, result, error)| result == -1 && error == Some(libc::ESRCH));
        let terminal = matches!(fallback_wait_kind, "terminal-success-map" | "terminal-typed-process-error");
        let cleanup_complete = child_absent && group_absent && host_unchanged && sentinel_identity_bound && sentinel_reaped && fallback_kill.is_ok() && terminal;
        eprintln!("spawn-stdin-closure-partial observations={} child={child_readback:?} group={group_readback:?} host={host_pid}/{original_host_identity:?}/{host_after:?} sentinel={sentinel_pid}/{original_sentinel:?} sentinel_before={sentinel_before_cleanup:?} sentinel_probe={sentinel_probe_text} sentinel_identity_bound={sentinel_identity_bound} sentinel_kill={sentinel_kill:?} sentinel_wait={sentinel_wait:?} sentinel_after={sentinel_after:?} sentinel_reaped={sentinel_reaped} fallback_kill={fallback_kill:?} fallback_wait={fallback_wait:?} fallback_wait_kind={fallback_wait_kind} cleanup_complete={cleanup_complete}", partial.into_inner());
        std::panic::resume_unwind(payload);
    }
}
#[test]
#[cfg(not(feature = "no_index"))]
fn run_io_contract_empty_output() {
    let engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    let records = TempDir::new();
    let record_path = records.path().join("empty-output-child.txt");
    let record_literal = record_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script = format!(r#"run("/bin/sh", ["-c", "printf 'child-pid=%s\\nchild-exit=0\\n' \"$$\" > \"$RECORD\""], #{{ env_clear: true, env: #{{ RECORD: "{record_literal}" }}, max_output: 1024, timeout: 5 }})"#);

    let result = engine.eval::<Map>(&script).unwrap();
    assert!(result["success"].as_bool().unwrap());
    assert_eq!(result["code"].as_int().unwrap(), 0);
    assert!(!result["timed_out"].as_bool().unwrap());
    assert!(result["stdout_complete"].as_bool().unwrap());
    assert!(result["stderr_complete"].as_bool().unwrap());
    assert_eq!(result["stdout"].as_immutable_string_ref().unwrap().as_str(), "");
    assert_eq!(result["stderr"].as_immutable_string_ref().unwrap().as_str(), "");
    let child_record = std::fs::read_to_string(&record_path).unwrap();
    assert_child_record(&record_path, 0);
    eprintln!("x14_empty_output stdout_len=0 stderr_len=0 child_record={:?} child_reaped=true", child_record.trim());
}

#[test]
#[cfg(all(feature = "f32_float", not(feature = "no_index"), not(feature = "no_float")))]
fn f32_process_timeouts_validate_before_launch_and_preserve_host_output_bounds() {
    let engine = engine(SysConfig::default().max_output(4).programs(ProgramPolicy::AllowList(vec!["/bin/sh".into()])));
    let records = TempDir::new();
    let record = records.path().join("f32-child.txt");
    let record_literal = record.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script = format!(r#"run("/bin/sh", ["-c", "printf 'child-pid=%s\\nchild-exit=0\\n' \"$$\" > \"$RECORD\"; printf ok"], #{{ env_clear: true, env: #{{ RECORD: "{record_literal}" }}, timeout: seconds, max_output: 4096 }})"#);
    for seconds in [rhai::FLOAT::NAN, rhai::FLOAT::INFINITY, rhai::FLOAT::NEG_INFINITY, -0.5, rhai::FLOAT::MAX] {
        let mut scope = Scope::new();
        scope.push("seconds", seconds);
        let error = engine.eval_with_scope::<Map>(&mut scope, &script).unwrap_err();
        let typed = match error.as_ref() {
            EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>().unwrap(),
            other => panic!("expected typed duration denial for {seconds:?}, got {other:?}"),
        };
        assert!(matches!(typed, SysError::Denied(_)), "invalid f32 duration must be denied: {typed:?}");
        assert!(!record.exists(), "invalid f32 duration started a real child: {seconds:?}");
    }
    let mut scope = Scope::new();
    scope.push("seconds", 0.5 as rhai::FLOAT);
    let result = engine.eval_with_scope::<Map>(&mut scope, &script).unwrap();
    assert_child_record(&record, 0);
    assert_eq!(result["code"].as_int().unwrap(), 0, "finite fractional f32 timeout preserves normal completion");
    assert!(result["success"].as_bool().unwrap());
    assert!(!result["timed_out"].as_bool().unwrap());
    assert!(result["stdout_complete"].as_bool().unwrap() && result["stderr_complete"].as_bool().unwrap());
    assert_eq!(result["stdout"].as_immutable_string_ref().unwrap().as_str(), "ok");
    assert_eq!(result["stderr"].as_immutable_string_ref().unwrap().as_str(), "");
    std::fs::remove_file(&record).unwrap();
    let over_cap = script.replace("; printf ok", "; printf abcde");
    assert_ne!(over_cap, script, "output-cap control must change the child's actual output");
    let error = engine.eval_with_scope::<Map>(&mut scope, &over_cap).unwrap_err();
    assert_child_record(&record, 0);
    assert_output_limit_error(error, "stdout", b"abcd");
    eprintln!("f32_process invalid_durations_no_child=5 finite_fractional_success=true host_cap=4 retained_prefix=abcd children_reaped=true");
}

#[test]
#[cfg(not(feature = "no_index"))]
fn run_io_contract_string_stdin_round_trip() {
    let engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    let records = TempDir::new();
    let record_path = records.path().join("string-stdin-child.txt");
    let record_literal = record_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let expected = "first process input line\nsecond process input line\n";
    let input_literal = expected.replace('\\', "\\\\").replace('\n', "\\n");
    let script = format!(r#"run("/bin/sh", ["-c", "printf 'child-pid=%s\\nchild-exit=0\\n' \"$$\" > \"$RECORD\"; exec /bin/cat"], #{{ env_clear: true, env: #{{ RECORD: "{record_literal}" }}, stdin: "{input_literal}", max_output: 1024, timeout: 5 }})"#);

    let result = engine.eval::<Map>(&script).unwrap();
    assert!(result["success"].as_bool().unwrap());
    assert_eq!(result["code"].as_int().unwrap(), 0);
    assert!(!result["timed_out"].as_bool().unwrap());
    assert!(result["stdout_complete"].as_bool().unwrap());
    assert!(result["stderr_complete"].as_bool().unwrap());
    assert_eq!(result["stdout"].as_immutable_string_ref().unwrap().as_str(), expected);
    assert_eq!(result["stderr"].as_immutable_string_ref().unwrap().as_str(), "");
    let child_record = std::fs::read_to_string(&record_path).unwrap();
    assert_child_record(&record_path, 0);
    eprintln!("x16_string_stdin bytes={} exact_round_trip=true child_record={:?} child_reaped=true", expected.len(), child_record.trim());
}

#[test]
#[cfg(not(feature = "no_index"))]
fn run_io_contract_blob_stdin_round_trip_with_concurrent_output() {
    const INPUT_BYTES: usize = 1024 * 1024;
    const STREAM_BYTES: usize = 256 * 1024;
    const OUTPUT_LIMIT: usize = 2 * 1024 * 1024;
    let engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    let executable = std::env::current_exe().unwrap();
    let executable = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let records = TempDir::new();
    let record_path = records.path().join("blob-stdin-child.txt");
    let expected_path = records.path().join("expected-input.bin");
    let received_path = records.path().join("received-input.bin");
    let input: Blob = (0..INPUT_BYTES).map(|index| ((index * 31 + 17) & 0xff) as u8).collect();
    std::fs::write(&expected_path, &input).unwrap();
    let record_literal = record_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let expected_literal = expected_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let received_literal = received_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script = format!(
        r#"run_raw("{executable}", ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {FIXTURE_ENV}: "0", {FIXTURE_RECORD_ENV}: "{record_literal}", RHAI_SYS_PROCESS_IO_STRESS: "1", RHAI_SYS_PROCESS_IO_BYTES: "{INPUT_BYTES}", RHAI_SYS_PROCESS_STDOUT_BYTES: "{STREAM_BYTES}", RHAI_SYS_PROCESS_STDERR_BYTES: "{STREAM_BYTES}", RHAI_SYS_PROCESS_IO_EXPECTED: "{expected_literal}", RHAI_SYS_PROCESS_IO_RECEIVED: "{received_literal}", RHAI_SYS_PROCESS_IO_ECHO: "1" }},
            stdin: payload, max_output: {OUTPUT_LIMIT}, timeout: 10
        }})"#
    );
    let mut scope = Scope::new();
    scope.push("payload", input.clone());

    let result = engine.eval_with_scope::<Map>(&mut scope, &script).unwrap();
    assert!(result["success"].as_bool().unwrap(), "blob child exited unsuccessfully: code={:?}", result["code"]);
    assert_eq!(result["code"].as_int().unwrap(), 0);
    assert!(!result["timed_out"].as_bool().unwrap());
    assert!(result["stdout_complete"].as_bool().unwrap());
    assert!(result["stderr_complete"].as_bool().unwrap());
    let stdout = result["stdout"].clone().try_cast::<Blob>().unwrap();
    let stderr = result["stderr"].clone().try_cast::<Blob>().unwrap();
    let mut expected_stdout = LIBTEST_QUIET_START.to_vec();
    expected_stdout.extend(std::iter::repeat(b'o').take(STREAM_BYTES));
    expected_stdout.extend_from_slice(&input);
    let first_stdout_difference = stdout.iter().zip(&expected_stdout).position(|(actual, expected)| actual != expected);
    assert!(stdout == expected_stdout, "stdout contract mismatch: observed_bytes={} expected_bytes={} first_difference={first_stdout_difference:?}", stdout.len(), expected_stdout.len());
    let expected_stderr = vec![b'e'; STREAM_BYTES];
    let first_stderr_difference = stderr.iter().zip(&expected_stderr).position(|(actual, expected)| actual != expected);
    assert!(stderr == expected_stderr, "stderr contract mismatch: observed_bytes={} expected_bytes={} first_difference={first_stderr_difference:?}", stderr.len(), expected_stderr.len());
    let received = std::fs::read(&received_path).unwrap();
    let first_input_difference = received.iter().zip(&input).position(|(actual, expected)| actual != expected);
    assert!(received == input, "child stdin readback mismatch: observed_bytes={} expected_bytes={} first_difference={first_input_difference:?}", received.len(), input.len());
    let child_record = std::fs::read_to_string(&record_path).unwrap();
    assert_io_stress_record(&record_path, INPUT_BYTES, true);
    eprintln!(
        "x17_blob_stdin bytes={INPUT_BYTES} received_bytes={} stdout_bytes={} stderr_bytes={} exact_round_trip=true concurrent_streams=true child_record={:?} child_reaped=true",
        received.len(),
        stdout.len(),
        stderr.len(),
        child_record.trim()
    );
}

#[test]
#[cfg(not(feature = "no_index"))]
fn process_supervisor_handles_large_simultaneous_io_and_exact_per_stream_caps() {
    const INPUT_BYTES: usize = 128 * 1024;
    const CAP: usize = 256 * 1024;
    const EXPECTED_OUTPUT_BYTE: u8 = b'o';
    let engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    let executable = std::env::current_exe().unwrap();
    let executable = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let records = TempDir::new();
    let record_path = records.path().join("exact-cap.txt");
    let record_literal = record_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let script = io_stress_script(&executable, &record_literal, INPUT_BYTES, CAP - LIBTEST_QUIET_START.len(), CAP, CAP, 5.0);
    let result = engine.eval::<Map>(&script).unwrap();
    let stdout = result["stdout"].clone().try_cast::<Blob>().unwrap();
    let stderr = result["stderr"].clone().try_cast::<Blob>().unwrap();
    let mut expected_stdout = LIBTEST_QUIET_START.to_vec();
    expected_stdout.extend(std::iter::repeat(EXPECTED_OUTPUT_BYTE).take(CAP - LIBTEST_QUIET_START.len()));
    assert_eq!(stdout.len(), expected_stdout.len(), "stdout length mismatch");
    for (index, (actual, expected)) in stdout.iter().zip(&expected_stdout).enumerate() {
        assert_eq!(actual, expected, "stdout differs at byte {index}");
    }
    assert_eq!(stderr.len(), CAP, "stderr length mismatch");
    for (index, byte) in stderr.iter().enumerate() {
        assert_eq!(*byte, b'e', "stderr differs at byte {index}");
    }
    assert!(result["success"].as_bool().unwrap());
    assert!(result["stdout_complete"].as_bool().unwrap());
    assert!(result["stderr_complete"].as_bool().unwrap());
    assert_io_stress_record(&records.path().join("exact-cap.txt"), INPUT_BYTES, true);
}

#[test]
#[cfg(not(feature = "no_index"))]
fn process_output_limit_is_primary_and_retains_each_stream_prefix_at_n_plus_one() {
    const INPUT_BYTES: usize = 96 * 1024;
    const CAP: usize = 4096;
    let engine = engine(SysConfig::default().programs(ProgramPolicy::Any));
    let executable = std::env::current_exe().unwrap();
    let executable = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");

    for stream in ["stdout", "stderr"] {
        let records = TempDir::new();
        let record_path = records.path().join(format!("{stream}-overflow.txt"));
        let record_literal = record_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let stdout_payload = if stream == "stdout" { CAP - LIBTEST_QUIET_START.len() + 1 } else { 0 };
        let stderr_payload = if stream == "stderr" { CAP + 1 } else { 0 };
        let script = io_stress_script(&executable, &record_literal, INPUT_BYTES, stdout_payload, stderr_payload, CAP, 5.0);
        let error = engine.eval::<Map>(&script).unwrap_err();
        let expected_prefix = if stream == "stdout" {
            let mut prefix = LIBTEST_QUIET_START.to_vec();
            prefix.extend(std::iter::repeat(b'o').take(CAP - LIBTEST_QUIET_START.len()));
            prefix
        } else {
            vec![b'e'; CAP]
        };
        assert_output_limit_error(error, stream, &expected_prefix);
        assert_io_stress_record(&record_path, INPUT_BYTES, false);
    }
}

#[test]
#[cfg(not(feature = "no_index"))]
fn process_script_output_option_cannot_raise_the_host_cap() {
    const CAP: usize = 4096;
    let engine = engine(SysConfig::default().max_output(CAP).programs(ProgramPolicy::Any));
    let executable = std::env::current_exe().unwrap();
    let executable = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    for stream in ["stdout", "stderr"] {
        let records = TempDir::new();
        let record_path = records.path().join(format!("host-cap-{stream}.txt"));
        let record_literal = record_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let stdout_payload = if stream == "stdout" { CAP - LIBTEST_QUIET_START.len() + 1 } else { 0 };
        let stderr_payload = if stream == "stderr" { CAP + 1 } else { 0 };
        let script = io_stress_script(&executable, &record_literal, 0, stdout_payload, stderr_payload, CAP * 2, 5.0);
        let error = engine.eval::<Map>(&script).unwrap_err();
        // Read the independent record and prove reaping before checking the bounded prefix.
        assert_io_stress_record(&record_path, 0, false);
        let expected_prefix = if stream == "stdout" {
            let mut prefix = LIBTEST_QUIET_START.to_vec();
            prefix.extend(std::iter::repeat(b'o').take(CAP - LIBTEST_QUIET_START.len()));
            prefix
        } else {
            vec![b'e'; CAP]
        };
        assert_output_limit_error(error, stream, &expected_prefix);
    }
}

#[test]
#[cfg(not(feature = "no_index"))]
fn zero_output_cap_reports_output_limit_with_an_empty_retained_prefix() {
    let engine = engine(SysConfig::permissive().programs(ProgramPolicy::Any));
    for stream in ["none", "stdout", "stderr"] {
        let records = TempDir::new();
        let record_path = records.path().join(format!("zero-cap-{stream}.txt"));
        let record_literal = record_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let output = match stream {
            "none" => "",
            "stdout" => "; printf x",
            "stderr" => "; printf x >&2",
            _ => unreachable!(),
        };
        let script = format!(r#"run("/bin/sh", #{{ env_clear: true, env: #{{ RECORD: "{record_literal}" }}, stdin: "printf 'child-pid=%s\\n' \"$$\" > \"$RECORD\"{output}", max_output: 0, timeout: 5 }})"#);
        if stream == "none" {
            let result = engine.eval::<Map>(&script).unwrap();
            assert!(result["success"].as_bool().unwrap());
            assert_eq!(result["code"].as_int().unwrap(), 0);
            assert!(result["stdout_complete"].as_bool().unwrap());
            assert!(result["stderr_complete"].as_bool().unwrap());
            assert!(result["stdout"].as_immutable_string_ref().unwrap().as_str().is_empty());
            assert!(result["stderr"].as_immutable_string_ref().unwrap().as_str().is_empty());
        } else {
            let error = engine.eval::<Map>(&script).unwrap_err();
            assert_output_limit_error(error, stream, &[]);
        }
        let record = std::fs::read_to_string(record_path).unwrap();
        let pid: libc::pid_t = record.trim().strip_prefix("child-pid=").unwrap().parse().unwrap();
        assert_eq!(unsafe { libc::kill(pid, 0) }, -1, "zero-cap {stream} child {pid} is still present");
        assert_eq!(std::io::Error::last_os_error().raw_os_error(), Some(libc::ESRCH));
    }
}

#[test]
#[cfg(not(feature = "no_index"))]
fn run_deadline_returns_bounded_partial_output_after_terminating_child() {
    let config = SysConfig::default().programs(ProgramPolicy::Any);
    #[cfg(feature = "no_float")]
    let config = config.default_timeout(Some(0.1));
    let engine = engine(config);
    // Integer-only scripts use the same fractional deadline configured by the host.
    let timeout_option = if cfg!(feature = "no_float") { "" } else { "timeout: 0.1" };
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
                {timeout_option}
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
fn run_deadline_with_blocked_stdin_and_active_stdout_stderr() {
    const INPUT_BYTES: usize = 512 * 1024;
    const OUTPUT_LIMIT: usize = 64 * 1024 * 1024;
    let config = SysConfig::default().max_output(OUTPUT_LIMIT).programs(ProgramPolicy::Any);
    #[cfg(feature = "no_float")]
    let config = config.default_timeout(Some(0.25));
    let mut engine = engine(config);
    #[cfg(not(feature = "unchecked"))]
    engine.set_max_string_size(OUTPUT_LIMIT);
    let timeout_option = if cfg!(feature = "no_float") { "" } else { "timeout: 0.25" };
    let executable = std::env::current_exe().unwrap();
    let executable = executable.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let input = "i".repeat(INPUT_BYTES);

    for raw in [true, false] {
        let records = TempDir::new();
        let record_path = records.path().join("deadline-io-record.txt");
        let record_literal = record_path.to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
        let api = if raw { "run_raw" } else { "run" };
        let script = format!(
            r#"{api}("{executable}", ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
                env_clear: true,
                env: #{{ {FIXTURE_ENV}: "0", {FIXTURE_RECORD_ENV}: "{record_literal}", RHAI_SYS_PROCESS_DEADLINE_IO: "1" }},
                stdin: "{input}", max_output: {OUTPUT_LIMIT}, {timeout_option}
            }})"#
        );
        let result = match engine.eval::<Map>(&script) {
            Ok(result) => result,
            Err(error) => {
                assert_timed_child_record(&record_path);
                let sys_error = match error.as_ref() {
                    rhai::EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>().unwrap(),
                    other => panic!("unexpected deadline I/O error: {other:?}"),
                };
                assert!(matches!(sys_error, SysError::Process { cause: ProcessCause::Timeout(_), .. }), "unexpected primary deadline I/O cause: {sys_error:?}");
                panic!("successful deadline cleanup returned an error instead of a run result map");
            }
        };

        // Check independent child ownership before output assertions, so the wrong-marker
        // control still proves that the timed-out child was terminated and reaped.
        assert_timed_child_record(&record_path);
        assert!(result["timed_out"].as_bool().unwrap(), "blocked stdin/output fixture did not hit its deadline");
        assert!(!result["stdout_complete"].as_bool().unwrap());
        assert!(!result["stderr_complete"].as_bool().unwrap());
        if raw {
            let stdout = result["stdout"].clone().try_cast::<Blob>().unwrap();
            let stderr = result["stderr"].clone().try_cast::<Blob>().unwrap();
            assert!(stdout.starts_with(LIBTEST_QUIET_START));
            assert!(stdout.windows(b"stdout-ready\n".len()).any(|bytes| bytes == b"stdout-ready\n"));
            assert!(stdout.windows(4096).any(|bytes| bytes.iter().all(|byte| *byte == b'o')), "stdout payload chunk missing");
            assert!(stderr.windows(ACTIVE_STDERR_MARKER.len()).any(|bytes| bytes == ACTIVE_STDERR_MARKER.as_bytes()), "stderr active-stream marker missing");
            assert!(stderr.windows(1024).any(|bytes| bytes.iter().all(|byte| *byte == b'e')), "stderr payload chunk missing");
            assert!(stdout.len() <= OUTPUT_LIMIT && stderr.len() <= OUTPUT_LIMIT);
        } else {
            let stdout = result["stdout"].as_immutable_string_ref().unwrap();
            let stderr = result["stderr"].as_immutable_string_ref().unwrap();
            assert!(stdout.starts_with(&*String::from_utf8_lossy(LIBTEST_QUIET_START)));
            assert!(stdout.contains("stdout-ready\n"));
            assert!(stdout.as_bytes().windows(4096).any(|bytes| bytes.iter().all(|byte| *byte == b'o')), "stdout payload chunk missing");
            assert!(stderr.contains(ACTIVE_STDERR_MARKER), "stderr active-stream marker missing");
            assert!(stderr.as_bytes().windows(1024).any(|bytes| bytes.iter().all(|byte| *byte == b'e')), "stderr payload chunk missing");
            assert!(stdout.len() <= OUTPUT_LIMIT && stderr.len() <= OUTPUT_LIMIT);
        }
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
            timeout: 5
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
#[cfg(all(not(feature = "no_index"), not(feature = "unchecked")))]
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
            timeout: 5
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

/// Text expansion is checked at the public wait boundary without changing raw capture
/// or replacing an output-limit cause that the process supervisor already committed.
#[test]
#[cfg(all(not(feature = "no_index"), not(feature = "unchecked")))]
fn child_wait_preserves_decoded_expansion_reports_and_committed_primary_cause() {
    let executable = std::env::current_exe().unwrap().to_string_lossy().into_owned();
    for primary_limit in [false, true] {
        let records = TempDir::new();
        let record = records.path().join("child-record.txt");
        let record_literal = record.to_string_lossy();
        let engine_limit = executable.len().max(record_literal.len()) + 24;
        let invalid_count = if primary_limit { engine_limit * 2 } else { engine_limit / 2 };
        let mut expected_raw = LIBTEST_QUIET_START.to_vec();
        expected_raw.extend(std::iter::repeat(0xff).take(invalid_count));
        assert!(String::from_utf8_lossy(&expected_raw).len() > engine_limit);
        if !primary_limit {
            assert!(expected_raw.len() < engine_limit);
        } else {
            expected_raw.truncate(engine_limit);
        }
        let mut engine = engine(SysConfig::default().programs(ProgramPolicy::AllowList(vec![executable.clone()])));
        engine.set_max_string_size(engine_limit);
        let script = format!(
            r#"spawn({executable:?}, ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
                env_clear: true,
                env: #{{ {FIXTURE_ENV}: "0", {FIXTURE_RECORD_ENV}: {record_literal:?}, RHAI_SYS_PROCESS_INVALID_COUNT: "{invalid_count}" }},
                max_output: 1024
            }})"#
        );
        let child = engine.eval::<Dynamic>(&script).unwrap().cast::<rhai::packages::sys::Child>();
        let mut scope = Scope::new();
        scope.push("child", child.clone());
        scope.push("sibling", child);
        let mut first = None;
        let waits = if cfg!(feature = "no_float") {
            ["child.wait(5)", "sibling.wait(5)", "child.wait(0)"]
        } else {
            ["child.wait(5.0)", "sibling.wait(5.0)", "child.wait(0.0)"]
        };
        for expression in waits {
            let error = engine.eval_with_scope::<Dynamic>(&mut scope, expression).unwrap_err();
            let sys_error = match error.as_ref() {
                EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>().unwrap(),
                other => panic!("expected a typed process error from {expression}, got {other:?}"),
            };
            let (cause, report) = match sys_error {
                SysError::Process { cause: ProcessCause::OutputLimit(message), report } => (message, report),
                other => panic!("expected preserved OutputLimit, got {other:?}"),
            };
            if primary_limit {
                assert!(cause.starts_with("stdout for `"), "decoded expansion replaced the committed primary cause: {cause}");
            } else {
                assert!(cause.starts_with("decoded process output exceeded"), "unexpected no-primary cause: {cause}");
                assert_eq!(report.exit_code(), Some(0), "normally completed child exit is preserved");
                assert_eq!(report.exit_signal(), None);
                assert!(report.stdout_complete() && report.stderr_complete());
            }
            assert_eq!(report.stdout_bytes(), expected_raw, "wait must retain exact raw bytes");
            assert!(report.stderr_bytes().is_empty());
            assert!(!report.timed_out());
            let snapshot = (cause, report);
            if let Some(first) = &first {
                assert_eq!(&snapshot, first, "cloned and repeated waits must preserve the terminal report");
            } else {
                first = Some(snapshot);
            }
        }
        assert_child_record(&record, 0);
        eprintln!("child_wait_expansion primary_limit={primary_limit} raw_bytes={} exact=true cloned_snapshot=true child_reaped=true", expected_raw.len());
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
    let record = std::fs::read_to_string(&record_path).unwrap();
    let pid: libc::pid_t = record.trim().strip_prefix("child-pid=").unwrap().parse().unwrap();
    assert_eq!(unsafe { libc::kill(pid, 0) }, -1, "child {pid} is still present");
    assert_eq!(std::io::Error::last_os_error().raw_os_error(), Some(libc::ESRCH));
    eprintln!("no-index scalar child_pid={pid} reap=ESRCH");
    let expected = std::fs::canonicalize(&child_dir).unwrap();
    assert_eq!(result["stdout"].as_immutable_string_ref().unwrap().as_str(), format!("{}\n", expected.display()));
    assert!(result["stdout_complete"].as_bool().unwrap());
    assert!(result["stderr_complete"].as_bool().unwrap());
    assert!(result["success"].as_bool().unwrap());
    assert_eq!(result["code"].as_int().unwrap(), 0);
    let missing_raw_api = engine.eval::<Map>(r#"run_raw("/bin/pwd")"#).unwrap_err();
    assert!(matches!(missing_raw_api.as_ref(), rhai::EvalAltResult::ErrorFunctionNotFound(name, _) if name.starts_with("run_raw")), "run_raw remains registered: {missing_raw_api:?}");
}
