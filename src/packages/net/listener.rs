//! Shared TCP listener lifecycle and bounded accept.

use super::{reserve_handle, reserve_shared_handle, NetState};
use crate::plugin::*;
use crate::{EvalAltResult, Module, Shared};
use std::io;
use std::net::{IpAddr, SocketAddr, TcpListener};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

/// A script-visible TCP listener. Clones share close state and quota ownership.
#[derive(Clone)]
pub struct NetListener(Arc<SharedListenerState>);

struct SharedListenerState {
    listener: Mutex<Option<TcpListener>>,
    open_handles: Arc<AtomicUsize>,
    max_handles: usize,
    accept_timeout: Duration,
    read_timeout: Duration,
    max_read_bytes: usize,
    write_timeout: Duration,
    max_write_bytes: usize,
    address: SocketAddr,
}

impl NetListener {
    fn close(&mut self) {
        let mut listener = self
            .0
            .listener
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        if listener.take().is_some() {
            self.0.open_handles.fetch_sub(1, Ordering::AcqRel);
        }
    }

    fn is_closed(&mut self) -> bool {
        self.0
            .listener
            .lock()
            .map(|listener| listener.is_none())
            .unwrap_or(true)
    }

    fn local_addr(&mut self) -> Result<String, Box<EvalAltResult>> {
        let listener = self
            .0
            .listener
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        let listener = listener.as_ref().ok_or_else(|| {
            net_io_error(
                "local_addr",
                self.0.address,
                io::ErrorKind::NotConnected,
                "listener is closed",
            )
        })?;
        listener
            .local_addr()
            .map(|address| address.to_string())
            .map_err(|error| {
                super::NetError::io("local_addr", self.0.address.to_string(), &error).into()
            })
    }

    fn accept(&mut self, timeout_ms: crate::INT) -> Result<super::NetStream, Box<EvalAltResult>> {
        if timeout_ms <= 0 {
            return Err(super::NetError::invalid(
                "accept",
                self.0.address.to_string(),
                "accept timeout must be a positive number of milliseconds",
            )
            .into());
        }
        let requested = Duration::from_millis(timeout_ms as u64);
        let timeout = requested.min(self.0.accept_timeout);
        let deadline = Instant::now().checked_add(timeout).ok_or_else(|| {
            super::NetError::invalid(
                "accept",
                self.0.address.to_string(),
                "accept timeout is not representable",
            )
        })?;
        let reservation = reserve_shared_handle(
            &self.0.open_handles,
            self.0.max_handles,
            "accept",
            self.0.address.to_string(),
        )?;

        loop {
            let remaining = deadline.saturating_duration_since(Instant::now());
            if remaining.is_zero() {
                return Err(accept_timeout(self.0.address));
            }
            let outcome = {
                let listener = self
                    .0
                    .listener
                    .lock()
                    .unwrap_or_else(|poisoned| poisoned.into_inner());
                let listener = listener.as_ref().ok_or_else(|| {
                    net_io_error(
                        "accept",
                        self.0.address,
                        io::ErrorKind::NotConnected,
                        "listener is closed",
                    )
                })?;
                listener.accept()
            };
            match outcome {
                Ok((stream, _peer)) => {
                    if let Err(error) = stream.set_nonblocking(true) {
                        return Err(super::NetError::io(
                            "accept",
                            self.0.address.to_string(),
                            &error,
                        )
                        .into());
                    }
                    reservation.commit();
                    return Ok(super::NetStream::new(
                        stream,
                        self.0.open_handles.clone(),
                        self.0.read_timeout,
                        self.0.max_read_bytes,
                        self.0.write_timeout,
                        self.0.max_write_bytes,
                    ));
                }
                Err(error) if error.kind() == io::ErrorKind::WouldBlock => {
                    std::thread::sleep(remaining.min(Duration::from_millis(5)));
                }
                Err(error) => {
                    return Err(
                        super::NetError::io("accept", self.0.address.to_string(), &error).into(),
                    )
                }
            }
        }
    }
}

