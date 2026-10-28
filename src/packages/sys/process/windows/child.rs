//! Shared Windows Child handles, backed by an independently running supervisor.

use super::*;
use std::sync::atomic::{AtomicBool, AtomicU32};
use std::sync::{mpsc, Condvar};
use windows_sys::Win32::Foundation::CloseHandle;
use windows_sys::Win32::System::Threading::{CreateEventW, SetEvent};

pub(super) struct Cancellation {
    event: usize,
    requested: AtomicBool,
    #[cfg(test)]
    probe: Option<Arc<PendingProbe>>,
}

impl Cancellation {
    fn new() -> std_io::Result<Self> {
        // SAFETY: no security attributes or event name are supplied.
        let event = unsafe { CreateEventW(std::ptr::null(), 1, 0, std::ptr::null()) };
        if event.is_null() {
            return Err(std_io::Error::last_os_error());
        }
        Ok(Self {
            event: event as usize,
            requested: AtomicBool::new(false),
            #[cfg(test)]
            probe: None,
        })
    }
    pub(super) fn handle(&self) -> HANDLE {
        self.event as HANDLE
    }
    pub(super) fn requested(&self) -> bool {
        self.requested.load(Ordering::Acquire)
    }
    #[cfg(test)]
    pub(super) fn probe(&self) -> Option<&PendingProbe> {
        self.probe.as_deref()
    }
    fn request(&self) {
        self.requested.store(true, Ordering::Release);
        // SAFETY: the Arc owning this event outlives this call and the supervisor wait.
        unsafe {
            SetEvent(self.handle());
        }
    }
}

// Per-execution test-only synchronization; no process-wide hooks or product API.
#[cfg(test)]
#[derive(Default)]
pub(super) struct PendingProbe {
    state: Mutex<PendingProbeState>,
    changed: Condvar,
    skip_cancellation: AtomicBool,
}

#[cfg(test)]
#[derive(Default)]
struct PendingProbeState {
    observed_unsignaled: bool,
    parked: bool,
    gate_timed_out: bool,
    kill_requested_at_release: bool,
    pending_at_release: bool,
    released: bool,
    cancellation_completed: bool,
    owner_retired: bool,
}

#[cfg(test)]
impl PendingProbe {
    pub(super) fn skip_cancellation(&self) -> bool {
        self.skip_cancellation.load(Ordering::Acquire)
    }
    pub(super) fn observe_and_gate(&self, writer: &PipeWriter, cancellation: &Cancellation) {
        if !writer.is_pending()
            || unsafe { WaitForSingleObject(writer.event_handle(), 0) } != WAIT_TIMEOUT
        {
            return;
        }
        let mut state = self.state.lock().unwrap_or_else(|p| p.into_inner());
        if state.observed_unsignaled {
            return;
        }
        state.observed_unsignaled = true;
        state.parked = true;
        self.changed.notify_all();
        let deadline = Instant::now() + Duration::from_secs(10);
        while !state.released {
            let left = deadline.saturating_duration_since(Instant::now());
            if left.is_zero() {
                state.gate_timed_out = true;
                break;
            }
            state = self
                .changed
                .wait_timeout(state, left)
                .unwrap_or_else(|p| p.into_inner())
                .0;
        }
        state.kill_requested_at_release = cancellation.requested();
        state.pending_at_release = writer.is_pending()
            && unsafe { WaitForSingleObject(writer.event_handle(), 0) } == WAIT_TIMEOUT;
        state.parked = false;
        self.changed.notify_all();
    }
    pub(super) fn completed(&self, completed: bool) {
        let mut state = self.state.lock().unwrap_or_else(|p| p.into_inner());
        state.cancellation_completed = completed;
        self.changed.notify_all();
    }
    pub(super) fn retired(&self) {
        let mut state = self.state.lock().unwrap_or_else(|p| p.into_inner());
        state.owner_retired = true;
        self.changed.notify_all();
    }
}
impl Drop for Cancellation {
    fn drop(&mut self) {
        // SAFETY: this structure owns exactly one event handle.
        unsafe {
            CloseHandle(self.handle());
        }
    }
}

