//! Prepared public-Engine acceptance fixture for the shared `spawn`/`Child` API.
//!
//! This file is intentionally unregistered until the public `spawn` surface and its
//! Clone-capable Rhai Child type exist. See
//! `.scratch/process-unix-run/shared-child-contract-activation.md` for the exact activation.

use rhai::packages::sys::{ProgramPolicy, SysConfig, SysPackage};
use rhai::packages::Package;
use rhai::{Dynamic, Engine, Map, Scope, INT};
use std::path::{Path, PathBuf};
use std::process::{Child as ControllerChild, Command, Stdio};
#[cfg(feature = "sync")]
use std::sync::{mpsc, Arc, Barrier};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::thread;
use std::time::{Duration, Instant};

const SCENARIO_ENV: &str = "RHAI_SHARED_CHILD_SCENARIO";
const ROOT_ENV: &str = "RHAI_SHARED_CHILD_ROOT";
const FIXTURE_ENV: &str = "RHAI_SHARED_CHILD_FIXTURE";
const LIBTEST_QUIET_START: &str = "\nrunning 1 test\n";

/// Re-executed as a bounded controller. The OS child fixture is a separate invocation of this
/// same test binary, so all behavior below goes through the real Engine and real process API.
#[test]
fn scenario_entry() {
    let Ok(scenario) = std::env::var(SCENARIO_ENV) else {
        return;
    };
    let root = PathBuf::from(std::env::var_os(ROOT_ENV).expect("scenario root"));
    match scenario.as_str() {
        "blocked_input_wait_snapshot" => blocked_input_wait_snapshot(&root),
        "drop_true" => drop_final_client(&root, true),
        "drop_false" => drop_final_client(&root, false),
        #[cfg(feature = "sync")]
        "sync_wait_cancel" => sync_wait_cancel(&root),
        other => panic!("unknown shared-child scenario {other}"),
    }
}

/// OS fixture. Its readiness and completion files are atomically replaced and independently
/// read by the controller; it never uses a shell, helper process, fixed sleep, or inherited
/// stdout as a readiness signal.
#[test]
fn fixture_entry() {
    let Ok(mode) = std::env::var(FIXTURE_ENV) else {
        return;
    };
    let root = PathBuf::from(std::env::var_os(ROOT_ENV).expect("fixture root"));
    let pid = std::process::id();
    atomic_record(&root, "child.status", &format!("pid={pid} state=ready\n"));

    match mode.as_str() {
        "blocked_input" => {
            wait_for_file(&root.join("release-input"), Duration::from_secs(18));
            let mut input = Vec::new();
            std::io::Read::read_to_end(&mut std::io::stdin(), &mut input)
                .expect("read transferred stdin");
            atomic_record(
                &root,
                "child.consumed",
                &format!("pid={pid} bytes={} valid={}\n", input.len(), input.iter().all(|b| *b == b'i')),
            );
            wait_for_file(&root.join("release-exit"), Duration::from_secs(18));
            use std::io::Write;
            std::io::stdout().write_all(b"shared-child-output\n").unwrap();
            std::io::stderr().write_all(b"shared-child-error\n").unwrap();
            std::io::stdout().flush().unwrap();
            std::io::stderr().flush().unwrap();
            atomic_record(&root, "child.status", &format!("pid={pid} state=exited code=17\n"));
            std::process::exit(17);
        }
        "hold" => {
            let deadline = Instant::now() + Duration::from_secs(18);
            loop {
                for nonce in ["one", "two", "three"] {
                    let request = root.join(format!("probe-{nonce}.request"));
                    if request.exists() {
                        let token = std::fs::read_to_string(&request).expect("read probe token");
                        atomic_record(&root, &format!("probe-{nonce}.reply"), &token);
                        let _ = std::fs::remove_file(request);
                    }
                }
                if root.join("release-exit").exists() {
                    use std::io::Write;
                    std::io::stdout().write_all(b"released\n").unwrap();
                    atomic_record(&root, "child.status", &format!("pid={pid} state=exited code=0\n"));
                    return;
                }
                assert!(Instant::now() < deadline, "fixture controller deadline expired");
                thread::sleep(Duration::from_millis(5));
            }
        }
        other => panic!("unknown OS fixture mode {other}"),
    }
}

