//! Standalone POSIX acceptance executable for cancellable, bounded process I/O.
//! Only the explicit `--acceptance` mode is supported; there is no implicit demo.
use std::env;
use std::fs::File;
use std::io::{self, Read, Write};
use std::os::fd::{AsRawFd, FromRawFd, IntoRawFd, OwnedFd};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{mpsc, Arc, Mutex};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};

const STREAM_WORKLOAD: usize = 2 * 1024 * 1024;
const CASE_LIMIT: Duration = Duration::from_secs(8);

#[derive(Debug, PartialEq, Eq)]
enum End {
    Eof,
    Cancelled,
    OutputLimit,
    Failed(String),
}

#[derive(Debug)]
struct Capture {
    bytes: Vec<u8>,
    end: End,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum WaitOutcome {
    FileReady,
    WakeDrained(usize),
    Quiet,
    Cancelled,
}

struct Wake {
    read: OwnedFd,
    write: OwnedFd,
    release_generation: Arc<Mutex<usize>>,
}

struct WorkerAbort {
    cancelled: AtomicBool,
    first_cause: Mutex<Option<String>>,
    wakes: Vec<Wake>,
}

impl WorkerAbort {
    fn trigger(&self, cause: impl Into<String>) {
        let mut first = self.first_cause.lock().unwrap_or_else(|e| e.into_inner());
        if first.is_none() {
            *first = Some(cause.into());
            self.cancelled.store(true, Ordering::Release);
        }
        drop(first);
        for wake in &self.wakes {
            let _ = wake.send();
        }
    }

    fn first_cause(&self) -> Option<String> {
        self.first_cause
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .clone()
    }
}

impl Wake {
    fn new() -> io::Result<Self> {
        let mut fds = [-1; 2];
        if unsafe { libc::pipe(fds.as_mut_ptr()) } != 0 {
            return Err(io::Error::last_os_error());
        }
        let read = unsafe { OwnedFd::from_raw_fd(fds[0]) };
        let write = unsafe { OwnedFd::from_raw_fd(fds[1]) };
        for fd in [read.as_raw_fd(), write.as_raw_fd()] {
            let old = unsafe { libc::fcntl(fd, libc::F_GETFL) };
            if old < 0 || unsafe { libc::fcntl(fd, libc::F_SETFL, old | libc::O_NONBLOCK) } < 0 {
                return Err(io::Error::last_os_error());
            }
            let flags = unsafe { libc::fcntl(fd, libc::F_GETFD) };
            if flags < 0 || unsafe { libc::fcntl(fd, libc::F_SETFD, flags | libc::FD_CLOEXEC) } < 0
            {
                return Err(io::Error::last_os_error());
            }
        }
        Ok(Self {
            read,
            write,
            release_generation: Arc::new(Mutex::new(0)),
        })
    }

    fn send(&self) -> io::Result<()> {
        let byte = [1u8];
        loop {
            let rc = unsafe { libc::write(self.write.as_raw_fd(), byte.as_ptr().cast(), 1) };
            if rc == 1 {
                return Ok(());
            }
            let err = io::Error::last_os_error();
            if err.kind() == io::ErrorKind::Interrupted {
                continue;
            }
            if err.kind() == io::ErrorKind::WouldBlock {
                return Ok(());
            }
            return Err(err);
        }
    }

    fn send_release(&self) -> io::Result<()> {
        let mut generation = self
            .release_generation
            .lock()
            .unwrap_or_else(|e| e.into_inner());
        self.send()?;
        *generation += 1;
        Ok(())
    }

    fn drain(&self) -> io::Result<()> {
        let mut bytes = [0u8; 64];
        loop {
            let rc = unsafe {
                libc::read(
                    self.read.as_raw_fd(),
                    bytes.as_mut_ptr().cast(),
                    bytes.len(),
                )
            };
            if rc > 0 {
                continue;
            }
            if rc == 0 {
                return Ok(());
            }
            let err = io::Error::last_os_error();
            if err.kind() == io::ErrorKind::Interrupted {
                continue;
            }
            if err.kind() == io::ErrorKind::WouldBlock {
                return Ok(());
            }
            return Err(err);
        }
    }

