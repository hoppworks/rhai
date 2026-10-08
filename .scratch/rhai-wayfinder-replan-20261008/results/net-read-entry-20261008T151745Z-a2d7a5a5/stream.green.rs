//! Shared logical TCP handle lifecycle and bounded TCP stream I/O.

use crate::plugin::*;
use crate::{EvalAltResult, Module};
use std::io::{self, Read, Write};
use std::net::{Shutdown, TcpStream};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

const MAX_POLL_INTERVAL: Duration = Duration::from_millis(2);

/// A script-visible TCP stream handle. Cloned values share one close state.
///
/// `read_blob` and `read_string` return one available prefix, which may be shorter than
/// requested; for a positive length, a zero-length result means EOF. Their `read_to_end_*` counterparts continue
/// until EOF or their explicit byte cap. Every read has the host deadline and may request
/// a shorter timeout. Text is decoded lossily per call, so a UTF-8 character split across
/// calls can become replacement characters. Raw receive storage is capped at 1 MiB; lossy
/// text can expand to at most three bytes per received byte.
///
/// `write_string` and `write_blob` attempt one non-blocking socket write and return the
/// actual accepted byte count. Their `write_all_*` counterparts continue until every
/// input byte is accepted. Each call has the finite host write deadline and may request
/// a shorter positive timeout; write input is capped by the host limit (at most 1 MiB)
/// and, in checked builds, the engine string/blob limit. A write error reports the
/// accepted prefix in `NetError::partial_bytes`. Clones share directional half-close:
/// `shutdown_read` and `shutdown_write` are idempotent and leave the other direction
/// available; `close` shuts down both directions for all clones.
/// Concurrent writes through distinct clones are independently bounded and are not
/// serialized; write-all calls may interleave at socket-write boundaries.
#[derive(Clone)]
pub struct NetStream(Arc<SharedStreamState>);

struct SharedStreamState {
    socket: Mutex<Option<Arc<TcpStream>>>,
    open_handles: Arc<AtomicUsize>,
    read_timeout: Duration,
    max_read_bytes: usize,
    write_timeout: Duration,
    max_write_bytes: usize,
    read_shutdown: AtomicBool,
    write_shutdown: AtomicBool,
    shutdown_lock: Mutex<()>,
    target: String,
    #[cfg(feature = "testing-environ")]
    read_entry_notifier: Mutex<Option<std::sync::mpsc::SyncSender<&'static str>>>,
    #[cfg(test)]
    read_wait_notifier: Mutex<Option<std::sync::mpsc::SyncSender<()>>>,
    #[cfg(test)]
    write_wait_notifier: Mutex<Option<std::sync::mpsc::SyncSender<()>>>,
}

impl NetStream {
    pub(super) fn new(
        stream: TcpStream,
        open_handles: Arc<AtomicUsize>,
        read_timeout: Duration,
        max_read_bytes: usize,
        write_timeout: Duration,
        max_write_bytes: usize,
    ) -> Self {
        let target = stream
            .peer_addr()
            .map(|address| address.to_string())
            .unwrap_or_else(|_| "TCP stream".to_string());
        Self(Arc::new(SharedStreamState {
            socket: Mutex::new(Some(Arc::new(stream))),
            open_handles,
            read_timeout,
            max_read_bytes,
            write_timeout,
            max_write_bytes,
            read_shutdown: AtomicBool::new(false),
            write_shutdown: AtomicBool::new(false),
            shutdown_lock: Mutex::new(()),
            target,
            #[cfg(feature = "testing-environ")]
            read_entry_notifier: Mutex::new(None),
            #[cfg(test)]
            read_wait_notifier: Mutex::new(None),
            #[cfg(test)]
            write_wait_notifier: Mutex::new(None),
        }))
    }