#[test]
fn spawn_returns_while_large_stdin_is_blocked_and_wait_snapshots_are_stable() {
    run_bounded_controller("blocked_input_wait_snapshot");
}

#[test]
fn nonfinal_child_clone_drop_keeps_the_real_child_available() {
    run_bounded_controller("drop_true");
}

#[test]
fn final_drop_honors_both_kill_on_drop_policies() {
    run_bounded_controller("drop_false");
}

#[cfg(feature = "sync")]
#[test]
fn sync_waiter_can_be_cancelled_through_another_shared_child_handle() {
    run_bounded_controller("sync_wait_cancel");
}

fn engine(kill_on_drop: bool) -> Engine {
    let executable = std::env::current_exe().expect("test executable");
    let executable = executable.to_string_lossy().into_owned();
    let config = SysConfig::default()
        .programs(ProgramPolicy::AllowList(vec![executable]))
        .kill_on_drop(kill_on_drop)
        .max_output(64 * 1024);
    let mut engine = Engine::new();
    SysPackage::new(config)
        .expect("construct sys package")
        .register_into_engine(&mut engine);
    engine
}

fn spawn_fixture(engine: &Engine, scope: &mut Scope<'_>, root: &Path, mode: &str, input: Option<String>) -> Dynamic {
    let executable = std::env::current_exe().expect("test executable");
    scope.push("fixture_exe", executable.to_string_lossy().into_owned());
    scope.push("fixture_root", root.to_string_lossy().into_owned());
    scope.push("fixture_mode", mode.to_owned());
    let mut script = String::from(
        r#"spawn(fixture_exe, ["--exact", "shared_child_contract::fixture_entry", "--quiet", "--nocapture"], #{
            env_clear: true,
            env: #{ "RHAI_SHARED_CHILD_FIXTURE": fixture_mode, "RHAI_SHARED_CHILD_ROOT": fixture_root }
        })"#,
    );
    if let Some(input) = input {
        scope.push("fixture_stdin", input);
        script = script.replace("})", ", stdin: fixture_stdin })");
    }
    match engine.eval_with_scope::<Dynamic>(scope, &script) {
        Ok(value) => value,
        Err(error) => panic!("public Engine spawn failed: {error}"),
    }
}

fn blocked_input_wait_snapshot(root: &Path) {
    const INPUT_SIZE: usize = 8 * 1024 * 1024;
    let engine = engine(true);
    let mut scope = Scope::new();
    let payload = "i".repeat(INPUT_SIZE);
    let before = Instant::now();
    let child = spawn_fixture(&engine, &mut scope, root, "blocked_input", Some(payload));
    let spawn_elapsed = before.elapsed();
    scope.push_dynamic("child", child);
    let pid = engine.eval_with_scope::<INT>(&mut scope, "child.id").unwrap() as i32;
    wait_for_state(root, "child.status", "ready", Duration::from_secs(3));
    assert!(spawn_elapsed < Duration::from_secs(2), "spawn blocked for {spawn_elapsed:?}");
    assert!(!root.join("child.consumed").exists(), "fixture unexpectedly consumed stdin before release");
    eprintln!("shared-child blocked-stdin ready pid={pid} spawn_elapsed_ms={}", spawn_elapsed.as_millis());

    let timed_wait = engine.eval_with_scope::<Dynamic>(&mut scope, "child.wait(0.02)").unwrap();
    assert!(timed_wait.is_unit(), "finite wait must return unit while fixture remains held");
    assert!(!root.join("child.consumed").exists(), "timed wait unexpectedly released stdin");
    std::fs::write(root.join("release-input"), "go").unwrap();
    wait_for_file(&root.join("child.consumed"), Duration::from_secs(5));
    let consumed = std::fs::read_to_string(root.join("child.consumed")).unwrap();
    assert_eq!(consumed.trim(), format!("pid={pid} bytes={INPUT_SIZE} valid=true"));

    std::fs::write(root.join("release-exit"), "go").unwrap();

    let first = engine.eval_with_scope::<Map>(&mut scope, "child.wait()").unwrap();
    assert_eq!(first["code"].as_int().unwrap(), 17);
    assert_eq!(first["stdout"].as_immutable_string_ref().unwrap().as_str(), format!("{LIBTEST_QUIET_START}shared-child-output\n"));
    assert_eq!(first["stderr"].as_immutable_string_ref().unwrap().as_str(), "shared-child-error\n");
    assert!(first["stdout_complete"].as_bool().unwrap());
    assert!(first["stderr_complete"].as_bool().unwrap());

    let mut mutated = first;
    mutated.insert("stdout".into(), Dynamic::from("caller-mutated\n"));
    let repeated_wait = engine.eval_with_scope::<Map>(&mut scope, "child.wait()").unwrap();
    let ready_snapshot = engine.eval_with_scope::<Map>(&mut scope, "child.try_wait()").unwrap();
    for snapshot in [&repeated_wait, &ready_snapshot] {
        assert_eq!(snapshot["code"].as_int().unwrap(), 17);
        assert_eq!(snapshot["stdout"].as_immutable_string_ref().unwrap().as_str(), format!("{LIBTEST_QUIET_START}shared-child-output\n"));
    }
    wait_for_state(root, "child.status", "exited", Duration::from_secs(2));
    assert_pid_reaped(pid);
    eprintln!("shared-child final pid={pid} child_record={:?} reap=ESRCH stable-wait=1 stable-try-wait=1", std::fs::read_to_string(root.join("child.status")).unwrap());
}