struct Control {
    cancellation: Cancellation,
    result: Mutex<Option<Result<ProcessReport, (ProcessCause, ProcessReport)>>>,
    changed: Condvar,
    pid: AtomicU32,
    engine_limit: usize,
    kill_on_drop: bool,
}
struct Lease {
    control: Arc<Control>,
}

// Once a child exists, retain its exact process and pipe ownership on every unwind.
struct HandoffOwner(Option<ProcessOwner>);
impl Drop for HandoffOwner {
    fn drop(&mut self) {
        if let Some(owner) = self.0.take() {
            let _ = retain_for_cleanup(owner);
        }
    }
}
impl Drop for Lease {
    fn drop(&mut self) {
        if self.control.kill_on_drop {
            self.control.cancellation.request();
        }
    }
}

/// A shared handle to a child process launched by the `sys` package.
#[derive(Clone)]
pub struct ProcessChild {
    lease: Arc<Lease>,
}

fn registration(name: &str, comments: &[&str], params: &[&str]) -> crate::FuncRegistration {
    let reg = crate::FuncRegistration::new(name);
    #[cfg(feature = "metadata")]
    let reg = reg.with_comments(comments).with_params_info(params);
    #[cfg(not(feature = "metadata"))]
    let _ = (comments, params);
    reg
}

pub(super) fn register(module: &mut Module, state: &Shared<SysState>) {
    module.set_custom_type::<ProcessChild>("Child");
    let getter = crate::FuncRegistration::new(crate::engine::make_getter("id"))
        .with_purity(true)
        .with_volatility(false);
    #[cfg(feature = "metadata")]
    let getter = getter
        .with_comments(["/// Child process identifier (PID)."])
        .with_params_info(["child: &mut Child", "crate::INT"]);
    getter.set_into_module(module, |child: &mut ProcessChild| {
        child.lease.control.pid.load(Ordering::Acquire) as INT
    });
    registration(
        "try_wait",
        &["/// Poll the child without blocking."],
        &["child: &mut Child", "Dynamic"],
    )
    .with_purity(false)
    .set_into_module(module, |child: &mut ProcessChild| {
        child.snapshot(false, None)
    });
    registration(
        "wait",
        &["/// Wait for a child result."],
        &["child: &mut Child", "Map"],
    )
    .with_purity(false)
    .set_into_module(module, |child: &mut ProcessChild| -> Res<Map> {
        Ok(child.snapshot(true, None)?.cast())
    });
    #[cfg(not(feature = "no_float"))]
    registration(
        "wait",
        &["/// Wait up to the supplied timeout for the child and return a result map when it finishes. If it is still running when the timeout expires, return unit without cancelling the child."],
        &["child: &mut Child", "seconds: crate::FLOAT", "Dynamic"],
    )
    .with_purity(false)
    .set_into_module(
        module,
        |child: &mut ProcessChild, seconds: crate::FLOAT| -> Res<Dynamic> {
            if !seconds.is_finite() || seconds < 0.0 {
                return Err(SysError::Denied(
                    "wait timeout must be a finite non-negative number".into(),
                )
                .into());
            }
            let duration = Duration::try_from_secs_f64(seconds as f64)
                .map_err(|_| SysError::Denied("wait timeout is out of range".into()))?;
            child.snapshot(true, Some(duration))
        },
    );
    #[cfg(feature = "no_float")]
    registration(
        "wait",
        &["/// Wait up to the supplied timeout in whole seconds for the child and return a result map when it finishes. If it is still running when the timeout expires, return unit without cancelling the child."],
        &["child: &mut Child", "seconds: crate::INT", "Dynamic"],
    )
    .with_purity(false)
    .set_into_module(
        module,
        |child: &mut ProcessChild, seconds: INT| -> Res<Dynamic> {
            if seconds < 0 {
                return Err(SysError::Denied("wait timeout must be non-negative".into()).into());
            }
            child.snapshot(true, Some(Duration::from_secs(seconds as u64)))
        },
    );
    registration(
        "kill",
        &["/// Request cancellation of the child."],
        &["child: &mut Child"],
    )
    .with_purity(false)
    .set_into_module(module, |child: &mut ProcessChild| {
        child.lease.control.cancellation.request()
    });
    let st = state.clone();
    crate::packages::sys::reg("spawn", &["/// Spawn a child and return a shared handle."])
        .set_into_module(
            module,
            move |ctx: NativeCallContext, program: &str| -> Res<ProcessChild> {
                spawn(&ctx, &st, program, Vec::new(), Map::new())
            },
        );
    let st = state.clone();
    crate::packages::sys::reg("spawn", &["/// Spawn a child with options."]).set_into_module(
        module,
        move |ctx: NativeCallContext, program: &str, options: Map| -> Res<ProcessChild> {
            spawn(&ctx, &st, program, Vec::new(), options)
        },
    );
    #[cfg(not(feature = "no_index"))]
    {
        let st = state.clone();
        crate::packages::sys::reg("spawn", &["/// Spawn a child with arguments."]).set_into_module(
            module,
            move |ctx: NativeCallContext, program: &str, args: Array| -> Res<ProcessChild> {
                spawn(&ctx, &st, program, parse_args(args)?, Map::new())
            },
        );
        let st = state.clone();
        crate::packages::sys::reg("spawn", &["/// Spawn a child with arguments and options."])
            .set_into_module(
                module,
                move |ctx: NativeCallContext,
                      program: &str,
                      args: Array,
                      options: Map|
                      -> Res<ProcessChild> {
                    spawn(&ctx, &st, program, parse_args(args)?, options)
                },
            );
    }
}

