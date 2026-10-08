//! Helpers shared by the `sys` package tests.
#![allow(dead_code)]

use rhai::packages::sys::{SysConfig, SysError, SysPackage};
use rhai::packages::Package;
use rhai::{Engine, EvalAltResult};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::{Duration, Instant};

const ENV_FIXTURE_TEST: &str = "RHAI_SYS_ENV_FIXTURE_TEST";

/// Run one environment assertion in a process whose environment was explicitly built
/// for that fixture. The child receives the exact test name so it cannot recurse.
pub fn run_env_fixture(test_name: &str, vars: &[(&str, std::ffi::OsString)]) -> bool {
    if std::env::var(ENV_FIXTURE_TEST).as_deref() == Ok(test_name) {
        return true;
    }

    let mut command = Command::new(std::env::current_exe().expect("test executable"));
    command
        .args(["--exact", test_name, "--nocapture"])
        .env_clear()
        .env(ENV_FIXTURE_TEST, test_name)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    for (name, value) in vars {
        command.env(name, value);
    }

    let mut child = command.spawn().expect("spawn isolated environment fixture");
    let deadline = Instant::now() + Duration::from_secs(30);
    loop {
        if let Some(status) = child.try_wait().expect("poll environment fixture") {
            let output = child.wait_with_output().expect("collect fixture output");
            assert!(
                status.success(),
                "environment fixture {test_name} failed ({status}):\nstdout:\n{}\nstderr:\n{}",
                String::from_utf8_lossy(&output.stdout),
                String::from_utf8_lossy(&output.stderr)
            );
            return false;
        }
        if Instant::now() >= deadline {
            child.kill().expect("kill timed-out environment fixture");
            let output = child.wait_with_output().expect("reap timed-out fixture");
            panic!("environment fixture {test_name} timed out after 30 seconds:\nstdout:\n{}\nstderr:\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
        }
        std::thread::sleep(Duration::from_millis(10));
    }
}

/// A fresh, empty directory under the system temp directory, removed on drop.
pub struct TempDir(PathBuf);

impl TempDir {
    pub fn new() -> Self {
        static COUNTER: AtomicUsize = AtomicUsize::new(0);
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!("rhai-sys-test-{}-{}-{n}", std::process::id(), std::thread::current().name().unwrap_or("t").replace("::", "_")));
        std::fs::create_dir_all(&path).unwrap();
        Self(path)
    }
    pub fn path(&self) -> &Path {
        &self.0
    }
    /// The path as a string with forward slashes, for use inside scripts.
    pub fn as_script_path(&self) -> String {
        self.0.to_str().unwrap().replace('\\', "/")
    }
    pub fn write(&self, rel: &str, data: impl AsRef<[u8]>) {
        let p = self.0.join(rel);
        if let Some(parent) = p.parent() {
            std::fs::create_dir_all(parent).unwrap();
        }
        std::fs::write(p, data).unwrap();
    }
    pub fn read(&self, rel: &str) -> Vec<u8> {
        std::fs::read(self.0.join(rel)).unwrap()
    }
    pub fn exists(&self, rel: &str) -> bool {
        self.0.join(rel).exists()
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

/// An engine with the `sys` package registered under `config`.
pub fn engine(config: SysConfig) -> Engine {
    let mut engine = Engine::new();
    SysPackage::new(config).expect("SysPackage::new").register_into_engine(&mut engine);
    engine
}

/// Run `script`, expecting it to fail with a `SysError`, and return that error.
pub fn sys_err(engine: &Engine, script: &str) -> SysError {
    let err = engine.run(script).expect_err("script should fail with a SysError");
    match *err {
        EvalAltResult::ErrorRuntime(value, _) => value.try_cast::<SysError>().expect("ErrorRuntime should carry a SysError"),
        other => panic!("expected ErrorRuntime, got {other:?}"),
    }
}

/// Run `script`, expecting a `SysError`, and return its variant name.
pub fn err_kind(engine: &Engine, script: &str) -> &'static str {
    sys_err(engine, script).kind()
}