    fn wait_ready(
        &self,
        file: i32,
        events: i16,
        cancel: &AtomicBool,
        deadline: Instant,
    ) -> io::Result<WaitOutcome> {
        let mut p = [
            libc::pollfd {
                fd: file,
                events,
                revents: 0,
            },
            libc::pollfd {
                fd: self.read.as_raw_fd(),
                events: libc::POLLIN,
                revents: 0,
            },
        ];
        loop {
            let left = deadline.saturating_duration_since(Instant::now());
            if left.is_zero() {
                return Err(io::Error::new(
                    io::ErrorKind::TimedOut,
                    "worker readiness deadline",
                ));
            }
            let millis = left.as_millis().clamp(1, 50) as i32;
            let rc = unsafe { libc::poll(p.as_mut_ptr(), p.len() as _, millis) };
            if rc > 0 {
                if p[1].revents != 0 {
                    if cancel.load(Ordering::Acquire) {
                        return Ok(WaitOutcome::Cancelled);
                    }
                    let generation = self
                        .release_generation
                        .lock()
                        .unwrap_or_else(|e| e.into_inner());
                    self.drain()?;
                    return Ok(WaitOutcome::WakeDrained(*generation));
                }
                if p[0].revents & (events | libc::POLLHUP | libc::POLLERR | libc::POLLNVAL) != 0 {
                    return Ok(WaitOutcome::FileReady);
                }
                continue;
            }
            if rc == 0 {
                return Ok(WaitOutcome::Quiet);
            }
            let error = io::Error::last_os_error();
            if error.kind() == io::ErrorKind::Interrupted {
                continue;
            }
            return Err(error);
        }
    }
}

fn set_nonblocking(fd: i32) -> io::Result<()> {
    let old = unsafe { libc::fcntl(fd, libc::F_GETFL) };
    if old < 0 || unsafe { libc::fcntl(fd, libc::F_SETFL, old | libc::O_NONBLOCK) } < 0 {
        return Err(io::Error::last_os_error());
    }
    Ok(())
}

fn capture_worker<F: AsRawFd + Send + 'static>(
    file: F,
    wake: Wake,
    cap: usize,
    name: &'static str,
    ready: mpsc::SyncSender<&'static str>,
    checkpoint: mpsc::SyncSender<(&'static str, usize)>,
    pending: mpsc::SyncSender<&'static str>,
    checkpoint_at: usize,
    released: Arc<AtomicBool>,
    abort: Arc<WorkerAbort>,
) -> Capture {
    let fd = file.as_raw_fd();
    let mut bytes = Vec::with_capacity(cap.min(8192));
    let mut active = false;
    let mut checkpoint_sent = false;
    let mut pending_sent = false;
    let mut drained_release_generation = 0usize;
    let mut chunk = [0u8; 8192];
    let deadline = Instant::now() + CASE_LIMIT;
    loop {
        if abort.first_cause().is_some() {
            return Capture {
                bytes,
                end: End::Cancelled,
            };
        }
        if Instant::now() >= deadline {
            abort.trigger(format!("{name}-deadline"));
            return Capture {
                bytes,
                end: End::Failed("reader deadline".into()),
            };
        }
        // Probe once before blocking so EAGAIN itself is part of the explicit
        // active/readiness handshake, including an empty but pipe-held stream.
        let read_len = if checkpoint_sent {
            chunk.len()
        } else {
            chunk.len().min(checkpoint_at.saturating_sub(bytes.len()))
        };
        let rc = unsafe { libc::read(fd, chunk.as_mut_ptr().cast(), read_len) };
        if rc == 0 {
            return Capture {
                bytes,
                end: End::Eof,
            };
        }
        if rc > 0 {
            let n = rc as usize;
            let room = cap.saturating_sub(bytes.len());
            bytes.extend_from_slice(&chunk[..n.min(room)]);
            if !checkpoint_sent && bytes.len() >= checkpoint_at {
                checkpoint_sent = true;
                let _ = checkpoint.try_send((name, bytes.len()));
            }
            if n > room {
                let cause_name = name.strip_suffix("-reader").unwrap_or(name);
                abort.trigger(format!("{cause_name}-output-limit"));
                return Capture {
                    bytes,
                    end: End::OutputLimit,
                };
            }
            continue;
        }
        let err = io::Error::last_os_error();
        if err.kind() == io::ErrorKind::Interrupted {
            continue;
        }
        if err.kind() != io::ErrorKind::WouldBlock {
            abort.trigger(format!("{name}-read-error"));
            return Capture {
                bytes,
                end: End::Failed(err.to_string()),
            };
        }
        if !active {
            active = true;
            // This acknowledgement is emitted only after an actual EAGAIN on
            // the nonblocking pipe, immediately before the worker polls.
            let _ = ready.try_send(name);
        }
        let wait_result = match wake.wait_ready(fd, libc::POLLIN, &abort.cancelled, deadline) {
            Ok(v) => v,
            Err(e) => {
                abort.trigger(format!("{name}-poll-error"));
                return Capture {
                    bytes,
                    end: End::Failed(e.to_string()),
                };
            }
        };
        match wait_result {
            WaitOutcome::WakeDrained(generation) => drained_release_generation = generation,
            WaitOutcome::Quiet
                if checkpoint_sent
                    && released.load(Ordering::Acquire)
                    && drained_release_generation > 0
                    && !pending_sent =>
            {
                pending_sent = true;
                let _ = pending.try_send(name);
            }
            WaitOutcome::Cancelled => {
                return Capture {
                    bytes,
                    end: End::Cancelled,
                }
            }
            WaitOutcome::FileReady | WaitOutcome::Quiet => {}
        }
    }
}

struct WriterResult {
    bytes: usize,
    end: &'static str,
}

fn writer_worker<F: AsRawFd + Send + 'static>(
    file: F,
    wake: Wake,
    payload: Vec<u8>,
    ready: mpsc::SyncSender<&'static str>,
    checkpoint: mpsc::SyncSender<(&'static str, usize)>,
    pending: mpsc::SyncSender<&'static str>,
    staged: bool,
    ignore_pipe_close: bool,
    release: mpsc::Receiver<()>,
    abort: Arc<WorkerAbort>,
) -> io::Result<WriterResult> {
    let fd = file.as_raw_fd();
    let mut offset = 0;
    let mut active = false;
    let mut pending_sent = false;
    let mut drained_release_generation = 0usize;
    let mut released = !staged;
    let deadline = Instant::now() + CASE_LIMIT;
    while offset < payload.len() {
        if abort.first_cause().is_some() {
            return Ok(WriterResult {
                bytes: offset,
                end: "cancelled",
            });
        }
        if Instant::now() >= deadline {
            abort.trigger("stdin-writer-deadline");
            return Ok(WriterResult {
                bytes: offset,
                end: "failed",
            });
        }
        if staged && !released && offset == STREAM_WORKLOAD / 2 {
            let _ = checkpoint.try_send(("stdin-writer", offset));
            if let Err(e) = release.recv_timeout(CASE_LIMIT) {
                abort.trigger("stdin-writer-release-error");
                let _ = e;
                return Ok(WriterResult {
                    bytes: offset,
                    end: "failed",
                });
            }
            released = true;
        }
        let write_len = if staged && offset < STREAM_WORKLOAD / 2 {
            (STREAM_WORKLOAD / 2) - offset
        } else {
            payload.len() - offset
        };
        let rc = unsafe { libc::write(fd, payload[offset..].as_ptr().cast(), write_len) };
        if rc > 0 {
            offset += rc as usize;
            continue;
        }
        if rc == 0 {
            abort.trigger("stdin-writer-write-zero");
            return Ok(WriterResult {
                bytes: offset,
                end: "failed",
            });
        }
        let err = io::Error::last_os_error();
        if err.kind() == io::ErrorKind::Interrupted {
            continue;
        }
        if err.kind() == io::ErrorKind::WouldBlock {
            if !active {
                active = true;
                let _ = ready.try_send("stdin-writer");
            }
            match wake.wait_ready(fd, libc::POLLOUT, &abort.cancelled, deadline) {
                Ok(WaitOutcome::WakeDrained(generation)) => drained_release_generation = generation,
                Ok(WaitOutcome::Quiet)
                    if staged && released && drained_release_generation > 0 && !pending_sent =>
                {
                    pending_sent = true;
                    let _ = pending.try_send("stdin-writer");
                }
                Ok(WaitOutcome::Cancelled) => {
                    return Ok(WriterResult {
                        bytes: offset,
                        end: "cancelled",
                    })
                }
                Ok(WaitOutcome::FileReady | WaitOutcome::Quiet) => {}
                Err(_) => {
                    abort.trigger("stdin-writer-poll-error");
                    return Ok(WriterResult {
                        bytes: offset,
                        end: "failed",
                    });
                }
            }
            continue;
        }
        if ignore_pipe_close && err.raw_os_error() == Some(libc::EPIPE) {
            return Ok(WriterResult {
                bytes: offset,
                end: "broken_pipe",
            });
        }
        abort.trigger("stdin-writer-write-error");
        let _ = err;
        return Ok(WriterResult {
            bytes: offset,
            end: "failed",
        });
    }
    drop(file); // communicate EOF after the exact bounded workload is sent
    Ok(WriterResult {
        bytes: offset,
        end: "complete",
    })
}

struct RunningIo {
    abort: Arc<WorkerAbort>, // retained wake writers outlive all cancellation logic
    released: Arc<AtomicBool>,
    out: Option<JoinHandle<Capture>>,
    err: Option<JoinHandle<Capture>>,
    input: Option<JoinHandle<io::Result<WriterResult>>>,
    release: Option<mpsc::SyncSender<()>>,
}

impl RunningIo {
    fn poke_all(&self) {
        for wake in &self.abort.wakes {
            let _ = wake.send();
        }
    }

