#![cfg(feature = "sys")]
//! Environment functions (matrix rows E1 to E3, E5).

mod sys_support;

use rhai::packages::sys::{EnvPolicy, SysConfig};
use std::ffi::OsString;
use sys_support::{engine, run_env_fixture};

// E1, E2: set and unset variables under `All`.
#[test]
fn test_env_var_set_and_unset() {
    if !run_env_fixture("test_env_var_set_and_unset", &[("RHAI_SYS_TEST_E1", "value".into())]) {
        return;
    }
    let e = engine(SysConfig::default().env(EnvPolicy::All));
    assert_eq!(e.eval::<String>(r#"env_var("RHAI_SYS_TEST_E1")"#).unwrap(), "value");
    assert_eq!(e.eval::<()>(r#"env_var("RHAI_SYS_TEST_DEFINITELY_UNSET")"#).unwrap(), ());
    assert!(e.eval::<bool>(r#"env_var("RHAI_SYS_TEST_DEFINITELY_UNSET") == ()"#).unwrap());
}

// Default policy hides everything.
#[test]
fn test_env_default_policy_hides_all() {
    if !run_env_fixture("test_env_default_policy_hides_all", &[("RHAI_SYS_TEST_E_DEFAULT", "value".into())]) {
        return;
    }
    let e = engine(SysConfig::default());
    assert_eq!(e.eval::<()>(r#"env_var("RHAI_SYS_TEST_E_DEFAULT")"#).unwrap(), ());
    assert!(e.eval::<rhai::Map>("env_vars()").unwrap().is_empty());
}

// E3: `env_vars` under `All` contains a known variable.
#[test]
fn test_env_vars_all() {
    if !run_env_fixture("test_env_vars_all", &[("RHAI_SYS_TEST_E3", "three".into())]) {
        return;
    }
    let e = engine(SysConfig::default().env(EnvPolicy::All));
    let value = e.eval::<String>("env_vars().RHAI_SYS_TEST_E3").unwrap();
    assert_eq!(value, "three");
}

// An explicitly allowed value is visible through both public environment functions.
#[test]
fn test_env_allow_list_value() {
    if !run_env_fixture("test_env_allow_list_value", &[("RHAI_SYS_TEST_ALLOW_LISTED", "allowed".into())]) {
        return;
    }
    let e = engine(SysConfig::default().env(EnvPolicy::AllowList(vec!["RHAI_SYS_TEST_ALLOW_LISTED".into()])));
    assert_eq!(e.eval::<String>(r#"env_var("RHAI_SYS_TEST_ALLOW_LISTED")"#).unwrap(), "allowed");
    let vars = e.eval::<rhai::Map>("env_vars()").unwrap();
    assert_eq!(vars.get("RHAI_SYS_TEST_ALLOW_LISTED").unwrap().clone().try_cast::<String>().unwrap(), "allowed");
    assert_eq!(vars.len(), 1);
}

// E5: `cwd` matches the host process.
#[test]
fn test_cwd_matches_process() {
    if !run_env_fixture("test_cwd_matches_process", &[]) {
        return;
    }
    let e = engine(SysConfig::default());
    let expected = std::env::current_dir().unwrap();
    assert_eq!(e.eval::<String>("cwd()").unwrap(), expected.to_str().unwrap());
}

// A listed but unset variable is `()` and absent from `env_vars`.
#[test]
fn test_env_allow_list_unset_variable() {
    if !run_env_fixture("test_env_allow_list_unset_variable", &[]) {
        return;
    }
    let e = engine(SysConfig::default().env(EnvPolicy::AllowList(vec!["RHAI_SYS_TEST_UNSET_LISTED".into()])));
    assert_eq!(e.eval::<()>(r#"env_var("RHAI_SYS_TEST_UNSET_LISTED")"#).unwrap(), ());
    assert!(e.eval::<rhai::Map>("env_vars()").unwrap().is_empty());
}

// E4: a non-UTF-8 value reads as `()` and is skipped by `env_vars`.
#[cfg(unix)]
#[test]
fn test_env_var_non_utf8() {
    use std::os::unix::ffi::OsStringExt;
    if !run_env_fixture("test_env_var_non_utf8", &[("RHAI_SYS_TEST_E4", OsString::from_vec(vec![0x66, 0xFF, 0x6F]))]) {
        return;
    }
    let e = engine(SysConfig::default().env(EnvPolicy::All));
    assert_eq!(e.eval::<()>(r#"env_var("RHAI_SYS_TEST_E4")"#).unwrap(), ());
    let vars = e.eval::<rhai::Map>("env_vars()").unwrap();
    assert!(!vars.contains_key("RHAI_SYS_TEST_E4"));
    assert!(!vars.is_empty());
}
