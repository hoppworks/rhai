#![cfg(all(feature = "sys", unix))]
//! Public process execution contracts (Unix slice).

mod sys_support;

use rhai::packages::sys::{FsAccess, ProcessCause, ProcessScope, ProgramPolicy, SysConfig, SysError};
#[cfg(not(feature = "no_index"))]
use rhai::Blob;
use rhai::{Dynamic, Engine, Map, Scope};
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
const LIBTEST_QUIET_START: &[u8] = b"\nrunning 1 test\n";
const ACTIVE_STDERR_MARKER: &str = "stderr-active-marker\n";
const ACTIVE_STDERR_OUTPUT: &str = "stderr-active-marker\n";
const MANAGED_SPAWN_HOLD_ENV: &str = "RHAI_SYS_MANAGED_SPAWN_HOLD";

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
        if std::env::var_os("RHAI_SYS_PROCESS_IO_STRESS").is_some() {
            let expected = std::env::var("RHAI_SYS_PROCESS_IO_BYTES").unwrap().parse::<usize>().unwrap();
            let out_bytes = std::env::var("RHAI_SYS_PROCESS_STDOUT_BYTES").unwrap().parse::<usize>().unwrap();
            let err_bytes = std::env::var("RHAI_SYS_PROCESS_STDERR_BYTES").unwrap().parse::<usize>().unwrap();
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
            assert!(input.iter().all(|byte| *byte == b'i'));
            let complete_record = record_path.with_extension("complete");
            std::fs::write(&complete_record, format!("child-pid={child_pid} input-bytes={} input-valid=true\n", input.len())).unwrap();
            std::fs::rename(complete_record, record_path).unwrap();
            stdout_writer.join().unwrap();
            stderr_writer.join().unwrap();
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
        .expect("start managed worker fixture");
    let worker_pid = worker.id();
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
    managed_atomic_record(
        &root.join("leader-record"),
        &format!("pid={leader_pid} pgid={leader_pgid} worker={worker_pid} worker-pgid={} leaf={} leaf-pgid={}\n", worker_fields["pgid"], leaf_fields["pid"], leaf_fields["pgid"]),
    );
    // Dropping Child intentionally leaves the worker for the process-scope owner to close.
    drop(worker);
}

/// Re-exec fixture worker: remain alive with inherited stdout/stderr until the fixture guard
/// releases it, or until its bounded fallback expires after a failed assertion.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_scope_worker_fixture() {
    if std::env::var(MANAGED_FIXTURE_ENV).as_deref() != Ok("worker") {
        return;
    }
    let record = std::path::PathBuf::from(std::env::var_os(MANAGED_WORKER_ENV).unwrap());
    let leaf_record = std::path::PathBuf::from(std::env::var_os(MANAGED_LEAF_ENV).unwrap());
    let release = std::path::PathBuf::from(std::env::var_os(MANAGED_RELEASE_ENV).unwrap());
    let pid = std::process::id();
    let pgid = unsafe { libc::getpgrp() };
    managed_atomic_record(&record, &format!("pid={pid} pgid={pgid} ready=true\n"));
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
    managed_atomic_record(&record, &format!("pid={pid} pgid={pgid} ready=true\n"));
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
    managed_atomic_record(
        &root.join("leader-record"),
        &format!("pid={leader_pid} pgid={leader_pgid} worker={worker_pid} worker_pgid={} leaf={} leaf_pgid={}\n", worker_fields["pgid"], leaf_fields["pid"], leaf_fields["pgid"]),
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
    managed_atomic_record(&leader_record, &format!("pid={leader_pid} pgid={leader_pgid} holder={holder_pid} holder_pgid={sentinel_pgid} sentinel_pgid={sentinel_pgid}\n"));
    let deadline = Instant::now() + Duration::from_secs(15);
    while !root.join("release-leader").exists() && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(5));
    }
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
    managed_atomic_record(&record, &format!("pid={pid} pgid={pgid} ready=true\n"));
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
fn managed_record_fields(record: &str) -> std::collections::HashMap<String, i32> {
    record
        .split_whitespace()
        .filter_map(|field| {
            let (key, value) = field.split_once('=')?;
            Some((key.to_owned(), value.parse().ok()?))
        })
        .collect()
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
        panic!("managed run returned a non-Denied error: {error:?}");
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
fn managed_spawn_script(fixture: &ManagedFixture) -> (Engine, String) {
    let executable = std::env::current_exe().unwrap().to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let root = fixture.root.as_script_path();
    let worker = fixture.path("worker-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let leaf = fixture.path("leaf-record").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let release = fixture.path("release-worker").to_string_lossy().replace('\\', "\\\\").replace('"', "\\\"");
    let config = SysConfig::default()
        .programs(ProgramPolicy::AllowList(vec![executable.clone()]))
        .process_scope(ProcessScope::Managed)
        .max_output(4096)
        .kill_on_drop(true);
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
    let (engine, script) = managed_spawn_script(&fixture);
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

/// Dropping a nonfinal shared Child clone preserves the running group; dropping the final
/// script-client handle applies `kill_on_drop` to its leader and descendants.
#[test]
#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]
fn managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not() {
    let fixture = ManagedFixture::new();
    let mut sentinel = managed_spawn_sentinel();
    let sentinel_pid = sentinel.0.id() as i32;
    let (engine, script) = managed_spawn_script(&fixture);
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
fn io_stress_script(executable: &str, record_path: &str, input_bytes: usize, stdout_bytes: usize, stderr_bytes: usize, limit: usize) -> String {
    let input = "i".repeat(input_bytes);
    format!(
        r#"run_raw("{executable}", ["--exact", "process_fixture", "--nocapture", "--quiet"], #{{
            env_clear: true,
            env: #{{ {FIXTURE_ENV}: "0", {FIXTURE_RECORD_ENV}: "{record_path}", RHAI_SYS_PROCESS_IO_STRESS: "1", RHAI_SYS_PROCESS_IO_BYTES: "{input_bytes}", RHAI_SYS_PROCESS_STDOUT_BYTES: "{stdout_bytes}", RHAI_SYS_PROCESS_STDERR_BYTES: "{stderr_bytes}" }},
            stdin: "{input}", max_output: {limit}, timeout: 5.0
        }})"#
    )
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
    let script = io_stress_script(&executable, &record_literal, INPUT_BYTES, CAP - LIBTEST_QUIET_START.len(), CAP, CAP);
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
        let script = io_stress_script(&executable, &record_literal, INPUT_BYTES, stdout_payload, stderr_payload, CAP);
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
        let script = format!(r#"run("/bin/sh", #{{ env_clear: true, env: #{{ RECORD: "{record_literal}" }}, stdin: "printf 'child-pid=%s\\n' \"$$\" > \"$RECORD\"{output}", max_output: 0, timeout: 5.0 }})"#);
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
fn run_deadline_with_blocked_stdin_and_active_stdout_stderr() {
    const INPUT_BYTES: usize = 512 * 1024;
    const OUTPUT_LIMIT: usize = 64 * 1024 * 1024;
    let mut engine = engine(SysConfig::default().max_output(OUTPUT_LIMIT).programs(ProgramPolicy::Any));
    engine.set_max_string_size(OUTPUT_LIMIT);
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
                stdin: "{input}", max_output: {OUTPUT_LIMIT}, timeout: 0.25
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