    /// Observe the next real socket read that returns `WouldBlock`.
    ///
    /// This host-only test hook does not register a script function or alter the
    /// socket/deadline. A one-shot nonblocking send reports an entered public
    /// read operation; a caller must separately establish that it is unfinished.
    #[cfg(feature = "testing-environ")]
    #[doc(hidden)]
    pub fn observe_read_wait_for_testing(
        &self,
        notifier: std::sync::mpsc::SyncSender<&'static str>,
    ) {
        *self
            .0
            .read_entry_notifier
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner()) = Some(notifier);
    }

    fn socket(&self, op: &'static str) -> Result<Arc<TcpStream>, Box<EvalAltResult>> {
        self.0
            .socket
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
            .as_ref()
            .cloned()
            .ok_or_else(|| {
                super::NetError::io(
                    op,
                    self.0.target.clone(),
                    &io::Error::new(io::ErrorKind::NotConnected, "stream is closed"),
                )
                .into()
            })
    }

    fn close(&mut self) {
        let socket = {
            let mut state = self
                .0
                .socket
                .lock()
                .unwrap_or_else(|poisoned| poisoned.into_inner());
            state.take()
        };
        if let Some(socket) = socket {
            self.0.open_handles.fetch_sub(1, Ordering::AcqRel);
            let _ = socket.shutdown(Shutdown::Both);
        }
    }

    fn shutdown(&self, direction: Shutdown, op: &'static str) -> Result<(), Box<EvalAltResult>> {
        let _shutdown = self
            .0
            .shutdown_lock
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        let flag = match direction {
            Shutdown::Read => &self.0.read_shutdown,
            Shutdown::Write => &self.0.write_shutdown,
            Shutdown::Both => unreachable!(),
        };
        if flag.load(Ordering::Acquire) {
            return Ok(());
        }
        let socket = self.socket(op)?;
        socket.shutdown(direction).map_err(|error| {
            Box::<EvalAltResult>::from(super::NetError::io(op, self.0.target.clone(), &error))
        })?;
        flag.store(true, Ordering::Release);
        Ok(())
    }

    fn write_bytes(
        &self,
        bytes: &[u8],
        timeout_ms: Option<crate::INT>,
        engine_limit: usize,
        write_all: bool,
        op: &'static str,
    ) -> Result<crate::INT, Box<EvalAltResult>> {
        if self.0.write_shutdown.load(Ordering::Acquire) {
            return Err(super::NetError::io(
                op,
                self.0.target.clone(),
                &io::Error::new(
                    io::ErrorKind::BrokenPipe,
                    "stream write direction is shut down",
                ),
            )
            .into());
        }
        let host_limit = self.0.max_write_bytes.min(super::MAX_WRITE_BYTES);
        let limit = if engine_limit == 0 {
            host_limit
        } else {
            host_limit.min(engine_limit)
        };
        if bytes.len() > limit {
            return Err(super::NetError::resource_limit(
                op,
                self.0.target.clone(),
                format!("write input exceeds the {limit}-byte per-call limit"),
            )
            .into());
        }
        let timeout = if let Some(timeout_ms) = timeout_ms {
            if timeout_ms <= 0 {
                return Err(super::NetError::invalid(
                    op,
                    self.0.target.clone(),
                    "write timeout must be a positive number of milliseconds",
                )
                .into());
            }
            self.0
                .write_timeout
                .min(Duration::from_millis(timeout_ms as u64))
        } else {
            self.0.write_timeout
        };
        let deadline = Instant::now().checked_add(timeout).ok_or_else(|| {
            super::NetError::invalid(
                op,
                self.0.target.clone(),
                "write deadline is not representable",
            )
        })?;
        let socket = self.socket(op)?;
        if bytes.is_empty() {
            return Ok(0);
        }
        let mut transferred = 0;
        loop {
            if self.is_closed() {
                return Err(super::NetError::io(
                    op,
                    self.0.target.clone(),
                    &io::Error::new(
                        io::ErrorKind::NotConnected,
                        "stream was closed during write",
                    ),
                )
                .with_partial_bytes(transferred)
                .into());
            }
            if self.0.write_shutdown.load(Ordering::Acquire) {
                return Err(super::NetError::io(
                    op,
                    self.0.target.clone(),
                    &io::Error::new(
                        io::ErrorKind::BrokenPipe,
                        "stream write direction is shut down",
                    ),
                )
                .with_partial_bytes(transferred)
                .into());
            }
            if Instant::now() >= deadline {
                return Err(self.write_timeout_error(op, transferred));
            }
            match socket.as_ref().write(&bytes[transferred..]) {
                Ok(0) => {
                    return Err(super::NetError::io(
                        op,
                        self.0.target.clone(),
                        &io::Error::new(io::ErrorKind::WriteZero, "socket accepted no write bytes"),
                    )
                    .with_partial_bytes(transferred)
                    .into());
                }
                Ok(count) => {
                    transferred += count;
                    if !write_all || transferred == bytes.len() {
                        return Ok(transferred as crate::INT);
                    }
                }
                Err(error) if error.kind() == io::ErrorKind::WouldBlock => {
                    #[cfg(test)]
                    if let Some(notifier) = self
                        .0
                        .write_wait_notifier
                        .lock()
                        .unwrap_or_else(|poisoned| poisoned.into_inner())
                        .take()
                    {
                        let _ = notifier.send(());
                    }
                    let remaining = deadline.saturating_duration_since(Instant::now());
                    if remaining.is_zero() {
                        return Err(self.write_timeout_error(op, transferred));
                    }
                    std::thread::sleep(remaining.min(MAX_POLL_INTERVAL));
                }
                Err(error) if error.kind() == io::ErrorKind::Interrupted => {}
                Err(error) => {
                    return Err(super::NetError::io(op, self.0.target.clone(), &error)
                        .with_partial_bytes(transferred)
                        .into());
                }
            }
        }
    }

    fn write_timeout_error(&self, op: &'static str, partial_bytes: usize) -> Box<EvalAltResult> {
        super::NetError::io(
            op,
            self.0.target.clone(),
            &io::Error::new(io::ErrorKind::TimedOut, "write deadline expired"),
        )
        .with_partial_bytes(partial_bytes)
        .into()
    }

    fn write_string(
        &self,
        value: &str,
        timeout_ms: Option<crate::INT>,
        engine_limit: usize,
        write_all: bool,
    ) -> Result<crate::INT, Box<EvalAltResult>> {
        self.write_bytes(
            value.as_bytes(),
            timeout_ms,
            engine_limit,
            write_all,
            if write_all {
                "write_all_string"
            } else {
                "write_string"
            },
        )
    }

    #[cfg(not(feature = "no_index"))]
    fn write_blob(
        &self,
        value: &[u8],
        timeout_ms: Option<crate::INT>,
        engine_limit: usize,
        write_all: bool,
    ) -> Result<crate::INT, Box<EvalAltResult>> {
        self.write_bytes(
            value,
            timeout_ms,
            engine_limit,
            write_all,
            if write_all {
                "write_all_blob"
            } else {
                "write_blob"
            },
        )
    }

    fn is_closed(&self) -> bool {
        self.0
            .socket
            .lock()
            .map(|socket| socket.is_none())
            .unwrap_or(true)
    }

    fn peer_addr(&mut self) -> Result<String, Box<EvalAltResult>> {
        self.socket("peer_addr")?
            .peer_addr()
            .map(|address| address.to_string())
            .map_err(|error| super::NetError::io("peer_addr", self.0.target.clone(), &error).into())
    }

    #[cfg(not(feature = "no_index"))]
    fn read_blob(
        &self,
        requested: crate::INT,
        timeout_ms: Option<crate::INT>,
        engine_limit: usize,
        to_end: bool,
    ) -> Result<Vec<u8>, Box<EvalAltResult>> {
        self.read_bytes(
            requested,
            timeout_ms,
            engine_limit,
            to_end,
            if to_end {
                "read_to_end_blob"
            } else {
                "read_blob"
            },
        )
    }

    fn read_string(
        &self,
        requested: crate::INT,
        timeout_ms: Option<crate::INT>,
        engine_limit: usize,
        to_end: bool,
    ) -> Result<String, Box<EvalAltResult>> {
        let bytes = self.read_bytes(
            requested,
            timeout_ms,
            engine_limit,
            to_end,
            if to_end {
                "read_to_end_string"
            } else {
                "read_string"
            },
        )?;
        if engine_limit > 0 && lossy_utf8_len(&bytes) > engine_limit {
            return Err(super::NetError::resource_limit(
                if to_end {
                    "read_to_end_string"
                } else {
                    "read_string"
                },
                self.0.target.clone(),
                "lossy UTF-8 output exceeds the engine string size limit",
            )
            .with_partial_bytes(bytes.len())
            .into());
        }
        Ok(String::from_utf8_lossy(&bytes).into_owned())
    }

    fn read_bytes(
        &self,
        requested: crate::INT,
        timeout_ms: Option<crate::INT>,
        engine_limit: usize,
        to_end: bool,
        op: &'static str,
    ) -> Result<Vec<u8>, Box<EvalAltResult>> {
        if requested < 0 {
            return Err(super::NetError::invalid(
                op,
                self.0.target.clone(),
                "read length cannot be negative",
            )
            .into());
        }
        if requested == 0 {
            return Ok(Vec::new());
        }
        let timeout = if let Some(timeout_ms) = timeout_ms {
            if timeout_ms <= 0 {
                return Err(super::NetError::invalid(
                    op,
                    self.0.target.clone(),
                    "read timeout must be a positive number of milliseconds",
                )
                .into());
            }
            self.0
                .read_timeout
                .min(Duration::from_millis(timeout_ms as u64))
        } else {
            self.0.read_timeout
        };
        let deadline = Instant::now().checked_add(timeout).ok_or_else(|| {
            super::NetError::invalid(
                op,
                self.0.target.clone(),
                "read deadline is not representable",
            )
        })?;

        let mut limit = self.0.max_read_bytes.min(super::MAX_READ_BYTES);
        if engine_limit > 0 {
            limit = limit.min(engine_limit);
        }
        limit = limit.min(usize::try_from(requested).unwrap_or(usize::MAX));
        if limit == 0 {
            return Ok(Vec::new());
        }

        let socket = self.socket(op)?;
        let mut bytes = Vec::new();
        bytes.try_reserve_exact(limit).map_err(|error| {
            super::NetError::resource_limit(op, self.0.target.clone(), error.to_string())
        })?;
        bytes.resize(limit, 0);
        let mut captured = 0;
        loop {
            if Instant::now() >= deadline {
                return Err(self.timeout_error(op, captured));
            }
            let mut socket_ref = socket.as_ref();
            match socket_ref.read(&mut bytes[captured..limit]) {
                Ok(0) => {
                    if self.is_closed() {
                        return Err(super::NetError::io(
                            op,
                            self.0.target.clone(),
                            &io::Error::new(
                                io::ErrorKind::NotConnected,
                                "stream was closed during read",
                            ),
                        )
                        .with_partial_bytes(captured)
                        .into());
                    }
                    bytes.truncate(captured);
                    return Ok(bytes);
                }
                Ok(count) => {
                    captured += count;
                    if !to_end || captured == limit {
                        bytes.truncate(captured);
                        return Ok(bytes);
                    }
                }
                Err(error) if error.kind() == io::ErrorKind::WouldBlock => {
                    #[cfg(feature = "testing-environ")]
                    if let Some(notifier) = self
                        .0
                        .read_entry_notifier
                        .lock()
                        .unwrap_or_else(|poisoned| poisoned.into_inner())
                        .take()
                    {
                        let _ = notifier.try_send("read_wait");
                    }
                    #[cfg(test)]
                    if captured > 0 {
                        if let Some(notifier) = self
                            .0
                            .read_wait_notifier
                            .lock()
                            .unwrap_or_else(|poisoned| poisoned.into_inner())
                            .take()
                        {
                            let _ = notifier.send(());
                        }
                    }
                    let remaining = deadline.saturating_duration_since(Instant::now());
                    if remaining.is_zero() {
                        return Err(self.timeout_error(op, captured));
                    }
                    std::thread::sleep(remaining.min(MAX_POLL_INTERVAL));
                }
                Err(error) if error.kind() == io::ErrorKind::Interrupted => {}
                Err(error) => {
                    return Err(super::NetError::io(op, self.0.target.clone(), &error)
                        .with_partial_bytes(captured)
                        .into());
                }
            }
        }
    }

    fn timeout_error(&self, op: &'static str, partial_bytes: usize) -> Box<EvalAltResult> {
        super::NetError::io(
            op,
            self.0.target.clone(),
            &io::Error::new(io::ErrorKind::TimedOut, "read deadline expired"),
        )
        .with_partial_bytes(partial_bytes)
        .into()
    }
}

