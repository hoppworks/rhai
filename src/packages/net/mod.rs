//! Optional host-controlled TCP network access.
//!
//! The package starts with no grants. Hosts grant exact numeric socket endpoints with
//! [`NetConfig`] before registering a [`NetPackage`] with an engine. Connect and
//! listen grants are separate and match exact numeric socket endpoints.
//! With `no_object`, use the registered free-function forms (for example,
//! `write_all_string(stream, "hello")`, `peer_addr(stream)`, and
//! `accept(listener, 500)`) because dot syntax is unavailable.

#[cfg(feature = "no_std")]
compile_error!("the `net` feature requires `std`; it cannot be combined with `no_std`");

#[cfg(target_family = "wasm")]
compile_error!("the `net` feature is not available on WASM targets");

mod config;
mod error;
mod listener;
mod stream;

pub use config::NetConfig;
pub use error::NetError;
pub use listener::NetListener;
pub use stream::NetStream;

pub(super) const MAX_READ_BYTES: usize = 1024 * 1024;
pub(super) const MAX_WRITE_BYTES: usize = 1024 * 1024;

use crate::packages::Package;
use crate::{FuncRegistration, Module, Shared, SharedModule};
use std::net::{IpAddr, SocketAddr, TcpStream};
use std::sync::atomic::AtomicUsize;
use std::sync::Arc;

/// Host policy for outgoing TCP connections.
pub(super) struct NetState {
    config: NetConfig,
    open_handles: Arc<AtomicUsize>,
}

/// An optional package for host-authorized TCP connections.
#[derive(Clone)]
pub struct NetPackage(SharedModule);

impl NetPackage {
    /// Build a package using the supplied host grants and connect deadline.
    pub fn new(config: NetConfig) -> Result<Self, NetError> {
        if config.connect_timeout.is_zero()
            || std::time::Instant::now()
                .checked_add(config.connect_timeout)
                .is_none()
        {
            return Err(NetError::invalid(
                "configure connect timeout",
                format!("{:?}", config.connect_timeout),
                "connect timeout must be finite, positive, and representable",
            ));
        }
        if config.accept_timeout.is_zero()
            || std::time::Instant::now()
                .checked_add(config.accept_timeout)
                .is_none()
        {
            return Err(NetError::invalid(
                "configure accept timeout",
                format!("{:?}", config.accept_timeout),
                "accept timeout must be finite, positive, and representable",
            ));
        }
        if config.read_timeout.is_zero()
            || std::time::Instant::now()
                .checked_add(config.read_timeout)
                .is_none()
        {
            return Err(NetError::invalid(
                "configure read timeout",
                format!("{:?}", config.read_timeout),
                "read timeout must be finite, positive, and representable",
            ));
        }
        if config.write_timeout.is_zero()
            || std::time::Instant::now()
                .checked_add(config.write_timeout)
                .is_none()
        {
            return Err(NetError::invalid(
                "configure write timeout",
                format!("{:?}", config.write_timeout),
                "write timeout must be finite, positive, and representable",
            ));
        }
        if config.max_read_bytes == 0 || config.max_read_bytes > MAX_READ_BYTES {
            return Err(NetError::invalid(
                "configure read limit",
                config.max_read_bytes.to_string(),
                "read limit must be between 1 and 1048576 bytes",
            ));
        }
        if config.max_write_bytes == 0 || config.max_write_bytes > MAX_WRITE_BYTES {
            return Err(NetError::invalid(
                "configure write limit",
                config.max_write_bytes.to_string(),
                "write limit must be between 1 and 1048576 bytes",
            ));
        }
        if config.max_handles == 0 || config.max_handles > 64 {
            return Err(NetError::invalid(
                "configure handle limit",
                config.max_handles.to_string(),
                "handle limit must be between 1 and 64",
            ));
        }

        let state = Shared::new(NetState {
            config,
            open_handles: Arc::new(AtomicUsize::new(0)),
        });
        let mut module = Module::new();
        NetError::register(&mut module);
        module.set_custom_type::<NetStream>("NetStream");
        module.set_custom_type::<NetListener>("NetListener");
        stream::register(&mut module);
        listener::register(&mut module);

        let st = state.clone();
        reg(
            "connect",
            &["/// Connect to an exact host-granted numeric IP address and port."],
        )
        .set_into_module(&mut module, move |address: &str, port: crate::INT| {
            connect(&st, address, port)
        });

        let st = state.clone();
        reg(
            "listen",
            &["/// Listen on an exact host-granted numeric IP address and port."],
        )
        .set_into_module(&mut module, move |address: &str, port: crate::INT| {
            listener::listen(&st, address, port)
        });

        module.build_index();
        Ok(Self(module.into()))
    }
}