    fn poke_release_all(&self) {
        for wake in &self.abort.wakes {
            let _ = wake.send_release();
        }
    }

    fn wake_all(&self) {
        self.abort.cancelled.store(true, Ordering::Release);
        if let Some(release) = &self.release {
            let _ = release.try_send(());
        }
        self.poke_all();
    }

    fn join_natural(&mut self) -> io::Result<(Capture, Capture, io::Result<WriterResult>)> {
        let out = self
            .out
            .take()
            .expect("stdout worker")
            .join()
            .map_err(|_| io::Error::other("stdout worker panicked"))?;
        let err = self
            .err
            .take()
            .expect("stderr worker")
            .join()
            .map_err(|_| io::Error::other("stderr worker panicked"))?;
        let input = self
            .input
            .take()
            .expect("stdin worker")
            .join()
            .map_err(|_| io::Error::other("stdin worker panicked"))?;
        Ok((out, err, input))
    }
}

impl Drop for RunningIo {
    fn drop(&mut self) {
        // This is also the panic and assertion-failure path. Never rely on the
        // intentionally incomplete missing-wake request to perform cleanup.
        self.wake_all();
        if let Some(h) = self.out.take() {
            let _ = h.join();
        }
        if let Some(h) = self.err.take() {
            let _ = h.join();
        }
        if let Some(h) = self.input.take() {
            let _ = h.join();
        }
    }
}

fn launch_io(
    stdin: File,
    stdout: File,
    stderr: File,
    cap: usize,
    payload: Vec<u8>,
    staged: bool,
    ignore_pipe_close: bool,
    stderr_checkpoint_at: usize,
) -> io::Result<(
    RunningIo,
    mpsc::Receiver<&'static str>,
    mpsc::Receiver<(&'static str, usize)>,
    mpsc::Receiver<&'static str>,
)> {
    for fd in [stdin.as_raw_fd(), stdout.as_raw_fd(), stderr.as_raw_fd()] {
        set_nonblocking(fd)?;
    }
    let wakes = vec![Wake::new()?, Wake::new()?, Wake::new()?];
    // Complete every fallible descriptor operation before starting workers.
    // Retain each started thread immediately so a later spawn error is joined
    // through RunningIo::drop.
    let [wake_out, wake_err, wake_in] = [
        dup_wake(&wakes[0])?,
        dup_wake(&wakes[1])?,
        dup_wake(&wakes[2])?,
    ];
    let (tx, rx) = mpsc::sync_channel(3);
    let (checkpoint_tx, checkpoint_rx) = mpsc::sync_channel(3);
    let (pending_tx, pending_rx) = mpsc::sync_channel(3);
    let (release_tx, release_rx) = mpsc::sync_channel(1);
    let released = Arc::new(AtomicBool::new(false));
    let abort = Arc::new(WorkerAbort {
        cancelled: AtomicBool::new(false),
        first_cause: Mutex::new(None),
        wakes,
    });
    let mut owner = RunningIo {
        abort: abort.clone(),
        released: released.clone(),
        out: None,
        err: None,
        input: None,
        release: Some(release_tx),
    };
    let tx_out = tx.clone();
    let checkpoint = checkpoint_tx.clone();
    let pending = pending_tx.clone();
    let c = abort.clone();
    let gate = released.clone();
    let wake = wake_out;
    owner.out = Some(
        thread::Builder::new()
            .name("stdout-poll".into())
            .spawn(move || {
                capture_worker(
                    stdout,
                    wake,
                    cap,
                    "stdout-reader",
                    tx_out,
                    checkpoint,
                    pending,
                    STREAM_WORKLOAD / 2,
                    gate,
                    c,
                )
            })?,
    );
    let tx_err = tx.clone();
    let checkpoint = checkpoint_tx.clone();
    let pending = pending_tx.clone();
    let c = abort.clone();
    let gate = released.clone();
    let wake = wake_err;
    owner.err = Some(
        thread::Builder::new()
            .name("stderr-poll".into())
            .spawn(move || {
                capture_worker(
                    stderr,
                    wake,
                    cap,
                    "stderr-reader",
                    tx_err,
                    checkpoint,
                    pending,
                    stderr_checkpoint_at,
                    gate,
                    c,
                )
            })?,
    );
    let tx_in = tx.clone();
    let checkpoint = checkpoint_tx;
    let pending = pending_tx;
    let c = abort.clone();
    let wake = wake_in;
    owner.input = Some(
        thread::Builder::new()
            .name("stdin-poll".into())
            .spawn(move || {
                writer_worker(
                    stdin,
                    wake,
                    payload,
                    tx_in,
                    checkpoint,
                    pending,
                    staged,
                    ignore_pipe_close,
                    release_rx,
                    c,
                )
            })?,
    );
    drop(tx);
    Ok((owner, rx, checkpoint_rx, pending_rx))
}

fn send_frame(sock: i32, bytes: &[u8], deadline: Instant) -> io::Result<()> {
    loop {
        if Instant::now() >= deadline {
            return Err(io::Error::new(
                io::ErrorKind::TimedOut,
                "custodian send deadline",
            ));
        }
        let rc = unsafe { libc::send(sock, bytes.as_ptr().cast(), bytes.len(), 0) };
        if rc == bytes.len() as isize {
            return Ok(());
        }
        if rc >= 0 {
            return Err(io::Error::other("short custodian datagram"));
        }
        let err = io::Error::last_os_error();
        if err.kind() == io::ErrorKind::Interrupted {
            continue;
        }
        if err.kind() == io::ErrorKind::WouldBlock {
            if Instant::now() >= deadline {
                return Err(io::Error::new(
                    io::ErrorKind::TimedOut,
                    "custodian send deadline",
                ));
            }
            let mut p = libc::pollfd {
                fd: sock,
                events: libc::POLLOUT,
                revents: 0,
            };
            let rc = unsafe { libc::poll(&mut p, 1, 50) };
            if rc < 0 && io::Error::last_os_error().kind() != io::ErrorKind::Interrupted {
                return Err(io::Error::last_os_error());
            }
            continue;
        }
        return Err(err);
    }
}

fn receive_pipes(
    sock: i32,
    deadline: Instant,
) -> io::Result<(libc::c_int, libc::c_int, libc::c_int, u32)> {
    let (data, mut fds) = recv_datagram(sock, deadline)?;
    let value: serde_json::Value = serde_json::from_slice(&data).map_err(io::Error::other)?;
    let object = value
        .as_object()
        .ok_or_else(|| io::Error::other("pipes frame is not an object"))?;
    let mut keys: Vec<_> = object.keys().map(String::as_str).collect();
    keys.sort_unstable();
    if keys != ["anchor_pgid", "anchor_pid", "op", "pgid", "workload_pid"]
        || object.get("op").and_then(|v| v.as_str()) != Some("pipes")
    {
        return Err(io::Error::other(
            "pipes frame does not match the complete schema",
        ));
    }
    let number = |name: &str| -> io::Result<u32> {
        object
            .get(name)
            .and_then(|v| v.as_u64())
            .and_then(|v| u32::try_from(v).ok())
            .filter(|v| *v > 1)
            .ok_or_else(|| io::Error::other(format!("invalid {name}")))
    };
    let workload_pid = number("workload_pid")?;
    let pgid = number("pgid")?;
    if pgid != workload_pid || number("anchor_pgid")? != pgid || number("anchor_pid")? <= 1 {
        return Err(io::Error::other(
            "custodian process-group/anchor identity mismatch",
        ));
    }
    if fds.len() != 3 {
        return Err(io::Error::other(
            "custodian must pass exactly three pipe descriptors",
        ));
    }
    for fd in &fds {
        let old = unsafe { libc::fcntl(fd.as_raw_fd(), libc::F_GETFD) };
        if old < 0
            || unsafe { libc::fcntl(fd.as_raw_fd(), libc::F_SETFD, old | libc::FD_CLOEXEC) } < 0
        {
            return Err(io::Error::last_os_error());
        }
    }
    let err = fds.pop().unwrap().into_raw_fd();
    let out = fds.pop().unwrap().into_raw_fd();
    let input = fds.pop().unwrap().into_raw_fd();
    Ok((input, out, err, workload_pid))
}

fn recv_datagram(sock: i32, deadline: Instant) -> io::Result<(Vec<u8>, Vec<OwnedFd>)> {
    let mut data = [0u8; 65537];
    let mut control = [0usize; 32];
    loop {
        if Instant::now() >= deadline {
            return Err(io::Error::new(
                io::ErrorKind::TimedOut,
                "custodian receive deadline",
            ));
        }
        let mut msg: libc::msghdr = unsafe { std::mem::zeroed() };
        let mut iov = libc::iovec {
            iov_base: data.as_mut_ptr().cast(),
            iov_len: data.len(),
        };
        msg.msg_iov = &mut iov;
        msg.msg_iovlen = 1;
        msg.msg_control = control.as_mut_ptr().cast();
        msg.msg_controllen = std::mem::size_of_val(&control) as _;
        let rc = unsafe { libc::recvmsg(sock, &mut msg, 0) };
        if rc < 0 {
            let err = io::Error::last_os_error();
            if err.kind() == io::ErrorKind::Interrupted {
                if Instant::now() >= deadline {
                    return Err(io::Error::new(
                        io::ErrorKind::TimedOut,
                        "custodian receive deadline",
                    ));
                }
                continue;
            }
            if err.kind() != io::ErrorKind::WouldBlock {
                return Err(err);
            }
            let left = deadline.saturating_duration_since(Instant::now());
            if left.is_zero() {
                return Err(io::Error::new(
                    io::ErrorKind::TimedOut,
                    "custodian receive deadline",
                ));
            }
            let millis = left.as_millis().clamp(1, 50) as i32;
            let mut p = libc::pollfd {
                fd: sock,
                events: libc::POLLIN,
                revents: 0,
            };
            let rc = unsafe { libc::poll(&mut p, 1, millis) };
            if rc < 0 && io::Error::last_os_error().kind() != io::ErrorKind::Interrupted {
                return Err(io::Error::last_os_error());
            }
            continue;
        }
        let mut fds: Vec<OwnedFd> = Vec::new();
        let base = msg.msg_control as usize;
        let control_len = usize::try_from(msg.msg_controllen).map_err(io::Error::other)?;
        let mut ancillary_invalid = control_len > std::mem::size_of_val(&control);
        msg.msg_controllen = control_len.min(std::mem::size_of_val(&control)) as _;
        let end = base
            .checked_add(control_len.min(std::mem::size_of_val(&control)))
            .ok_or_else(|| io::Error::other("ancillary range overflow"))?;
        // SAFETY: A zero-length control payload is representable by socklen_t;
        // CMSG_LEN only computes the aligned header size for that payload.
        let data_offset = unsafe { libc::CMSG_LEN(0) as usize };
        let mut cmsg = unsafe { libc::CMSG_FIRSTHDR(&msg) };
        while !cmsg.is_null() {
            let address = cmsg as usize;
            if address < base
                || address % std::mem::align_of::<libc::cmsghdr>() != 0
                || address
                    .checked_add(std::mem::size_of::<libc::cmsghdr>())
                    .map_or(true, |x| x > end)
            {
                ancillary_invalid = true;
                break;
            }
            let header = unsafe { &*cmsg };
            let len = usize::try_from(header.cmsg_len).map_err(io::Error::other)?;
            let next = address
                .checked_add(len)
                .ok_or_else(|| io::Error::other("ancillary length overflow"))?;
            if len < data_offset || next > end {
                ancillary_invalid = true;
                break;
            }
            let bytes = len - data_offset;
            if header.cmsg_level == libc::SOL_SOCKET && header.cmsg_type == libc::SCM_RIGHTS {
                if bytes == 0 || bytes % std::mem::size_of::<libc::c_int>() != 0 {
                    ancillary_invalid = true;
                }
                let count = bytes / std::mem::size_of::<libc::c_int>();
                let ptr = unsafe { libc::CMSG_DATA(cmsg).cast::<libc::c_int>() };
                for index in 0..count {
                    let fd = unsafe { ptr.add(index).read_unaligned() };
                    if fd < 0 {
                        ancillary_invalid = true;
                    } else {
                        fds.push(unsafe { OwnedFd::from_raw_fd(fd) });
                    }
                }
            } else {
                ancillary_invalid = true;
            }
            cmsg = unsafe { libc::CMSG_NXTHDR(&msg, cmsg) };
        }
        if ancillary_invalid
            || rc == 0
            || rc as usize > 65536
            || msg.msg_flags & (libc::MSG_TRUNC | libc::MSG_CTRUNC) != 0
        {
            return Err(io::Error::other(
                "invalid, empty, or truncated custodian datagram",
            ));
        }
        return Ok((data[..rc as usize].to_vec(), fds));
    }
}

fn dup_cloexec(fd: i32) -> io::Result<OwnedFd> {
    let copy = unsafe { libc::fcntl(fd, libc::F_DUPFD_CLOEXEC, 3) };
    if copy < 0 {
        return Err(io::Error::last_os_error());
    }
    Ok(unsafe { OwnedFd::from_raw_fd(copy) })
}

fn dup_wake(w: &Wake) -> io::Result<Wake> {
    Ok(Wake {
        read: dup_cloexec(w.read.as_raw_fd())?,
        write: dup_cloexec(w.write.as_raw_fd())?,
        release_generation: Arc::clone(&w.release_generation),
    })
}

fn wait_pending(
    rx: &mpsc::Receiver<&'static str>,
    deadline: Instant,
) -> io::Result<Vec<&'static str>> {
    let mut names = Vec::new();
    while names.len() < 3 {
        let left = deadline.saturating_duration_since(Instant::now());
        if left.is_zero() {
            return Err(io::Error::other(format!(
                "three-worker post-checkpoint EAGAIN handshake timed out: {names:?}"
            )));
        }
        names.push(rx.recv_timeout(left).map_err(io::Error::other)?);
    }
    names.sort_unstable();
    if names != ["stderr-reader", "stdin-writer", "stdout-reader"] {
        return Err(io::Error::other(format!(
            "wrong worker handshakes: {names:?}"
        )));
    }
    Ok(names)
}

fn fixture(mode: &str) -> io::Result<()> {
    let mut input = io::stdin().lock();
    let mut output = io::stdout().lock();
    let mut error = io::stderr().lock();
    writeln!(
        error,
        "WORKLOAD_READY pid={} pgid={}",
        unsafe { libc::getpid() },
        unsafe { libc::getpgrp() }
    )?;
    error.flush()?;
    let mut buffer = [0u8; 8192];
    let mut total = 0usize;
    loop {
        let n = input.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        total += n;
        output.write_all(&buffer[..n])?;
        output.flush()?;
        let transformed: Vec<u8> = buffer[..n].iter().map(|b| b ^ 0xA5).collect();
        error.write_all(&transformed)?;
        error.flush()?;
        if (mode == "stall" || mode == "cancel") && total >= STREAM_WORKLOAD / 2 {
            break;
        }
    }
    if mode == "stall" || mode == "cancel" {
        loop {
            thread::sleep(Duration::from_secs(60));
        }
    }
    Ok(())
}

fn fixture_anchor() -> io::Result<()> {
    println!(
        "ANCHOR_READY pid={} pgid={}",
        unsafe { libc::getpid() },
        unsafe { libc::getpgrp() }
    );
    io::stdout().flush()
}

fn fixture_cap(channel: &str, count: usize) -> io::Result<()> {
    if count > 4097 || !matches!(channel, "stdout" | "stderr") {
        return Err(io::Error::other("invalid raw cap fixture arguments"));
    }
    let mut input = io::stdin().lock();
    let mut prefix = [0u8; 4096];
    input.read_exact(&mut prefix)?;
    if prefix
        .iter()
        .enumerate()
        .any(|(i, byte)| *byte != (i % 256) as u8)
    {
        return Err(io::Error::other(
            "raw cap fixture input prefix differs from pattern",
        ));
    }
    let prefix_hash = hex(&sha256(&prefix));
    let mut readiness = unsafe { File::from_raw_fd(3) };
    writeln!(
        readiness,
        "CAP_READY pid={} pgid={} channel={channel} bytes={count} stdin_bytes=4096 stdin_sha256={prefix_hash}",
        unsafe { libc::getpid() },
        unsafe { libc::getpgrp() }
    )?;
    readiness.flush()?;
    drop(readiness);
    let bytes: Vec<u8> = (0..count).map(|i| (i % 256) as u8).collect();
    if channel == "stdout" {
        io::stdout().write_all(&bytes)?;
        io::stdout().flush()?;
    } else {
        io::stderr().write_all(&bytes)?;
        io::stderr().flush()?;
    }
    // Close stdin after the independently verified prefix, leaving the real
    // parent writer to observe the pipe's actual broken-pipe outcome.
    Ok(())
}

fn run_acceptance() -> io::Result<()> {
    let inherited_sock: i32 = env::var("PROCESS_PROTOTYPE_CUSTODIAN_FD")
        .map_err(io::Error::other)?
        .parse()
        .map_err(io::Error::other)?;
    let _sock_owner = unsafe { OwnedFd::from_raw_fd(inherited_sock) };
    let sock = _sock_owner.as_raw_fd();
    let flags = unsafe { libc::fcntl(sock, libc::F_GETFL) };
    if flags < 0 || unsafe { libc::fcntl(sock, libc::F_SETFL, flags | libc::O_NONBLOCK) } < 0 {
        return Err(io::Error::last_os_error());
    }
    let fd_flags = unsafe { libc::fcntl(sock, libc::F_GETFD) };
    if fd_flags < 0 || unsafe { libc::fcntl(sock, libc::F_SETFD, fd_flags | libc::FD_CLOEXEC) } < 0
    {
        return Err(io::Error::last_os_error());
    }
    let control = env::var("PROCESS_PROTOTYPE_CONTROL").unwrap_or_else(|_| "normal".into());
    let timeout = 20;
    let is_cap = control.starts_with("stdout-") || control.starts_with("stderr-");
    let cap_parts: Vec<&str> = control.split('-').collect();
    let (cap_channel, requested_cap, cap_count) = if is_cap {
        if cap_parts.len() != 3 {
            return Err(io::Error::other("invalid cap case"));
        }
        (
            Some(cap_parts[0]),
            cap_parts[1].parse::<usize>().map_err(io::Error::other)?,
            cap_parts[2].parse::<usize>().map_err(io::Error::other)?,
        )
    } else {
        (None, STREAM_WORKLOAD + 256, STREAM_WORKLOAD)
    };
    let mode = match control.as_str() {
        "normal" => "stream",
        "topology-cancel" => "topology",
        _ => "stall",
    };
    let deadline = Instant::now() + Duration::from_secs(timeout);
    let exe = env::var("PROCESS_PROTOTYPE_WORKLOAD_BINARY").map_err(io::Error::other)?;
    let fixture_exe = if is_cap {
        env::var("PROCESS_PROTOTYPE_NATIVE_RUNNER_BINARY").map_err(io::Error::other)?
    } else {
        exe.clone()
    };
    let request = if let Some(channel) = cap_channel {
        serde_json::json!({"op":"run", "timeout_seconds":timeout,
                           "argv":[fixture_exe, "--fixture", "cap", channel, cap_count.to_string()]})
    } else {
        serde_json::json!({"op":"run", "timeout_seconds":timeout,
                           "argv":[fixture_exe, "--fixture", mode]})
    };
    send_frame(
        sock,
        &serde_json::to_vec(&request).map_err(io::Error::other)?,
        deadline,
    )?;
    let (in_fd, out_fd, err_fd, workload_pid) = receive_pipes(sock, deadline)?;
    let stdin = unsafe { File::from_raw_fd(in_fd) };
    let stdout = unsafe { File::from_raw_fd(out_fd) };
    let stderr = unsafe { File::from_raw_fd(err_fd) };
    let payload: Vec<u8> = (0..STREAM_WORKLOAD).map(|i| (i % 256) as u8).collect();
    let capture_cap = requested_cap;
    let needs_pending = matches!(
        control.as_str(),
        "cancel" | "missing-wake" | "term" | "kill" | "topology-cancel"
    );
    let (mut io, _ready, checkpoint, post_checkpoint_pending) = launch_io(
        stdin,
        stdout,
        stderr,
        capture_cap,
        payload.clone(),
        needs_pending,
        cap_channel.is_some(),
        STREAM_WORKLOAD / 2 + expected_line_len(workload_pid),
    )?;
    if cap_channel.is_some() {
        let (ready, ready_fds) = recv_datagram(sock, deadline)?;
        let ready: serde_json::Value = serde_json::from_slice(&ready).map_err(io::Error::other)?;
        let ready = ready.as_object().ok_or_else(|| {
            io::Error::other("cap fixture readiness acknowledgement is not an object")
        })?;
        if !ready_fds.is_empty()
            || ready.len() != 2
            || ready.get("op").and_then(|v| v.as_str()) != Some("fixture_ready_ack")
            || ready.get("status").and_then(|v| v.as_i64()) != Some(0)
        {
            return Err(io::Error::other(
                "custodian did not validate raw cap fixture readiness",
            ));
        }
    }
    let mut checkpoint_values = [0usize; 3];
    if needs_pending {
        let expected = STREAM_WORKLOAD / 2;
        let expected_stderr = expected + expected_line_len(workload_pid);
        let mut checkpoints = Vec::new();
        while checkpoints.len() < 3 {
            let left = deadline.saturating_duration_since(Instant::now());
            if left.is_zero() {
                return Err(io::Error::new(
                    io::ErrorKind::TimedOut,
                    "1MiB worker checkpoint deadline",
                ));
            }
            checkpoints.push(checkpoint.recv_timeout(left).map_err(io::Error::other)?);
        }
        checkpoints.sort_unstable_by_key(|(name, _)| *name);
        if checkpoints[0] != ("stderr-reader", expected_stderr)
            || checkpoints[1] != ("stdin-writer", expected)
            || checkpoints[2] != ("stdout-reader", expected)
        {
            return Err(io::Error::other(format!(
                "1MiB checkpoints differ: {checkpoints:?}"
            )));
        }
        checkpoint_values = [checkpoints[1].1, checkpoints[2].1, checkpoints[0].1];
        // Queue the release poke before publishing the pending-ack generation.
        // Workers drain this poke, observe a real EAGAIN again, then only
        // acknowledge after a subsequent quiet poll proves no wake is queued.
        io.poke_release_all();
        io.released.store(true, Ordering::Release);
        io.release
            .as_ref()
            .unwrap()
            .send(())
            .map_err(io::Error::other)?;
    }
    let pending = if needs_pending {
        wait_pending(&post_checkpoint_pending, deadline)?
    } else {
        Vec::new()
    };
    let mut active: Vec<&str> = [
        ("stderr-reader", !io.err.as_ref().unwrap().is_finished()),
        ("stdin-writer", !io.input.as_ref().unwrap().is_finished()),
        ("stdout-reader", !io.out.as_ref().unwrap().is_finished()),
    ]
    .into_iter()
    .filter_map(|(name, is_active)| if is_active { Some(name) } else { None })
    .collect();
    active.sort_unstable();
    let alive = active.len();
    if needs_pending
        && (alive != 3 || pending != ["stderr-reader", "stdin-writer", "stdout-reader"])
    {
        return Err(io::Error::other(
            "worker readiness became stale before live snapshot",
        ));
    }
    let live = serde_json::json!({"op":"io_live", "workers_started":3, "workers_alive":alive,
        "active_workers": active,
        "pending_workers":pending});
    send_frame(
        sock,
        &serde_json::to_vec(&live).map_err(io::Error::other)?,
        deadline,
    )?;
    let (ack, ack_fds) = recv_datagram(sock, deadline)?;
    let ack: serde_json::Value = serde_json::from_slice(&ack).map_err(io::Error::other)?;
    let ack = ack
        .as_object()
        .ok_or_else(|| io::Error::other("io_live acknowledgement is not an object"))?;
    if !ack_fds.is_empty()
        || ack.len() != 2
        || ack.get("op").and_then(|v| v.as_str()) != Some("io_live_ack")
        || ack.get("status").and_then(|v| v.as_i64()) != Some(0)
    {
        return Err(io::Error::other(
            "custodian did not acknowledge validated live snapshot",
        ));
    }
    let missing_wake_ms = if control == "missing-wake" {
        // Commit cancellation first but deliberately omit every wake write.
        // The workers must remain blocked until the retained emergency
        // writers are used below.
        io.abort.cancelled.store(true, Ordering::Release);
        thread::sleep(Duration::from_millis(250));
        let still_alive = usize::from(!io.out.as_ref().unwrap().is_finished())
            + usize::from(!io.err.as_ref().unwrap().is_finished())
            + usize::from(!io.input.as_ref().unwrap().is_finished());
        if still_alive != 3 {
            return Err(io::Error::other(
                "missing-wake control released a worker without a wake",
            ));
        }
        250
    } else {
        0
    };
    let cancelled = matches!(control.as_str(), "cancel" | "missing-wake" | "topology-cancel");
    let wake_started = Instant::now();
    let (out, err, sent) = if cancelled {
        io.wake_all();
        let out = io
            .out
            .take()
            .unwrap()
            .join()
            .map_err(|_| io::Error::other("stdout worker panicked"))?;
        let err = io
            .err
            .take()
            .unwrap()
            .join()
            .map_err(|_| io::Error::other("stderr worker panicked"))?;
        let input = io
            .input
            .take()
            .unwrap()
            .join()
            .map_err(|_| io::Error::other("stdin worker panicked"))?;
        (out, err, input)
    } else {
        io.join_natural()?
    };
    let wake_to_join_ms = if cancelled {
        wake_started.elapsed().as_millis() as u64
    } else {
        0
    };
    let writer = sent?;
    let sent = writer.bytes;
    if cancelled && (sent == 0 || sent >= STREAM_WORKLOAD) {
        return Err(io::Error::other(
            "stall workload did not demonstrate a bounded partial/backpressured write",
        ));
    }
    if cancelled
        && (out.bytes.len() != STREAM_WORKLOAD / 2
            || err.bytes.len() != STREAM_WORKLOAD / 2 + expected_line_len(workload_pid))
    {
        return Err(io::Error::other(
            "held-output worker checkpoints were not exactly 1MiB",
        ));
    }
    let ends_ok = if cancelled {
        out.end == End::Cancelled && err.end == End::Cancelled
    } else if let Some(channel) = cap_channel {
        let expected = if cap_count > requested_cap {
            End::OutputLimit
        } else {
            End::Eof
        };
        let target = if channel == "stdout" {
            &out.end
        } else {
            &err.end
        };
        let other = if channel == "stdout" {
            &err.end
        } else {
            &out.end
        };
        *target == expected && (other == &End::Eof || other == &End::Cancelled)
    } else {
        out.end == End::Eof && err.end == End::Eof
    };
    let cap_boundary_partial = cap_channel.is_some()
        && cap_count <= requested_cap
        && (4096..STREAM_WORKLOAD).contains(&sent)
        && io.abort.first_cause().is_none();
    if io.abort.first_cause().is_none()
        && (!ends_ok || (!cancelled && sent != STREAM_WORKLOAD && !cap_boundary_partial))
    {
        return Err(io::Error::other(format!(
            "worker result mismatch: {out:?} {err:?} sent={sent}"
        )));
    }
    if let Some(channel) = cap_channel {
        let raw = bytes_for_count(cap_count);
        let target = if channel == "stdout" {
            &out.bytes
        } else {
            &err.bytes
        };
        let other = if channel == "stdout" {
            &err.bytes
        } else {
            &out.bytes
        };
        if target != &raw[..target.len()]
            || !other.is_empty()
            || target.len() != requested_cap.min(cap_count)
        {
            return Err(io::Error::other("raw cap fixture bytes/capture differ"));
        }
        let cause = io.abort.first_cause();
        let expected_cause = if cap_count > requested_cap {
            Some(format!("{channel}-output-limit"))
        } else {
            None
        };
        let target_end = if channel == "stdout" {
            &out.end
        } else {
            &err.end
        };
        let other_end = if channel == "stdout" {
            &err.end
        } else {
            &out.end
        };
        let expected_end = if cap_count > requested_cap {
            End::OutputLimit
        } else {
            End::Eof
        };
        if cause != expected_cause
            || !(4096..STREAM_WORKLOAD).contains(&sent)
            || *target_end != expected_end
            || (*other_end != End::Eof
                && !(cap_count > requested_cap && *other_end == End::Cancelled))
        {
            return Err(io::Error::other(
                "raw cap byte count, end state or first cause differs from fixture truth",
            ));
        }
    } else if io.abort.first_cause().is_none() {
        {
            let expected_output = &payload[..out.bytes.len()];
            if out.bytes != expected_output
                || err.bytes.len() != expected_output.len() + expected_line_len(workload_pid)
                || !err.bytes.starts_with(b"WORKLOAD_READY ")
            {
                return Err(io::Error::other("exact stream/readiness readback mismatch"));
            }
            let expected_line = format!("WORKLOAD_READY pid={workload_pid} pgid={workload_pid}\n");
            let transformed: Vec<u8> = expected_output.iter().map(|b| b ^ 0xA5).collect();
            if err.bytes.get(..expected_line.len()) != Some(expected_line.as_bytes())
                || err.bytes[expected_line.len()..] != transformed
            {
                return Err(io::Error::other(
                    "readiness identity or transformed stream mismatch",
                ));
            }
        }
    }
    let stdout_end = end_name(&out.end);
    let stderr_end = end_name(&err.end);
    let first_cause = io.abort.first_cause();
    let stdin_end = writer.end;
    let readiness_len = if cap_channel.is_none() {
        expected_line_len(workload_pid)
    } else {
        0
    };
    let measured_stderr = &err.bytes[readiness_len.min(err.bytes.len())..];
    let stdout_prefix_len = if cap_channel.is_some() {
        out.bytes.len().min(4096)
    } else {
        out.bytes.len().min(64)
    };
    let stderr_prefix_len = if cap_channel.is_some() {
        measured_stderr.len().min(4096)
    } else {
        measured_stderr.len().min(64)
    };
    let event = serde_json::json!({"op":"native_done", "case":control,
        "workers_started":3, "workers_joined":3, "stdin_bytes":sent,
        "checkpoint_bytes":{"stdin":checkpoint_values[0],
            "stdout":checkpoint_values[1],
            "stderr":checkpoint_values[2].saturating_sub(expected_line_len(workload_pid))},
        "stdout_bytes":out.bytes.len(), "stderr_bytes":measured_stderr.len(),
        "stdin_end":stdin_end, "stdout_end":stdout_end, "stderr_end":stderr_end,
        "first_cause":first_cause,
        "wake_to_join_ms":wake_to_join_ms, "missing_wake_observation_ms":missing_wake_ms,
        "stdout_prefix_hex":hex(&out.bytes[..stdout_prefix_len]),
        "stderr_prefix_hex":hex(&measured_stderr[..stderr_prefix_len]),
        "stdin_sha256":hex(&sha256(&payload[..sent])), "stdout_sha256":hex(&sha256(&out.bytes)),
        "stderr_sha256":hex(&sha256(measured_stderr))});
    send_frame(
        sock,
        &serde_json::to_vec(&event).map_err(io::Error::other)?,
        deadline,
    )?;
    let (reply, extra) = recv_datagram(sock, deadline)?;
    let result: serde_json::Value = serde_json::from_slice(&reply).map_err(io::Error::other)?;
    let result_object = result
        .as_object()
        .ok_or_else(|| io::Error::other("result frame is not an object"))?;
    if !extra.is_empty()
        || result_object.len() != 2
        || result_object.get("op").and_then(|v| v.as_str()) != Some("result")
        || result_object.get("status").and_then(|v| v.as_i64()) != Some(0)
    {
        return Err(io::Error::other(
            "custodian did not acknowledge exact worker result",
        ));
    }
    Ok(())
}

fn expected_line_len(pid: u32) -> usize {
    format!("WORKLOAD_READY pid={pid} pgid={pid}\n").len()
}

fn end_name(end: &End) -> &'static str {
    match end {
        End::Eof => "eof",
        End::Cancelled => "cancelled",
        End::OutputLimit => "output_limit",
        End::Failed(_) => "failed",
    }
}