fn lossy_utf8_len(mut bytes: &[u8]) -> usize {
    let mut decoded_len = 0_usize;
    while !bytes.is_empty() {
        match std::str::from_utf8(bytes) {
            Ok(text) => {
                decoded_len = decoded_len.saturating_add(text.len());
                break;
            }
            Err(error) => {
                decoded_len = decoded_len.saturating_add(error.valid_up_to());
                let consumed = error
                    .error_len()
                    .unwrap_or_else(|| bytes.len() - error.valid_up_to());
                decoded_len = decoded_len.saturating_add('\u{fffd}'.len_utf8());
                bytes = &bytes[error.valid_up_to() + consumed..];
            }
        }
    }
    decoded_len
}

pub(super) fn register(module: &mut Module) {
    combine_with_exported_module!(module, "net_stream", net_stream_functions);
}

#[export_module]
mod net_stream_functions {
    /// Closes the socket for every clone of this stream.
    #[rhai_fn(name = "close")]
    pub fn close(stream: &mut super::NetStream) {
        stream.close();
    }

    /// Shuts down receiving on the socket and returns unit; sending remains available. Raises NetError on failure.
    #[rhai_fn(name = "shutdown_read", return_raw)]
    pub fn shutdown_read(stream: &mut super::NetStream) -> Result<(), Box<crate::EvalAltResult>> {
        stream.shutdown(std::net::Shutdown::Read, "shutdown_read")
    }

