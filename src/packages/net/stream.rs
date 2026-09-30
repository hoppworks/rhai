//! Shared logical TCP handle lifecycle and bounded receive operations.

use crate::plugin::*;
use crate::{EvalAltResult, Module};
use std::io::{self, Read};
use std::net::{Shutdown, TcpStream};
use std::sync::atomic::{AtomicUsize, Ordering};
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
#[derive(Clone)]
pub struct NetStream(Arc<SharedStreamState>);

struct SharedStreamState {
    socket: Mutex<Option<Arc<TcpStream>>>,
    open_handles: Arc<AtomicUsize>,
    read_timeout: Duration,
    max_read_bytes: usize,
    target: String,
    #[cfg(test)]
    read_wait_notifier: Mutex<Option<std::sync::mpsc::SyncSender<()>>>,
}

impl NetStream {
    pub(super) fn new(
        stream: TcpStream,
        open_handles: Arc<AtomicUsize>,
        read_timeout: Duration,
        max_read_bytes: usize,
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
            target,
            #[cfg(test)]
            read_wait_notifier: Mutex::new(None),
        }))
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
    #[rhai_fn(name = "close")]
    pub fn close(stream: &mut super::NetStream) {
        stream.close();
    }

    #[rhai_fn(get = "closed", pure)]
    pub fn closed(stream: &mut super::NetStream) -> bool {
        stream.is_closed()
    }

    #[rhai_fn(get = "peer_addr", return_raw)]
    pub fn peer_addr(stream: &mut super::NetStream) -> Result<String, Box<crate::EvalAltResult>> {
        stream.peer_addr()
    }

    #[cfg(not(feature = "no_index"))]
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

    #[test]
    fn clone_close_cancels_a_read_after_partial_progress() {
        use crate::packages::net::{NetConfig, NetPackage};
        use crate::packages::Package;
        use crate::{Engine, Scope};

        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let endpoint = listener.local_addr().unwrap();
        listener.set_nonblocking(true).unwrap();
        let (release_tx, release_rx) = mpsc::sync_channel(1);
        let peer = std::thread::spawn(move || {
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
            peer.write_all(b"a").unwrap();
            release_rx.recv_timeout(Duration::from_secs(2)).unwrap();
            peer.set_read_timeout(Some(Duration::from_secs(1))).unwrap();
            let mut byte = [0_u8; 1];
            assert_eq!(
                peer.read(&mut byte).unwrap(),
                0,
                "shared close shuts down the peer socket"
            );
        });

        let socket = TcpStream::connect(endpoint).unwrap();
        socket.set_nonblocking(true).unwrap();
        let handles = Arc::new(AtomicUsize::new(1));
        let stream = NetStream::new(socket, handles.clone(), Duration::from_secs(2), 8);
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
        let reader = std::thread::spawn(move || {
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
        });

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
}