impl ProcessChild {
    fn snapshot(&self, wait: bool, timeout: Option<Duration>) -> Res<Dynamic> {
        let control = &self.lease.control;
        let mut result = control.result.lock().unwrap_or_else(|p| p.into_inner());
        if wait {
            if let Some(timeout) = timeout {
                let deadline = Instant::now()
                    .checked_add(timeout)
                    .ok_or_else(|| SysError::Denied("wait timeout is out of range".into()))?;
                while result.is_none() {
                    let remaining = deadline.saturating_duration_since(Instant::now());
                    if remaining.is_zero() {
                        return Ok(Dynamic::UNIT);
                    }
                    let (next, timed) = control
                        .changed
                        .wait_timeout(result, remaining)
                        .unwrap_or_else(|p| p.into_inner());
                    result = next;
                    if timed.timed_out() && result.is_none() {
                        return Ok(Dynamic::UNIT);
                    }
                }
            } else {
                while result.is_none() {
                    result = control
                        .changed
                        .wait(result)
                        .unwrap_or_else(|p| p.into_inner());
                }
            }
        }
        let report = match &*result {
            None => return Ok(Dynamic::UNIT),
            Some(Ok(report)) => report,
            Some(Err((cause, report))) => {
                return Err(SysError::Process {
                    cause: cause.clone(),
                    report: report.clone(),
                }
                .into())
            }
        };
        if control.engine_limit > 0
            && (report.stdout().len() > control.engine_limit
                || report.stderr().len() > control.engine_limit)
        {
            return Err(SysError::Process {
                cause: ProcessCause::OutputLimit(format!(
                    "decoded process output exceeded the engine string limit of {} bytes",
                    control.engine_limit
                )),
                report: report.clone(),
            }
            .into());
        }
        let mut map = Map::new();
        map.insert(
            "success".into(),
            Dynamic::from(report.exit_code() == Some(0)),
        );
        map.insert(
            "code".into(),
            report
                .exit_code()
                .map(|n| Dynamic::from_int(n as INT))
                .unwrap_or(Dynamic::UNIT),
        );
        map.insert("signal".into(), Dynamic::UNIT);
        map.insert("timed_out".into(), Dynamic::from(report.timed_out()));
        map.insert(
            "stdout_complete".into(),
            Dynamic::from(report.stdout_complete()),
        );
        map.insert(
            "stderr_complete".into(),
            Dynamic::from(report.stderr_complete()),
        );
        map.insert(
            "stdout".into(),
            Dynamic::from(ImmutableString::from(report.stdout())),
        );
        map.insert(
            "stderr".into(),
            Dynamic::from(ImmutableString::from(report.stderr())),
        );
        Ok(Dynamic::from(map))
    }
}

fn spawn(
    ctx: &NativeCallContext,
    state: &Shared<SysState>,
    program: &str,
    args: Vec<String>,
    options: Map,
) -> Res<ProcessChild> {
    spawn_inner(
        ctx,
        state,
        program,
        args,
        options,
        #[cfg(test)]
        None,
    )
}