    /// Shuts down sending on the socket and returns unit; receiving remains available. Raises NetError on failure.
    #[rhai_fn(name = "shutdown_write", return_raw)]
    pub fn shutdown_write(stream: &mut super::NetStream) -> Result<(), Box<crate::EvalAltResult>> {
        stream.shutdown(std::net::Shutdown::Write, "shutdown_write")
    }

    /// Whether this stream and all its clones are closed.
    #[rhai_fn(name = "closed", get = "closed", pure)]
    pub fn closed(stream: &mut super::NetStream) -> bool {
        stream.is_closed()
    }

    /// Returns the remote TCP endpoint for this stream, or raises NetError.
    #[rhai_fn(name = "peer_addr", get = "peer_addr", return_raw)]
    pub fn peer_addr(stream: &mut super::NetStream) -> Result<String, Box<crate::EvalAltResult>> {
        stream.peer_addr()
    }

    /// Attempts one socket write and returns accepted bytes; the result may be short.
    /// The host write limit and checked Engine string limit apply. Raises NetError with accepted progress on failure.
    #[rhai_fn(name = "write_string", return_raw)]
    pub fn write_string(
        ctx: NativeCallContext,
        stream: &mut super::NetStream,
        value: &str,
    ) -> Result<crate::INT, Box<crate::EvalAltResult>> {
        #[cfg(not(feature = "unchecked"))]
        let limit = ctx.engine().max_string_size();
        #[cfg(feature = "unchecked")]
        let limit = 0;
        stream.write_string(value, None, limit, false)
    }

    /// Attempts one socket write with a positive timeout in milliseconds and returns accepted bytes; the result may be short.
    /// The timeout is capped by the host write deadline; host and checked Engine string limits apply. Raises NetError on failure.
    #[rhai_fn(name = "write_string", return_raw)]
    pub fn write_string_with_timeout(
        ctx: NativeCallContext,
        stream: &mut super::NetStream,
        value: &str,
        timeout_ms: crate::INT,
    ) -> Result<crate::INT, Box<crate::EvalAltResult>> {
        #[cfg(not(feature = "unchecked"))]
        let limit = ctx.engine().max_string_size();
        #[cfg(feature = "unchecked")]
        let limit = 0;
        stream.write_string(value, Some(timeout_ms), limit, false)
    }

