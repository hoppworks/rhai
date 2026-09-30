use std::env;
use std::io::{Read, Write};
use std::os::fd::AsRawFd;
use std::os::unix::process::CommandExt;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};

extern "C" {
    fn fcntl(fd: i32, cmd: i32, ...) -> i32;
    fn kill(pid: i32, sig: i32) -> i32;
    fn getpid() -> i32;
    fn getpgrp() -> i32;
}
const F_GETFL: i32 = 3;
const F_SETFL: i32 = 4;
const O_NONBLOCK: i32 = 0x0004;
const SIGKILL: i32 = 9;

fn nonblocking(fd: i32) {
    unsafe {
        let flags = fcntl(fd, F_GETFL);
        assert!(flags >= 0, "F_GETFL failed");
        assert!(fcntl(fd, F_SETFL, flags | O_NONBLOCK) >= 0, "F_SETFL failed");
    }
}
fn pump<R: Read + Send + 'static>(mut reader: R, stop: Arc<AtomicBool>, bytes: Arc<Mutex<Vec<u8>>>) -> JoinHandle<()> {
    thread::spawn(move || {
        let mut buf = [0u8; 8192];
        while !stop.load(Ordering::Acquire) {
            match reader.read(&mut buf) {
                Ok(0) => break,
                Ok(n) => bytes.lock().unwrap().extend_from_slice(&buf[..n]),
                Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => thread::sleep(Duration::from_millis(1)),
                Err(e) if e.kind() == std::io::ErrorKind::Interrupted => continue,
                Err(e) => panic!("reader failed: {e}"),
            }
        }
    })
}
fn writer<W: Write + Send + 'static>(mut pipe: W, data: Vec<u8>, stop: Arc<AtomicBool>) -> JoinHandle<()> {
    thread::spawn(move || {
        let mut offset = 0;
        while offset < data.len() && !stop.load(Ordering::Acquire) {
            match pipe.write(&data[offset..]) {
                Ok(0) => break,
                Ok(n) => offset += n,
                Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => thread::sleep(Duration::from_millis(1)),
                Err(e) if e.kind() == std::io::ErrorKind::Interrupted => continue,
                Err(e) if e.kind() == std::io::ErrorKind::BrokenPipe => break,
                Err(e) => panic!("writer failed: {e}"),
            }
        }
    })
}
fn launch(mode: &str) -> Child {
    let mut cmd = Command::new(env::current_exe().unwrap());
    cmd.arg("--fixture").arg(mode).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
    // Rust std's Unix process_group uses spawn attributes, before exec begins.
    cmd.process_group(0);
    cmd.spawn().unwrap()
}
fn kill_exact(pid: u32) {
    let rc = unsafe { kill(pid as i32, SIGKILL) };
    assert!(rc == 0 || std::io::Error::last_os_error().raw_os_error() == Some(3), "exact PID kill failed");
}
fn alive(pid: u32) -> bool {
    (unsafe { kill(pid as i32, 0) }) == 0
}
fn kill_group(child: &Child) {
    let rc = unsafe { kill(-(child.id() as i32), SIGKILL) };
    assert!(rc == 0 || std::io::Error::last_os_error().raw_os_error() == Some(3), "group kill failed: {}", std::io::Error::last_os_error());
}
fn wait_until<F: FnMut() -> bool>(deadline: Instant, mut f: F, what: &str) {
    while Instant::now() < deadline {
        if f() { return; }
        thread::sleep(Duration::from_millis(2));
    }
    panic!("deadline while waiting for {what}");
}
fn fixture(mode: &str) {
    match mode {
        "stream" => {
            eprintln!("WORKLOAD_READY pid={} pgid={}", unsafe { getpid() }, unsafe { getpgrp() });
            std::io::stderr().flush().unwrap();
            let mut input = [0u8; 4096];
            loop {
                let n = std::io::stdin().read(&mut input).unwrap();
                if n == 0 { break; }
                std::io::stdout().write_all(&input[..n]).unwrap();
                std::io::stdout().flush().unwrap();
                let transformed: Vec<u8> = input[..n].iter().map(|byte| byte ^ 0xA5).collect();
                std::io::stderr().write_all(&transformed).unwrap();
                std::io::stderr().flush().unwrap();
            }
        }
        "descendant" | "hold" => {
            let exe = env::current_exe().unwrap();
            let child = Command::new(exe).arg("--fixture").arg("sleeper").process_group(0).spawn().unwrap();
            println!("START pid={} pgid={} DESCENDANT_PID={}", unsafe { getpid() }, unsafe { getpgrp() }, child.id());
            std::io::stdout().flush().unwrap();
            // This separately owned process deliberately escapes the managed group and holds stdio.
            std::mem::forget(child);
            if mode == "hold" { loop { thread::sleep(Duration::from_secs(60)); } }
        }
        "anchor" => {
            println!("ANCHOR_READY pid={} pgid={}", unsafe { getpid() }, unsafe { getpgrp() });
            std::io::stdout().flush().unwrap();
            loop { thread::sleep(Duration::from_secs(60)); }
        }
        "sleeper" => loop { thread::sleep(Duration::from_secs(60)); },
        _ => panic!("unknown fixture"),
    }
}
fn main() {
    let args: Vec<_> = env::args().collect();
    if args.get(1).map(String::as_str) == Some("--fixture") { fixture(&args[2]); return; }
    let wrong = args.get(1).map(String::as_str) == Some("--wrong-assertion");

    // First user code immediately exercises the already-established owned process group.
    let mut streaming = launch("stream");
    let pid = streaming.id();
    let stop = Arc::new(AtomicBool::new(false));
    let out = Arc::new(Mutex::new(Vec::new()));
    let err = Arc::new(Mutex::new(Vec::new()));
    let stdout = streaming.stdout.take().unwrap();
    let stderr = streaming.stderr.take().unwrap();
    let stdin = streaming.stdin.take().unwrap();
    nonblocking(stdout.as_raw_fd()); nonblocking(stderr.as_raw_fd()); nonblocking(stdin.as_raw_fd());
    let ro = pump(stdout, stop.clone(), out.clone());
    let re = pump(stderr, stop.clone(), err.clone());
    let input = vec![b'Z'; 2 * 1024 * 1024];
    let wi = writer(stdin, input.clone(), stop.clone());
    let status = streaming.wait().unwrap();
    wi.join().unwrap(); ro.join().unwrap(); re.join().unwrap();
    assert!(status.success());
    assert_eq!(*out.lock().unwrap(), input);
    assert_eq!(*err.lock().unwrap(), input);
    println!("stream: {} bytes on each output, stdin fully transferred, exit={status}", input.len());
    assert!(unsafe { kill(-(pid as i32), 0) } == -1, "stream process group still exists after reaping");

    let mut sentinel = Command::new("/bin/sleep").arg("120").spawn().unwrap();
    let sentinel_pid = sentinel.id();

    // Cancellation with active child, full input pipe, output readers and held descendant.
    let mut active = launch("hold");
    let active_pid = active.id();
    let active_stop = Arc::new(AtomicBool::new(false));
    let active_out = Arc::new(Mutex::new(Vec::new()));
    let active_err = Arc::new(Mutex::new(Vec::new()));
    let active_stdout = active.stdout.take().unwrap(); let active_stderr = active.stderr.take().unwrap();
    let active_stdin = active.stdin.take().unwrap();
    nonblocking(active_stdout.as_raw_fd()); nonblocking(active_stderr.as_raw_fd()); nonblocking(active_stdin.as_raw_fd());
    let active_ro = pump(active_stdout, active_stop.clone(), active_out.clone());
    let active_re = pump(active_stderr, active_stop.clone(), active_err.clone());
    let active_wi = writer(active_stdin, vec![b'Q'; 32 * 1024 * 1024], active_stop.clone());
    wait_until(Instant::now() + Duration::from_secs(5), || String::from_utf8_lossy(&active_out.lock().unwrap()).contains("DESCENDANT_PID="), "active process readiness");
    let active_record = String::from_utf8_lossy(&active_out.lock().unwrap()).to_string();
    let active_pgid: i32 = active_record.split("pgid=").nth(1).unwrap().split_whitespace().next().unwrap().parse().unwrap();
    let active_descendant: u32 = active_record.split("DESCENDANT_PID=").nth(1).unwrap().split_whitespace().next().unwrap().parse().unwrap();
    assert_eq!(active_pgid, active_pid as i32, "managed group must exist before fixture user code starts");
    let cancel_start = Instant::now();
    kill_group(&active);
    active_stop.store(true, Ordering::Release);
    active_wi.join().unwrap(); active_ro.join().unwrap(); active_re.join().unwrap();
    let active_status = active.wait().unwrap();
    assert!(cancel_start.elapsed() < Duration::from_secs(2), "active cancellation and worker shutdown exceeded bound");
    assert!(alive(active_descendant), "escaped pipe-holder should outlive managed-group kill until separately cleaned");
    kill_exact(active_descendant);
    wait_until(Instant::now() + Duration::from_secs(5), || !alive(active_descendant), "exact escaped descendant cleanup");
    println!("active cancel: first-code pgid={active_pgid} equals child pid; child {active_pid} reaped={active_status}; escaped descendant {active_descendant} held pipes through group kill, workers honored cancel and joined in {:?}, then exact-PID cleanup succeeded", cancel_start.elapsed());

    let mut child = launch("descendant");
    let child_pid = child.id();
    let stop = Arc::new(AtomicBool::new(false));
    let out = Arc::new(Mutex::new(Vec::new()));
    let err = Arc::new(Mutex::new(Vec::new()));
    let stdout = child.stdout.take().unwrap(); let stderr = child.stderr.take().unwrap();
    let stdin = child.stdin.take().unwrap();
    nonblocking(stdout.as_raw_fd()); nonblocking(stderr.as_raw_fd()); nonblocking(stdin.as_raw_fd());
    let ro = pump(stdout, stop.clone(), out.clone());
    let re = pump(stderr, stop.clone(), err.clone());
    let wi = writer(stdin, vec![b'X'; 32 * 1024 * 1024], stop.clone());
    let deadline = Instant::now() + Duration::from_secs(5);
    wait_until(deadline, || String::from_utf8_lossy(&out.lock().unwrap()).contains("DESCENDANT_PID="), "descendant readiness");
    let text = String::from_utf8_lossy(&out.lock().unwrap()).to_string();
    let group_pid: i32 = text.split("pgid=").nth(1).unwrap().split_whitespace().next().unwrap().parse().unwrap();
    let descendant_pid: u32 = text.split("DESCENDANT_PID=").nth(1).unwrap().split_whitespace().next().unwrap().parse().unwrap();
    assert_eq!(group_pid, child_pid as i32, "exiting fixture was not in its owned group at first code");
    wait_until(deadline, || child.try_wait().unwrap().is_some(), "direct child exit");
    let before = Instant::now();
    kill_group(&child);
    stop.store(true, Ordering::Release);
    wi.join().unwrap(); ro.join().unwrap(); re.join().unwrap();
    let status = child.wait().unwrap();
    assert!(before.elapsed() < Duration::from_secs(2), "cancellation/shutdown exceeded bound");
    assert!(alive(descendant_pid), "escaped descendant should remain outside group scope");
    assert!(alive(sentinel_pid), "unrelated sentinel was harmed");
    println!("cancel after direct exit: child {child_pid} status={status}; escaped descendant {descendant_pid} still held pipes, but workers joined under cancellation; sentinel {sentinel_pid} alive; captured {} bytes; exact cleanup follows", out.lock().unwrap().len());
    kill_exact(descendant_pid);
    wait_until(Instant::now() + Duration::from_secs(5), || !alive(descendant_pid), "exact descendant cleanup");
    kill_exact(sentinel_pid);
    sentinel.wait().unwrap();

    let expected = if wrong { b"BROKEN".as_slice() } else { b"DESCENDANT_PID=".as_slice() };
    assert!(text.as_bytes().windows(expected.len()).any(|w| w == expected), "false-green control: expected fixture record absent");
    println!("assertion control passed");
}