fn spawn_inner(
    ctx: &NativeCallContext,
    state: &Shared<SysState>,
    program: &str,
    args: Vec<String>,
    options: Map,
    #[cfg(test)] probe: Option<Arc<PendingProbe>>,
) -> Res<ProcessChild> {
    if !state.config.programs.allows(program) {
        return Err(SysError::Denied(format!("program `{program}` is not allowed")).into());
    }
    if !state.config.allow_batch_files
        && [".bat", ".cmd"]
            .iter()
            .any(|ext| program.to_ascii_lowercase().ends_with(ext))
    {
        return Err(
            SysError::Denied("batch files are not allowed by host configuration".into()).into(),
        );
    }
    if options.contains_key("timeout") {
        return Err(SysError::Denied("spawn does not accept a timeout option".into()).into());
    }
    #[cfg(not(feature = "unchecked"))]
    let engine_limit = ctx.engine().max_string_size();
    #[cfg(feature = "unchecked")]
    let engine_limit = {
        let _ = ctx;
        0
    };
    let mut options = parse_options(state, options, engine_limit)?;
    let managed_input = if state.config.process_scope == ProcessScope::Managed {
        Some(super::managed_input(program, &args, &options)?)
    } else {
        None
    };
    let permit = ActivePermit::acquire()?;
    #[allow(unused_mut)]
    let mut cancellation = Cancellation::new()
        .map_err(|error| SysError::io("create child cancellation event", program, &error))?;
    #[cfg(test)]
    {
        cancellation.probe = probe;
    }
    let control = Arc::new(Control {
        cancellation,
        result: Mutex::new(None),
        changed: Condvar::new(),
        pid: AtomicU32::new(0),
        engine_limit,
        kill_on_drop: state.config.kill_on_drop,
    });
    let lease = Arc::new(Lease {
        control: Arc::clone(&control),
    });
    let worker_program = program.to_owned();
    let (stdout, stdout_child) =
        PipeReader::pair().map_err(|error| SysError::io("create stdout pipe", program, &error))?;
    let (stderr, stderr_child) =
        PipeReader::pair().map_err(|error| SysError::io("create stderr pipe", program, &error))?;
    let (stdin, child_stdin) = match options.stdin.take() {
        Some(input) if !input.is_empty() => {
            let (writer, child) = PipeWriter::pair(input)
                .map_err(|error| SysError::io("create stdin pipe", program, &error))?;
            (Some(writer), Some(child))
        }
        _ => (None, None),
    };
    let (sender, receiver) = mpsc::sync_channel::<(ProcessOwner, Arc<Control>, String, usize)>(1);
    thread::Builder::new()
        .name("rhai-windows-child-supervisor".into())
        .spawn(move || {
            let Ok((mut owner, control, program, limit)) = receiver.recv() else {
                return;
            };
            let supervised = catch_unwind(AssertUnwindSafe(|| {
                owner.supervise(None, limit, &program, Some(&control.cancellation))
            }));
            let result = match supervised {
                Ok(result) => result,
                Err(_) => {
                    if owner.has_pending_cleanup() {
                        owner.diagnostics.push(ProcessDiagnostic::new(
                            "retain cleanup custody",
                            None,
                            "child or overlapped operation remains active after supervisor panic",
                        ));
                    }
                    Err((
                        ProcessCause::Io {
                            op: "supervise child",
                            target: program.clone(),
                            kind: std_io::ErrorKind::Other,
                            message: "Windows child supervisor panicked".into(),
                        },
                        owner.snapshot(false),
                    ))
                }
            };
            if owner.has_pending_cleanup() {
                let _ = retain_for_cleanup(owner);
            } else {
                #[cfg(test)]
                {
                    drop(owner);
                    if let Some(probe) = control.cancellation.probe() {
                        probe.retired();
                    }
                }
            }
            *control.result.lock().unwrap_or_else(|p| p.into_inner()) = Some(result);
            control.changed.notify_all();
        })
        .map_err(|error| SysError::io("start child supervisor", program, &error))?;
    let owner = if let Some((application, mut command_line, environment)) = managed_input {
        let job = job::ManagedJob::new()
            .map_err(|error| SysError::io("create managed job", program, &error))?;
        let handles = launch::child_stdio(child_stdin, stdout_child, stderr_child)
            .map_err(|error| SysError::io("prepare child handles", program, &error))?;
        launch::create_suspended(job, handles, &application, &mut command_line, environment.as_deref(),
            stdin, stdout, stderr, permit)
            .and_then(launch::SuspendedOwner::resume)
            .map_err(|error| SysError::io("start managed process", program, &error))?
    } else {
        let mut command = Command::new(program);
        command
            .args(args)
            .stdin(child_stdin.map_or_else(Stdio::null, Stdio::from))
            .stdout(Stdio::from(stdout_child))
            .stderr(Stdio::from(stderr_child));
        if options.env_clear {
            command.env_clear();
        }
        for (key, value) in options.env {
            command.env(key, value);
        }
        let child = command
            .spawn()
            .map_err(|error| SysError::io("spawn process", program, &error))?;
        drop(command);
        ProcessOwner::new(child, stdin, stdout, stderr, permit)
    };
    let mut handoff = HandoffOwner(Some(owner));
    #[cfg(test)]
    {
        handoff.0.as_mut().expect("child owner").retirement_probe =
            control.cancellation.probe.clone();
    }
    control.pid.store(
        handoff.0.as_ref().expect("child owner").child.id(),
        Ordering::Release,
    );
    let worker_control = Arc::clone(&control);
    let owner = handoff.0.take().expect("child owner before handoff");
    if let Err(mpsc::SendError((owner, _, _, _))) =
        sender.send((owner, worker_control, worker_program, options.limit))
    {
        let _ = retain_for_cleanup(owner);
        return Err(SysError::io(
            "handoff child supervisor",
            program,
            &std_io::Error::new(
                std_io::ErrorKind::BrokenPipe,
                "child supervisor stopped before handoff",
            ),
        )
        .into());
    }
    Ok(ProcessChild { lease })
}