    /// Completes the full string write and returns the accepted count.
    /// The host write deadline, host limit and checked Engine string limit apply. Raises NetError with accepted progress on failure.
    #[rhai_fn(name = "write_all_string", return_raw)]
    pub fn write_all_string(
        ctx: NativeCallContext,
        stream: &mut super::NetStream,
        value: &str,
    ) -> Result<crate::INT, Box<crate::EvalAltResult>> {
        #[cfg(not(feature = "unchecked"))]
        let limit = ctx.engine().max_string_size();
        #[cfg(feature = "unchecked")]
        let limit = 0;
        stream.write_string(value, None, limit, true)
    }

    /// Completes the full string write using a positive timeout in milliseconds.
    /// The timeout is capped by the host write deadline; host and checked Engine string limits apply. Raises NetError with accepted progress on failure.
    #[rhai_fn(name = "write_all_string", return_raw)]
    pub fn write_all_string_with_timeout(
        ctx: NativeCallContext,
        stream: &mut super::NetStream,
        value: &str,
        timeout_ms: crate::INT,
    ) -> Result<crate::INT, Box<crate::EvalAltResult>> {
        #[cfg(not(feature = "unchecked"))]
        let limit = ctx.engine().max_string_size();
        #[cfg(feature = "unchecked")]
        let limit = 0;
        stream.write_string(value, Some(timeout_ms), limit, true)
    }

    #[cfg(not(feature = "no_index"))]
    /// Attempts one socket write and returns accepted bytes; the result may be short.
    /// The host write limit and checked Engine blob limit apply. Raises NetError with accepted progress on failure.
    #[rhai_fn(name = "write_blob", return_raw)]
    pub fn write_blob(
        ctx: NativeCallContext,
        stream: &mut super::NetStream,
        value: crate::Blob,
    ) -> Result<crate::INT, Box<crate::EvalAltResult>> {
        #[cfg(not(feature = "unchecked"))]
        let limit = ctx.engine().max_array_size();
        #[cfg(feature = "unchecked")]
        let limit = 0;
        stream.write_blob(&value, None, limit, false)
    }

    #[cfg(not(feature = "no_index"))]
    /// Attempts one socket write with a positive timeout in milliseconds and returns accepted bytes; the result may be short.
    /// The timeout is capped by the host write deadline; host and checked Engine blob limits apply. Raises NetError with accepted progress on failure.
    #[rhai_fn(name = "write_blob", return_raw)]
    pub fn write_blob_with_timeout(
        ctx: NativeCallContext,
        stream: &mut super::NetStream,
        value: crate::Blob,
        timeout_ms: crate::INT,
    ) -> Result<crate::INT, Box<crate::EvalAltResult>> {
        #[cfg(not(feature = "unchecked"))]
        let limit = ctx.engine().max_array_size();
        #[cfg(feature = "unchecked")]
        let limit = 0;
        stream.write_blob(&value, Some(timeout_ms), limit, false)
    }

    #[cfg(not(feature = "no_index"))]
    /// Completes the full blob write and returns the accepted count.
    /// The host write deadline, host limit and checked Engine blob limit apply. Raises NetError with accepted progress on failure.
    #[rhai_fn(name = "write_all_blob", return_raw)]
    pub fn write_all_blob(
        ctx: NativeCallContext,
        stream: &mut super::NetStream,
        value: crate::Blob,
    ) -> Result<crate::INT, Box<crate::EvalAltResult>> {
        #[cfg(not(feature = "unchecked"))]
        let limit = ctx.engine().max_array_size();
        #[cfg(feature = "unchecked")]
        let limit = 0;
        stream.write_blob(&value, None, limit, true)
    }

    #[cfg(not(feature = "no_index"))]
    /// Completes the full blob write using a positive timeout in milliseconds.
    /// The timeout is capped by the host write deadline; host and checked Engine blob limits apply. Raises NetError with accepted progress on failure.
    #[rhai_fn(name = "write_all_blob", return_raw)]
    pub fn write_all_blob_with_timeout(
        ctx: NativeCallContext,
        stream: &mut super::NetStream,
        value: crate::Blob,
        timeout_ms: crate::INT,
    ) -> Result<crate::INT, Box<crate::EvalAltResult>> {
        #[cfg(not(feature = "unchecked"))]
        let limit = ctx.engine().max_array_size();
        #[cfg(feature = "unchecked")]
        let limit = 0;
        stream.write_blob(&value, Some(timeout_ms), limit, true)
    }

    #[cfg(not(feature = "no_index"))]
    /// Reads one available blob prefix; a zero-length request returns immediately and a positive request means EOF when no bytes are received.
    /// Host and checked Engine limits bound the bytes received. Raises NetError on failure.
    #[rhai_fn(name = "read_blob", return_raw)]
    pub fn read_blob(
        ctx: NativeCallContext,
        stream: &mut super::NetStream,
        len: crate::INT,
    ) -> Result<crate::Blob, Box<crate::EvalAltResult>> {
        #[cfg(not(any(feature = "no_index", feature = "unchecked")))]
        let limit = ctx.engine().max_array_size();
        #[cfg(any(feature = "no_index", feature = "unchecked"))]
        let limit = 0;
        stream.read_blob(len, None, limit, false)
    }