fn bytes_for_count(count: usize) -> Vec<u8> {
    (0..count).map(|i| (i % 256) as u8).collect()
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn sha256(input: &[u8]) -> [u8; 32] {
    const K: [u32; 64] = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4,
        0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
        0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
        0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
        0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
        0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
        0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
        0xc67178f2,
    ];
    let mut h = [
        0x6a09e667u32,
        0xbb67ae85,
        0x3c6ef372,
        0xa54ff53a,
        0x510e527f,
        0x9b05688c,
        0x1f83d9ab,
        0x5be0cd19,
    ];
    let bit_len = (input.len() as u64).wrapping_mul(8);
    let mut data = input.to_vec();
    data.push(0x80);
    while data.len() % 64 != 56 {
        data.push(0);
    }
    data.extend_from_slice(&bit_len.to_be_bytes());
    for block in data.chunks_exact(64) {
        let mut w = [0u32; 64];
        for (i, chunk) in block.chunks_exact(4).take(16).enumerate() {
            w[i] = u32::from_be_bytes(chunk.try_into().unwrap());
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }
        let [mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut z] = h;
        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ (!e & g);
            let t1 = z
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(K[i])
                .wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let t2 = s0.wrapping_add(maj);
            z = g;
            g = f;
            f = e;
            e = d.wrapping_add(t1);
            d = c;
            c = b;
            b = a;
            a = t1.wrapping_add(t2);
        }
        for (x, v) in h.iter_mut().zip([a, b, c, d, e, f, g, z]) {
            *x = x.wrapping_add(v);
        }
    }
    let mut out = [0u8; 32];
    for (i, v) in h.iter().enumerate() {
        out[i * 4..i * 4 + 4].copy_from_slice(&v.to_be_bytes());
    }
    out
}