#[cfg(all(test, not(feature = "no_index")))]
mod pending_tests {
    use super::*;
    use crate::packages::sys::{ProgramPolicy, SysConfig};
    use crate::{Engine, Scope};
    use std::path::PathBuf;
    use windows_sys::Win32::Foundation::WAIT_OBJECT_0;
    use windows_sys::Win32::System::Threading::{
        GetExitCodeProcess, OpenProcess, TerminateProcess, PROCESS_QUERY_LIMITED_INFORMATION,
        PROCESS_TERMINATE,
    };

    const RECORD_ENV: &str = "RHAI_WINDOWS_PENDING_UNIT_RECORD";
    const SYNCHRONIZE: u32 = 0x0010_0000;

    #[test]
    fn pending_fixture() {
        let Ok(record) = std::env::var(RECORD_ENV) else {
            return;
        };
        let path = std::path::Path::new(&record);
        let temporary = path.with_extension("tmp");
        std::fs::write(&temporary, format!("{}", std::process::id())).unwrap();
        std::fs::rename(temporary, path).unwrap();
        let deadline = Instant::now() + Duration::from_secs(30);
        while Instant::now() < deadline {
            thread::sleep(Duration::from_millis(20));
        }
        panic!("pending fixture exceeded its safety deadline");
    }

    struct ExactChild(HANDLE, Arc<AtomicBool>);
    impl Drop for ExactChild {
        fn drop(&mut self) {
            // SAFETY: the guard owns the exact child handle until it closes it.
            unsafe {
                if WaitForSingleObject(self.0, 0) != WAIT_OBJECT_0 {
                    if TerminateProcess(self.0, 1) == 0 {
                        eprintln!(
                            "failed to terminate exact pending fixture: {}",
                            std_io::Error::last_os_error()
                        );
                    }
                }
                if WaitForSingleObject(self.0, 10_000) == WAIT_OBJECT_0 {
                    self.1.store(true, Ordering::Release);
                } else {
                    eprintln!(
                        "exact pending fixture exit was not confirmed; preserving its directory"
                    );
                }
                CloseHandle(self.0);
            }
        }
    }
    struct ReleaseProbe(Arc<PendingProbe>);
    impl Drop for ReleaseProbe {
        fn drop(&mut self) {
            let mut state = self.0.state.lock().unwrap_or_else(|p| p.into_inner());
            state.released = true;
            self.0.changed.notify_all();
        }
    }
    struct RemoveDir(PathBuf, Arc<AtomicBool>);
    impl Drop for RemoveDir {
        fn drop(&mut self) {
            if self.1.load(Ordering::Acquire) {
                if let Err(error) = std::fs::remove_dir_all(&self.0) {
                    eprintln!("failed to remove owned pending fixture directory: {error}");
                }
            } else {
                eprintln!(
                    "preserved pending fixture directory {} until exact child exit is confirmed",
                    self.0.display()
                );
            }
        }
    }

