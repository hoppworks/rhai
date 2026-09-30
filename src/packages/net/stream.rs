//! Shared logical TCP handle lifecycle.

use crate::plugin::*;
use crate::Module;
use std::net::TcpStream;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};

/// A script-visible TCP stream handle. Cloned values share one close state.
#[derive(Clone)]
pub struct NetStream(Arc<SharedStreamState>);

struct SharedStreamState {
    socket: Mutex<Option<TcpStream>>,
    open_handles: Arc<AtomicUsize>,
}

impl NetStream {
    pub(super) fn new(stream: TcpStream, open_handles: Arc<AtomicUsize>) -> Self {
        Self(Arc::new(SharedStreamState {
            socket: Mutex::new(Some(stream)),
            open_handles,
        }))
    }

    fn close(&mut self) {
        if let Ok(mut socket) = self.0.socket.lock() {
            if socket.take().is_some() {
                self.0.open_handles.fetch_sub(1, Ordering::AcqRel);
            }
        }
    }

    fn is_closed(&mut self) -> bool {
        self.0
            .socket
            .lock()
            .map(|socket| socket.is_none())
            .unwrap_or(true)
    }
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
