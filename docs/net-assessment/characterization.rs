//! Diagnostic contract checks; no production source changes.
#![cfg(not(feature = "no_index"))]

use rhai::{packages::Package, Engine, Scope};
use rhai_net::{NetworkingPackage, SharedTcpStream};
use std::io::{Read, Write};
use std::net::{Shutdown, TcpListener};
use std::sync::mpsc;
use std::time::{Duration, Instant};

fn engine() -> Engine {
    let mut engine = Engine::new();
    NetworkingPackage::new().register_into_engine(&mut engine);
    engine
}

fn connected(payload: &'static [u8]) -> (Engine, Scope<'static>) {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let address = listener.local_addr().unwrap().to_string();
    listener.set_nonblocking(true).unwrap();
    let (ready_tx, ready_rx) = mpsc::channel();
    let peer = std::thread::spawn(move || {
        let deadline = Instant::now() + Duration::from_secs(3);
        let mut stream = loop {
            match listener.accept() {
                Ok((stream, _)) => break stream,
                Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                    assert!(Instant::now() < deadline, "client did not connect");
                    std::thread::sleep(Duration::from_millis(1));
                }
                Err(error) => panic!("accept failed: {error}"),
            }
        };
        stream
            .set_write_timeout(Some(Duration::from_secs(3)))
            .unwrap();
        stream.write_all(payload).unwrap();
        stream.shutdown(Shutdown::Write).unwrap();
        ready_tx.send(()).unwrap();
    });
    let mut scope = Scope::new();
    scope.push("address", address);
    let engine = engine();
    let stream = engine
        .eval_with_scope::<SharedTcpStream>(&mut scope, "tcp_connect(address)")
        .unwrap();
    stream
        .borrow()
        .set_read_timeout(Some(Duration::from_secs(3)))
        .unwrap();
    scope.push("stream", stream);
    ready_rx.recv_timeout(Duration::from_secs(3)).unwrap();
    peer.join().unwrap();
    (engine, scope)
}

#[test]
fn test_eof_blob_is_empty() {
    let (engine, mut scope) = connected(b"");
    let actual = engine
        .eval_with_scope::<rhai::Blob>(&mut scope, "stream.read_blob(10)")
        .unwrap();
    assert!(actual.is_empty(), "EOF produced invented bytes: {actual:?}");
}

#[test]
fn test_short_blob_contains_only_received_bytes() {
    let payload = b"ABC";
    let (engine, mut scope) = connected(payload);
    let actual = engine
        .eval_with_scope::<rhai::Blob>(&mut scope, "stream.read_blob(10)")
        .unwrap();
    assert!(
        !actual.is_empty() && payload.starts_with(&actual),
        "peer sent {payload:?}; package returned {actual:?}"
    );
}

// These two tests express proposed input-validation contracts. The report
// distinguishes them from the existing documented byte-read contract.
#[test]
fn test_negative_port_is_rejected() {
    let result = engine().eval::<std::net::SocketAddr>(r#"addr("127.0.0.1", -1)"#);
    assert!(
        result.is_err(),
        "negative port was silently converted: {result:?}"
    );
}

#[test]
fn test_oversized_port_is_rejected() {
    let result = engine().eval::<std::net::SocketAddr>(r#"addr("127.0.0.1", 65536)"#);
    assert!(
        result.is_err(),
        "oversized port was silently converted: {result:?}"
    );
}

#[test]
fn test_script_write_reaches_independent_tcp_peer() {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let address = listener.local_addr().unwrap().to_string();
    listener.set_nonblocking(true).unwrap();
    let peer = std::thread::spawn(move || {
        let deadline = Instant::now() + Duration::from_secs(3);
        let mut stream = loop {
            match listener.accept() {
                Ok((stream, _)) => break stream,
                Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                    assert!(Instant::now() < deadline, "client did not connect");
                    std::thread::sleep(Duration::from_millis(1));
                }
                Err(error) => panic!("accept failed: {error}"),
            }
        };
        stream
            .set_read_timeout(Some(Duration::from_secs(3)))
            .unwrap();
        let mut bytes = Vec::new();
        stream.read_to_end(&mut bytes).unwrap();
        bytes
    });
    let mut scope = Scope::new();
    scope.push("address", address);
    let written = engine().eval_with_scope::<rhai::INT>(
        &mut scope,
        r#"let stream = tcp_connect(address); let count = stream.write("from Rhai"); stream.shutdown(); count"#,
    ).unwrap();
    assert_eq!(written, 9);
    assert_eq!(peer.join().unwrap(), b"from Rhai");
}
