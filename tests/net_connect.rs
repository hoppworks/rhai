#![cfg(all(feature = "net", not(feature = "no_object")))]

use rhai::packages::net::{NetConfig, NetError, NetPackage};
use rhai::packages::Package;
use rhai::{Engine, Scope};
use std::io::Read;
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::time::{Duration, Instant};

fn build_engine(config: NetConfig) -> Engine {
    let mut engine = Engine::new();
    NetPackage::new(config).expect("NetPackage::new").register_into_engine(&mut engine);
    engine
}

fn port(listener: &TcpListener) -> u16 {
    listener.local_addr().unwrap().port()
}

fn wait_accept(listener: &TcpListener) -> TcpStream {
    listener.set_nonblocking(true).unwrap();
    let deadline = Instant::now() + Duration::from_secs(2);
    loop {
        match listener.accept() {
            Ok((stream, _)) => return stream,
            Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                assert!(Instant::now() < deadline, "authorized connect was not accepted");
                std::thread::yield_now();
            }
            Err(error) => panic!("accept failed: {error}"),
        }
    }
}

#[test]
fn authorized_connect_is_observed_and_clone_close_is_shared() {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let endpoint: SocketAddr = listener.local_addr().unwrap();
    let config = NetConfig::default().allow_connect(endpoint);
    let engine = build_engine(config);
    let script = format!(r#"let first = connect("127.0.0.1", {}); let second = first; first.close(); if !second.closed {{ throw "clone did not share close"; }} second.close();"#, port(&listener));
    engine.run(&script).expect("authorized script connect and idempotent clone close");

    let mut peer = wait_accept(&listener);
    peer.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
    let mut byte = [0_u8; 1];
    let observed = peer.read(&mut byte).unwrap();
    if std::env::var_os("RHAI_NET_WRONG_EXPECTATION").is_some() {
        assert_ne!(observed, 0, "deliberately wrong peer EOF expectation");
    } else {
        assert_eq!(observed, 0, "peer independently observed close as EOF");
    }
}

#[test]
fn denied_and_invalid_endpoints_do_not_reach_peer_and_errors_are_catchable() {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let engine = build_engine(NetConfig::default());
    let port = port(&listener);

    let denied = engine
        .eval::<bool>(&format!(
            r#"let denied = false; try {{ connect("127.0.0.1", {port}); }} catch (err) {{ denied = err.kind == "Denied" && err.op == "connect" && err.target == "127.0.0.1:{port}" && err.message != "" && err.io_kind == (); }} denied"#
        ))
        .unwrap();
    assert!(denied, "default policy denies with inspectable NetError fields");

    let other_port = if port == u16::MAX { port - 1 } else { port + 1 };
    let mismatched = build_engine(NetConfig::default().allow_connect(SocketAddr::new("127.0.0.1".parse().unwrap(), other_port)));
    let mismatch_denied = mismatched
        .eval::<bool>(&format!(r#"let denied = false; try {{ connect("127.0.0.1", {port}); }} catch (err) {{ denied = err.kind == "Denied" && err.target == "127.0.0.1:{port}"; }} denied"#))
        .unwrap();
    assert!(mismatch_denied, "a grant for another port does not authorize this endpoint");

    for invalid in ["0", "-1", "65536"] {
        let script = format!(r#"let invalid = false; try {{ connect("127.0.0.1", {invalid}); }} catch (err) {{ invalid = err.kind == "InvalidInput" && err.op == "connect" && err.target != "" && err.message != "" && err.io_kind == "InvalidInput"; }} invalid"#);
        assert!(engine.eval::<bool>(&script).unwrap(), "invalid port {invalid} is catchable");
    }
    let non_numeric = engine
        .eval::<bool>(&format!(r#"let invalid = false; try {{ connect("localhost", {port}); }} catch (err) {{ invalid = err.kind == "InvalidInput" && err.op == "connect"; }} invalid"#))
        .unwrap();
    assert!(non_numeric, "hostnames are not resolved implicitly");

    listener.set_nonblocking(true).unwrap();
    match listener.accept() {
        Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {}
        Ok((stream, addr)) => panic!("denied/invalid endpoint unexpectedly reached peer from {addr}: {stream:?}"),
        Err(error) => panic!("peer accept failed: {error}"),
    }
}

#[test]
fn net_config_rejects_zero_deadline_and_invalid_handle_limits() {
    let error = NetPackage::new(NetConfig::default().connect_timeout(Duration::ZERO)).err().unwrap();
    assert_eq!(error.kind(), "InvalidInput");
    let error = NetPackage::new(NetConfig::default().accept_timeout(Duration::ZERO)).err().unwrap();
    assert_eq!(error.kind(), "InvalidInput");
    let error = NetPackage::new(NetConfig::default().read_timeout(Duration::ZERO)).err().unwrap();
    assert_eq!(error.kind(), "InvalidInput");
    for config in [
        NetConfig::default().connect_timeout(Duration::MAX),
        NetConfig::default().accept_timeout(Duration::MAX),
        NetConfig::default().read_timeout(Duration::MAX),
        NetConfig::default().write_timeout(Duration::MAX),
    ] {
        let error = NetPackage::new(config).err().expect("unrepresentable host deadlines are rejected");
        assert_eq!(error.kind(), "InvalidInput");
    }
    let error = NetPackage::new(NetConfig::default().max_read_bytes(0)).err().unwrap();
    assert_eq!(error.kind(), "InvalidInput");
    let error = NetPackage::new(NetConfig::default().max_read_bytes(1024 * 1024 + 1)).err().unwrap();
    assert_eq!(error.kind(), "InvalidInput");
    let error = NetPackage::new(NetConfig::default().max_handles(0)).err().unwrap();
    assert_eq!(error.kind(), "InvalidInput");
    let _: NetError = error;
}

#[test]
fn open_handle_limit_is_shared_across_package_engines_and_released_on_close() {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let endpoint = listener.local_addr().unwrap();
    let refused_listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let refused_endpoint = refused_listener.local_addr().unwrap();
    drop(refused_listener);
    let package = NetPackage::new(NetConfig::default().allow_connect(endpoint).allow_connect(refused_endpoint).max_handles(1)).unwrap();
    let mut first_engine = Engine::new();
    package.clone().register_into_engine(&mut first_engine);
    let mut second_engine = Engine::new();
    package.register_into_engine(&mut second_engine);

    let mut scope = Scope::new();
    first_engine
        .run_with_scope(
            &mut scope,
            &format!(
                r#"let failed = false; try {{ connect("127.0.0.1", {}); }} catch (err) {{ failed = err.kind == "Io"; }} if !failed {{ throw "refused connection did not fail"; }} let first = connect("127.0.0.1", {}); let copy = first;"#,
                refused_endpoint.port(),
                endpoint.port(),
            ),
        )
        .unwrap();
    let blocked = second_engine
        .eval::<bool>(&format!(r#"let blocked = false; try {{ connect("127.0.0.1", {}); }} catch (err) {{ blocked = err.kind == "ResourceLimit"; }} blocked"#, endpoint.port()))
        .unwrap();
    assert!(blocked, "package quota applies across cloned packages and engines");

    first_engine.run_with_scope(&mut scope, "first.close();").unwrap();
    let clone_closed = first_engine.eval_with_scope::<bool>(&mut scope, "copy.closed").unwrap();
    assert!(clone_closed, "a clone shares the closed state");
    second_engine.run(&format!(r#"let again = connect("127.0.0.1", {}); again.close();"#, endpoint.port())).unwrap();

    // An unclosed stream retained only by this script scope must release its slot
    // when that scope and its final handle are dropped.
    let mut drop_scope = Scope::new();
    second_engine
        .run_with_scope(&mut drop_scope, &format!(r#"let dropped = connect("127.0.0.1", {});"#, endpoint.port()))
        .unwrap();
    drop(drop_scope);
    second_engine
        .run(&format!(r#"let after_drop = connect("127.0.0.1", {}); after_drop.close();"#, endpoint.port()))
        .unwrap();

    for index in 0..4 {
        let mut peer = wait_accept(&listener);
        peer.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
        let mut byte = [0_u8; 1];
        assert_eq!(peer.read(&mut byte).unwrap(), 0, "stream {index} reaches EOF");
    }
    listener.set_nonblocking(true).unwrap();
    match listener.accept() {
        Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {}
        Ok((stream, addr)) => panic!("quota-denied connection unexpectedly reached peer from {addr}: {stream:?}"),
        Err(error) => panic!("peer accept failed: {error}"),
    }
}
