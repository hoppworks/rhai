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

#[test]
fn metadata_documents_tcp_handle_operations_and_overloads() {
    let mut engine = Engine::new();
    NetPackage::new(NetConfig::default()).unwrap().register_into_engine(&mut engine);
    let json = engine.gen_fn_metadata_to_json(false).unwrap();
    let metadata: serde_json::Value = serde_json::from_str(&json).unwrap();
    let functions = metadata["functions"].as_array().expect("public function metadata");

    // Check the metadata consumed by tooling, including semantic details users need
    // when reading and writing through the shared TCP handles.
    let require_comments = |name: &str, concepts: &[&str]| {
        let overloads = tcp_functions(functions, name);
        assert!(!overloads.is_empty(), "metadata omitted TCP function {name}: {json}");
        for function in overloads {
            let comments = function["docComments"].as_array().unwrap_or_else(|| panic!("{name} has no metadata comments: {function}"));
            let comments = comments.iter().filter_map(serde_json::Value::as_str).collect::<Vec<_>>().join(" ").to_lowercase();
            assert!(!comments.trim().is_empty(), "{name} metadata comments are empty: {function}");
            for concept in concepts {
                assert!(comments.contains(&concept.to_lowercase()), "{name} metadata should explain {concept:?}: {function}");
            }
        }
    };

    for name in ["connect", "listen"] {
        require_comments(name, &["numeric ip address and port", "host-granted"]);
    }
    require_comments("connect", &["port from 1 through 65535", "host connect deadline", "neterror"]);
    require_comments("listen", &["port from 0 through 65535", "ephemeral port", "neterror"]);
    require_comments("accept", &["positive timeout in milliseconds", "host accept deadline", "neterror"]);
    require_comments("read_string", &["zero-length request returns immediately", "positive request means eof", "host", "engine"]);
    #[cfg(not(feature = "no_index"))]
    require_comments("read_blob", &["zero-length request returns immediately", "positive request means eof", "host", "engine"]);
    require_signatures(&functions, "connect", &[(&[("address", "&str"), ("port", "crate::INT")], "NetStream")]);
    require_signatures(&functions, "listen", &[(&[("address", "&str"), ("port", "crate::INT")], "NetListener")]);
    require_signatures(&functions, "accept", &[(&[("listener", "&mut super::NetListener"), ("timeout_ms", "crate::INT")], "Result<super::super::NetStream,Box<crate::EvalAltResult>>")]);
    require_signatures(
        &functions,
        "read_string",
        &[
            (&[("stream", "&mut super::NetStream"), ("len", "crate::INT")], "Result<String,Box<crate::EvalAltResult>>"),
            (&[("stream", "&mut super::NetStream"), ("len", "crate::INT"), ("timeout_ms", "crate::INT")], "Result<String,Box<crate::EvalAltResult>>"),
        ],
    );
    #[cfg(not(feature = "no_index"))]
    require_signatures(
        &functions,
        "read_blob",
        &[
            (&[("stream", "&mut super::NetStream"), ("len", "crate::INT")], "Result<crate::Blob,Box<crate::EvalAltResult>>"),
            (&[("stream", "&mut super::NetStream"), ("len", "crate::INT"), ("timeout_ms", "crate::INT")], "Result<crate::Blob,Box<crate::EvalAltResult>>"),
        ],
    );
    require_comments("read_to_end_string", &["effective byte cap", "minimum", "host limit", "engine limit"]);
    require_signatures(
        &functions,
        "read_to_end_string",
        &[
            (&[("stream", "&mut super::NetStream"), ("max_bytes", "crate::INT")], "Result<String,Box<crate::EvalAltResult>>"),
            (&[("stream", "&mut super::NetStream"), ("max_bytes", "crate::INT"), ("timeout_ms", "crate::INT")], "Result<String,Box<crate::EvalAltResult>>"),
        ],
    );
    #[cfg(not(feature = "no_index"))]
    {
        require_comments("read_to_end_blob", &["effective byte cap", "minimum", "host limit", "engine limit"]);
        require_signatures(
            &functions,
            "read_to_end_blob",
            &[
                (&[("stream", "&mut super::NetStream"), ("max_bytes", "crate::INT")], "Result<crate::Blob,Box<crate::EvalAltResult>>"),
                (&[("stream", "&mut super::NetStream"), ("max_bytes", "crate::INT"), ("timeout_ms", "crate::INT")], "Result<crate::Blob,Box<crate::EvalAltResult>>"),
            ],
        );
    }
    require_comments("write_string", &["accepted", "result may be short", "host", "engine"]);
    require_comments("write_all_string", &["full", "accepted progress", "host", "engine"]);
    require_signatures(
        &functions,
        "write_string",
        &[
            (&[("stream", "&mut super::NetStream"), ("value", "&str")], "Result<crate::INT,Box<crate::EvalAltResult>>"),
            (&[("stream", "&mut super::NetStream"), ("value", "&str"), ("timeout_ms", "crate::INT")], "Result<crate::INT,Box<crate::EvalAltResult>>"),
        ],
    );
    require_signatures(
        &functions,
        "write_all_string",
        &[
            (&[("stream", "&mut super::NetStream"), ("value", "&str")], "Result<crate::INT,Box<crate::EvalAltResult>>"),
            (&[("stream", "&mut super::NetStream"), ("value", "&str"), ("timeout_ms", "crate::INT")], "Result<crate::INT,Box<crate::EvalAltResult>>"),
        ],
    );
    #[cfg(not(feature = "no_index"))]
    {
        require_comments("write_blob", &["accepted", "result may be short", "host", "engine"]);
        require_comments("write_all_blob", &["full", "accepted progress", "host", "engine"]);
        require_signatures(
            &functions,
            "write_blob",
            &[
                (&[("stream", "&mut super::NetStream"), ("value", "crate::Blob")], "Result<crate::INT,Box<crate::EvalAltResult>>"),
                (&[("stream", "&mut super::NetStream"), ("value", "crate::Blob"), ("timeout_ms", "crate::INT")], "Result<crate::INT,Box<crate::EvalAltResult>>"),
            ],
        );
        require_signatures(
            &functions,
            "write_all_blob",
            &[
                (&[("stream", "&mut super::NetStream"), ("value", "crate::Blob")], "Result<crate::INT,Box<crate::EvalAltResult>>"),
                (&[("stream", "&mut super::NetStream"), ("value", "crate::Blob"), ("timeout_ms", "crate::INT")], "Result<crate::INT,Box<crate::EvalAltResult>>"),
            ],
        );
    }
    for name in ["shutdown_read", "shutdown_write"] {
        require_comments(name, &["receiving", "sending", "unit", "neterror"]);
    }
    require_comments("close", &["every clone"]);
    require_comments("closed", &["all its clones"]);
    require_comments("peer_addr", &["remote tcp endpoint"]);
    require_comments("local_addr", &["local tcp endpoint"]);
    require_comments("kind", &["error category"]);
    require_comments("message", &["human-readable explanation"]);
    require_comments("io_kind", &["underlying i/o error kind", "unit"]);
    require_comments("op", &["operation that failed"]);
    require_comments("target", &["resource target"]);
    require_comments("partial_bytes", &["received or accepted", "not peer acknowledgement"]);
    require_signatures(&functions, "local_addr", &[(&[("listener", "&mut super::NetListener")], "Result<String,Box<crate::EvalAltResult>>")]);
    require_signatures(&functions, "peer_addr", &[(&[("stream", "&mut super::NetStream")], "Result<String,Box<crate::EvalAltResult>>")]);
    require_signatures(&functions, "shutdown_read", &[(&[("stream", "&mut super::NetStream")], "Result<(),Box<crate::EvalAltResult>>")]);
    require_signatures(&functions, "shutdown_write", &[(&[("stream", "&mut super::NetStream")], "Result<(),Box<crate::EvalAltResult>>")]);
    require_signatures(&functions, "close", &[(&[("listener", "&mut super::NetListener")], ""), (&[("stream", "&mut super::NetStream")], "")]);
    require_signatures(&functions, "closed", &[(&[("listener", "&mut super::NetListener")], "bool"), (&[("stream", "&mut super::NetStream")], "bool")]);
    require_signatures(&functions, "kind", &[(&[("err", "&mut NetError")], "ImmutableString")]);
    require_signatures(&functions, "message", &[(&[("err", "&mut NetError")], "ImmutableString")]);
    require_signatures(&functions, "io_kind", &[(&[("err", "&mut NetError")], "Dynamic")]);
    require_signatures(&functions, "op", &[(&[("err", "&mut NetError")], "ImmutableString")]);
    require_signatures(&functions, "target", &[(&[("err", "&mut NetError")], "ImmutableString")]);
    require_signatures(&functions, "partial_bytes", &[(&[("err", "&mut NetError")], "crate::INT")]);
}

