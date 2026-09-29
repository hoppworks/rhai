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
fn read_file_cases() {
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
fn read_binary() {
    let (t, e) = rw();
    t.write("bin.dat", [0x68, 0x69, 0xFF, 0xFE, 0x00]);
    assert_eq!(e.eval::<String>(r#"read_file("bin.dat")"#).unwrap(), "hi\u{FFFD}\u{FFFD}\0");
    assert_eq!(e.eval::<rhai::Blob>(r#"read_file_blob("bin.dat")"#).unwrap(), vec![0x68, 0x69, 0xFF, 0xFE, 0x00]);
}

// F5: large file round trip.
#[cfg(not(feature = "no_index"))]
#[test]
fn large_file_round_trip() {
    let (t, e) = rw();
    let data: Vec<u8> = (0..8 * 1024 * 1024).map(|i| (i % 251) as u8).collect();
    t.write("big.dat", &data);
    let back = e.eval::<rhai::Blob>(r#"read_file_blob("big.dat")"#).unwrap();
    assert_eq!(back, data);
    e.run(r#"let b = read_file_blob("big.dat"); write_file("copy.dat", b)"#).unwrap();
    assert_eq!(t.read("copy.dat"), data);
}

// F6, F7, F8: write truncates, append concatenates, blobs are exact.
#[cfg(not(feature = "no_index"))]
#[test]
fn write_append_blob() {
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
fn write_into_missing_parent() {
    let (t, e) = rw();
    assert_eq!(err_kind(&e, r#"write_file("nope/x.txt", "x")"#), "Io");
    assert!(!t.exists("nope"));
}

// F10, F11: predicates and metadata.
#[test]
fn predicates_and_metadata() {
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
fn read_dir_cases() {
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
fn create_dir_cases() {
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
fn remove_cases() {
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
fn rename_and_copy() {
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
fn unicode_names() {
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
fn no_handle_leak() {
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
fn unrestricted_round_trip() {
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
