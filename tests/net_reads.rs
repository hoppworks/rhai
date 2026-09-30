#![cfg(all(feature = "net", not(feature = "no_object")))]

use rhai::packages::net::{NetConfig, NetError, NetPackage};
use rhai::packages::Package;
use rhai::{Dynamic, Engine, Scope};
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
#[cfg(feature = "sync")]
use std::sync::mpsc;
use std::time::Duration;

fn engine(config: NetConfig) -> Engine {
    let mut engine = Engine::new();
    NetPackage::new(config).expect("valid NetConfig").register_into_engine(&mut engine);
    engine
}

fn connected<F, R>(config: NetConfig, peer_action: F, script: impl FnOnce(&mut Engine, u16) -> R) -> R
where
    F: FnOnce(std::net::TcpStream) + Send + 'static,
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
        stream.set_nonblocking(false).expect("accepted peer socket is blocking for bounded fixture reads");
        stream.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
        peer_action(stream);
    });
    let result = script(&mut engine, endpoint.port());
    peer.join().expect("peer exits after the script operation");
    result
}

#[test]
fn stream_read_string_returns_exact_lossy_text_from_peer_bytes() {
    let actual = connected(
        NetConfig::default(),
        |mut peer| {
            peer.write_all(&[0x61, 0xff, 0x62]).unwrap();
            peer.shutdown(std::net::Shutdown::Write).unwrap();
            let mut byte = [0_u8; 1];
            match peer.read(&mut byte) {
                Ok(_) => {}
                Err(error) if error.kind() == std::io::ErrorKind::TimedOut => {}
                Err(error) => panic!("bounded peer read failed: {error}"),
            }
        },
        |engine, port| {
            engine
                .eval::<String>(&format!(r#"let stream = connect("127.0.0.1", {port}); let text = stream.read_to_end_string(3); stream.close(); text"#))
                .unwrap()
        },
    );
    if std::env::var_os("RHAI_NET_WRONG_READ_EXPECTATION").is_some() {
        assert_eq!(actual, "wrong peer payload");
    } else {
        assert_eq!(actual, "a\u{fffd}b");
    }
}

#[test]
fn one_shot_text_read_replaces_a_utf8_character_cut_by_the_available_prefix() {
    let actual = connected(
        NetConfig::default(),
        |mut peer| {
            peer.write_all(&[0xe2, 0x82]).unwrap();
            peer.shutdown(std::net::Shutdown::Write).unwrap();
            let mut byte = [0_u8; 1];
            let _ = peer.read(&mut byte);
        },
        |engine, port| {
            engine
                .eval::<String>(&format!(r#"let stream = connect("127.0.0.1", {port}); let text = stream.read_string(8); stream.close(); text"#))
                .unwrap()
        },
    );
    assert_eq!(actual, "\u{fffd}");
}

#[test]
fn one_shot_read_returns_an_available_short_prefix_without_waiting_for_more() {
    let actual = connected(
        NetConfig::default(),
        |mut peer| {
            peer.write_all(b"a").unwrap();
            let mut byte = [0_u8; 1];
            let _ = peer.read(&mut byte);
        },
        |engine, port| {
            engine
                .eval::<String>(&format!(r#"let stream = connect("127.0.0.1", {port}); let text = stream.read_string(9); stream.close(); text"#))
                .unwrap()
        },
    );
    assert_eq!(actual, "a");
}

#[cfg(feature = "f32_float")]
#[test]
fn f32_float_timeout_arguments_reject_fractional_and_non_finite_values() {
    let result = connected(
        NetConfig::default().read_timeout(Duration::from_millis(35)),
        |mut peer| {
            peer.write_all(b"Z").unwrap();
            let mut byte = [0_u8; 1];
            let _ = peer.read(&mut byte);
        },
        |engine, port| {
            engine
                .eval::<bool>(&format!(
                    r#"let stream = connect("127.0.0.1", {port});
                       let fraction_rejected = false;
                       try {{ stream.read_string(1, 1.5); }} catch (error) {{ fraction_rejected = true; }}
                       let nan = 0.0 / 0.0;
                       let nan_rejected = false;
                       try {{ stream.read_string(1, nan); }} catch (error) {{ nan_rejected = true; }}
                       let infinity = 1.0 / 0.0;
                       let infinity_rejected = false;
                       try {{ stream.read_string(1, infinity); }} catch (error) {{ infinity_rejected = true; }}
                       let byte = stream.read_string(1, 100);
                       let extreme_capped = false;
                       try {{ stream.read_string(1, {}); }} catch (error) {{ extreme_capped = error.kind == "Timeout"; }}
                       close(stream);
                       fraction_rejected && nan_rejected && infinity_rejected && byte == "Z" && extreme_capped"#,
                    rhai::INT::MAX
                ))
                .unwrap()
        },
    );
    assert!(result, "only integer millisecond timeouts are accepted, without consuming peer data");
}

#[cfg(not(feature = "no_index"))]
#[test]
fn blob_reads_validate_lengths_return_exact_short_prefix_and_obey_host_cap() {
    let got = connected(
        NetConfig::default().max_read_bytes(3),
        |mut peer| {
            peer.write_all(b"abcdef").unwrap();
            peer.shutdown(std::net::Shutdown::Write).unwrap();
            let mut byte = [0_u8; 1];
            let _ = peer.read(&mut byte);
        },
        |engine, port| {
            let mut scope = Scope::new();
            let script = format!(
                r#"
                let stream = connect("127.0.0.1", {port});
                let invalid = false;
                try {{ stream.read_blob(-1); }} catch (err) {{ invalid = err.kind == "InvalidInput" && err.op == "read_blob"; }}
                let zero = stream.read_blob(0).len == 0;
                let first = stream.read_blob(9);
                let second = stream.read_to_end_blob(9);
                let third = stream.read_to_end_blob(9);
                let eof = stream.read_blob(2).len == 0;
                stream.close();
                let invalid_result = invalid;
                let zero_result = zero;
                let eof_result = eof;
            "#
            );
            engine.run_with_scope(&mut scope, &script).unwrap();
            (
                scope.get_value::<bool>("invalid_result").unwrap(),
                scope.get_value::<bool>("zero_result").unwrap(),
                scope.get_value::<bool>("eof_result").unwrap(),
                scope.get_value::<rhai::Blob>("first").unwrap(),
                scope.get_value::<rhai::Blob>("second").unwrap(),
                scope.get_value::<rhai::Blob>("third").unwrap(),
            )
        },
    );
    assert!(got.0 && got.1 && got.2);
    assert!((1..=3).contains(&got.3.len()), "positive one-shot read returns its available prefix");
    assert!(got.3.len() <= 3 && got.4.len() <= 3 && got.5.len() <= 3, "host cap applies to every receive call");
    let mut exact = got.3;
    exact.extend(got.4);
    exact.extend(got.5);
    assert_eq!(exact, b"abcdef", "short prefix and EOF loop capture no padding or lost bytes");
}

#[test]
fn no_data_read_times_out_and_bounded_eof_loop_reports_partial_progress() {
    let result = connected(
        NetConfig::default().read_timeout(Duration::from_millis(60)),
        |mut peer| {
            // Keep the peer open until the script observes the timeout and closes its clone.
            let mut byte = [0_u8; 1];
            let _ = peer.read(&mut byte);
        },
        |engine, port| {
            engine
                .eval::<String>(&format!(
                    r#"
                let stream = connect("127.0.0.1", {port});
                let invalid = false;
                try {{ stream.read_string(1, 0); }} catch (err) {{ invalid = err.kind == "InvalidInput" && err.op == "read_string"; }}
                let shortened = "NO_ERROR";
                try {{ stream.read_string(1, 5); }} catch (err) {{ shortened = err.to_string(); }}
                let host = "NO_ERROR";
                try {{ stream.read_string(1); }} catch (err) {{ host = err.to_string(); }}
                let details = invalid.to_string() + "," + shortened + "," + host; stream.close(); details
            "#
                ))
                .unwrap()
        },
    );
    let mut fields = result.splitn(3, ",");
    assert_eq!(fields.next(), Some("true"), "invalid timeout is rejected: {result}");
    for error in fields {
        assert!(error.starts_with("Timeout (TimedOut): cannot read_string `127.0.0.1:"), "script timeout reports structured fields: {result}");
    }

    let partial = connected(
        NetConfig::default().read_timeout(Duration::from_millis(80)),
        |mut peer| {
            peer.write_all(b"abc").unwrap();
            let mut byte = [0_u8; 1];
            let _ = peer.read(&mut byte);
        },
        |engine, port| {
            engine
                .eval::<bool>(&format!(
                    r#"
                let stream = connect("127.0.0.1", {port});
                let result = false;
                try {{ stream.read_to_end_string(8); }} catch (err) {{ result = err.kind == "Timeout" && err.op == "read_to_end_string" && err.target == "127.0.0.1:{port}" && err.io_kind == "TimedOut" && err.partial_bytes == 3; }}
                stream.close(); result
            "#
                ))
                .unwrap()
        },
    );
    assert!(partial, "EOF loop timeout retains the actual three-byte prefix count");

    #[cfg(not(feature = "no_index"))]
    let partial_blob = connected(
        NetConfig::default().read_timeout(Duration::from_millis(80)),
        |mut peer| {
            peer.write_all(b"abc").unwrap();
            let mut byte = [0_u8; 1];
            let _ = peer.read(&mut byte);
        },
        |engine, port| {
            engine
                .eval::<bool>(&format!(
                    r#"let stream = connect("127.0.0.1", {port}); let result = false; try {{ stream.read_to_end_blob(8); }} catch (err) {{ result = err.kind == "Timeout" && err.op == "read_to_end_blob" && err.partial_bytes == 3; }} stream.close(); result"#
                ))
                .unwrap()
        },
    );
    #[cfg(not(feature = "no_index"))]
    assert!(partial_blob, "bounded blob timeout identifies its operation and captured prefix");
}

#[cfg(not(feature = "unchecked"))]
#[test]
fn engine_string_limit_keeps_ascii_and_reports_lossy_expansion_progress() {
    let (ascii, error) = connected(
        NetConfig::default(),
        |mut peer| {
            peer.write_all(&[b'a', 0xff]).unwrap();
            peer.shutdown(std::net::Shutdown::Write).unwrap();
            let mut byte = [0_u8; 1];
            let _ = peer.read(&mut byte);
        },
        |engine, port| {
            let mut scope = Scope::new();
            engine.run_with_scope(&mut scope, &format!(r#"let stream = connect("127.0.0.1", {port});"#)).unwrap();
            engine.set_max_string_size(1);
            let ascii = engine.eval_with_scope::<String>(&mut scope, "stream.read_string(1)").unwrap();
            let error = engine
                .eval_with_scope::<Dynamic>(&mut scope, "let caught = (); try { stream.read_string(1); } catch (err) { caught = err; } caught")
                .unwrap()
                .try_cast::<NetError>()
                .unwrap();
            engine.run_with_scope(&mut scope, "stream.close();").unwrap();
            (ascii, error)
        },
    );
    assert_eq!(ascii, "a", "valid ASCII succeeds at the engine string limit");
    assert_eq!(error.kind(), "ResourceLimit");
    assert_eq!(error.op(), "read_string");
    assert_eq!(error.partial_bytes(), 1, "lossy expansion reports the consumed raw byte count");
}

#[cfg(all(feature = "unchecked", not(feature = "no_index")))]
#[test]
fn unchecked_mode_keeps_the_host_receive_cap() {
    let actual = connected(
        NetConfig::default().max_read_bytes(2),
        |mut peer| {
            peer.write_all(b"abc").unwrap();
            peer.shutdown(std::net::Shutdown::Write).unwrap();
            let mut byte = [0_u8; 1];
            let _ = peer.read(&mut byte);
        },
        |engine, port| {
            let mut scope = Scope::new();
            engine.run_with_scope(&mut scope, &format!(r#"let stream = connect("127.0.0.1", {port});"#)).unwrap();
            engine.eval_with_scope::<String>(&mut scope, "stream.read_string(8)").unwrap()
        },
    );
    assert_eq!(actual, "ab");
}

#[test]
fn accepted_stream_inherits_host_receive_cap() {
    let config = NetConfig::default().allow_listen("127.0.0.1:0".parse().unwrap()).max_read_bytes(2);
    let engine = engine(config);
    let mut scope = Scope::new();
    engine.run_with_scope(&mut scope, r#"let listener = listen("127.0.0.1", 0);"#).unwrap();
    let address = engine.eval_with_scope::<String>(&mut scope, "listener.local_addr").unwrap();
    let mut peer = TcpStream::connect(address.parse::<SocketAddr>().unwrap()).unwrap();
    peer.write_all(b"abcdef").unwrap();
    peer.shutdown(std::net::Shutdown::Write).unwrap();
    let actual = engine
        .eval_with_scope::<String>(&mut scope, "let stream = listener.accept(500); let text = stream.read_string(8); stream.close(); text")
        .unwrap();
    assert_eq!(actual, "ab", "accepted stream carries the package read cap");
}

#[cfg(feature = "no_index")]
#[test]
fn no_index_keeps_string_reads_and_omits_blob_methods() {
    let actual = connected(
        NetConfig::default(),
        |mut peer| {
            peer.write_all(b"a").unwrap();
            peer.shutdown(std::net::Shutdown::Write).unwrap();
            let mut byte = [0_u8; 1];
            let _ = peer.read(&mut byte);
        },
        |engine, port| {
            engine
                .eval::<bool>(&format!(
                    r#"
                    let stream = connect("127.0.0.1", {port});
                    let text = stream.read_string(1) == "a";
                    let omitted = false;
                    try {{ stream.read_blob(1); }} catch (err) {{ omitted = true; }}
                    stream.close(); text && omitted
                "#
                ))
                .unwrap()
        },
    );
    assert!(actual, "no_index preserves string reads and does not register blob reads");
}

#[cfg(feature = "sync")]
#[test]
fn closing_a_clone_cancels_an_outstanding_read_and_releases_quota() {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let endpoint = listener.local_addr().unwrap();
    let package = NetPackage::new(NetConfig::default().allow_connect(endpoint).read_timeout(Duration::from_secs(2)).max_handles(1)).unwrap();
    let mut reader_engine = Engine::new();
    package.clone().register_into_engine(&mut reader_engine);
    let mut control_engine = Engine::new();
    package.register_into_engine(&mut control_engine);

    let (peer_ready_tx, peer_ready_rx) = mpsc::sync_channel(1);
    let (peer_release_tx, peer_release_rx) = mpsc::sync_channel(1);
    listener.set_nonblocking(true).unwrap();
    let peer = std::thread::spawn(move || {
        let deadline = std::time::Instant::now() + Duration::from_secs(2);
        let (_peer, _) = loop {
            match listener.accept() {
                Ok(peer) => break peer,
                Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                    assert!(std::time::Instant::now() < deadline, "script did not connect to cancellation peer");
                    std::thread::yield_now();
                }
                Err(error) => panic!("peer accept failed: {error}"),
            }
        };
        peer_ready_tx.send(()).unwrap();
        if peer_release_rx.recv_timeout(Duration::from_secs(4)).is_err() {
            return;
        }
        listener.set_nonblocking(true).unwrap();
        let deadline = std::time::Instant::now() + Duration::from_secs(2);
        loop {
            match listener.accept() {
                Ok((mut peer, _)) => {
                    peer.set_read_timeout(Some(Duration::from_secs(1))).unwrap();
                    peer.set_nonblocking(false).unwrap();
                    let mut byte = [0_u8; 1];
                    assert_eq!(peer.read(&mut byte).unwrap(), 0, "quota-retry stream is closed");
                    return;
                }
                Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                    assert!(std::time::Instant::now() < deadline, "quota was not released for a second connection");
                    std::thread::yield_now();
                }
                Err(error) => panic!("peer accept failed: {error}"),
            }
        }
    });

    let mut reader_scope = Scope::new();
    reader_engine
        .run_with_scope(&mut reader_scope, &format!(r#"let stream = connect("127.0.0.1", {}); let copy = stream;"#, endpoint.port()))
        .unwrap();
    let close_copy = reader_scope.get_value::<rhai::packages::net::NetStream>("copy").unwrap();
    peer_ready_rx.recv_timeout(Duration::from_secs(1)).unwrap();

    let (ready_tx, ready_rx) = mpsc::sync_channel(1);
    let (result_tx, result_rx) = mpsc::sync_channel(1);
    let reader = std::thread::spawn(move || {
        let _ = ready_tx.send(());
        let result = reader_engine.eval_with_scope::<String>(&mut reader_scope, "stream.read_string(1)");
        let _ = result_tx.send(result.map_err(|error| error.to_string()));
    });
    ready_rx.recv_timeout(Duration::from_secs(1)).unwrap();

    // The peer remains open and sends no bytes; clone close must end this operation before its host deadline.
    let started = std::time::Instant::now();
    let mut close_scope = Scope::new();
    close_scope.push("stream", close_copy);
    control_engine.run_with_scope(&mut close_scope, "stream.close();").unwrap();
    let result = result_rx.recv_timeout(Duration::from_secs(1)).unwrap();
    assert!(started.elapsed() < Duration::from_secs(1), "close cancels ahead of the two-second read deadline");
    assert!(result.is_err(), "shutdown reports the cancelled active read as an error");
    reader.join().unwrap();
    peer_release_tx.send(()).unwrap();
    control_engine
        .eval::<bool>(&format!(r#"let stream = connect("127.0.0.1", {}); stream.close(); true"#, endpoint.port()))
        .unwrap();
    peer.join().unwrap();
}
