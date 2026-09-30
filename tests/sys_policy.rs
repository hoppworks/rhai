#![cfg(feature = "sys")]
//! Policy enforcement (matrix rows P1 to P12, R1, R2, R7).

mod sys_support;

use rhai::packages::sys::{EnvPolicy, FsAccess, SysConfig, SysError};
use rhai::{Engine, EvalAltResult};
use sys_support::{engine, err_kind, sys_err, TempDir};

// P1: default config denies every filesystem call.
#[test]
fn test_default_config_denies_fs() {
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
fn test_read_only_root() {
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
fn test_remove_dir_all_needs_delete_access() {
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
fn test_parent_traversal_is_denied() {
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
fn test_symlink_escape_is_denied() {
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
fn test_absolute_paths() {
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
fn test_multiple_roots() {
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
fn test_env_allow_list() {
    if !sys_support::run_env_fixture("test_env_allow_list", &[("RHAI_SYS_TEST_ALLOWED", "yes".into()), ("RHAI_SYS_TEST_HIDDEN", "no".into())]) {
        return;
    }
    let e = engine(SysConfig::default().env(EnvPolicy::AllowList(vec!["RHAI_SYS_TEST_ALLOWED".into()])));
    assert_eq!(e.eval::<String>(r#"env_var("RHAI_SYS_TEST_ALLOWED")"#).unwrap(), "yes");
    assert_eq!(e.eval::<()>(r#"env_var("RHAI_SYS_TEST_HIDDEN")"#).unwrap(), ());
    let vars = e.eval::<rhai::Map>("env_vars()").unwrap();
    assert!(vars.contains_key("RHAI_SYS_TEST_ALLOWED"));
    assert!(!vars.contains_key("RHAI_SYS_TEST_HIDDEN"));
}

// Unrestricted mode still honours the access level.
#[test]
fn test_unrestricted_respects_access_level() {
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
fn test_missing_root_fails_early() {
    let t = TempDir::new();
    let missing = t.path().join("nope");
    let err = rhai::packages::sys::SysPackage::new(SysConfig::default().fs_root(&missing, FsAccess::Read)).err().expect("should fail");
    assert!(matches!(err, SysError::Io { .. }), "{err}");
}

// R7: scripts can catch the error and inspect it.
#[test]
fn test_errors_are_catchable() {
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
fn test_plain_engine_has_no_sys_functions() {
    let e = Engine::new();
    let err = e.run(r#"read_file("x")"#).unwrap_err();
    assert!(matches!(*err, EvalAltResult::ErrorFunctionNotFound(..)));
}

// Hosts can downcast the boxed error to `SysError`.
#[test]
fn test_host_can_downcast() {
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

// Nested roots: the longest matching root decides the access level.
#[test]
fn test_nested_roots_longest_prefix() {
    let outer = TempDir::new();
    outer.write("outer.txt", "o");
    outer.write("inner/inner.txt", "i");
    let inner = outer.path().join("inner");
    let e = engine(SysConfig::default().fs_root(outer.path(), FsAccess::Read).fs_root(&inner, FsAccess::ReadWrite));
    let inner_new = format!("{}/inner/new.txt", outer.as_script_path());
    e.run(&format!(r#"write_file("{inner_new}", "x")"#)).unwrap();
    assert!(outer.exists("inner/new.txt"));

    let outer_new = format!("{}/new.txt", outer.as_script_path());
    assert_eq!(err_kind(&e, &format!(r#"write_file("{outer_new}", "x")"#)), "Denied");
    // Relative paths resolve against the first root, which is read-only.
    assert_eq!(err_kind(&e, r#"write_file("inner/other.txt", "x")"#), "Denied");
    assert_eq!(e.eval::<String>(r#"read_file("inner/inner.txt")"#).unwrap(), "i");
}

// A root configured through `..` or `.` components still confines correctly.
#[test]
fn test_root_with_dot_components() {
    let t = TempDir::new();
    t.write("sub/a.txt", "a");
    t.write("secret.txt", "s");
    let root = t.path().join("sub").join("..").join("sub");
    let e = engine(SysConfig::default().fs_root(&root, FsAccess::Read));
    assert_eq!(e.eval::<String>(r#"read_file("a.txt")"#).unwrap(), "a");
    let canonical = format!("{}/sub/a.txt", t.as_script_path());
    assert_eq!(e.eval::<String>(&format!(r#"read_file("{canonical}")"#)).unwrap(), "a");
    assert_eq!(err_kind(&e, r#"read_file("../secret.txt")"#), "Denied");
}

// A root that is itself a symlink: both the link path and the real path are accepted.
#[cfg(unix)]
#[test]
fn test_symlinked_root() {
    let t = TempDir::new();
    t.write("real/a.txt", "a");
    let link = t.path().join("link");
    std::os::unix::fs::symlink(t.path().join("real"), &link).unwrap();
    let e = engine(SysConfig::default().fs_root(&link, FsAccess::Read));
    assert_eq!(e.eval::<String>(r#"read_file("a.txt")"#).unwrap(), "a");
    let via_link = format!("{}/link/a.txt", t.as_script_path());
    let via_real = format!("{}/real/a.txt", t.as_script_path());
    assert_eq!(e.eval::<String>(&format!(r#"read_file("{via_link}")"#)).unwrap(), "a");
    assert_eq!(e.eval::<String>(&format!(r#"read_file("{via_real}")"#)).unwrap(), "a");
}

#[cfg(target_os = "macos")]
#[test]
fn test_root_accepts_macos_system_prefix_aliases() {
    let t = TempDir::new();
    t.write("real/a.txt", "payload");
    std::os::unix::fs::symlink(t.path().join("real"), t.path().join("link")).unwrap();
    let e = engine(SysConfig::default().fs_root(t.path().join("link"), FsAccess::Read));

    let var_path = format!("{}/real/a.txt", t.as_script_path());
    let private_path = var_path.replacen("/var/", "/private/var/", 1);
    assert_eq!(e.eval::<String>(&format!(r#"read_file("{var_path}")"#)).unwrap(), "payload");
    assert_eq!(e.eval::<String>(&format!(r#"read_file("{private_path}")"#)).unwrap(), "payload");
    assert_eq!(err_kind(&e, &format!(r#"write_file("{private_path}", "changed")"#)), "Denied");
    assert_eq!(std::fs::read(t.path().join("real/a.txt")).unwrap(), b"payload");
}

#[cfg(target_os = "macos")]
#[test]
fn test_nested_roots_keep_permissions_through_system_prefix_aliases() {
    let t = TempDir::new();
    t.write("inner/marker.txt", "nested payload");
    let outer_var = t.as_script_path();
    let outer_private = outer_var.replacen("/var/", "/private/var/", 1);
    let inner_var = format!("{outer_var}/inner");
    let inner_private = inner_var.replacen("/var/", "/private/var/", 1);
    let e = engine(SysConfig::default().fs_root(&outer_var, FsAccess::Read).fs_root(&inner_private, FsAccess::ReadWrite));

    for path in [format!("{inner_var}/marker.txt"), format!("{inner_private}/marker.txt")] {
        assert_eq!(e.eval::<String>(&format!(r#"read_file("{path}")"#)).unwrap(), "nested payload");
    }
    let inner_new = format!("{inner_var}/created.txt");
    e.run(&format!(r#"write_file("{inner_new}", "nested write")"#)).unwrap();
    assert_eq!(std::fs::read(t.path().join("inner/created.txt")).unwrap(), b"nested write");

    let outer_new = format!("{outer_private}/outer-created.txt");
    assert_eq!(err_kind(&e, &format!(r#"write_file("{outer_new}", "denied")"#)), "Denied");
    assert!(!t.path().join("outer-created.txt").exists());
}

// Configured root paths are opened using OS symlink/parent semantics.
#[cfg(unix)]
#[test]
fn test_configured_root_symlink_then_parent_uses_os_resolution() {
    let t = TempDir::new();
    t.write("lexical/allowed/marker.txt", "lexical sentinel");
    t.write("real/allowed/marker.txt", "OS-selected root");
    std::fs::create_dir_all(t.path().join("real/child")).unwrap();
    std::os::unix::fs::symlink(t.path().join("real/child"), t.path().join("lexical/link")).unwrap();

    let configured = t.path().join("lexical/link/../allowed");
    let selected = std::fs::canonicalize(t.path().join("real/allowed")).unwrap();
    assert_eq!(std::fs::canonicalize(&configured).unwrap(), selected);
    let e = engine(SysConfig::default().fs_root(&configured, FsAccess::ReadWrite));

    assert_eq!(e.eval::<String>(r#"read_file("marker.txt")"#).unwrap(), "OS-selected root");
    e.run(r#"write_file("created.txt", "script data")"#).unwrap();
    assert_eq!(std::fs::read(t.path().join("real/allowed/created.txt")).unwrap(), b"script data");
    assert!(!t.exists("lexical/allowed/created.txt"));
}

// Absolute paths containing `..`: allowed while they stay lexically inside the root.
#[test]
fn test_absolute_path_with_parent_components() {
    let t = TempDir::new();
    t.write("a.txt", "a");
    t.write("sub/b.txt", "b");
    let e = engine(SysConfig::default().fs_root(t.path(), FsAccess::Read));
    let base = t.as_script_path();
    assert_eq!(e.eval::<String>(&format!(r#"read_file("{base}/sub/../a.txt")"#)).unwrap(), "a");
    // Leaving the root and coming back is refused on purpose.
    let root_name = t.path().file_name().unwrap().to_str().unwrap();
    assert_eq!(err_kind(&e, &format!(r#"read_file("{base}/../{root_name}/a.txt")"#)), "Denied");
}

// Copying between roots needs read on the source and write on the destination.
#[test]
fn test_copy_across_roots() {
    let a = TempDir::new();
    a.write("src.txt", "payload");
    let b = TempDir::new();
    let e = engine(SysConfig::default().fs_root(a.path(), FsAccess::Read).fs_root(b.path(), FsAccess::ReadWrite));
    let dst = format!("{}/dst.txt", b.as_script_path());
    e.run(&format!(r#"copy_file("src.txt", "{dst}")"#)).unwrap();
    assert_eq!(b.read("dst.txt"), b"payload");
    assert_eq!(err_kind(&e, r#"copy_file("src.txt", "copy.txt")"#), "Denied");
    assert!(!a.exists("copy.txt"));
}

// Config builder semantics.
#[test]
fn test_config_builder() {
    use rhai::packages::sys::{FsPolicy, ProgramPolicy};

    let t = TempDir::new();
    t.write("a.txt", "a");

    // `fs_root` after `fs_unrestricted` switches back to confined mode.
    let e = engine(SysConfig::default().fs_unrestricted(FsAccess::ReadWriteDelete).fs_root(t.path(), FsAccess::Read));
    let other = TempDir::new();
    other.write("b.txt", "b");
    let outside = format!("{}/b.txt", other.as_script_path());
    assert_eq!(err_kind(&e, &format!(r#"read_file("{outside}")"#)), "Denied");
    assert_eq!(e.eval::<String>(r#"read_file("a.txt")"#).unwrap(), "a");

    // `permissive` grants everything.
    let p = SysConfig::permissive();
    assert_eq!(p.clone().fs_unrestricted(FsAccess::ReadWriteDelete), p);
    assert!(EnvPolicy::All.allows("ANYTHING"));
    assert!(!EnvPolicy::None.allows("ANYTHING"));
    assert!(EnvPolicy::AllowList(vec!["A".into()]).allows("A"));
    assert!(!EnvPolicy::AllowList(vec!["A".into()]).allows("AB"));
    assert!(ProgramPolicy::Any.allows("rm"));
    assert!(!ProgramPolicy::None.allows("rm"));
    assert!(ProgramPolicy::AllowList(vec!["git".into()]).allows("git"));
    assert!(!ProgramPolicy::AllowList(vec!["git".into()]).allows("/usr/bin/git"));
    assert_eq!(FsPolicy::default(), FsPolicy::Roots(Vec::new()));
    assert!(FsAccess::Read < FsAccess::ReadWrite && FsAccess::ReadWrite < FsAccess::ReadWriteDelete);
}

// The package can live under a namespace and be shared by several engines.
#[cfg(not(feature = "no_module"))]
#[test]
fn test_static_module_and_sharing() {
    use rhai::packages::sys::SysPackage;
    use rhai::packages::Package;

    let t = TempDir::new();
    t.write("a.txt", "a");
    let pkg = SysPackage::new(SysConfig::default().fs_root(t.path(), FsAccess::Read)).unwrap();

    let mut e1 = Engine::new();
    pkg.register_into_engine_as(&mut e1, "sys");
    assert_eq!(e1.eval::<String>(r#"sys::read_file("a.txt")"#).unwrap(), "a");
    let err = e1.run(r#"read_file("a.txt")"#).unwrap_err();
    assert!(matches!(*err, EvalAltResult::ErrorFunctionNotFound(..)));

    let mut e2 = Engine::new();
    pkg.clone().register_into_engine(&mut e2);
    assert_eq!(e2.eval::<String>(r#"read_file("a.txt")"#).unwrap(), "a");
}

// Errors carry the position of the failing call.
#[cfg(not(feature = "no_position"))]
#[test]
fn test_error_position() {
    let e = engine(SysConfig::default());
    let err = e.run("let x = 1;\nlet y = 2;\nread_file(\"x\");\n").unwrap_err();
    assert_eq!(err.position().line(), Some(3));
}

// Display and `kind` of every variant, plus `to_debug` from a script.
#[test]
fn test_error_variants() {
    let cases = [
        (SysError::Denied("d".into()), "Denied", "Denied: d"),
        (SysError::Timeout("t".into()), "Timeout", "Timeout: t"),
        (SysError::OutputLimit("o".into()), "OutputLimit", "OutputLimit: o"),
        (SysError::NotUtf8("n".into()), "NotUtf8", "NotUtf8: n"),
    ];
    for (err, kind, text) in cases {
        assert_eq!(err.kind(), kind);
        assert_eq!(err.to_string(), text);
    }
    let t = TempDir::new();
    let e = engine(SysConfig::default().fs_root(t.path(), FsAccess::Read));
    let dbg = e
        .eval::<String>(
            r#"
                let d = "";
                try { read_file("nope"); } catch (err) { d = err.to_debug(); }
                d
            "#,
        )
        .unwrap();
    assert!(dbg.starts_with("Io {"), "{dbg}");
    assert!(dbg.contains("NotFound"), "{dbg}");
}

// Under `sync` the package can be used from several threads at once.
#[cfg(feature = "sync")]
#[test]
fn test_sync_threads() {
    let t = TempDir::new();
    t.write("a.txt", "shared");
    let e = std::sync::Arc::new(engine(SysConfig::default().fs_root(t.path(), FsAccess::ReadWrite)));
    let handles: Vec<_> = (0..4)
        .map(|i| {
            let e = e.clone();
            std::thread::spawn(move || {
                for _ in 0..20 {
                    assert_eq!(e.eval::<String>(r#"read_file("a.txt")"#).unwrap(), "shared");
                    e.run(&format!(r#"write_file("t{i}.txt", "{i}")"#)).unwrap();
                }
            })
        })
        .collect();
    for h in handles {
        h.join().unwrap();
    }
    assert!(t.exists("t3.txt"));
}

// Function metadata includes the doc-comments.
#[cfg(feature = "metadata")]
#[test]
fn test_function_metadata() {
    let e = engine(SysConfig::default());
    let json = e.gen_fn_metadata_to_json(false).unwrap();
    assert!(json.contains("\"name\": \"read_file\""), "{json}");
    assert!(json.contains("# Example"), "{json}");
    assert!(json.contains("SysError"), "{json}");
}
