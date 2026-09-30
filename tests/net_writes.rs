#![cfg(all(feature = "net", not(feature = "no_object")))]

use rhai::packages::net::{NetConfig, NetPackage};
use rhai::packages::Package;
use rhai::Engine;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::panic::{catch_unwind, resume_unwind, AssertUnwindSafe};
use std::time::Duration;

fn read_bounded_to_end(mut stream: &TcpStream, max_bytes: usize) -> Vec<u8> {
    let mut bytes = Vec::new();
    stream.take((max_bytes + 1) as u64).read_to_end(&mut bytes).unwrap();
    assert!(bytes.len() <= max_bytes, "peer data exceeded fixture bound");
    bytes
}

fn engine(config: NetConfig) -> Engine {
    let mut engine = Engine::new();
    NetPackage::new(config).expect("valid NetConfig").register_into_engine(&mut engine);
    engine
}

fn connected<F, P, R>(config: NetConfig, peer_action: F, script: impl FnOnce(&mut Engine, u16) -> R) -> (R, P)
where
    F: FnOnce(TcpStream) -> P + Send + 'static,
    P: Send + 'static,
{
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let endpoint: SocketAddr = listener.local_addr().unwrap();
    listener.set_nonblocking(true).unwrap();
    let mut engine = engine(config.allow_connect(endpoint));
    let peer = std::thread::spawn(move || {
        let deadline = std::time::Instant::now() + Duration::from_secs(2);
        let (stream, _) = loop {
            match listener.accept() {
                Ok(peer) => break peer,
                Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                    assert!(std::time::Instant::now() < deadline, "script did not connect");
                    std::thread::yield_now();
                }
                Err(error) => panic!("peer accept failed: {error}"),
            }
        };
        stream.set_nonblocking(false).unwrap();
        stream.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
        stream.set_write_timeout(Some(Duration::from_secs(2))).unwrap();
        peer_action(stream)
    });
    let result = catch_unwind(AssertUnwindSafe(|| script(&mut engine, endpoint.port())));
    let peer_result = peer.join().expect("peer exits after script operation");
    match result {
        Ok(result) => (result, peer_result),
        Err(payload) => resume_unwind(payload),
    }
}

#[test]
fn script_writes_string_and_write_all_report_real_peer_bytes() {
    let (counts, received) = connected(
        NetConfig::default(),
        |mut peer| read_bounded_to_end(&peer, 20 * 1024 * 1024),
        |engine, port| {
            engine
                .eval::<String>(&format!(
                    r#"let stream = connect("127.0.0.1", {port});
                       let first = stream.write_string("hello");
                       let second = stream.write_all_string(" world");
                       stream.shutdown_write(); stream.close(); first.to_string() + "," + second.to_string()"#
                ))
                .unwrap()
        },
    );
    assert_eq!(counts, "5,6");
    assert_eq!(received, b"hello world");
}

#[cfg(not(feature = "no_index"))]
#[test]
fn script_write_blob_preserves_exact_bytes() {
    let (count, received) = connected(
        NetConfig::default(),
        |mut peer| read_bounded_to_end(&peer, 20 * 1024 * 1024),
        |engine, port| {
            let mut scope = rhai::Scope::new();
            scope.push("payload", rhai::Blob::from([0_u8, 255, 65]));
            engine
                .eval_with_scope::<rhai::INT>(
                    &mut scope,
                    &format!(
                        r#"let stream = connect("127.0.0.1", {port});
                           let count = stream.write_all_blob(payload);
                           stream.shutdown_write(); stream.close(); count"#
                    ),
                )
                .unwrap()
        },
    );
    assert_eq!(count, 3);
    if std::env::var_os("RHAI_NET_WRONG_WRITE_EXPECTATION").is_some() {
        assert_eq!(received, [0, 254, b'A']);
    } else {
        assert_eq!(received, [0, 255, b'A']);
    }
}

#[cfg(feature = "no_index")]
#[test]
fn no_index_keeps_string_writes_and_omits_blob_writes() {
    let (result, received) = connected(
        NetConfig::default(),
        |peer| read_bounded_to_end(&peer, 20 * 1024 * 1024),
        |engine, port| {
            let mut scope = rhai::Scope::new();
            engine
                .eval_with_scope::<rhai::INT>(
                    &mut scope,
                    &format!(
                        r#"let stream = connect("127.0.0.1", {port});
                           let count = stream.write_all_string("ok"); stream.shutdown_write(); count"#
                    ),
                )
                .unwrap();
            scope.push("payload", vec![1_u8, 2, 3]);
            let omitted = engine.eval_with_scope::<()>(&mut scope, "stream.write_blob(payload)").unwrap_err();
            let omitted = matches!(*omitted, rhai::EvalAltResult::ErrorFunctionNotFound(..));
            engine.run_with_scope(&mut scope, "stream.close();").unwrap();
            omitted
        },
    );
    assert!(result);
    assert_eq!(received, b"ok");
}

