#![cfg(all(feature = "net", feature = "no_object"))]

use rhai::packages::net::{NetConfig, NetPackage};
use rhai::packages::Package;
use rhai::Engine;
use std::io::{Read, Write};
use std::net::{Shutdown, SocketAddr, TcpListener, TcpStream};
use std::time::{Duration, Instant};

struct JoinOnDrop<T>(Option<std::thread::JoinHandle<T>>);

impl<T> JoinOnDrop<T> {
    fn new(handle: std::thread::JoinHandle<T>) -> Self {
        Self(Some(handle))
    }

    fn join(mut self) -> T {
        self.0.take().unwrap().join().expect("peer fixture thread joins")
    }
}

impl<T> Drop for JoinOnDrop<T> {
    fn drop(&mut self) {
        if let Some(handle) = self.0.take() {
            let _ = handle.join();
        }
    }
}

#[test]
fn registered_stream_functions_work_without_dot_syntax() {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let endpoint: SocketAddr = listener.local_addr().unwrap();
    let peer = JoinOnDrop::new(std::thread::spawn(move || {
        listener.set_nonblocking(true).unwrap();
        let deadline = Instant::now() + Duration::from_secs(2);
        let (mut stream, _) = loop {
            match listener.accept() {
                Ok(peer) => break peer,
                Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                    assert!(Instant::now() < deadline, "script did not connect");
                    std::thread::yield_now();
                }
                Err(error) => panic!("peer accept failed: {error}"),
            }
        };
        stream.set_nonblocking(false).unwrap();
        stream.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
        stream.write_all(b"reply").unwrap();
        stream.shutdown(Shutdown::Write).unwrap();
        let mut bytes = Vec::new();
        stream.read_to_end(&mut bytes).unwrap();
        bytes
    }));

    let mut engine = Engine::new();
    NetPackage::new(NetConfig::default().allow_connect(endpoint)).unwrap().register_into_engine(&mut engine);
    let count = engine
        .eval::<String>(&format!(
            r#"let stream = connect("127.0.0.1", {});
               let response = read_to_end_string(stream, 5);
               let address = peer_addr(stream);
               if address != "127.0.0.1:{}" {{ throw "peer_addr returned another endpoint"; }}
               if closed(stream) {{ throw "new stream reported closed"; }}
               let count = write_all_string(stream, "ping");
               if count != 4 {{ throw "write count differed from peer bytes"; }}
               shutdown_write(stream); close(stream);
               if !closed(stream) {{ throw "closed stream reported open"; }}
               response + "|" + address"#,
            endpoint.port(),
            endpoint.port()
        ))
        .expect("registered NetStream functions are callable with explicit handles");

    assert_eq!(count, format!("reply|{endpoint}"));
    let received = peer.join();
    if std::env::var_os("RHAI_NET_NO_OBJECT_WRONG_PEER_EXPECTATION").is_some() {
        assert_eq!(received, b"pang", "deliberately wrong independent peer expectation");
    } else {
        assert_eq!(received, b"ping", "independent peer observed exact script bytes");
    }
}

#[test]
fn registered_listener_functions_work_with_explicit_handle_arguments() {
    let reservation = TcpListener::bind("127.0.0.1:0").unwrap();
    let endpoint: SocketAddr = reservation.local_addr().unwrap();
    drop(reservation);

    let peer = JoinOnDrop::new(std::thread::spawn(move || {
        let deadline = Instant::now() + Duration::from_secs(2);
        let mut stream = loop {
            match TcpStream::connect_timeout(&endpoint, Duration::from_millis(50)) {
                Ok(stream) => break stream,
                Err(error) if matches!(error.kind(), std::io::ErrorKind::ConnectionRefused | std::io::ErrorKind::TimedOut) => {
                    assert!(Instant::now() < deadline, "script listener was not reachable");
                    std::thread::yield_now();
                }
                Err(error) => panic!("peer connect failed: {error}"),
            }
        };
        stream.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
        let mut bytes = Vec::new();
        stream.read_to_end(&mut bytes).unwrap();
        bytes
    }));

    let mut engine = Engine::new();
    NetPackage::new(NetConfig::default().allow_listen(endpoint)).unwrap().register_into_engine(&mut engine);
    let result = engine
        .eval::<rhai::INT>(&format!(
            r#"let listener = listen("127.0.0.1", {});
               let address = local_addr(listener);
               if address != "127.0.0.1:{}" {{ throw "local_addr returned another endpoint"; }}
               if closed(listener) {{ throw "new listener reported closed"; }}
               let stream = accept(listener, 500);
               let count = write_all_string(stream, "pong");
               shutdown_write(stream); close(stream);
               if !closed(stream) {{ throw "closed stream reported open"; }}
               close(listener);
               if !closed(listener) {{ throw "closed listener reported open"; }}
               count"#,
            endpoint.port(),
            endpoint.port()
        ))
        .expect("registered listener and stream functions accept explicit handles");

    assert_eq!(result, 4);
    assert_eq!(peer.join(), b"pong");
}

#[test]
fn registered_error_getters_are_callable_with_explicit_arguments() {
    let mut engine = Engine::new();
    NetPackage::new(NetConfig::default()).unwrap().register_into_engine(&mut engine);
    let inspected = engine
        .eval::<bool>(
            r#"let inspected = false;
               try { connect("127.0.0.1", 9); }
               catch (error) { inspected = kind(error) == "Denied" && message(error) != "" && io_kind(error) == () && op(error) == "connect" && target(error) == "127.0.0.1:9" && partial_bytes(error) == 0; }
               inspected"#,
        )
        .expect("registered NetError getters accept explicit error arguments");
    assert!(inspected, "denied errors expose kind, op, and partial byte count");
}