    #[cfg(not(feature = "no_index"))]
    /// Reads one available blob prefix with a positive timeout in milliseconds; a zero-length request returns immediately and a positive request means EOF when no bytes are received.
    /// The timeout is capped by the host read deadline; host and checked Engine limits apply. Raises NetError on failure.
    #[rhai_fn(name = "read_blob", return_raw)]
    pub fn read_blob_with_timeout(
        ctx: NativeCallContext,
        stream: &mut super::NetStream,
        len: crate::INT,
        timeout_ms: crate::INT,
    ) -> Result<crate::Blob, Box<crate::EvalAltResult>> {
        #[cfg(not(any(feature = "no_index", feature = "unchecked")))]
        let limit = ctx.engine().max_array_size();
        #[cfg(any(feature = "no_index", feature = "unchecked"))]
        let limit = 0;
        stream.read_blob(len, Some(timeout_ms), limit, false)
    }

    #[cfg(not(feature = "no_index"))]
    /// Reads a blob through EOF or the effective byte cap, the minimum of the requested byte limit, host limit and checked Engine limit.
    /// Raises NetError on failure.
    #[rhai_fn(name = "read_to_end_blob", return_raw)]
    pub fn read_to_end_blob(
        ctx: NativeCallContext,
        stream: &mut super::NetStream,
        max_bytes: crate::INT,
    ) -> Result<crate::Blob, Box<crate::EvalAltResult>> {
        #[cfg(not(feature = "unchecked"))]
        let limit = ctx.engine().max_array_size();
        #[cfg(feature = "unchecked")]
        let limit = 0;
        stream.read_blob(max_bytes, None, limit, true)
    }

    #[cfg(not(feature = "no_index"))]
    /// Reads a blob through EOF or the effective byte cap with a positive timeout in milliseconds.
    /// The cap is the minimum of the requested byte limit, host limit and checked Engine limit; the timeout is capped by the host read deadline. Raises NetError on failure.
    #[rhai_fn(name = "read_to_end_blob", return_raw)]
    pub fn read_to_end_blob_with_timeout(
        ctx: NativeCallContext,
        stream: &mut super::NetStream,
        max_bytes: crate::INT,
        timeout_ms: crate::INT,
    ) -> Result<crate::Blob, Box<crate::EvalAltResult>> {
        #[cfg(not(feature = "unchecked"))]
        let limit = ctx.engine().max_array_size();
        #[cfg(feature = "unchecked")]
        let limit = 0;
        stream.read_blob(max_bytes, Some(timeout_ms), limit, true)
    }

    /// Reads one available string prefix; a zero-length request returns immediately and a positive request means EOF when no bytes are received.
    /// Host and checked Engine limits bound received bytes and decoded output. Raises NetError on failure.
    #[rhai_fn(name = "read_string", return_raw)]
    pub fn read_string(
        ctx: NativeCallContext,
        stream: &mut super::NetStream,
        len: crate::INT,
    ) -> Result<String, Box<crate::EvalAltResult>> {
        #[cfg(not(feature = "unchecked"))]
        let limit = ctx.engine().max_string_size();
        #[cfg(feature = "unchecked")]
        let limit = 0;
        stream.read_string(len, None, limit, false)
    }

    /// Reads one available string prefix with a positive timeout in milliseconds; a zero-length request returns immediately and a positive request means EOF when no bytes are received.
    /// The timeout is capped by the host read deadline; host and checked Engine limits apply. Raises NetError on failure.
    #[rhai_fn(name = "read_string", return_raw)]
    pub fn read_string_with_timeout(
        ctx: NativeCallContext,
        stream: &mut super::NetStream,
        len: crate::INT,
        timeout_ms: crate::INT,
    ) -> Result<String, Box<crate::EvalAltResult>> {
        #[cfg(not(feature = "unchecked"))]
        let limit = ctx.engine().max_string_size();
        #[cfg(feature = "unchecked")]
        let limit = 0;
        stream.read_string(len, Some(timeout_ms), limit, false)
    }

    /// Reads a string through EOF or the effective byte cap, the minimum of the requested byte limit, host limit and checked Engine limit.
    /// Raises NetError on failure.
    #[rhai_fn(name = "read_to_end_string", return_raw)]
    pub fn read_to_end_string(
        ctx: NativeCallContext,
        stream: &mut super::NetStream,
        max_bytes: crate::INT,
    ) -> Result<String, Box<crate::EvalAltResult>> {
        #[cfg(not(feature = "unchecked"))]
        let limit = ctx.engine().max_string_size();
        #[cfg(feature = "unchecked")]
        let limit = 0;
        stream.read_string(max_bytes, None, limit, true)
    }

    /// Reads a string through EOF or the effective byte cap with a positive timeout in milliseconds.
    /// The cap is the minimum of the requested byte limit, host limit and checked Engine limit; the timeout is capped by the host read deadline. Raises NetError on failure.
    #[rhai_fn(name = "read_to_end_string", return_raw)]
    pub fn read_to_end_string_with_timeout(
        ctx: NativeCallContext,
        stream: &mut super::NetStream,
        max_bytes: crate::INT,
        timeout_ms: crate::INT,
    ) -> Result<String, Box<crate::EvalAltResult>> {
        #[cfg(not(feature = "unchecked"))]
        let limit = ctx.engine().max_string_size();
        #[cfg(feature = "unchecked")]
        let limit = 0;
        stream.read_string(max_bytes, Some(timeout_ms), limit, true)
    }
}

