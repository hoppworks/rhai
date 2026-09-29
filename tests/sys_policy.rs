#![cfg(feature = "sys")]
//! Policy enforcement (matrix rows P1 to P12, R1, R2, R7).

mod sys_support;

use rhai::packages::sys::{EnvPolicy, FsAccess, SysConfig, SysError};
use rhai::{Engine, EvalAltResult};
use sys_support::{engine, err_kind, sys_err, TempDir};

// P1: default config denies every filesystem call.
#[test]
fn default_config_denies_fs() {
    let e = engine(SysConfig::default());
    let mut scripts = vec![r#"read_file("x")"#, r#"write_file("x", "y")"#, r#"exists("x")"#, r#"create_dir("x")"#, r#"remove_file("x")"#];
    #[cfg(not(feature = "no_index"))]
    scripts.push(r#"read_dir(".")"#);
    for script in scripts {
        assert_eq!(err_kind(&e, script), "Denied", "{script}");
    }
}

// P3, P4: read-only root.
#[test]
fn read_only_root() {
    let t = TempDir::new();
    t.write("a.txt", "hello");
    let e = engine(SysConfig::default().fs_root(t.path(), FsAccess::Read));

    assert_eq!(e.eval::<String>(r#"read_file("a.txt")"#).unwrap(), "hello");
    assert_eq!(err_kind(&e, r#"write_file("b.txt", "x")"#), "Denied");
    assert_eq!(err_kind(&e, r#"append_file("a.txt", "x")"#), "Denied");
    assert_eq!(err_kind(&e, r#"create_dir("d")"#), "Denied");
    assert_eq!(err_kind(&e, r#"remove_file("a.txt")"#), "Denied");
    assert_eq!(err_kind(&e, r#"rename("a.txt", "b.txt")"#), "Denied");
    assert!(!t.exists("b.txt"));
    assert_eq!(t.read("a.txt"), b"hello");
}

// P5: recursive deletion needs ReadWriteDelete.
#[test]
fn remove_dir_all_needs_delete_access() {
    let t = TempDir::new();
    t.write("d/inner.txt", "x");

    let e = engine(SysConfig::default().fs_root(t.path(), FsAccess::ReadWrite));
    assert_eq!(err_kind(&e, r#"remove_dir_all("d")"#), "Denied");
    assert!(t.exists("d/inner.txt"));

    let e = engine(SysConfig::default().fs_root(t.path(), FsAccess::ReadWriteDelete));
    e.run(r#"remove_dir_all("d")"#).unwrap();
    assert!(!t.exists("d"));
}

// P6: `..` cannot leave the root and nothing outside is touched.
#[test]
fn parent_traversal_is_denied() {
    let outer = TempDir::new();
    outer.write("secret.txt", "s");
    let root = outer.path().join("root");
    std::fs::create_dir(&root).unwrap();
    let e = engine(SysConfig::default().fs_root(&root, FsAccess::ReadWriteDelete));

    let mut scripts = vec![r#"read_file("../secret.txt")"#, r#"read_file("sub/../../secret.txt")"#, r#"exists("../secret.txt")"#, r#"write_file("../new.txt", "x")"#];
    #[cfg(not(feature = "no_index"))]
    scripts.push(r#"read_dir("..")"#);
    for script in scripts {
        assert_eq!(err_kind(&e, script), "Denied", "{script}");
    }
    assert!(!outer.exists("new.txt"));
    // A `..` that stays inside the root is fine.
    e.run(r#"create_dir("sub"); write_file("sub/../ok.txt", "x")"#).unwrap();
    assert!(root.join("ok.txt").exists());
}

// P7: a symlink inside the root that points outside is refused by cap-std.
#[cfg(unix)]
#[test]
fn symlink_escape_is_denied() {
    let outer = TempDir::new();
    outer.write("secret.txt", "s");
    let root = outer.path().join("root");
    std::fs::create_dir(&root).unwrap();
    std::os::unix::fs::symlink(outer.path().join("secret.txt"), root.join("link")).unwrap();
    std::os::unix::fs::symlink(outer.path(), root.join("dirlink")).unwrap();

    let e = engine(SysConfig::default().fs_root(&root, FsAccess::ReadWrite));
    assert_eq!(err_kind(&e, r#"read_file("link")"#), "Denied");
    assert_eq!(err_kind(&e, r#"read_file("dirlink/secret.txt")"#), "Denied");
    assert_eq!(err_kind(&e, r#"write_file("dirlink/new.txt", "x")"#), "Denied");
    assert!(!outer.exists("new.txt"));
}

// P8, P9: absolute paths inside and outside a root.
#[test]
fn absolute_paths() {
    let t = TempDir::new();
    t.write("a.txt", "abs");
    let other = TempDir::new();
    other.write("b.txt", "other");
    let e = engine(SysConfig::default().fs_root(t.path(), FsAccess::Read));

    let inside = format!("{}/a.txt", t.as_script_path());
    assert_eq!(e.eval::<String>(&format!(r#"read_file("{inside}")"#)).unwrap(), "abs");
    let outside = format!("{}/b.txt", other.as_script_path());
    let err = sys_err(&e, &format!(r#"read_file("{outside}")"#));
    assert!(matches!(err, SysError::Denied(..)), "{err}");
    assert!(err.to_string().contains("outside every configured root"));
}

// Two roots: relative paths use the first, absolute paths pick the matching one.
#[test]
fn multiple_roots() {
    let a = TempDir::new();
    a.write("in_a.txt", "A");
    let b = TempDir::new();
    b.write("in_b.txt", "B");
    let e = engine(SysConfig::default().fs_root(a.path(), FsAccess::Read).fs_root(b.path(), FsAccess::ReadWrite));
    assert_eq!(e.eval::<String>(r#"read_file("in_a.txt")"#).unwrap(), "A");
    assert_eq!(err_kind(&e, r#"read_file("in_b.txt")"#), "Io");
    let b_file = format!("{}/in_b.txt", b.as_script_path());
    assert_eq!(e.eval::<String>(&format!(r#"read_file("{b_file}")"#)).unwrap(), "B");
    let new_in_b = format!("{}/new.txt", b.as_script_path());
    e.run(&format!(r#"write_file("{new_in_b}", "x")"#)).unwrap();
    assert!(b.exists("new.txt"));
    let new_in_a = format!("{}/new.txt", a.as_script_path());
    assert_eq!(err_kind(&e, &format!(r#"write_file("{new_in_a}", "x")"#)), "Denied");
    // F16: rename across roots.
    let from = format!("{}/in_b.txt", b.as_script_path());
    assert_eq!(err_kind(&e, &format!(r#"rename("{from}", "moved.txt")"#)), "Denied");
}

// P12: env allow-list.
#[test]
fn env_allow_list() {
    std::env::set_var("RHAI_SYS_TEST_ALLOWED", "yes");
    std::env::set_var("RHAI_SYS_TEST_HIDDEN", "no");
    let e = engine(SysConfig::default().env(EnvPolicy::AllowList(vec!["RHAI_SYS_TEST_ALLOWED".into()])));
    assert_eq!(e.eval::<String>(r#"env_var("RHAI_SYS_TEST_ALLOWED")"#).unwrap(), "yes");
    assert_eq!(e.eval::<()>(r#"env_var("RHAI_SYS_TEST_HIDDEN")"#).unwrap(), ());
    let vars = e.eval::<rhai::Map>("env_vars()").unwrap();
    assert!(vars.contains_key("RHAI_SYS_TEST_ALLOWED"));
    assert!(!vars.contains_key("RHAI_SYS_TEST_HIDDEN"));
}

// Unrestricted mode still honours the access level.
#[test]
fn unrestricted_respects_access_level() {
    let t = TempDir::new();
    t.write("a.txt", "x");
    let e = engine(SysConfig::default().fs_unrestricted(FsAccess::Read));
    let p = format!("{}/a.txt", t.as_script_path());
    assert_eq!(e.eval::<String>(&format!(r#"read_file("{p}")"#)).unwrap(), "x");
    assert_eq!(err_kind(&e, &format!(r#"write_file("{p}", "y")"#)), "Denied");
    assert_eq!(t.read("a.txt"), b"x");
}

// A root that does not exist fails at package creation, not at first use.
#[test]
fn missing_root_fails_early() {
    let t = TempDir::new();
    let missing = t.path().join("nope");
    let err = rhai::packages::sys::SysPackage::new(SysConfig::default().fs_root(&missing, FsAccess::Read)).err().expect("should fail");
    assert!(matches!(err, SysError::Io { .. }), "{err}");
}

// R7: scripts can catch the error and inspect it.
#[test]
fn errors_are_catchable() {
    let t = TempDir::new();
    let e = engine(SysConfig::default().fs_root(t.path(), FsAccess::Read));
    let msg = e
        .eval::<String>(
            r#"
                let msg = "not reached";
                try { write_file("x", "y"); }
                catch (err) { msg = err.kind + "|" + err.message + "|" + type_of(err) + "|" + err.io_kind; }
                msg
            "#,
        )
        .unwrap();
    assert!(msg.starts_with("Denied|Denied: "), "{msg}");
    assert!(msg.ends_with("|SysError|"), "{msg}");

    let msg = e
        .eval::<String>(
            r#"
                let msg = "not reached";
                try { read_file("missing.txt"); }
                catch (err) { msg = err.kind + "|" + err.io_kind + "|" + err.op + "|" + err.target + "|" + err; }
                msg
            "#,
        )
        .unwrap();
    assert!(msg.starts_with("Io|NotFound|read file|missing.txt|Io (NotFound): cannot read file `missing.txt`"), "{msg}");

    // A caught error does not abort the script; execution continues.
    #[cfg(not(feature = "no_index"))]
    let n = e
        .eval::<rhai::INT>(
            r#"
                let n = 0;
                for f in ["a", "b", "c"] { try { read_file(f); } catch { n += 1; } }
                n
            "#,
        )
        .unwrap();
    #[cfg(not(feature = "no_index"))]
    assert_eq!(n, 3);
}

// R1: without the package nothing is registered.
#[test]
fn plain_engine_has_no_sys_functions() {
    let e = Engine::new();
    let err = e.run(r#"read_file("x")"#).unwrap_err();
    assert!(matches!(*err, EvalAltResult::ErrorFunctionNotFound(..)));
}

// Hosts can downcast the boxed error to `SysError`.
#[test]
fn host_can_downcast() {
    let t = TempDir::new();
    let e = engine(SysConfig::default().fs_root(t.path(), FsAccess::Read));
    let err = sys_err(&e, r#"read_file("missing.txt")"#);
    match err {
        SysError::Io { op, target, kind, .. } => {
            assert_eq!(op, "read file");
            assert_eq!(target, "missing.txt");
            assert_eq!(kind, std::io::ErrorKind::NotFound);
        }
        other => panic!("{other}"),
    }
}