    #[test]
    fn public_kill_cancels_an_observed_pending_stdin_write() {
        let nonce = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root =
            std::env::temp_dir().join(format!("rhai-win-pending-{}-{nonce}", std::process::id()));
        std::fs::create_dir(&root).unwrap();
        let exit_confirmed = Arc::new(AtomicBool::new(false));
        let _directory = RemoveDir(root.clone(), Arc::clone(&exit_confirmed));
        let record = root.join("child.pid");
        let probe = Arc::new(PendingProbe::default());
        if std::env::var_os("RHAI_WINDOWS_PENDING_SKIP_CANCEL").is_some() {
            probe.skip_cancellation.store(true, Ordering::Release);
        }
        let gate = ReleaseProbe(Arc::clone(&probe));
        let config = SysConfig::default().programs(ProgramPolicy::Any);
        let fs = crate::packages::sys::fs::FsState::open(&config.fs).unwrap();
        let state = Shared::new(SysState { config, fs });
        let mut module = Module::new();
        register(&mut module, &state);
        let state_for_spawn = state.clone();
        let probe_for_spawn = Arc::clone(&probe);
        crate::packages::sys::reg(
            "spawn",
            &["/// Spawn a child with test-only pending observation."],
        )
        .set_into_module(
            &mut module,
            move |ctx: NativeCallContext,
                  program: &str,
                  args: Array,
                  options: Map|
                  -> Res<ProcessChild> {
                spawn_inner(
                    &ctx,
                    &state_for_spawn,
                    program,
                    parse_args(args)?,
                    options,
                    Some(Arc::clone(&probe_for_spawn)),
                )
            },
        );
        module.build_index();
        let mut engine = Engine::new();
        #[cfg(not(feature = "unchecked"))]
        engine.set_max_array_size(2_097_152);
        engine.register_global_module(module.into());
        let executable = std::env::current_exe()
            .unwrap()
            .to_string_lossy()
            .replace('\\', "\\\\")
            .replace('"', "\\\"");
        let record_literal = record
            .to_string_lossy()
            .replace('\\', "\\\\")
            .replace('"', "\\\"");
        let mut scope = Scope::new();
        scope.push("input", vec![0x5au8; 1_048_576]);
        let script = format!(
            r#"spawn("{executable}", ["--exact", "packages::sys::process::windows::child::pending_tests::pending_fixture", "--nocapture", "--quiet"], #{{env_clear: true, env: #{{ {RECORD_ENV}: "{record_literal}" }}, stdin: input, max_output: 1024}})"#
        );
        let child = engine
            .eval_with_scope::<Dynamic>(&mut scope, &script)
            .expect("public spawn returned a child");
        let control = child
            .clone()
            .try_cast::<ProcessChild>()
            .expect("public child type")
            .lease
            .control
            .clone();
        scope.push_dynamic("child", child);
        let deadline = Instant::now() + Duration::from_secs(10);
        let pid = loop {
            match std::fs::read_to_string(&record) {
                Ok(value) => break value.trim().parse::<u32>().unwrap(),
                Err(error)
                    if error.kind() == std_io::ErrorKind::NotFound && Instant::now() < deadline =>
                {
                    thread::sleep(Duration::from_millis(10))
                }
                Err(error) => panic!("pending fixture readiness: {error}"),
            }
        };
        // SAFETY: the record was written by the gated live fixture; open an exact process handle.
        let raw = unsafe {
            OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE | SYNCHRONIZE,
                0,
                pid,
            )
        };
        assert!(
            !raw.is_null(),
            "open exact pending fixture: {}",
            std_io::Error::last_os_error()
        );
        let exact = ExactChild(raw, Arc::clone(&exit_confirmed));
        let mut observed = probe.state.lock().unwrap_or_else(|p| p.into_inner());
        while !observed.observed_unsignaled {
            let left = deadline.saturating_duration_since(Instant::now());
            assert!(
                !left.is_zero(),
                "kernel-pending stdin write was not observed"
            );
            observed = probe
                .changed
                .wait_timeout(observed, left)
                .unwrap_or_else(|p| p.into_inner())
                .0;
        }
        assert_eq!(
            unsafe { WaitForSingleObject(exact.0, 0) },
            WAIT_TIMEOUT,
            "exact child must still be live"
        );
        assert!(
            observed.parked && !observed.gate_timed_out,
            "worker must remain gated at the unsignaled write"
        );
        engine.run_with_scope(&mut scope, "child.kill();").unwrap();
        assert!(
            control.cancellation.requested(),
            "public kill must set the real cancellation request"
        );
        observed.released = true;
        probe.changed.notify_all();
        drop(observed);
        drop(gate);
        let mut observed = probe.state.lock().unwrap_or_else(|p| p.into_inner());
        let gate_deadline = Instant::now() + Duration::from_secs(10);
        while observed.parked {
            let left = gate_deadline.saturating_duration_since(Instant::now());
            assert!(!left.is_zero(), "pending worker did not leave its gate");
            observed = probe
                .changed
                .wait_timeout(observed, left)
                .unwrap_or_else(|p| p.into_inner())
                .0;
        }
        assert!(
            observed.observed_unsignaled
                && !observed.gate_timed_out
                && observed.kill_requested_at_release
                && observed.pending_at_release,
            "kill must coincide with an unsignaled pending write"
        );
        drop(observed);
        let result = engine.eval_with_scope::<Map>(&mut scope, "child.wait()");
        assert_eq!(
            unsafe { WaitForSingleObject(exact.0, 10_000) },
            WAIT_OBJECT_0,
            "exact child did not exit"
        );
        let mut exit = u32::MAX;
        assert_ne!(unsafe { GetExitCodeProcess(exact.0, &mut exit) }, 0);
        let mut observed = probe.state.lock().unwrap_or_else(|p| p.into_inner());
        let retirement_deadline = Instant::now() + Duration::from_secs(10);
        while !observed.owner_retired {
            let left = retirement_deadline.saturating_duration_since(Instant::now());
            assert!(!left.is_zero(), "exact pending owner did not retire");
            observed = probe
                .changed
                .wait_timeout(observed, left)
                .unwrap_or_else(|p| p.into_inner())
                .0;
        }
        if probe.skip_cancellation() {
            let error =
                result.expect_err("suppressed initial cancellation must report incomplete cleanup");
            let sys = match *error {
                crate::EvalAltResult::ErrorRuntime(value, _) => {
                    value.try_cast::<SysError>().expect("typed cleanup error")
                }
                other => panic!("unexpected incomplete-cleanup error: {other:?}"),
            };
            match sys {
                SysError::Process { report, .. } => {
                    assert!(report
                        .cleanup_diagnostics()
                        .iter()
                        .any(|d| d.operation() == "cancel stdin"));
                    assert!(report
                        .cleanup_diagnostics()
                        .iter()
                        .any(|d| d.operation() == "retain cleanup custody"));
                }
                other => panic!("expected process cleanup error, got {other:?}"),
            }
            assert!(!observed.cancellation_completed && observed.owner_retired);
            eprintln!("windows_pending_mutant_readback pid={pid} exit={exit} pending_at_kill=true incomplete_cleanup=true retained_owner_retired=true");
            panic!("deliberately suppressed initial pending write cancellation");
        }
        let result = result.expect("pending write cancellation must finish");
        assert_eq!(result["code"].as_int().unwrap() as u32, exit);
        assert!(
            observed.observed_unsignaled
                && !observed.gate_timed_out
                && observed.kill_requested_at_release
                && observed.pending_at_release
                && observed.cancellation_completed
                && observed.owner_retired,
            "pending, completion and owner-retirement proof must all be present"
        );
        eprintln!("windows_pending_public_kill_readback pid={pid} exit={exit} pending_unsignaled=true cancellation_complete=true owner_retired=true");
        if std::env::var_os("RHAI_WINDOWS_PENDING_WRONG_EXPECTATION").is_some() {
            assert!(
                !observed.cancellation_completed,
                "deliberately wrong pending cancellation completion expectation"
            );
        }
    }
}
