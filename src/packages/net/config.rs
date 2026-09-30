//! Host-side configuration for the optional `net` package.

use std::net::SocketAddr;
use std::time::Duration;

/// Host grants and finite deadlines for TCP operations.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NetConfig {
    pub(crate) connect: Vec<SocketAddr>,
    pub(crate) listen: Vec<SocketAddr>,
    pub(crate) connect_timeout: Duration,
    pub(crate) accept_timeout: Duration,
    pub(crate) read_timeout: Duration,
    pub(crate) write_timeout: Duration,
    pub(crate) max_read_bytes: usize,
    pub(crate) max_write_bytes: usize,
    pub(crate) max_handles: usize,
}

impl Default for NetConfig {
    fn default() -> Self {
        Self {
            connect: Vec::new(),
            listen: Vec::new(),
            connect_timeout: Duration::from_secs(5),
            accept_timeout: Duration::from_secs(5),
            read_timeout: Duration::from_secs(5),
            write_timeout: Duration::from_secs(5),
            max_read_bytes: 1024 * 1024,
            max_write_bytes: 1024 * 1024,
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

    /// Grant listening on exactly this numeric IP address and port.
    ///
    /// Port zero is an explicit grant for an OS-selected ephemeral port.
    #[must_use]
    pub fn allow_listen(mut self, endpoint: SocketAddr) -> Self {
        self.listen.push(endpoint);
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

    /// Set the finite positive host ceiling for script accept waits.
    ///
    /// Scripts may request a shorter timeout. A zero duration is rejected when
    /// [`super::NetPackage::new`] builds the package.
    #[must_use]
    pub fn accept_timeout(mut self, timeout: Duration) -> Self {
        self.accept_timeout = timeout;
        self
    }

    /// Set the finite positive host ceiling for script stream reads.
    ///
    /// Script methods may request a shorter timeout. Receive storage is always capped at
    /// 1 MiB, and this setting may lower that cap. Zero is rejected when the package is built.
    #[must_use]
    pub fn read_timeout(mut self, timeout: Duration) -> Self {
        self.read_timeout = timeout;
        self
    }

    /// Set the finite positive host ceiling for script stream writes (five seconds by default).
    ///
    /// Script methods may request a shorter timeout. Zero is rejected when the package is built.
    #[must_use]
    pub fn write_timeout(mut self, timeout: Duration) -> Self {
        self.write_timeout = timeout;
        self
    }

    /// Lower the per-call receive allocation ceiling (at most 1 MiB).
    ///
    /// Zero is rejected when the package is built. Engine string/blob limits may lower the
    /// effective bound further in checked builds.
    #[must_use]
    pub fn max_read_bytes(mut self, limit: usize) -> Self {
        self.max_read_bytes = limit;
        self
    }

    /// Lower the per-call stream write input ceiling (at most 1 MiB; defaults to 1 MiB).
    ///
    /// `write_*` returns the actual count from one socket write; `write_all_*` continues
    /// until the full input is accepted or reports the transferred count on failure. Zero
    /// is rejected when the package is built. Engine string/blob limits may lower the
    /// effective bound further in checked builds.
    #[must_use]
    pub fn max_write_bytes(mut self, limit: usize) -> Self {
        self.max_write_bytes = limit;
        self
    }

    /// Lower the shared open stream/listener ceiling (at most 64, the package maximum).
    #[must_use]
    pub fn max_handles(mut self, limit: usize) -> Self {
        self.max_handles = limit;
        self
    }
}