fn function_params(function: &serde_json::Value) -> Vec<(String, String)> {
    function["params"]
        .as_array()
        .unwrap_or_else(|| panic!("metadata omitted ordered parameters: {function}"))
        .iter()
        .map(|param| {
            (
                param["name"].as_str().unwrap_or_else(|| panic!("metadata parameter has no name: {param}")).to_owned(),
                param["type"].as_str().unwrap_or_else(|| panic!("metadata parameter has no type: {param}")).to_owned(),
            )
        })
        .collect()
}

fn tcp_functions<'a>(functions: &'a [serde_json::Value], name: &str) -> Vec<&'a serde_json::Value> {
    functions
        .iter()
        .filter(|function| function["name"] == name)
        .filter(|function| {
            match name {
                // These closure registrations require explicit metadata parameter information.
                "connect" | "listen" => true,
                _ => {
                    let params = function_params(function);
                    let receiver_type = params.first().map(|param| param.1.as_str()).unwrap_or_default();
                    match name {
                        "accept" | "local_addr" => receiver_type.contains("NetListener"),
                        "close" | "closed" => receiver_type.contains("NetStream") || receiver_type.contains("NetListener"),
                        "kind" | "message" | "io_kind" | "op" | "target" | "partial_bytes" | "to_string" => receiver_type.contains("NetError"),
                        _ => receiver_type.contains("NetStream"),
                    }
                }
            }
        })
        .collect()
}

