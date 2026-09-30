#![cfg(feature = "net")]

use rhai::packages::net::{NetConfig, NetPackage};
use rhai::packages::Package;
use rhai::{Engine, Scope};
use std::net::{SocketAddr, TcpStream};
use std::time::Duration;

fn build_engine(config: NetConfig) -> Engine {
    let mut engine = Engine::new();
    NetPackage::new(config).expect("NetPackage::new").register_into_engine(&mut engine);
    engine
}

fn build_engine_with_package(package: &NetPackage) -> Engine {
    let mut engine = Engine::new();
    package.clone().register_into_engine(&mut engine);
    engine
}

#[test]
fn authorized_listener_accepts_an_independent_peer() {
    let config = NetConfig::default().allow_listen("127.0.0.1:0".parse().unwrap());
    let engine = build_engine(config);
    let mut scope = Scope::new();
    engine
        .run_with_scope(&mut scope, r#"let listener = listen("127.0.0.1", 0);"#)
        .expect("script binds an explicitly granted ephemeral listener");

    let address = engine.eval_with_scope::<String>(&mut scope, "listener.local_addr").expect("listener reports its actual bound address");
    let endpoint: SocketAddr = address.parse().expect("numeric local socket address");
    assert_eq!(endpoint.ip().to_string(), "127.0.0.1");
    assert_ne!(endpoint.port(), 0, "OS selected an ephemeral port");

    let client = TcpStream::connect_timeout(&endpoint, Duration::from_secs(2)).expect("independent OS client connects to the script listener");
    let client_address = client.local_addr().unwrap().to_string();
    scope.push("expected_peer", client_address.clone());

    let accepted_peer = engine
        .eval_with_scope::<String>(&mut scope, "let accepted = listener.accept(500); accepted.peer_addr")
        .expect("script accepts the independent client and reports its peer");
    let expected_peer = if std::env::var_os("RHAI_NET_WRONG_PEER_EXPECTATION").is_some() { "127.0.0.1:1" } else { client_address.as_str() };
    assert_eq!(accepted_peer, expected_peer, "accepted peer matches the independently created socket");
}

#[test]
fn denied_and_invalid_listener_endpoints_never_bind() {
    let occupied = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
    let endpoint = occupied.local_addr().unwrap();
    let mismatched_port = if endpoint.port() == u16::MAX { endpoint.port() - 1 } else { endpoint.port() + 1 };
    let engine = build_engine(NetConfig::default().allow_listen(SocketAddr::new(endpoint.ip(), mismatched_port)));
    let denied = engine
        .eval::<bool>(&format!(
            r#"let denied = false; try {{ listen("127.0.0.1", {}); }} catch (err) {{ denied = err.kind == "Denied" && err.op == "listen" && err.target == "127.0.0.1:{}" && err.io_kind == (); }} denied"#,
            endpoint.port(),
            endpoint.port()
        ))
        .unwrap();
    assert!(denied, "a grant for another port denies before OS bind");
    let zero_denied = engine
        .eval::<bool>(r#"let denied = false; try { listen("127.0.0.1", 0); } catch (err) { denied = err.kind == "Denied" && err.target == "127.0.0.1:0"; } denied"#)
        .unwrap();
    assert!(zero_denied, "port zero requires its own explicit grant");

    for port in ["-1", "65536"] {
        let invalid = engine
            .eval::<bool>(&format!(
                r#"let invalid = false; try {{ listen("127.0.0.1", {port}); }} catch (err) {{ invalid = err.kind == "InvalidInput" && err.op == "listen" && err.io_kind == "InvalidInput"; }} invalid"#
            ))
            .unwrap();
        assert!(invalid, "out-of-range listener port {port} is rejected");
    }
    let non_numeric = engine
        .eval::<bool>(&format!(r#"let invalid = false; try {{ listen("localhost", {}); }} catch (err) {{ invalid = err.kind == "InvalidInput" && err.op == "listen"; }} invalid"#, endpoint.port()))
        .unwrap();
    assert!(non_numeric, "listener names are not resolved implicitly");

    occupied.set_nonblocking(true).unwrap();
    let client = TcpStream::connect(endpoint).expect("pre-existing listener remains active");
    let accept_deadline = std::time::Instant::now() + Duration::from_secs(1);
    let (accepted, peer) = loop {
        match occupied.accept() {
            Ok(pair) => break pair,
            Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                assert!(std::time::Instant::now() < accept_deadline, "pre-existing listener did not receive independent client");
                std::thread::yield_now();
            }
            Err(error) => panic!("pre-existing listener failed: {error}"),
        }
    };
    assert_eq!(client.local_addr().unwrap(), peer);
    assert_eq!(accepted.peer_addr().unwrap(), client.local_addr().unwrap());
}

#[test]
fn bind_failure_releases_listener_quota() {
    let occupied = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
    let endpoint = occupied.local_addr().unwrap();
    let engine = build_engine(NetConfig::default().allow_listen(endpoint).max_handles(1));
    let failures = engine
        .eval::<bool>(&format!(
            r#"let first = ""; try {{ listen("127.0.0.1", {}); }} catch (err) {{ first = err.kind; }} let second = ""; try {{ listen("127.0.0.1", {}); }} catch (err) {{ second = err.kind; }} first == "Io" && second == "Io""#,
            endpoint.port(),
            endpoint.port()
        ))
        .unwrap();
    assert!(failures, "failed binds release their reserved quota slot");
}

#[test]
fn no_client_accept_times_out_with_catchable_net_error() {
    let config = NetConfig::default()
        .allow_listen("127.0.0.1:0".parse().unwrap())
        .accept_timeout(Duration::from_millis(40))
        .max_handles(2);
    let engine = build_engine(config);
    let started = std::time::Instant::now();
    let timed_out = engine
        .eval::<bool>(
            r#"let listener = listen("127.0.0.1", 0); let timeout_count = 0; for n in 0..2 { try { listener.accept(1000); } catch (err) { if err.kind == "Timeout" && err.op == "accept" && err.io_kind == "TimedOut" && err.target != "" && err.message != "" { timeout_count += 1; } } } let invalid_timeout = false; try { listener.accept(0); } catch (err) { invalid_timeout = err.kind == "InvalidInput" && err.op == "accept"; } let negative_timeout = false; try { listener.accept(-1); } catch (err) { negative_timeout = err.kind == "InvalidInput" && err.op == "accept"; } listener.close(); timeout_count == 2 && invalid_timeout && negative_timeout"#,
        )
        .unwrap();
    assert!(timed_out, "accept deadline is a catchable, inspectable NetError");
    assert!(started.elapsed() < Duration::from_secs(1), "host deadline bounds wait");
}

#[cfg(feature = "sync")]
#[test]
fn closing_a_clone_unblocks_an_accept_waiting_on_shared_quota() {
    let package = NetPackage::new(NetConfig::default().allow_listen("127.0.0.1:0".parse().unwrap()).max_handles(2)).unwrap();
    let accept_engine = build_engine_with_package(&package);
    let control_engine = build_engine_with_package(&package);
    let mut accept_scope = Scope::new();
    accept_engine.run_with_scope(&mut accept_scope, r#"let listener = listen("127.0.0.1", 0);"#).unwrap();
    let close_clone = accept_scope
        .get_value::<rhai::packages::net::NetListener>("listener")
        .expect("scope retains a clonable listener handle");

    let (ready_tx, ready_rx) = std::sync::mpsc::sync_channel(1);
    let (result_tx, result_rx) = std::sync::mpsc::sync_channel(1);
    let accept_thread = std::thread::spawn(move || {
        let _ = ready_tx.send(());
        let result = accept_engine.eval_with_scope::<bool>(
            &mut accept_scope,
            r#"let caught = false; let done = false; while !done { try { listener.accept(5000); done = true; } catch (err) { if err.kind == "ResourceLimit" { } else { caught = err.kind == "Io" && err.op == "accept"; done = true; } } } caught"#,
        );
        let _ = result_tx.send(result);
    });
    let worker_ready = ready_rx.recv_timeout(Duration::from_secs(1));

    let mut probe_scope = Scope::new();
    probe_scope.push("probe_listener", close_clone.clone());
    let probe_deadline = std::time::Instant::now() + Duration::from_secs(2);
    let mut observed_accept_reservation = false;
    let mut probe_error = None;
    let mut last_probe_state = String::new();
    loop {
        let state = match control_engine.eval_with_scope::<String>(&mut probe_scope, r#"let state = "created"; try { probe_listener.accept(1); } catch (err) { state = err.kind; } state"#) {
            Ok(state) => state,
            Err(error) => {
                probe_error = Some(error.to_string());
                break;
            }
        };
        last_probe_state = state.clone();
        if state == "ResourceLimit" {
            observed_accept_reservation = true;
            break;
        }
        if std::time::Instant::now() >= probe_deadline {
            break;
        }
        std::thread::yield_now();
    }

    let mut close_scope = Scope::new();
    close_scope.push("listener", close_clone);
    let close_result = control_engine.run_with_scope(&mut close_scope, "listener.close();");
    let result = result_rx.recv_timeout(Duration::from_secs(1));
    let joined = accept_thread.join();
    let worker_result = match result {
        Ok(value) => value.map_err(|error| error.to_string()),
        Err(error) => Err(format!("accept worker result unavailable: {error}")),
    };
    assert!(joined.is_ok(), "accept worker joins after clone close");
    assert!(worker_ready.is_ok(), "accept worker starts before the bounded probe");
    assert!(close_result.is_ok(), "clone close succeeds");
    assert!(probe_error.is_none(), "quota probe evaluation succeeds: {probe_error:?}");
    assert!(observed_accept_reservation, "accept reserves the shared quota before waiting; last probe was {last_probe_state:?}, worker result was {worker_result:?}");
    assert!(worker_result.unwrap(), "closed listener produces a catchable accept error");
}

#[test]
fn listener_clones_share_close_and_final_drop_releases_the_bind() {
    let engine = build_engine(NetConfig::default().allow_listen("127.0.0.1:0".parse().unwrap()));
    let mut scope = Scope::new();
    engine.run_with_scope(&mut scope, r#"let listener = listen("127.0.0.1", 0); let copy = listener;"#).unwrap();
    let first_address = engine.eval_with_scope::<String>(&mut scope, "listener.local_addr").unwrap();
    let closed = engine
        .eval_with_scope::<bool>(&mut scope, "listener.close(); let same_state = copy.closed; copy.close(); copy.closed")
        .unwrap();
    assert!(closed, "closing either clone closes the shared listener idempotently");
    drop(scope);
    let rebound = std::net::TcpListener::bind(first_address.parse::<SocketAddr>().unwrap()).expect("explicit close releases the OS bind");
    drop(rebound);

    let mut drop_scope = Scope::new();
    engine.run_with_scope(&mut drop_scope, r#"let unclosed = listen("127.0.0.1", 0);"#).unwrap();
    let last_address = engine.eval_with_scope::<String>(&mut drop_scope, "unclosed.local_addr").unwrap();
    drop(drop_scope);
    let rebound = std::net::TcpListener::bind(last_address.parse::<SocketAddr>().unwrap()).expect("final listener handle drop releases the OS bind");
    drop(rebound);
}

#[test]
fn accepted_stream_uses_the_shared_package_quota_across_engines() {
    let accepted_listener = std::net::TcpListener::bind("127.0.0.1:0").expect("independent client target");
    let connect_endpoint = accepted_listener.local_addr().unwrap();
    let package = NetPackage::new(NetConfig::default().allow_listen("127.0.0.1:0".parse().unwrap()).allow_connect(connect_endpoint).max_handles(2)).unwrap();
    let first_engine = build_engine_with_package(&package);
    let second_engine = build_engine_with_package(&package);
    let mut scope = Scope::new();
    first_engine.run_with_scope(&mut scope, r#"let listener = listen("127.0.0.1", 0);"#).unwrap();
    let listener_address = first_engine.eval_with_scope::<String>(&mut scope, "listener.local_addr").unwrap().parse::<SocketAddr>().unwrap();
    let _independent_client = TcpStream::connect(listener_address).unwrap();
    let peer = first_engine.eval_with_scope::<String>(&mut scope, "let accepted = listener.accept(500); accepted.peer_addr").unwrap();
    assert!(peer.starts_with("127.0.0.1:"));

    let blocked = second_engine
        .eval::<bool>(&format!(
            r#"let blocked = false; try {{ connect("127.0.0.1", {}); }} catch (err) {{ blocked = err.kind == "ResourceLimit" && err.op == "connect"; }} blocked"#,
            connect_endpoint.port()
        ))
        .unwrap();
    assert!(blocked, "accepted streams and listeners share one package quota");

    drop(scope);
    second_engine
        .run(&format!(r#"let stream = connect("127.0.0.1", {}); stream.close();"#, connect_endpoint.port()))
        .unwrap();
    let mut peer = accepted_listener.accept().unwrap().0;
    peer.set_read_timeout(Some(Duration::from_secs(1))).unwrap();
    let mut byte = [0_u8; 1];
    assert_eq!(std::io::Read::read(&mut peer, &mut byte).unwrap(), 0);
}