pub(super) fn listen(
    state: &Shared<NetState>,
    address: &str,
    port: crate::INT,
) -> Result<NetListener, Box<EvalAltResult>> {
    let target = format!("{address}:{port}");
    let ip: IpAddr = address.parse().map_err(|_| {
        super::NetError::invalid(
            "listen",
            target.clone(),
            "address must be a numeric IPv4 or IPv6 address",
        )
    })?;
    if !(0..=u16::MAX as crate::INT).contains(&port) {
        return Err(
            super::NetError::invalid("listen", target, "port must be between 0 and 65535").into(),
        );
    }
    let endpoint = SocketAddr::new(ip, port as u16);
    let target = endpoint.to_string();
    if !state.config.listen.iter().any(|grant| *grant == endpoint) {
        return Err(super::NetError::denied(
            "listen",
            target,
            "host policy does not grant this endpoint",
        )
        .into());
    }

    let reservation = reserve_handle(state, "listen", target.clone())?;
    let listener = match TcpListener::bind(endpoint) {
        Ok(listener) => listener,
        Err(error) => return Err(super::NetError::io("listen", target, &error).into()),
    };
    if let Err(error) = listener.set_nonblocking(true) {
        return Err(super::NetError::io("listen", target, &error).into());
    }
    let address = match listener.local_addr() {
        Ok(address) => address,
        Err(error) => return Err(super::NetError::io("listen", target, &error).into()),
    };
    reservation.commit();
    Ok(NetListener(Arc::new(SharedListenerState {
        listener: Mutex::new(Some(listener)),
        open_handles: state.open_handles.clone(),
        max_handles: state.config.max_handles,
        accept_timeout: state.config.accept_timeout,
        read_timeout: state.config.read_timeout,
        max_read_bytes: state.config.max_read_bytes,
        write_timeout: state.config.write_timeout,
        max_write_bytes: state.config.max_write_bytes,
        address,
    })))
}

fn accept_timeout(address: SocketAddr) -> Box<EvalAltResult> {
    super::NetError::io(
        "accept",
        address.to_string(),
        &io::Error::new(io::ErrorKind::TimedOut, "accept deadline expired"),
    )
    .into()
}

fn net_io_error(
    op: &'static str,
    address: SocketAddr,
    kind: io::ErrorKind,
    message: &str,
) -> Box<EvalAltResult> {
    super::NetError::io(op, address.to_string(), &io::Error::new(kind, message)).into()
}

pub(super) fn register(module: &mut Module) {
    combine_with_exported_module!(module, "net_listener", net_listener_functions);
}

#[export_module]
mod net_listener_functions {
    #[rhai_fn(name = "close")]
    pub fn close(listener: &mut super::NetListener) {
        listener.close();
    }

    #[rhai_fn(get = "closed")]
    pub fn closed(listener: &mut super::NetListener) -> bool {
        listener.is_closed()
    }

    #[rhai_fn(get = "local_addr", return_raw)]
    pub fn local_addr(
        listener: &mut super::NetListener,
    ) -> Result<String, Box<crate::EvalAltResult>> {
        listener.local_addr()
    }

    #[rhai_fn(name = "accept", return_raw)]
    pub fn accept(
        listener: &mut super::NetListener,
        timeout_ms: crate::INT,
    ) -> Result<super::super::NetStream, Box<crate::EvalAltResult>> {
        listener.accept(timeout_ms)
    }
}

impl Drop for SharedListenerState {
    fn drop(&mut self) {
        let listener = match self.listener.get_mut() {
            Ok(listener) => listener,
            Err(poisoned) => poisoned.into_inner(),
        };
        if listener.take().is_some() {
            self.open_handles.fetch_sub(1, Ordering::AcqRel);
        }
    }
}