fn main() {
    let result = (|| -> io::Result<()> {
        let limit = libc::rlimit {
            rlim_cur: 32,
            rlim_max: 32,
        };
        if unsafe { libc::setrlimit(libc::RLIMIT_NOFILE, &limit) } != 0 {
            return Err(io::Error::last_os_error());
        }
        let args: Vec<String> = env::args().skip(1).collect();
        if args.first().map(String::as_str) == Some("--acceptance") {
            let binary = env::var("PROCESS_PROTOTYPE_WORKLOAD_BINARY").map_err(io::Error::other)?;
            let control = env::var("PROCESS_PROTOTYPE_CONTROL").map_err(io::Error::other)?;
            if args.len() != 5
                || args[0] != "--acceptance"
                || args[1] != "--binary"
                || args[2] != binary
                || args[3] != "--case"
                || args[4] != control
                || env::var_os("PROCESS_PROTOTYPE_CUSTODIAN_FD").is_none()
            {
                return Err(io::Error::other(
                    "native acceptance arguments do not match custodian environment",
                ));
            }
            run_acceptance()
        } else if args.first().map(String::as_str) == Some("--fixture")
            && env::var_os("PROCESS_PROTOTYPE_CUSTODIAN_FD").is_some()
        {
            match args.as_slice() {
                [_, mode] if matches!(mode.as_str(), "stream" | "stall" | "cancel") => {
                    fixture(mode)
                }
                [_, mode] if mode == "anchor" => fixture_anchor(),
                [_, mode, channel, count]
                    if mode == "cap"
                        && env::var("PROCESS_PROTOTYPE_FIXTURE_AUTHORIZATION")
                            .ok()
                            .as_deref()
                            == Some("raw-cap-v1") =>
                {
                    fixture_cap(channel, count.parse().map_err(io::Error::other)?)
                }
                _ => Err(io::Error::other("invalid fixture arguments")),
            }
        } else {
            Err(io::Error::other(
                "usage: --acceptance --binary PATH --case CASE | --fixture MODE",
            ))
        }
    })();
    if let Err(error) = result {
        eprintln!("acceptance failed: {error}");
        std::process::exit(1);
    }
}