#[test]
fn write_half_close_keeps_the_read_direction_and_is_idempotent() {
    let (result, peer_bytes) = connected(
        NetConfig::default(),
        |mut peer| {
            peer.write_all(b"reply").unwrap();
            read_bounded_to_end(&peer, 20 * 1024 * 1024)
        },
        |engine, port| {
            engine
                .eval::<String>(&format!(
                    r#"let stream = connect("127.0.0.1", {port});
                       stream.shutdown_write(); stream.shutdown_write();
                       let write_closed = false;
                       try {{ stream.write_string("x"); }} catch (err) {{ write_closed = err.kind == "Io"; }}
                       let response = stream.read_to_end_string(8);
                       stream.close(); let empty_closed = false;
                       try {{ stream.write_string(""); }} catch (err) {{ empty_closed = err.kind == "Io"; }}
                       write_closed.to_string() + "," + empty_closed.to_string() + "|" + response"#
                ))
                .unwrap()
        },
    );
    assert_eq!(result, "true,true|reply");
    assert_eq!(peer_bytes, b"");
}

#[test]
fn bounded_write_timeout_reports_partial_bytes_matching_peer_readback() {
    let (release_tx, release_rx) = std::sync::mpsc::sync_channel(1);
    let (result, peer_bytes) = connected(
        NetConfig::default().write_timeout(Duration::from_millis(30)).max_write_bytes(64 * 1024),
        move |peer| {
            release_rx.recv_timeout(Duration::from_secs(3)).expect("script finishes its bounded writes");
            read_bounded_to_end(&peer, 64 * 1024 * 1024)
        },
        move |engine, port| {
            let mut scope = rhai::Scope::new();
            scope.push("payload", "x".repeat(64 * 1024));
            let started = std::time::Instant::now();
            let result = engine
                .eval_with_scope::<String>(
                    &mut scope,
                    &format!(
                        r#"let stream = connect("127.0.0.1", {port});
                           let kind = "none"; let partial = -1; let successes = 0; let finished = false;
                           while successes < 1024 && !finished {{
                               try {{ stream.write_all_string(payload, 1000); successes += 1; }}
                               catch (err) {{ kind = err.kind; partial = err.partial_bytes; finished = true; }}
                           }}
                           stream.close(); kind + ":" + successes.to_string() + ":" + partial.to_string()"#
                    ),
                )
                .unwrap();
            release_tx.send(()).unwrap();
            (result, started.elapsed())
        },
    );
    let (result, elapsed) = result;
    assert!(elapsed < Duration::from_millis(500), "script timeout cannot extend the 30ms host ceiling: {elapsed:?}");
    let mut fields = result.split(':');
    assert_eq!(fields.next(), Some("Timeout"), "write did not hit its finite deadline: {result}");
    let successes: usize = fields.next().unwrap().parse().unwrap();
    let reported: usize = fields.next().unwrap().parse().unwrap();
    assert!(reported < 64 * 1024, "partial count is within the attempted write: {result}");
    assert_eq!(peer_bytes.len(), successes * 64 * 1024 + reported, "independent peer readback matches accepted writes plus partial_bytes");
    assert!(peer_bytes.iter().all(|byte| *byte == b'x'));
}

#[test]
fn host_write_cap_rejects_oversize_input_without_peer_bytes() {
    let (result, received) = connected(
        NetConfig::default().max_write_bytes(3),
        |mut peer| read_bounded_to_end(&peer, 20 * 1024 * 1024),
        |engine, port| {
            engine
                .eval::<String>(&format!(
                    r#"let stream = connect("127.0.0.1", {port}); let rejected = false;
                       try {{ stream.write_string("four"); }} catch (err) {{ rejected = err.kind == "ResourceLimit"; }}
                       let invalid = false; try {{ stream.write_string("x", 0); }} catch (err) {{ invalid = err.kind == "InvalidInput" && err.op == "write_string"; }}
                       stream.close(); let empty_closed = false;
                       try {{ stream.write_string(""); }} catch (err) {{ empty_closed = err.kind == "Io"; }}
                       rejected.to_string() + "," + invalid.to_string() + "," + empty_closed.to_string()"#
                ))
                .unwrap()
        },
    );
    assert_eq!(result, "true,true,true");
    assert!(received.is_empty(), "rejected write sends no prefix");
}