fn drop_final_client(root: &Path, kill_on_drop: bool) {
    let engine = engine(kill_on_drop);
    let mut scope = Scope::new();
    let child = spawn_fixture(&engine, &mut scope, root, "hold", None);
    let pid = engine.eval_with_scope::<INT>(&mut scope, "child.id").unwrap() as i32;
    wait_for_state(root, "child.status", "ready", Duration::from_secs(3));
    let alias = child.clone();
    drop(child);
    scope.push_dynamic("remaining", alias);
    issue_probe(&engine, &mut scope, root, pid, "one");
    eprintln!("shared-child nonfinal-drop pid={pid} child_record=ready operational_probe=one");

    // Dropping the remaining Dynamic is the final script-client release. The Engine/package
    // stays alive so this distinguishes ClientLease behavior from service/package lifetime.
    scope.remove::<Dynamic>("remaining");
    if kill_on_drop {
        wait_for_pid_gone(pid, Duration::from_secs(5));
        eprintln!("shared-child final-drop kill_on_drop=true pid={pid} reap=ESRCH");
    } else {
        issue_probe(&engine, &mut scope, root, pid, "two");
        std::fs::write(root.join("release-exit"), "go").unwrap();
        wait_for_state(root, "child.status", "exited", Duration::from_secs(5));
        wait_for_pid_gone(pid, Duration::from_secs(5));
        eprintln!("shared-child final-drop kill_on_drop=false pid={pid} child_record={:?} eventual_reap=ESRCH", std::fs::read_to_string(root.join("child.status")).unwrap());
    }
}

#[cfg(feature = "sync")]
fn sync_wait_cancel(root: &Path) {
    let engine = Arc::new(engine(false));
    let mut scope = Scope::new();
    let child = spawn_fixture(&engine, &mut scope, root, "hold", None);
    let pid = engine.eval_with_scope::<INT>(&mut scope, "child.id").unwrap() as i32;
    wait_for_state(root, "child.status", "ready", Duration::from_secs(3));

    let barrier = Arc::new(Barrier::new(2));
    let (started_tx, started_rx) = mpsc::sync_channel(1);
    let (done_tx, done_rx) = mpsc::sync_channel(1);
    let waiter_engine = Arc::clone(&engine);
    let waiter_child = child.clone();
    let waiter_barrier = Arc::clone(&barrier);
    let waiter = thread::spawn(move || {
        let mut waiter_scope = Scope::new();
        waiter_scope.push_dynamic("child", waiter_child);
        waiter_barrier.wait();
        started_tx.send(()).unwrap();
        let result = waiter_engine.eval_with_scope::<Dynamic>(&mut waiter_scope, "child.wait(10.0)");
        done_tx.send(result.map(|value| value.is_unit())).unwrap();
    });
    barrier.wait();
    started_rx.recv_timeout(Duration::from_secs(2)).expect("waiter entered public wait call");

    let mut cancel_scope = Scope::new();
    cancel_scope.push_dynamic("child", child.clone());
    engine.eval_with_scope::<Dynamic>(&mut cancel_scope, "child.kill()").expect("concurrent public cancellation");
    let waited = done_rx.recv_timeout(Duration::from_secs(4)).expect("cancellation wakes bounded waiter");
    assert!(waited.is_ok(), "waiter failed: {waited:?}");
    waiter.join().expect("waiter thread");
    let final_result = engine.eval_with_scope::<Map>(&mut cancel_scope, "child.wait()").unwrap();
    assert!(final_result.contains_key("code"));
    wait_for_pid_gone(pid, Duration::from_secs(5));
    eprintln!("shared-child sync-cancel pid={pid} waiter_returned=1 final_wait=1 reap=ESRCH");
}

