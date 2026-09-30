//! Optional host-controlled TCP connect access.
//!
//! The package starts with no grants. Hosts grant exact numeric socket endpoints with
//! [`NetConfig::allow_connect`] before registering a [`NetPackage`] with an engine.
//! This first slice supports outgoing connections and shared close only; listeners and
//! byte transfer are not included.

#[cfg(feature = "no_std")]
compile_error!("the `net` feature requires `std`; it cannot be combined with `no_std`");

#[cfg(target_family = "wasm")]
compile_error!("the `net` feature is not available on WASM targets");

mod config;
mod error;
mod stream;

pub use config::NetConfig;
pub use error::NetError;
pub use stream::NetStream;

use crate::packages::Package;
use crate::{FuncRegistration, Module, Shared, SharedModule};
use std::net::{IpAddr, SocketAddr, TcpStream};
use std::sync::atomic::AtomicUsize;
use std::sync::Arc;

/// Host policy for outgoing TCP connections.
struct NetState {
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
        stream::register(&mut module);

        let st = state.clone();
        reg(
            "connect",
            &["/// Connect to an exact host-granted numeric IP address and port."],
        )
        .set_into_module(&mut module, move |address: &str, port: crate::INT| {
            connect(&st, address, port)
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

    let previous = state.open_handles.fetch_update(
        std::sync::atomic::Ordering::AcqRel,
        std::sync::atomic::Ordering::Acquire,
        |open| (open < state.config.max_handles).then_some(open + 1),
    );
    if previous.is_err() {
        return Err(NetError::resource_limit(
            "connect",
            target,
            "host TCP handle limit is reached",
        )
        .into());
    }
    let socket = match TcpStream::connect_timeout(&endpoint, state.config.connect_timeout) {
        Ok(socket) => socket,
        Err(error) => {
            state
                .open_handles
                .fetch_sub(1, std::sync::atomic::Ordering::AcqRel);
            return Err(NetError::io("connect", target, &error).into());
        }
    };
    Ok(NetStream::new(socket, state.open_handles.clone()))
}

#[allow(unused_variables)]
fn reg(name: &str, comments: &[&str]) -> FuncRegistration {
    let registration = FuncRegistration::new(name).with_volatility(true);
    #[cfg(feature = "metadata")]
    let registration = registration.with_comments(comments);
    registration
}