impl Drop for SharedStreamState {
    fn drop(&mut self) {
        let socket = match self.socket.get_mut() {
            Ok(socket) => socket,
            Err(poisoned) => poisoned.into_inner(),
        };
        if socket.take().is_some() {
            self.open_handles.fetch_sub(1, Ordering::AcqRel);
        }
    }
}

#[cfg(all(test, feature = "sync"))]
mod tests {
    use super::*;
    use crate::packages::net::NetError;
    use std::io::Write;
    use std::net::TcpListener;
    use std::sync::mpsc;

    struct ThreadJoinGuard<T>(Option<std::thread::JoinHandle<T>>);

    impl<T> ThreadJoinGuard<T> {
        fn new(handle: std::thread::JoinHandle<T>) -> Self {
            Self(Some(handle))
        }

        fn join(mut self) -> std::thread::Result<T> {
            self.0.take().expect("thread handle is present").join()
        }
    }

    impl<T> Drop for ThreadJoinGuard<T> {
        fn drop(&mut self) {
            if let Some(handle) = self.0.take() {
                let _ = handle.join();
            }
        }
    }

    #[test]
    fn clone_close_cancels_a_read_after_partial_progress() {
        use crate::packages::net::{NetConfig, NetPackage};
        use crate::packages::Package;
        use crate::{Engine, Scope};

        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let endpoint = listener.local_addr().unwrap();
        listener.set_nonblocking(true).unwrap();
        let (release_tx, release_rx) = mpsc::sync_channel(1);
        let peer = ThreadJoinGuard::new(std::thread::spawn(move || {
            let deadline = Instant::now() + Duration::from_secs(2);
            let (mut peer, _) = loop {
                match listener.accept() {
                    Ok(peer) => break peer,
                    Err(error) if error.kind() == io::ErrorKind::WouldBlock => {
                        assert!(Instant::now() < deadline, "reader did not connect to peer");
                        std::thread::yield_now();
                    }
                    Err(error) => panic!("peer accept failed: {error}"),
                }
            };
            peer.set_nonblocking(false)
                .expect("accepted peer socket is blocking for bounded fixture I/O");
            peer.set_write_timeout(Some(Duration::from_secs(1)))
                .unwrap();
            peer.write_all(b"a").unwrap();
            release_rx.recv_timeout(Duration::from_secs(2)).unwrap();
            peer.set_read_timeout(Some(Duration::from_secs(1))).unwrap();
            let mut byte = [0_u8; 1];
            assert_eq!(
                peer.read(&mut byte).unwrap(),
                0,
                "shared close shuts down the peer socket"
            );
        }));

        let socket = TcpStream::connect(endpoint).unwrap();
        socket.set_nonblocking(true).unwrap();
        let handles = Arc::new(AtomicUsize::new(1));
        let stream = NetStream::new(
            socket,
            handles.clone(),
            Duration::from_secs(2),
            8,
            Duration::from_secs(2),
            8,
        );
        let (waiting_tx, waiting_rx) = mpsc::sync_channel(1);
        *stream
            .0
            .read_wait_notifier
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner()) = Some(waiting_tx);

        let package = NetPackage::new(NetConfig::default()).unwrap();
        let mut read_engine = Engine::new();
        package.clone().register_into_engine(&mut read_engine);
        let mut close_engine = Engine::new();
        package.register_into_engine(&mut close_engine);

        let reader_stream = stream.clone();
        let (result_tx, result_rx) = mpsc::sync_channel(1);
        let reader = ThreadJoinGuard::new(std::thread::spawn(move || {
            let mut scope = Scope::new();
            scope.push("stream", reader_stream);
            let result = match read_engine
                .eval_with_scope::<String>(&mut scope, "stream.read_to_end_string(8)")
            {
                Ok(text) => Ok(text),
                Err(error) => match *error {
                    EvalAltResult::ErrorRuntime(value, _) => {
                        Err(value.try_cast::<NetError>().unwrap())
                    }
                    other => panic!("expected structured close error, got {other}"),
                },
            };
            result_tx.send(result).unwrap();
        }));

