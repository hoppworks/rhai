#![cfg(all(feature = "net", feature = "metadata"))]

use rhai::packages::net::{NetConfig, NetPackage};
use rhai::packages::Package;
use rhai::Engine;

#[test]
fn metadata_exposes_the_documented_tcp_surface() {
    let mut engine = Engine::new();
    NetPackage::new(NetConfig::default()).unwrap().register_into_engine(&mut engine);
    let json = engine.gen_fn_metadata_to_json(false).unwrap();
    let metadata: serde_json::Value = serde_json::from_str(&json).unwrap();
    let functions = metadata["functions"].as_array().expect("public function metadata");
    for name in [
        "connect",
        "listen",
        "accept",
        "read_string",
        "read_to_end_string",
        "write_string",
        "write_all_string",
        "shutdown_read",
        "shutdown_write",
        "close",
        "closed",
        "peer_addr",
        "local_addr",
        "kind",
        "message",
        "io_kind",
        "op",
        "target",
        "partial_bytes",
    ] {
        assert!(functions.iter().any(|function| function["name"] == name), "metadata omitted documented TCP function {name}: {json}");
    }
    for custom_type in ["NetStream", "NetListener", "NetError"] {
        assert!(json.contains(custom_type), "metadata omitted {custom_type}: {json}");
    }
}
