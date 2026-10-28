//! Shared Windows Child handles, backed by an independently running supervisor.

use super::*;
use std::sync::atomic::{AtomicBool, AtomicU32};
use std::sync::{mpsc, Condvar};
use windows_sys::Win32::Foundation::CloseHandle;
use windows_sys::Win32::System::Threading::{CreateEventW, SetEvent};

pub(super) struct Cancellation {
    event: usize,
    requested: AtomicBool,
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
        })
    }
    pub(super) fn handle(&self) -> HANDLE {
        self.event as HANDLE
    }
    pub(super) fn requested(&self) -> bool {
        self.requested.load(Ordering::Acquire)
    }
    fn request(&self) {
        self.requested.store(true, Ordering::Release);
        // SAFETY: the Arc owning this event outlives this call and the supervisor wait.
        unsafe {
            SetEvent(self.handle());
        }
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
    if !state.config.programs.allows(program) {
        return Err(SysError::Denied(format!("program `{program}` is not allowed")).into());
    }
    if state.config.process_scope == ProcessScope::Managed {
        return Err(
            SysError::Denied("Windows managed process scope is not yet supported".into()).into(),
        );
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
    let options = parse_options(state, options, engine_limit)?;
    let permit = ActivePermit::acquire()?;
    let cancellation = Cancellation::new()
        .map_err(|error| SysError::io("create child cancellation event", program, &error))?;
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
    let (stdin, child_stdin) = match options.stdin {
        Some(input) if !input.is_empty() => {
            let (writer, child) = PipeWriter::pair(input)
                .map_err(|error| SysError::io("create stdin pipe", program, &error))?;
            (Some(writer), Stdio::from(child))
        }
        _ => (None, Stdio::null()),
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
            }
            *control.result.lock().unwrap_or_else(|p| p.into_inner()) = Some(result);
            control.changed.notify_all();
        })
        .map_err(|error| SysError::io("start child supervisor", program, &error))?;
    let mut command = Command::new(program);
    command
        .args(args)
        .stdin(child_stdin)
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
    let mut handoff = HandoffOwner(Some(ProcessOwner::new(
        child, stdin, stdout, stderr, permit,
    )));
    drop(command);
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