        waiting_rx
            .recv_timeout(Duration::from_secs(1))
            .expect("read loop reached WouldBlock after capturing the peer byte");
        let mut close_scope = Scope::new();
        close_scope.push("stream", stream.clone());
        close_engine
            .run_with_scope(&mut close_scope, "stream.close(); stream.close();")
            .unwrap();
        let error = result_rx
            .recv_timeout(Duration::from_secs(1))
            .unwrap()
            .unwrap_err();
        assert_eq!(error.kind(), "Io");
        assert_eq!(error.op(), "read_to_end_string");
        assert_eq!(
            error.partial_bytes(),
            1,
            "close preserves bytes captured before cancellation"
        );
        assert_eq!(
            handles.load(Ordering::Acquire),
            0,
            "shared quota decrements once"
        );
        release_tx.send(()).unwrap();
        reader.join().unwrap();
        peer.join().unwrap();
    }

    #[test]
    fn clone_close_cancels_a_write_after_socket_would_block() {
        use crate::packages::net::{NetConfig, NetPackage};
        use crate::packages::Package;
        use crate::{Engine, Scope};

        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let endpoint = listener.local_addr().unwrap();
        listener.set_nonblocking(true).unwrap();
        let (peer_ready_tx, peer_ready_rx) = mpsc::sync_channel(1);
        let (peer_release_tx, peer_release_rx) = mpsc::sync_channel(1);
        let peer = ThreadJoinGuard::new(std::thread::spawn(move || {
            let deadline = Instant::now() + Duration::from_secs(3);
            let (peer, _) = loop {
                match listener.accept() {
                    Ok(pair) => break pair,
                    Err(error) if error.kind() == io::ErrorKind::WouldBlock => {
                        assert!(Instant::now() < deadline, "writer did not connect to peer");
                        std::thread::yield_now();
                    }
                    Err(error) => panic!("accept failed: {error}"),
                }
            };
            peer.set_nonblocking(false).unwrap();
            peer.set_write_timeout(Some(Duration::from_secs(1)))
                .unwrap();
            peer_ready_tx.send(()).unwrap();
            peer_release_rx
                .recv_timeout(Duration::from_secs(3))
                .unwrap();
            peer.set_read_timeout(Some(Duration::from_secs(1))).unwrap();
            let mut received = Vec::new();
            peer.take((64 * 1024 * 1024 + 1) as u64)
                .read_to_end(&mut received)
                .unwrap();
            assert!(
                received.len() <= 64 * 1024 * 1024,
                "peer fixture stayed within its 64 MiB byte cap"
            );
            received.len()
        }));

        let socket = TcpStream::connect(endpoint).unwrap();
        socket.set_nonblocking(true).unwrap();
        let handles = Arc::new(AtomicUsize::new(1));
        let stream = NetStream::new(
            socket,
            handles.clone(),
            Duration::from_secs(2),
            1024 * 1024,
            Duration::from_secs(2),
            1024 * 1024,
        );
        let (waiting_tx, waiting_rx) = mpsc::sync_channel(1);
        *stream
            .0
            .write_wait_notifier
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner()) = Some(waiting_tx);

        let package = NetPackage::new(NetConfig::default()).unwrap();
        let mut write_engine = Engine::new();
        package.clone().register_into_engine(&mut write_engine);
        let mut close_engine = Engine::new();
        package.register_into_engine(&mut close_engine);
        peer_ready_rx.recv_timeout(Duration::from_secs(1)).unwrap();

        let (result_tx, result_rx) = mpsc::sync_channel(1);
        let writer_stream = stream.clone();
        let writer = ThreadJoinGuard::new(std::thread::spawn(move || {
            let mut scope = Scope::new();
            scope.push("stream", writer_stream);
            scope.push("payload", "x".repeat(64 * 1024));
            let mut completed_bytes = 0_usize;
            for _ in 0..1024 {
                match write_engine
                    .eval_with_scope::<crate::INT>(&mut scope, "stream.write_all_string(payload)")
                {
                    Ok(count) => completed_bytes += count as usize,
                    Err(error) => match *error {
                        EvalAltResult::ErrorRuntime(value, _) => {
                            let error = value.try_cast::<NetError>().unwrap();
                            result_tx.send(Ok((completed_bytes, error))).unwrap();
                            return;
                        }
                        other => panic!("expected structured write error, got {other}"),
                    },
                }
            }
            result_tx.send(Err(completed_bytes)).unwrap();
        }));

        waiting_rx
            .recv_timeout(Duration::from_secs(2))
            .expect("socket write reached WouldBlock");
        let started = Instant::now();
        let mut close_scope = Scope::new();
        close_scope.push("stream", stream.clone());
        close_engine
            .run_with_scope(&mut close_scope, "stream.close(); stream.close();")
            .unwrap();
        let (completed_bytes, error) = result_rx
            .recv_timeout(Duration::from_secs(1))
            .expect("close unblocks the active write")
            .expect("the 64 MiB fixture reaches socket backpressure");
        assert!(started.elapsed() < Duration::from_secs(1));
        assert_eq!(error.kind(), "Io");
        assert_eq!(error.op(), "write_all_string");
        assert!(
            completed_bytes + error.partial_bytes() as usize > 0,
            "preserve bytes accepted across repeated writes before close"
        );
        assert!(
            error.partial_bytes() < 64 * 1024,
            "final call respects its input cap"
        );
        assert_eq!(
            handles.load(Ordering::Acquire),
            0,
            "shared quota decrements once"
        );
        peer_release_tx.send(()).unwrap();
        writer.join().unwrap();
        let peer_bytes = peer.join().unwrap();
        assert_eq!(
            peer_bytes,
            completed_bytes + error.partial_bytes() as usize,
            "peer readback matches full writes plus the final partial count"
        );
    }
}