#[cfg(not(feature = "unchecked"))]
#[test]
fn engine_string_limit_rejects_write_before_peer_bytes() {
    let (result, received) = connected(
        NetConfig::default(),
        |peer| read_bounded_to_end(&peer, 1),
        |engine, port| {
            let mut scope = rhai::Scope::new();
            scope.push("payload", "four".to_string());
            engine.eval_with_scope::<()>(&mut scope, &format!(r#"let stream = connect("127.0.0.1", {port});"#)).unwrap();
            engine.set_max_string_size(3);
            let error = engine.eval_with_scope::<rhai::INT>(&mut scope, "stream.write_string(payload)").unwrap_err();
            let detail = format!("{error:?}");
            let rejected = match *error {
                rhai::EvalAltResult::ErrorDataTooLarge(..) => true,
                rhai::EvalAltResult::ErrorRuntime(value, _) => value.try_cast::<rhai::packages::net::NetError>().map_or(false, |error| error.kind() == "ResourceLimit"),
                _ => false,
            };
            assert!(rejected, "unexpected engine-limit error: {detail}");
            scope.remove::<String>("payload");
            engine.run_with_scope(&mut scope, "stream.close();").unwrap();
            rejected
        },
    );
    assert!(result);
    assert!(received.is_empty());
}

#[test]
fn invalid_host_write_bounds_are_rejected() {
    assert!(NetPackage::new(NetConfig::default().max_write_bytes(0)).is_err());
    assert!(NetPackage::new(NetConfig::default().max_write_bytes(1024 * 1024 + 1)).is_err());
    assert!(NetPackage::new(NetConfig::default().write_timeout(Duration::ZERO)).is_err());
    assert!(NetPackage::new(NetConfig::default().write_timeout(Duration::MAX)).is_err());
}

#[test]
fn read_half_close_is_idempotent_and_keeps_stream_open_for_close() {
    let (result, peer_bytes) = connected(
        NetConfig::default(),
        |mut peer| read_bounded_to_end(&peer, 20 * 1024 * 1024),
        |engine, port| {
            engine
                .eval::<String>(&format!(
                    r#"let stream = connect("127.0.0.1", {port});
                       stream.shutdown_read(); stream.shutdown_read();
                       let received = stream.read_string(8);
                       let written = stream.write_all_string("still writable");
                       stream.shutdown_write(); stream.close(); received + ":" + written.to_string()"#
                ))
                .unwrap()
        },
    );
    assert_eq!(result, ":14");
    assert_eq!(peer_bytes, b"still writable");
}

#[test]
fn accepted_stream_writes_are_read_back_by_the_peer() {
    let mut engine = engine(NetConfig::default().allow_listen("127.0.0.1:0".parse().unwrap()));
    let mut scope = rhai::Scope::new();
    engine.run_with_scope(&mut scope, r#"let listener = listen("127.0.0.1", 0);"#).unwrap();
    let address = engine.eval_with_scope::<String>(&mut scope, "listener.local_addr").unwrap();
    let mut peer = TcpStream::connect(address.parse::<SocketAddr>().unwrap()).unwrap();
    peer.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
    peer.set_write_timeout(Some(Duration::from_secs(2))).unwrap();
    let result = engine
        .eval_with_scope::<rhai::INT>(
            &mut scope,
            r#"let stream = listener.accept(500); let count = stream.write_all_string("accepted");
           stream.shutdown_write(); stream.close(); listener.close(); count"#,
        )
        .unwrap();
    let received = read_bounded_to_end(&peer, 8);
    assert_eq!(result, 8);
    assert_eq!(received, b"accepted");
}

#[test]
fn accepted_stream_inherits_host_write_cap() {
    let mut engine = engine(NetConfig::default().allow_listen("127.0.0.1:0".parse().unwrap()).max_write_bytes(2));
    let mut scope = rhai::Scope::new();
    engine.run_with_scope(&mut scope, r#"let listener = listen("127.0.0.1", 0);"#).unwrap();
    let address = engine.eval_with_scope::<String>(&mut scope, "listener.local_addr").unwrap();
    let peer = TcpStream::connect(address.parse::<SocketAddr>().unwrap()).unwrap();
    peer.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
    peer.set_write_timeout(Some(Duration::from_secs(2))).unwrap();
    let result = engine
        .eval_with_scope::<bool>(
            &mut scope,
            r#"let stream = listener.accept(500); let rejected = false;
               try {{ stream.write_string("abc"); }} catch (err) {{ rejected = err.kind == "ResourceLimit"; }}
               stream.close(); listener.close(); rejected"#,
        )
        .unwrap();
    assert!(result);
    let received = read_bounded_to_end(&peer, 1);
    assert!(received.is_empty(), "accepted stream rejects above inherited host cap");
}