fn issue_probe(engine: &Engine, scope: &mut Scope<'_>, root: &Path, pid: i32, nonce: &str) {
    let request = root.join(format!("probe-{nonce}.request"));
    let reply = root.join(format!("probe-{nonce}.reply"));
    std::fs::write(&request, nonce).unwrap();
    wait_for_file(&reply, Duration::from_secs(3));
    assert_eq!(std::fs::read_to_string(reply).unwrap(), nonce);
    assert!(process_exists(pid), "fixture stopped responding to a fresh challenge");
    let _ = (engine, scope); // Keep the live public Engine/Scope at each challenge site.
}

/// Outer tests run every potentially blocking Engine call in this exact owned process group.
/// On timeout or assertion unwind the guard kills only that group, reaps its direct controller,
/// then verifies any recorded OS fixture PID is absent before its temp root is dropped.
fn run_bounded_controller(scenario: &str) {
    let root = FixtureDir::new();
    let root_path = root.path().to_path_buf();
    let executable = std::env::current_exe().expect("test executable");
    let mut command = Command::new(executable);
    command
        .args(["--exact", "shared_child_contract::scenario_entry", "--quiet", "--nocapture"])
        .env_clear()
        .env(SCENARIO_ENV, scenario)
        .env(ROOT_ENV, root.path())
        .env("AGENT_RUNTIME_DIR", std::env::var_os("AGENT_RUNTIME_DIR").expect("scoped runtime"))
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let child = command.spawn().expect("spawn bounded scenario controller");
    let controller_pid = child.id() as i32;
    eprintln!("shared-child controller_started scenario={scenario} pid={controller_pid} root={}", root_path.display());
    let mut guard = ControllerGuard { child: Some(child), controller_pid, record: root_path.join("child.status") };
    let deadline = Instant::now() + Duration::from_secs(12);
    loop {
        if let Some(status) = guard.child.as_mut().unwrap().try_wait().expect("poll exact scenario child") {
            let output = guard.child.take().unwrap().wait_with_output().expect("reap exact scenario child");
            eprintln!("shared-child controller_reaped scenario={scenario} pid={controller_pid} status={status}");
            assert_pid_reaped(controller_pid);
            eprintln!("shared-child controller_esrch pid={controller_pid} verified=true");
            if !status.success() {
                panic!("scenario {scenario} failed ({status})\nstdout:\n{}\nstderr:\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
            }
            if let Some(pid) = read_record_pid(&guard.record) {
                wait_for_pid_gone(pid, Duration::from_secs(3));
            }
            eprintln!("shared-child scenario={scenario} controller_pid={controller_pid} status=ok fixture_record={:?}", std::fs::read_to_string(&guard.record).ok());
            return;
        }
        assert!(Instant::now() < deadline, "scenario {scenario} exceeded 12s external watchdog; fixture_record={:?}", std::fs::read_to_string(&guard.record).ok());
        thread::sleep(Duration::from_millis(10));
    }
}

/// Fixture data lives inside the scoped runtime, so the runner can remove it if its hard
/// watchdog has to terminate the test process before Rust destructors run.
struct FixtureDir(PathBuf);

impl FixtureDir {
    fn new() -> Self {
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let runtime = PathBuf::from(std::env::var_os("AGENT_RUNTIME_DIR").expect("scoped runtime"));
        let path = runtime.join(format!("shared-child-fixture-{}-{}", std::process::id(), NEXT.fetch_add(1, Ordering::Relaxed)));
        std::fs::create_dir(&path).expect("create exact fixture root");
        Self(path)
    }

    fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for FixtureDir {
    fn drop(&mut self) {
        std::fs::remove_dir_all(&self.0).expect("remove exact fixture root");
    }
}

struct ControllerGuard {
    child: Option<ControllerChild>,
    controller_pid: i32,
    record: PathBuf,
}

impl Drop for ControllerGuard {
    fn drop(&mut self) {
        let recorded_pid = read_record_pid(&self.record);
        let fixture_live = recorded_pid.is_some_and(process_exists);
        if let Some(mut child) = self.child.take() {
            if child.try_wait().ok().flatten().is_none() {
                // Stop only the exact controller Child. It remains in the scoped runner's
                // inherited process group; this guard does not claim descendant custody.
                if let Err(error) = child.kill() {
                    eprintln!("shared-child watchdog controller_kill_error pid={} error={error}", self.controller_pid);
                }
            }
            match child.wait_with_output() {
                Ok(output) => {
                    eprintln!("shared-child controller_reap=complete stdout={:?} stderr={:?}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
                    eprintln!("shared-child controller_esrch pid={} verified={}", self.controller_pid, pid_is_esrch(self.controller_pid));
                }
                Err(error) => eprintln!("shared-child controller_reap=error error={error}"),
            }
        }
        if let Some(pid) = recorded_pid {
            if fixture_live {
                wait_for_pid_gone(pid, Duration::from_secs(3));
            }
            eprintln!("shared-child fixture_cleanup pid={pid} absent={}", !process_exists(pid));
        }
    }
}

fn atomic_record(root: &Path, name: &str, contents: &str) {
    let path = root.join(name);
    let temp = root.join(format!(".{name}.tmp-{}", std::process::id()));
    std::fs::write(&temp, contents).expect("write record temp");
    std::fs::rename(temp, path).expect("atomically publish fixture record");
}

fn wait_for_file(path: &Path, timeout: Duration) {
    let deadline = Instant::now() + timeout;
    while !path.exists() {
        assert!(Instant::now() < deadline, "timed out waiting for fixture path {}", path.display());
        thread::sleep(Duration::from_millis(5));
    }
}

fn wait_for_state(root: &Path, name: &str, state: &str, timeout: Duration) {
    let path = root.join(name);
    let deadline = Instant::now() + timeout;
    loop {
        if let Ok(record) = std::fs::read_to_string(&path) {
            if record.split_whitespace().any(|field| field == format!("state={state}")) {
                return;
            }
        }
        assert!(Instant::now() < deadline, "timed out waiting for state={state} in {}", path.display());
        thread::sleep(Duration::from_millis(5));
    }
}

fn read_record_pid(path: &Path) -> Option<i32> {
    std::fs::read_to_string(path).ok()?.split_whitespace().find_map(|field| field.strip_prefix("pid=")?.parse().ok())
}

fn process_exists(pid: i32) -> bool {
    let result = unsafe { libc::kill(pid, 0) };
    result == 0 || std::io::Error::last_os_error().raw_os_error() != Some(libc::ESRCH)
}

fn wait_for_pid_gone(pid: i32, timeout: Duration) {
    let deadline = Instant::now() + timeout;
    while process_exists(pid) {
        assert!(Instant::now() < deadline, "fixture pid={pid} did not become absent before watchdog");
        thread::sleep(Duration::from_millis(5));
    }
    assert!(pid_is_esrch(pid), "expected exact pid={pid} to be absent with ESRCH");
}

fn assert_pid_reaped(pid: i32) {
    assert!(pid_is_esrch(pid), "expected exact pid={pid} to be absent with ESRCH");
}

fn pid_is_esrch(pid: i32) -> bool {
    let result = unsafe { libc::kill(pid, 0) };
    result == -1 && std::io::Error::last_os_error().raw_os_error() == Some(libc::ESRCH)
}
