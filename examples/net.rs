//! Run with `cargo run --example net --features net`.
//! The host grants only the ephemeral loopback endpoint created below.

use rhai::packages::net::{NetConfig, NetPackage};
use rhai::packages::Package;
use rhai::{Engine, Scope};
use std::io::{self, Read, Write};
use std::net::{Shutdown, TcpListener};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};

struct Peer(Option<JoinHandle<io::Result<Vec<u8>>>>);

impl Peer {
    fn join(mut self) -> io::Result<Vec<u8>> {
        self.0
            .take()
            .unwrap()
            .join()
            .map_err(|_| io::Error::new(io::ErrorKind::Other, "loopback peer panicked"))?
    }
}

impl Drop for Peer {
    fn drop(&mut self) {
        if let Some(handle) = self.0.take() {
            let _ = handle.join();
        }
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let endpoint = listener.local_addr()?;
    listener.set_nonblocking(true)?;
    let peer = Peer(Some(thread::spawn(move || {
        let deadline = Instant::now() + Duration::from_secs(2);
        let mut socket = loop {
            match listener.accept() {
                Ok((socket, _)) => break socket,
                Err(error) if error.kind() == io::ErrorKind::WouldBlock => {
                    if Instant::now() >= deadline {
                        return Err(io::Error::new(
                            io::ErrorKind::TimedOut,
                            "no script connection",
                        ));
                    }
                    thread::yield_now();
                }
                Err(error) => return Err(error),
            }
        };
        socket.set_nonblocking(false)?;
        socket.set_read_timeout(Some(Duration::from_secs(2)))?;
        socket.set_write_timeout(Some(Duration::from_secs(2)))?;
        let mut received = Vec::new();
        (&mut socket).take(17).read_to_end(&mut received)?;
        socket.write_all(b"pong")?;
        socket.shutdown(Shutdown::Write)?;
        Ok(received)
    })));

    let config = NetConfig::default()
        .allow_connect(endpoint)
        .connect_timeout(Duration::from_secs(2))
        .read_timeout(Duration::from_secs(2))
        .write_timeout(Duration::from_secs(2))
        .max_read_bytes(16)
        .max_write_bytes(16)
        .max_handles(1);
    let mut engine = Engine::new();
    NetPackage::new(config)?.register_into_engine(&mut engine);
    let mut scope = Scope::new();
    scope.push("port", endpoint.port() as rhai::INT);
    // Explicit calls also work when `no_object` disables dot syntax.
    let reply = engine.eval_with_scope::<String>(
        &mut scope,
        r#"
            let stream = connect("127.0.0.1", port);
            let written = write_all_string(stream, "ping", 1000);
            if written != 4 { throw "short write"; }
            shutdown_write(stream);
            let reply = read_to_end_string(stream, 16, 1000);
            close(stream);
            reply
        "#,
    )?;
    let received = peer.join()?;
    assert_eq!(
        received, b"ping",
        "independent peer received the script bytes"
    );
    assert_eq!(reply, "pong", "script received the peer reply");
    println!("Peer received ping; script received {reply}.");
    Ok(())
}
