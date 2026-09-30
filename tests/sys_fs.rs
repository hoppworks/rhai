#![cfg(feature = "sys")]
//! Filesystem functions (matrix rows F1 to F18).

mod sys_support;

use rhai::packages::sys::{FsAccess, SysConfig, SysError};
use rhai::{Engine, Map, INT};
use sys_support::{engine, err_kind, sys_err, TempDir};

fn rw() -> (TempDir, Engine) {
    let t = TempDir::new();
    let e = engine(SysConfig::default().fs_root(t.path(), FsAccess::ReadWriteDelete));
    (t, e)
}

// F1, F2, F3: read existing, missing and empty files.
#[test]
fn test_read_file_cases() {
    let (t, e) = rw();
    t.write("text.txt", "hello\nworld");
    t.write("empty.txt", "");
    assert_eq!(e.eval::<String>(r#"read_file("text.txt")"#).unwrap(), "hello\nworld");
    assert_eq!(e.eval::<String>(r#"read_file("empty.txt")"#).unwrap(), "");
    let err = sys_err(&e, r#"read_file("missing.txt")"#);
    match &err {
        SysError::Io { kind, .. } => assert_eq!(*kind, std::io::ErrorKind::NotFound),
        other => panic!("{other}"),
    }
    assert!(err.to_string().contains("missing.txt"), "{err}");
}

// F4: binary content, lossy as string and exact as blob.
#[cfg(not(feature = "no_index"))]
#[test]
fn test_read_binary() {
    let (t, e) = rw();
    t.write("bin.dat", [0x68, 0x69, 0xFF, 0xFE, 0x00]);
    assert_eq!(e.eval::<String>(r#"read_file("bin.dat")"#).unwrap(), "hi\u{FFFD}\u{FFFD}\0");
    assert_eq!(e.eval::<rhai::Blob>(r#"read_file_blob("bin.dat")"#).unwrap(), vec![0x68, 0x69, 0xFF, 0xFE, 0x00]);
}

// F5: large file round trip.
#[cfg(not(feature = "no_index"))]
#[test]
fn test_large_file_round_trip() {
    let (t, e) = rw();
    let data: Vec<u8> = (0..8 * 1024 * 1024).map(|i: u32| u8::try_from(i % 251).unwrap()).collect();
    t.write("big.dat", &data);
    let back = e.eval::<rhai::Blob>(r#"read_file_blob("big.dat")"#).unwrap();
    assert_eq!(back, data);
    e.run(r#"let b = read_file_blob("big.dat"); write_file("copy.dat", b)"#).unwrap();
    assert_eq!(t.read("copy.dat"), data);
}

// F6, F7, F8: write truncates, append concatenates, blobs are exact.
#[cfg(not(feature = "no_index"))]
#[test]
fn test_write_append_blob() {
    let (t, e) = rw();
    e.run(r#"write_file("w.txt", "first version, longer")"#).unwrap();
    e.run(r#"write_file("w.txt", "second")"#).unwrap();
    assert_eq!(t.read("w.txt"), b"second");

    e.run(r#"append_file("a.txt", "one"); append_file("a.txt", "two")"#).unwrap();
    assert_eq!(t.read("a.txt"), b"onetwo");

    e.run(r#"write_file("b.bin", blob(3, 0xAA)); append_file("b.bin", blob(2, 0x01))"#).unwrap();
    assert_eq!(t.read("b.bin"), [0xAA, 0xAA, 0xAA, 0x01, 0x01]);
}

// F9: writing into a missing parent fails without leaving a file.
#[test]
fn test_write_into_missing_parent() {
    let (t, e) = rw();
    assert_eq!(err_kind(&e, r#"write_file("nope/x.txt", "x")"#), "Io");
    assert!(!t.exists("nope"));
}

// F10, F11: predicates and metadata.
#[test]
fn test_predicates_and_metadata() {
    let (t, e) = rw();
    t.write("f.txt", "12345");
    t.write("d/inner.txt", "");

    assert!(e.eval::<bool>(r#"exists("f.txt")"#).unwrap());
    assert!(e.eval::<bool>(r#"exists("d")"#).unwrap());
    assert!(!e.eval::<bool>(r#"exists("missing")"#).unwrap());
    assert!(e.eval::<bool>(r#"is_file("f.txt")"#).unwrap());
    assert!(!e.eval::<bool>(r#"is_file("d")"#).unwrap());
    assert!(!e.eval::<bool>(r#"is_file("missing")"#).unwrap());
    assert!(e.eval::<bool>(r#"is_dir("d")"#).unwrap());
    assert!(!e.eval::<bool>(r#"is_dir("f.txt")"#).unwrap());
    assert!(!e.eval::<bool>(r#"is_dir("missing")"#).unwrap());

    let m = e.eval::<Map>(r#"metadata("f.txt")"#).unwrap();
    assert_eq!(m["size"].as_int().unwrap(), 5);
    assert!(m["is_file"].as_bool().unwrap());
    assert!(!m["is_dir"].as_bool().unwrap());
    assert!(!m["is_symlink"].as_bool().unwrap());
    assert!(!m["readonly"].as_bool().unwrap());
    let modified = m["modified"].as_int().unwrap();
    assert!(modified > 1_600_000_000, "modified = {modified}");

    let m = e.eval::<Map>(r#"metadata("d")"#).unwrap();
    assert!(m["is_dir"].as_bool().unwrap());

    assert_eq!(err_kind(&e, r#"metadata("missing")"#), "Io");
}

// F12, F13: directory listing.
#[cfg(not(feature = "no_index"))]
#[test]
fn test_read_dir_cases() {
    let (t, e) = rw();
    t.write("b.txt", "");
    t.write("a.txt", "");
    t.write("sub/c.txt", "");
    let names = e.eval::<rhai::Array>(r#"read_dir(".")"#).unwrap();
    let names: Vec<String> = names.into_iter().map(|d| d.into_string().unwrap()).collect();
    assert_eq!(names, ["a.txt", "b.txt", "sub"]);

    let names = e.eval::<rhai::Array>(r#"read_dir("")"#).unwrap();
    assert_eq!(names.len(), 3);

    let names = e.eval::<rhai::Array>(r#"read_dir("sub")"#).unwrap();
    assert_eq!(names.len(), 1);

    assert_eq!(err_kind(&e, r#"read_dir("a.txt")"#), "Io");
    assert_eq!(err_kind(&e, r#"read_dir("missing")"#), "Io");
}

// F14: create_dir needs the parent, create_dir_all does not.
#[test]
fn test_create_dir_cases() {
    let (t, e) = rw();
    assert_eq!(err_kind(&e, r#"create_dir("x/y")"#), "Io");
    assert!(!t.exists("x"));
    e.run(r#"create_dir_all("x/y/z")"#).unwrap();
    assert!(t.path().join("x/y/z").is_dir());
    e.run(r#"create_dir("x/y/w")"#).unwrap();
    assert!(t.path().join("x/y/w").is_dir());
    assert_eq!(err_kind(&e, r#"create_dir("x")"#), "Io");
}

// F15: remove_dir refuses a non-empty directory, remove_dir_all does not.
#[test]
fn test_remove_cases() {
    let (t, e) = rw();
    t.write("d/inner.txt", "");
    t.write("f.txt", "");
    assert_eq!(err_kind(&e, r#"remove_dir("d")"#), "Io");
    assert!(t.exists("d/inner.txt"));
    e.run(r#"remove_file("f.txt")"#).unwrap();
    assert!(!t.exists("f.txt"));
    assert_eq!(err_kind(&e, r#"remove_file("f.txt")"#), "Io");
    e.run(r#"remove_dir_all("d")"#).unwrap();
    assert!(!t.exists("d"));
    e.run(r#"create_dir("empty"); remove_dir("empty")"#).unwrap();
    assert!(!t.exists("empty"));
}

// F17 plus rename inside one root.
#[test]
fn test_rename_and_copy() {
    let (t, e) = rw();
    t.write("src.txt", "payload");
    e.run(r#"copy_file("src.txt", "dst.txt")"#).unwrap();
    assert_eq!(t.read("dst.txt"), b"payload");
    assert_eq!(t.read("src.txt"), b"payload");

    e.run(r#"create_dir("sub"); rename("dst.txt", "sub/moved.txt")"#).unwrap();
    assert!(!t.exists("dst.txt"));
    assert_eq!(t.read("sub/moved.txt"), b"payload");

    assert_eq!(err_kind(&e, r#"rename("missing.txt", "x.txt")"#), "Io");
    assert_eq!(err_kind(&e, r#"copy_file("missing.txt", "x.txt")"#), "Io");
}

// F18: unicode file names.
#[cfg(not(feature = "no_index"))]
#[test]
fn test_unicode_names() {
    let (t, e) = rw();
    e.run(r#"write_file("grüße-日本.txt", "ok")"#).unwrap();
    assert_eq!(t.read("grüße-日本.txt"), b"ok");
    let names = e.eval::<rhai::Array>(r#"read_dir(".")"#).unwrap();
    assert_eq!(names[0].clone().into_string().unwrap(), "grüße-日本.txt");
    assert_eq!(e.eval::<String>(r#"read_file("grüße-日本.txt")"#).unwrap(), "ok");
}

// Cleanup after many operations: no handle leak.
#[cfg(target_os = "linux")]
#[cfg(not(feature = "no_index"))]
#[test]
fn test_no_handle_leak() {
    let (_t, e) = rw();
    let count = || std::fs::read_dir("/proc/self/fd").unwrap().count();
    e.run(r#"for i in 0..10 { write_file("f" + i, "x"); read_file("f" + i); metadata("f" + i); read_dir("."); }"#).unwrap();
    let before = count();
    e.run(r#"for i in 0..200 { write_file("f" + i, "x"); read_file("f" + i); metadata("f" + i); read_dir("."); remove_file("f" + i); }"#)
        .unwrap();
    let after = count();
    assert!(after <= before + 2, "fd count grew from {before} to {after}");
}

// The unrestricted mode works with absolute paths anywhere.
#[cfg(not(feature = "no_index"))]
#[test]
fn test_unrestricted_round_trip() {
    let t = TempDir::new();
    let e = engine(SysConfig::permissive());
    let base = t.as_script_path();
    e.run(&format!(
        r#"
            create_dir_all("{base}/a/b");
            write_file("{base}/a/b/f.txt", "deep");
            rename("{base}/a/b/f.txt", "{base}/a/g.txt");
        "#
    ))
    .unwrap();
    assert_eq!(t.read("a/g.txt"), b"deep");
    let names = e.eval::<rhai::Array>(&format!(r#"read_dir("{base}/a")"#)).unwrap();
    assert_eq!(names.len(), 2);
    let size = e
        .eval::<INT>(&format!(r#"metadata("{base}/a/g.txt").size"#))
        .map_err(|err| match *err {
            rhai::EvalAltResult::ErrorRuntime(v, _) => v.try_cast::<SysError>().unwrap().to_string(),
            other => other.to_string(),
        })
        .unwrap();
    assert_eq!(size, 4);
    e.run(&format!(r#"remove_dir_all("{base}/a")"#)).unwrap();
    assert!(!t.exists("a"));
}

#[cfg(unix)]
#[test]
fn test_unrestricted_symlinks_follow_host_semantics() {
    let t = TempDir::new();
    t.write("actual/absolute.txt", "absolute target");
    t.write("actual/relative.txt", "relative target");
    std::fs::create_dir_all(t.path().join("links")).unwrap();
    std::os::unix::fs::symlink(t.path().join("actual/absolute.txt"), t.path().join("links/absolute")).unwrap();
    std::os::unix::fs::symlink("../actual/relative.txt", t.path().join("links/relative")).unwrap();
    let e = engine(SysConfig::permissive());
    let base = t.as_script_path();

    assert_eq!(e.eval::<String>(&format!(r#"read_file("{base}/links/absolute")"#)).unwrap(), "absolute target");
    assert_eq!(e.eval::<String>(&format!(r#"read_file("{base}/links/relative")"#)).unwrap(), "relative target");
    e.run(&format!(r#"write_file("{base}/links/absolute", "changed"); copy_file("{base}/links/relative", "{base}/copied.txt")"#))
        .unwrap();
    assert_eq!(std::fs::read(t.path().join("actual/absolute.txt")).unwrap(), b"changed");
    assert_eq!(std::fs::read(t.path().join("copied.txt")).unwrap(), b"relative target");

    e.run(&format!(r#"remove_file("{base}/links/absolute")"#)).unwrap();
    assert!(!t.path().join("links/absolute").exists());
    assert_eq!(std::fs::read(t.path().join("actual/absolute.txt")).unwrap(), b"changed");
    assert_eq!(std::fs::read(t.path().join("actual/relative.txt")).unwrap(), b"relative target");
}

// Operations on the wrong kind of entry fail with an I/O error, not a panic.
#[test]
fn test_wrong_entry_kind() {
    let (t, e) = rw();
    t.write("f.txt", "x");
    t.write("d/inner.txt", "x");
    assert_eq!(err_kind(&e, r#"read_file("d")"#), "Io");
    assert_eq!(err_kind(&e, r#"write_file("d", "x")"#), "Io");
    assert_eq!(err_kind(&e, r#"append_file("d", "x")"#), "Io");
    assert_eq!(err_kind(&e, r#"remove_file("d")"#), "Io");
    assert_eq!(err_kind(&e, r#"remove_dir("f.txt")"#), "Io");
    assert_eq!(err_kind(&e, r#"create_dir("f.txt")"#), "Io");
    assert_eq!(err_kind(&e, r#"copy_file("d", "e")"#), "Io");
    assert!(t.exists("d/inner.txt"));
    assert_eq!(t.read("f.txt"), b"x");
}

// Symlink and read-only flags in `metadata`; `exists` on a dangling link.
#[cfg(unix)]
#[test]
fn test_metadata_symlink_and_readonly() {
    use std::os::unix::fs::PermissionsExt;
    let (t, e) = rw();
    t.write("target.txt", "12345");
    // Symlinks inside a confined root must be relative: cap-std treats an absolute link
    // target as an escape, even when it points back into the root.
    std::os::unix::fs::symlink("target.txt", t.path().join("link")).unwrap();
    std::os::unix::fs::symlink("gone", t.path().join("dangling")).unwrap();
    std::os::unix::fs::symlink(t.path().join("target.txt"), t.path().join("abs_link")).unwrap();
    std::fs::set_permissions(t.path().join("target.txt"), std::fs::Permissions::from_mode(0o444)).unwrap();

    let m = e.eval::<Map>(r#"metadata("link")"#).unwrap();
    assert!(m["is_symlink"].as_bool().unwrap());
    assert!(m["is_file"].as_bool().unwrap());
    assert_eq!(m["size"].as_int().unwrap(), 5);
    assert!(m["readonly"].as_bool().unwrap());
    let m = e.eval::<Map>(r#"metadata("target.txt")"#).unwrap();
    assert!(!m["is_symlink"].as_bool().unwrap());

    assert_eq!(err_kind(&e, r#"read_file("abs_link")"#), "Denied");

    assert!(!e.eval::<bool>(r#"exists("dangling")"#).unwrap());
    assert!(!e.eval::<bool>(r#"is_file("dangling")"#).unwrap());
    let err = sys_err(&e, r#"metadata("dangling")"#);
    assert!(matches!(err, SysError::Io { kind: std::io::ErrorKind::NotFound, .. }), "{err}");
    std::fs::set_permissions(t.path().join("target.txt"), std::fs::Permissions::from_mode(0o644)).unwrap();
}

// F19: a non-UTF-8 file name makes `read_dir` fail with `NotUtf8`.
#[cfg(all(unix, not(feature = "no_index")))]
#[test]
fn test_non_utf8_file_name() {
    use std::os::unix::ffi::OsStrExt;
    let (t, e) = rw();
    t.write("ok.txt", "");
    let unsupported = match std::fs::write(t.path().join(std::ffi::OsStr::from_bytes(b"bad\xFF.txt")), "") {
        Ok(()) => false,
        Err(err) => {
            eprintln!("filesystem does not support creating the non-UTF-8 fixture: {err}");
            true
        }
    };
    if unsupported {
        return;
    }
    let err = sys_err(&e, r#"read_dir(".")"#);
    assert!(matches!(err, SysError::NotUtf8(..)), "{err}");
    assert_eq!(err_kind(&e, r#"read_dir(".")"#), "NotUtf8");
}

// Rename overwrites an existing file and moves directories.
#[cfg(unix)]
#[test]
fn test_rename_overwrite_and_directory() {
    let (t, e) = rw();
    t.write("a.txt", "A");
    t.write("b.txt", "B");
    e.run(r#"rename("a.txt", "b.txt")"#).unwrap();
    assert!(!t.exists("a.txt"));
    assert_eq!(t.read("b.txt"), b"A");

    t.write("d/x.txt", "x");
    e.run(r#"rename("d", "moved")"#).unwrap();
    assert!(!t.exists("d"));
    assert_eq!(t.read("moved/x.txt"), b"x");
}

// Paths with `./`, `sub/./x` and a trailing slash.
#[test]
fn test_path_spellings() {
    let (t, e) = rw();
    t.write("a.txt", "a");
    t.write("sub/c.txt", "c");
    assert_eq!(e.eval::<String>(r#"read_file("./a.txt")"#).unwrap(), "a");
    assert_eq!(e.eval::<String>(r#"read_file("sub/./c.txt")"#).unwrap(), "c");
    assert_eq!(e.eval::<String>(r#"read_file("./sub/../a.txt")"#).unwrap(), "a");
    assert!(e.eval::<bool>(r#"is_dir("sub/")"#).unwrap());
    assert!(e.eval::<bool>(r#"is_dir(".")"#).unwrap());
    assert!(e.eval::<bool>(r#"is_dir("")"#).unwrap());
    #[cfg(not(feature = "no_index"))]
    assert_eq!(e.eval::<rhai::Array>(r#"read_dir("sub/")"#).unwrap().len(), 1);
}

// Deep trees and many entries.
#[cfg(not(feature = "no_index"))]
#[test]
fn test_deep_tree_and_many_entries() {
    let (t, e) = rw();
    e.run(r#"create_dir_all("l1/l2/l3/l4/l5"); write_file("l1/l2/l3/l4/l5/leaf.txt", "leaf")"#).unwrap();
    assert_eq!(t.read("l1/l2/l3/l4/l5/leaf.txt"), b"leaf");

    e.run(r#"create_dir("many"); for i in 0..300 { write_file("many/f" + i, ""); }"#).unwrap();
    let names = e.eval::<rhai::Array>(r#"read_dir("many")"#).unwrap();
    assert_eq!(names.len(), 300);
    let names: Vec<String> = names.into_iter().map(|d| d.into_string().unwrap()).collect();
    let mut sorted = names.clone();
    sorted.sort();
    assert_eq!(names, sorted);

    e.run(r#"remove_dir_all("l1"); remove_dir_all("many")"#).unwrap();
    assert!(!t.exists("l1") && !t.exists("many"));
}

// Unrestricted mode resolves relative paths against the process directory.
#[test]
fn test_unrestricted_relative_paths() {
    let e = engine(SysConfig::default().fs_unrestricted(FsAccess::Read));
    assert!(e.eval::<bool>(r#"exists("Cargo.toml")"#).unwrap());
    assert!(e.eval::<bool>(r#"is_file("Cargo.toml")"#).unwrap());
    assert!(e.eval::<bool>(r#"is_dir("src")"#).unwrap());
    assert!(e.eval::<String>(r#"read_file("Cargo.toml")"#).unwrap().contains("[package]"));
    assert!(e.eval::<bool>(r#"is_file("src/../Cargo.toml")"#).unwrap());
    #[cfg(not(feature = "no_index"))]
    assert!(e.eval::<rhai::Array>(r#"read_dir(".")"#).unwrap().iter().any(|d| d.clone().into_string().unwrap() == "Cargo.toml"));
}

// Unrestricted mode: a missing chain of parents is `NotFound`, not something else.
#[test]
fn test_unrestricted_missing_parents() {
    let t = TempDir::new();
    let e = engine(SysConfig::permissive());
    let p = format!("{}/no/such/dir/file.txt", t.as_script_path());
    let err = sys_err(&e, &format!(r#"read_file("{p}")"#));
    assert!(matches!(err, SysError::Io { kind: std::io::ErrorKind::NotFound, .. }), "{err}");
    assert_eq!(err_kind(&e, &format!(r#"write_file("{p}", "x")"#)), "Io");
    assert!(!t.exists("no"));
    e.run(&format!(r#"create_dir_all("{}/no/such/dir"); write_file("{p}", "x")"#, t.as_script_path())).unwrap();
    assert_eq!(t.read("no/such/dir/file.txt"), b"x");
}

// Empty writes and switching between string and blob content.
#[cfg(not(feature = "no_index"))]
#[test]
fn test_empty_and_mixed_writes() {
    let (t, e) = rw();
    e.run(r#"write_file("e.txt", "")"#).unwrap();
    assert_eq!(t.read("e.txt"), b"");
    assert_eq!(e.eval::<rhai::INT>(r#"metadata("e.txt").size"#).unwrap(), 0);
    e.run(r#"write_file("e.txt", "text"); write_file("e.txt", blob(2, 0x00))"#).unwrap();
    assert_eq!(t.read("e.txt"), [0, 0]);
    assert_eq!(err_kind(&e, r#"append_file("nope/x.bin", blob(1, 1))"#), "Io");
    assert!(!t.exists("nope"));
}

// F20, F21 and Windows path spellings. These run natively on Windows and under Wine.
#[cfg(windows)]
#[test]
fn test_windows_paths() {
    let (t, e) = rw();
    t.write("sub/a.txt", "a");

    // Forward slashes, backslashes and a mix all address the same file.
    assert_eq!(e.eval::<String>(r#"read_file("sub/a.txt")"#).unwrap(), "a");
    assert_eq!(e.eval::<String>(r#"read_file("sub\\a.txt")"#).unwrap(), "a");
    assert_eq!(e.eval::<String>(r#"read_file(".\\sub/a.txt")"#).unwrap(), "a");
    // Backslash traversal is refused like the forward-slash form.
    assert_eq!(err_kind(&e, r#"read_file("..\\x.txt")"#), "Denied");
    assert_eq!(err_kind(&e, r#"read_file("sub\\..\\..\\x.txt")"#), "Denied");

    // Absolute paths with a drive letter, in both spellings.
    let fwd = format!("{}/sub/a.txt", t.as_script_path());
    let back = fwd.replace('/', "\\\\");
    assert_eq!(e.eval::<String>(&format!(r#"read_file("{fwd}")"#)).unwrap(), "a");
    assert_eq!(e.eval::<String>(&format!(r#"read_file("{back}")"#)).unwrap(), "a");

    // A rooted path without a drive (`\foo`) is not absolute and cannot escape.
    assert_eq!(err_kind(&e, r#"read_file("\\Windows\\win.ini")"#), "Denied");

    // F21: a reserved device name fails with an I/O error and does not hang.
    let start = std::time::Instant::now();
    let kind = err_kind(&e, r#"write_file("CON", "x")"#);
    assert_eq!(kind, "Io");
    assert!(start.elapsed().as_secs() < 5);
    assert!(!t.exists("CON"));
}
