//! Host-side configuration for the optional `net` package.

use std::net::SocketAddr;
use std::time::Duration;

/// Host grants and the maximum duration for a connect operation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NetConfig {
    pub(crate) connect: Vec<SocketAddr>,
    pub(crate) connect_timeout: Duration,
    pub(crate) max_handles: usize,
}

impl Default for NetConfig {
    fn default() -> Self {
        Self {
            connect: Vec::new(),
            connect_timeout: Duration::from_secs(5),
            max_handles: 64,
        }
    }
}

impl NetConfig {
    /// Grant outgoing connections to exactly this numeric IP address and port.
    #[must_use]
    pub fn allow_connect(mut self, endpoint: SocketAddr) -> Self {
        self.connect.push(endpoint);
        self
    }

    /// Set the finite positive host ceiling for connect operations.
    ///
    /// A zero duration is rejected when [`super::NetPackage::new`] builds the package.
    #[must_use]
    pub fn connect_timeout(mut self, timeout: Duration) -> Self {
        self.connect_timeout = timeout;
        self
    }

    /// Lower the shared open-stream ceiling (at most 64, the package maximum).
    #[must_use]
    pub fn max_handles(mut self, limit: usize) -> Self {
        self.max_handles = limit;
        self
    }
}