impl Package for NetPackage {
    fn init(_module: &mut Module) {}

    #[inline(always)]
    fn as_shared_module(&self) -> SharedModule {
        self.0.clone()
    }
}

fn connect(
    state: &Shared<NetState>,
    address: &str,
    port: crate::INT,
) -> Result<NetStream, Box<crate::EvalAltResult>> {
    let target = format!("{address}:{port}");
    let ip: IpAddr = address.parse().map_err(|_| {
        NetError::invalid(
            "connect",
            target.clone(),
            "address must be a numeric IPv4 or IPv6 address",
        )
    })?;
    if !(1..=u16::MAX as crate::INT).contains(&port) {
        return Err(
            NetError::invalid("connect", target, "port must be between 1 and 65535").into(),
        );
    }
    let endpoint = SocketAddr::new(ip, port as u16);
    let target = endpoint.to_string();
    if !state.config.connect.iter().any(|grant| *grant == endpoint) {
        return Err(NetError::denied(
            "connect",
            target,
            "host policy does not grant this endpoint",
        )
        .into());
    }

    let reservation = reserve_handle(state, "connect", target.clone())?;
    let socket = match TcpStream::connect_timeout(&endpoint, state.config.connect_timeout) {
        Ok(socket) => socket,
        Err(error) => return Err(NetError::io("connect", target, &error).into()),
    };
    if let Err(error) = socket.set_nonblocking(true) {
        return Err(NetError::io("connect", target, &error).into());
    }
    reservation.commit();
    Ok(NetStream::new(
        socket,
        state.open_handles.clone(),
        state.config.read_timeout,
        state.config.max_read_bytes,
        state.config.write_timeout,
        state.config.max_write_bytes,
    ))
}

pub(super) struct HandleReservation {
    open_handles: Arc<AtomicUsize>,
    committed: bool,
}

impl HandleReservation {
    pub(super) fn commit(mut self) {
        self.committed = true;
    }
}

impl Drop for HandleReservation {
    fn drop(&mut self) {
        if !self.committed {
            self.open_handles
                .fetch_sub(1, std::sync::atomic::Ordering::AcqRel);
        }
    }
}

pub(super) fn reserve_handle(
    state: &NetState,
    op: &'static str,
    target: impl Into<String>,
) -> Result<HandleReservation, Box<crate::EvalAltResult>> {
    reserve_shared_handle(&state.open_handles, state.config.max_handles, op, target)
}

pub(super) fn reserve_shared_handle(
    open_handles: &Arc<AtomicUsize>,
    max_handles: usize,
    op: &'static str,
    target: impl Into<String>,
) -> Result<HandleReservation, Box<crate::EvalAltResult>> {
    let target = target.into();
    let previous = open_handles.fetch_update(
        std::sync::atomic::Ordering::AcqRel,
        std::sync::atomic::Ordering::Acquire,
        |open| (open < max_handles).then_some(open + 1),
    );
    if previous.is_err() {
        return Err(
            NetError::resource_limit(op, target, "host TCP handle limit is reached").into(),
        );
    }
    Ok(HandleReservation {
        open_handles: open_handles.clone(),
        committed: false,
    })
}

#[allow(unused_variables)]
fn reg(name: &str, comments: &[&str]) -> FuncRegistration {
    let registration = FuncRegistration::new(name).with_volatility(true);
    #[cfg(feature = "metadata")]
    let registration = registration.with_comments(comments);
    registration
}
