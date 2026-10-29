#![cfg(all(feature = "sys", windows, feature = "no_index"))]
//! Public scalar process behavior when array-taking overloads are unavailable.

mod sys_support;

use rhai::packages::sys::{ProcessScope, ProgramPolicy, SysConfig, SysError};
use rhai::{Dynamic, EvalAltResult, ImmutableString, Map, Scope};

#[link(name = "kernel32")]
extern "system" {
    fn GetComputerNameW(buffer: *mut u16, size: *mut u32) -> i32;
}

fn native_hostname() -> String {
    let mut buffer = [0_u16; 256];
    let mut size = buffer.len() as u32;
    assert_ne!(unsafe { GetComputerNameW(buffer.as_mut_ptr(), &mut size) }, 0,
        "GetComputerNameW: {}", std::io::Error::last_os_error());
    String::from_utf16(&buffer[..size as usize]).expect("Windows computer name must be UTF-16")
}

fn hostname_program() -> String {
    std::path::PathBuf::from(std::env::var_os("SystemRoot").expect("SystemRoot"))
        .join(r"System32\hostname.exe").to_string_lossy().into_owned()
}

#[test]
fn windows_scalar_run_reports_native_hostname() {
    let expected = native_hostname();
    assert!(expected.is_ascii(), "hostname fixture needs an ASCII computer name: {expected:?}");
    for (label, supervision) in [("direct", ProcessScope::DirectChild), ("managed", ProcessScope::Managed)] {
        let engine = sys_support::engine(SysConfig::default().programs(ProgramPolicy::Any).process_scope(supervision));
        let mut scope = Scope::new();
        scope.push("program", hostname_program());
        let report = engine.eval_with_scope::<Map>(&mut scope, "run(program)")
            .expect("public scalar run must execute hostname.exe");
        assert_eq!(report["code"].as_int().unwrap(), 0);
        assert!(report["success"].as_bool().unwrap());
        assert!(report["stdout_complete"].as_bool().unwrap());
        assert!(report["stderr_complete"].as_bool().unwrap());
        let stdout = report["stdout"].clone().try_cast::<ImmutableString>().unwrap();
        let actual = stdout.trim();
        eprintln!("windows_scalar_hostname_readback label={label} host_api={expected:?} child={actual:?}");
        assert_eq!(actual, expected, "child hostname must match the independent Windows API");
        if std::env::var("RHAI_WINDOWS_SCALAR_WRONG_EXPECTATION").as_deref() == Ok(label) {
            assert_ne!(actual, expected, "deliberately wrong Windows scalar hostname expectation");
        }
    }
}

#[test]
fn windows_scalar_rejects_unavailable_env_remove_option() {
    for (label, supervision) in [("direct", ProcessScope::DirectChild), ("managed", ProcessScope::Managed)] {
        let engine = sys_support::engine(SysConfig::default().programs(ProgramPolicy::Any).process_scope(supervision));
        let mut scope = Scope::new();
        scope.push("program", hostname_program());
        let error = engine.eval_with_scope::<Dynamic>(&mut scope, "run(program, #{ env_remove: 7 })")
            .expect_err("no_index must reject the unavailable env_remove option");
        let typed = match *error { EvalAltResult::ErrorRuntime(value, _) => value.try_cast::<SysError>(), _ => None };
        eprintln!("windows_scalar_env_remove_readback label={label} typed_error={typed:?}");
        assert!(matches!(&typed, Some(SysError::Denied(message)) if message.contains("unsupported Windows process option `env_remove`")),
            "expected typed unavailable-option denial: {typed:?}");
        if std::env::var("RHAI_WINDOWS_SCALAR_DENIAL_WRONG_EXPECTATION").as_deref() == Ok(label) {
            assert!(!matches!(&typed, Some(SysError::Denied(_))), "deliberately wrong scalar denial expectation");
        }
    }
}

#[test]
fn windows_scalar_does_not_register_raw_run() {
    let engine = sys_support::engine(SysConfig::default().programs(ProgramPolicy::Any));
    let mut scope = Scope::new();
    scope.push("program", hostname_program());
    let error = engine.eval_with_scope::<Dynamic>(&mut scope, "run_raw(program)")
        .expect_err("run_raw must be unavailable under no_index");
    eprintln!("windows_scalar_raw_unavailable error={error:?}");
    assert!(matches!(*error, EvalAltResult::ErrorFunctionNotFound(..)), "expected missing raw overload");
}
