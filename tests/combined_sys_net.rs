#![cfg(all(feature = "sys", feature = "net", not(feature = "no_object")))]

use rhai::packages::net::{NetConfig, NetError, NetPackage};
use rhai::packages::sys::{FsAccess, SysConfig, SysError, SysPackage};
use rhai::packages::Package;
use rhai::{Engine, EvalAltResult};
use std::io::{Read, Write};
use std::net::TcpListener;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::{Duration, Instant};

struct TempDir(PathBuf);

impl TempDir {
    fn new() -> Self {
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let path = std::env::temp_dir().join(format!("rhai-combined-sys-net-{}-{}", std::process::id(), NEXT.fetch_add(1, Ordering::Relaxed)));
        std::fs::create_dir(&path).expect("create unique fixture root");
        Self(path)
    }

    fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

struct PeerThread(Option<std::thread::JoinHandle<(Vec<u8>, Vec<u8>)>>);

impl PeerThread {
    fn join(mut self) -> (Vec<u8>, Vec<u8>) {
        self.0.take().expect("peer thread exists").join().expect("peer thread completed")
    }
}

impl Drop for PeerThread {
    fn drop(&mut self) {
        if let Some(thread) = self.0.take() {
            let _ = thread.join();
        }
    }
}

fn error_payload<T: 'static>(result: Result<(), Box<EvalAltResult>>) -> T {
    match *result.expect_err("operation must fail") {
        EvalAltResult::ErrorRuntime(value, _) => value.try_cast::<T>().expect("expected structured package error"),
        other => panic!("expected structured runtime error, got {other:?}"),
    }
}

#[test]
fn sys_and_net_packages_coexist_in_one_engine_with_os_readback_and_typed_errors() {
    const CLIENT_BYTES: &[u8] = b"independent-client-bytes";
    const PEER_BYTES: &[u8] = b"independent-peer-reply";

    let root = TempDir::new();
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind OS-selected port");
    listener.set_nonblocking(true).expect("configure bounded readiness polling");
    let endpoint = listener.local_addr().expect("read selected endpoint");
    let peer = PeerThread(Some(std::thread::spawn(move || {
        let deadline = Instant::now() + Duration::from_secs(5);
        let (mut stream, _) = loop {
            match listener.accept() {
                Ok(peer) => break peer,
                Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                    assert!(Instant::now() < deadline, "script did not connect to ready listener");
                    std::thread::yield_now();
                }
                Err(error) => panic!("peer accept failed: {error}"),
            }
        };
        stream.set_nonblocking(false).expect("make accepted peer stream blocking before bounded I/O");
        stream.set_read_timeout(Some(Duration::from_secs(5))).expect("bound peer read");
        stream.set_write_timeout(Some(Duration::from_secs(5))).expect("bound peer write");
        let mut received = vec![0; CLIENT_BYTES.len()];
        stream.read_exact(&mut received).expect("receive script bytes");
        stream.write_all(PEER_BYTES).expect("send independent peer bytes");
        (received, PEER_BYTES.to_vec())
    })));

    let mut engine = Engine::new();
    SysPackage::new(SysConfig::default().fs_root(root.path(), FsAccess::ReadWriteDelete))
        .expect("construct filesystem package")
        .register_into_engine(&mut engine);
    NetPackage::new(NetConfig::default().allow_connect(endpoint))
        .expect("construct network package")
        .register_into_engine(&mut engine);

    engine
        .run(&format!(
            r#"
                let file = open_file("exchange.txt");
                file.write("filesystem-payload");
                let stream = connect("127.0.0.1", {});
                stream.write_all_string("{}");
                let reply = stream.read_to_end_string({});
                if reply != "{}" {{ throw "unexpected peer bytes"; }}
                stream.close();
            "#,
            endpoint.port(),
            std::str::from_utf8(CLIENT_BYTES).unwrap(),
            PEER_BYTES.len(),
            std::str::from_utf8(PEER_BYTES).unwrap(),
        ))
        .unwrap_or_else(|error| panic!("both package APIs execute in the same Engine: {error:?}"));

    let host_file = std::fs::read(root.path().join("exchange.txt")).expect("fresh host file readback");
    let expected_host_file = if std::env::var_os("RHAI_COMBINED_WRONG_EXPECTATION").is_some() {
        b"incorrect filesystem expectation".as_slice()
    } else {
        b"filesystem-payload".as_slice()
    };
    assert!(
        host_file == expected_host_file,
        "fresh host readback must match independent expected bytes; actual={:?}; expected={:?}",
        String::from_utf8_lossy(&host_file),
        String::from_utf8_lossy(expected_host_file),
    );
    let (peer_received, peer_sent) = peer.join();
    assert_eq!(peer_received, CLIENT_BYTES, "independent peer received exact script bytes");
    assert_eq!(peer_sent, PEER_BYTES, "independent peer sent exact expected reply");

    let sys_error: SysError = error_payload(engine.run("read_file(\"missing-independent.txt\")").map(|_| ()));
    assert_eq!(sys_error.kind(), "Io");
    let net_error: NetError = error_payload(engine.run("connect(\"127.0.0.1\", 1)").map(|_| ()));
    assert_eq!(net_error.kind(), "Denied");
}