fn require_signatures(functions: &[serde_json::Value], name: &str, expected: &[(&[(&str, &str)], &str)]) {
    let overloads = tcp_functions(functions, name);
    assert_eq!(overloads.len(), expected.len(), "{name} has unexpected TCP overload count: {overloads:?}");
    let mut actual = Vec::new();
    for function in &overloads {
        let params = function_params(function);
        assert_eq!(function["numParams"].as_u64(), Some(params.len() as u64), "{name} numParams disagrees with ordered params: {function}");
        let names = params.iter().map(|param| param.0.as_str()).collect::<Vec<_>>();
        let return_type = function["returnType"].as_str().unwrap_or_default();
        assert!(
            expected.iter().any(|(expected_params, expected_return)| {
                names == expected_params.iter().map(|(name, _)| *name).collect::<Vec<_>>() && params.iter().map(|param| param.1.as_str()).collect::<Vec<_>>() == expected_params.iter().map(|(_, type_name)| *type_name).collect::<Vec<_>>() && return_type == *expected_return
            }),
            "{name} has unexpected parameter or return types: {function}"
        );
        if names.last() == Some(&"timeout_ms") {
            let comments = function["docComments"]
                .as_array()
                .unwrap_or_else(|| panic!("{name} timeout overload has no metadata comments: {function}"));
            let comments = comments.iter().filter_map(serde_json::Value::as_str).collect::<Vec<_>>().join(" ").to_lowercase();
            assert!(comments.contains("positive timeout in milliseconds"), "{name} timeout overload must document its unit and positive-value requirement: {function}");
        }
        actual.push((params, return_type.to_owned()));
    }
    actual.sort();
    let mut expected = expected
        .iter()
        .map(|(params, return_type)| (params.iter().map(|(name, type_name)| ((*name).to_owned(), (*type_name).to_owned())).collect::<Vec<_>>(), (*return_type).to_owned()))
        .collect::<Vec<_>>();
    expected.sort();
    assert_eq!(actual, expected, "{name} must retain each ordered public signature and type exactly once");
}
