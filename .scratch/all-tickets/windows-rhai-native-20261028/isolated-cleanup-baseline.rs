//! Native Windows process execution with cancellable, bounded output capture.

mod io;
mod stdin;
mod child;

pub use child::ProcessChild;

use self::io::PipeReader;
use self::stdin::PipeWriter;
use super::{ProcessCause, ProcessDiagnostic, ProcessExit, ProcessReport};
use crate::packages::sys::{ProcessScope, SysError, SysState};
#[cfg(not(feature = "no_index"))]
use crate::Array;
use crate::{Dynamic, ImmutableString, Map, Module, NativeCallContext, Shared, INT};
use std::io as std_io;
use std::os::windows::io::AsRawHandle;
use std::panic::{catch_unwind, resume_unwind, AssertUnwindSafe};
use std::process::{Child, Command, ExitStatus, Stdio};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, OnceLock};
use std::thread;
use std::time::{Duration, Instant};
use windows_sys::Win32::Foundation::{HANDLE, WAIT_FAILED, WAIT_OBJECT_0, WAIT_TIMEOUT};
use windows_sys::Win32::System::Threading::{WaitForMultipleObjects, WaitForSingleObject};

type Res<T> = Result<T, Box<crate::EvalAltResult>>;
const MAX_OWNED_WINDOWS_PROCESSES: usize = 64;
static ACTIVE_WINDOWS_PROCESSES: AtomicUsize = AtomicUsize::new(0);

struct ActivePermit;

impl ActivePermit {
    fn acquire() -> Res<Self> {
        ACTIVE_WINDOWS_PROCESSES
            .fetch_update(Ordering::AcqRel, Ordering::Acquire, |active| {
                (active < MAX_OWNED_WINDOWS_PROCESSES).then_some(active + 1)
            })
            .map_err(|_| {
                SysError::Denied(format!(
                    "Windows process owner capacity of {MAX_OWNED_WINDOWS_PROCESSES} is full"
                ))
            })?;
        Ok(Self)
    }
}

impl Drop for ActivePermit {
    fn drop(&mut self) {
        ACTIVE_WINDOWS_PROCESSES.fetch_sub(1, Ordering::AcqRel);
    }
}

pub(super) fn register(module: &mut Module, state: &Shared<SysState>) {
    child::register(module, state);
    let st = state.clone();
    crate::packages::sys::reg(
        "run",
        &["/// Run a child program and return lossy UTF-8 stdout and stderr."],
    )
    .set_into_module(
        module,
        move |ctx: NativeCallContext, program: &str| -> Res<Map> {
            run_map(&ctx, &st, program, Vec::new(), Map::new(), false)
        },
    );
    let st = state.clone();
    crate::packages::sys::reg("run", &["/// Run a child program with options."]).set_into_module(
        module,
        move |ctx: NativeCallContext, program: &str, options: Map| -> Res<Map> {
            run_map(&ctx, &st, program, Vec::new(), options, false)
        },
    );
    #[cfg(not(feature = "no_index"))]
    {
        let st = state.clone();
        crate::packages::sys::reg("run", &["/// Run a child program with arguments."])
            .set_into_module(
                module,
                move |ctx: NativeCallContext, program: &str, args: Array| -> Res<Map> {
                    run_map(&ctx, &st, program, parse_args(args)?, Map::new(), false)
                },
            );
        let st = state.clone();
        crate::packages::sys::reg(
            "run",
            &["/// Run a child program with arguments and options."],
        )
        .set_into_module(
            module,
            move |ctx: NativeCallContext, program: &str, args: Array, options: Map| -> Res<Map> {
                run_map(&ctx, &st, program, parse_args(args)?, options, false)
            },
        );
        let st = state.clone();
        crate::packages::sys::reg(
            "run_raw",
            &["/// Run a program and capture raw output bytes."],
        )
        .set_into_module(
            module,
            move |ctx: NativeCallContext, program: &str| -> Res<Map> {
                run_map(&ctx, &st, program, Vec::new(), Map::new(), true)
            },
        );
        let st = state.clone();
        crate::packages::sys::reg(
            "run_raw",
            &["/// Run a program with options and capture raw output bytes."],
        )
        .set_into_module(
            module,
            move |ctx: NativeCallContext, program: &str, options: Map| -> Res<Map> {
                run_map(&ctx, &st, program, Vec::new(), options, true)
            },
        );
        let st = state.clone();
        crate::packages::sys::reg(
            "run_raw",
            &["/// Run a program with arguments and capture raw output bytes."],
        )
        .set_into_module(
            module,
            move |ctx: NativeCallContext, program: &str, args: Array| -> Res<Map> {
                run_map(&ctx, &st, program, parse_args(args)?, Map::new(), true)
            },
        );
        let st = state.clone();
        crate::packages::sys::reg(
            "run_raw",
            &["/// Run a program and capture raw output bytes."],
        )
        .set_into_module(
            module,
            move |ctx: NativeCallContext, program: &str, args: Array, options: Map| -> Res<Map> {
                run_map(&ctx, &st, program, parse_args(args)?, options, true)
            },
        );
    }
}

#[cfg(not(feature = "no_index"))]
fn parse_args(args: Array) -> Res<Vec<String>> {
    args.into_iter()
        .map(|arg| {
            arg.try_cast::<ImmutableString>()
                .map(|text| text.to_string())
                .ok_or_else(|| SysError::Denied("process arguments must be strings".into()).into())
        })
        .collect()
}

struct Options {
    env: Vec<(String, String)>,
    env_clear: bool,
    stdin: Option<Vec<u8>>,
    timeout: Option<Duration>,
    limit: usize,
}

fn deadline_after(
    started: Instant,
    timeout: Option<Duration>,
) -> Result<Option<Instant>, SysError> {
    timeout
        .map(|duration| {
            started
                .checked_add(duration)
                .ok_or_else(|| SysError::Denied("process timeout is out of range".into()))
        })
        .transpose()
}

fn parse_options(state: &SysState, mut options: Map, engine_limit: usize) -> Res<Options> {
    for key in options.keys() {
        if !["env", "env_clear", "stdin", "timeout", "max_output"].contains(&key.as_str()) {
            return Err(
                SysError::Denied(format!("unsupported Windows process option `{key}`")).into(),
            );
        }
    }
    let env_clear = match options.remove("env_clear") {
        None => false,
        Some(value) => value
            .try_cast::<bool>()
            .ok_or_else(|| SysError::Denied("process option `env_clear` must be a bool".into()))?,
    };
    let env = match options.remove("env") {
        None => Vec::new(),
        Some(value) => value
            .try_cast::<Map>()
            .ok_or_else(|| SysError::Denied("process option `env` must be a map".into()))?
            .into_iter()
            .map(|(key, value)| {
                value
                    .try_cast::<ImmutableString>()
                    .map(|text| (key.to_string(), text.to_string()))
                    .ok_or_else(|| {
                        SysError::Denied("environment values must be strings".into()).into()
                    })
            })
            .collect::<Res<Vec<_>>>()?,
    };
    let stdin = match options.remove("stdin") {
        None => None,
        Some(value) if value.is_unit() => None,
        Some(value) => Some(parse_stdin(value)?),
    };
    let timeout = match options.remove("timeout") {
        None => state.config.default_timeout,
        Some(value) if value.is_unit() => None,
        Some(value) => Some(
            value
                .clone()
                .try_cast::<INT>()
                .map(|n| n as f64)
                .or_else(|| {
                    #[cfg(not(feature = "no_float"))]
                    {
                        value.try_cast::<crate::FLOAT>().map(|n| n as f64)
                    }
                    #[cfg(feature = "no_float")]
                    {
                        None
                    }
                })
                .ok_or_else(|| {
                    SysError::Denied("process option `timeout` must be numeric".into())
                })?,
        ),
    }
    .map(|seconds| {
        if !seconds.is_finite() || seconds < 0.0 {
            return Err(SysError::Denied(
                "process timeout must be finite and non-negative".into(),
            ));
        }
        Duration::try_from_secs_f64(seconds)
            .map_err(|_| SysError::Denied("process timeout is out of range".into()))
    })
    .transpose()?;
    let requested = options
        .remove("max_output")
        .map(|value| {
            value
                .try_cast::<INT>()
                .ok_or_else(|| {
                    SysError::Denied(
                        "process option `max_output` must be a non-negative integer".into(),
                    )
                })
                .and_then(|n| {
                    usize::try_from(n)
                        .map_err(|_| SysError::Denied("max_output must be non-negative".into()))
                })
        })
        .transpose()?
        .unwrap_or(state.config.max_output);
    let limit = requested.min(state.config.max_output);
    let limit = if engine_limit == 0 {
        limit
    } else {
        limit.min(engine_limit)
    };
    Ok(Options {
        env,
        env_clear,
        stdin,
        timeout,
        limit,
    })
}

fn parse_stdin(value: Dynamic) -> Res<Vec<u8>> {
    #[cfg(not(feature = "no_index"))]
    let value = match value.try_cast_result::<crate::Blob>() {
        Ok(bytes) => return Ok(bytes),
        Err(value) => value,
    };
    value
        .try_cast::<ImmutableString>()
        .map(|text| text.as_bytes().to_vec())
        .ok_or_else(|| {
            let expected = if cfg!(feature = "no_index") {
                "a string"
            } else {
                "a string or blob"
            };
            SysError::Denied(format!("process option `stdin` must be {expected}")).into()
        })
}

fn run_map(
    ctx: &NativeCallContext,
    state: &Shared<SysState>,
    program: &str,
    args: Vec<String>,
    options: Map,
    raw: bool,
) -> Res<Map> {
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
    #[cfg(not(feature = "unchecked"))]
    let engine_limit = if raw {
        ctx.engine().max_array_size()
    } else {
        ctx.engine().max_string_size()
    };
    #[cfg(feature = "unchecked")]
    let engine_limit = {
        let _ = ctx;
        0
    };
    let options = parse_options(state, options, engine_limit)?;
    let permit = ActivePermit::acquire()?;
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
    let deadline = deadline_after(Instant::now(), options.timeout)?;
    let child = command
        .spawn()
        .map_err(|error| SysError::io("spawn process", program, &error))?;
    drop(command);
    let mut owner = ProcessOwner::new(child, stdin, stdout, stderr, permit);
    let supervised = catch_unwind(AssertUnwindSafe(|| {
        owner.supervise(deadline, options.limit, program, None)
    }));
    let supervised = match supervised {
        Ok(result) => result,
        Err(panic) => {
            let _ = retain_for_cleanup(owner);
            resume_unwind(panic);
        }
    };
    if owner.has_pending_cleanup() {
        let _ = retain_for_cleanup(owner);
    }
    let report = match supervised {
        Ok(report) => report,
        Err((cause, report)) => return Err(SysError::Process { cause, report }.into()),
    };
    if !raw && engine_limit > 0 {
        if report.stdout().len() > engine_limit || report.stderr().len() > engine_limit {
            return Err(SysError::Process {
                cause: ProcessCause::OutputLimit(format!(
                    "decoded process output exceeded the engine string limit of {engine_limit} bytes"
                )),
                report,
            }
            .into());
        }
    }
    let mut result = Map::new();
    result.insert(
        "success".into(),
        Dynamic::from(report.exit_code() == Some(0)),
    );
    result.insert(
        "code".into(),
        report
            .exit_code()
            .map(|n| Dynamic::from_int(n as INT))
            .unwrap_or(Dynamic::UNIT),
    );
    result.insert("signal".into(), Dynamic::UNIT);
    result.insert("timed_out".into(), Dynamic::from(report.timed_out()));
    result.insert(
        "stdout_complete".into(),
        Dynamic::from(report.stdout_complete()),
    );
    result.insert(
        "stderr_complete".into(),
        Dynamic::from(report.stderr_complete()),
    );
    result.insert(
        "stdout".into(),
        if raw {
            Dynamic::from(report.stdout_bytes().to_vec())
        } else {
            Dynamic::from(ImmutableString::from(report.stdout()))
        },
    );
    result.insert(
        "stderr".into(),
        if raw {
            Dynamic::from(report.stderr_bytes().to_vec())
        } else {
            Dynamic::from(ImmutableString::from(report.stderr()))
        },
    );
    Ok(result)
}

struct ProcessOwner {
    _permit: ActivePermit,
    child: Child,
    stdin: Option<PipeWriter>,
    stdout: PipeReader,
    stderr: PipeReader,
    out: Vec<u8>,
    err: Vec<u8>,
    exit: Option<ExitStatus>,
    diagnostics: Vec<ProcessDiagnostic>,
    #[cfg(test)]
    retirement_probe: Option<Arc<child::PendingProbe>>,
    #[cfg(test)]
    retirement_panic_probe: Option<Arc<std::sync::atomic::AtomicBool>>,
}

type RetainedOwner = Arc<Mutex<Option<ProcessOwner>>>;
static RETAINED_CLEANUP: OnceLock<Mutex<Vec<RetainedOwner>>> = OnceLock::new();

fn retained_registry() -> &'static Mutex<Vec<RetainedOwner>> {
    RETAINED_CLEANUP.get_or_init(|| Mutex::new(Vec::new()))
}

fn retain_for_cleanup(owner: ProcessOwner) -> std_io::Result<()> {
    retain_for_cleanup_inner(owner).map(|_| ())
}

fn retain_for_cleanup_inner(owner: ProcessOwner) -> std_io::Result<RetainedOwner> {
    let cell = Arc::new(Mutex::new(Some(owner)));
    retained_registry()
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
        .push(Arc::clone(&cell));
    // The registry holds the owner even if thread creation fails. Once started, the worker
    // exclusively owns it until both child and pending I/O reach observed completion.
    let worker_cell = Arc::clone(&cell);
    thread::Builder::new()
        .name("rhai-windows-process-cleanup".into())
        .spawn(move || {
            let mut owner = worker_cell
                .lock()
                .unwrap_or_else(|poisoned| poisoned.into_inner())
                .take()
                .expect("retained cleanup owner missing");
            #[cfg(test)]
            let probe = owner.retirement_probe.clone();
            owner.finish_in_background();
            #[cfg(test)]
            {
                drop(owner);
                if let Some(probe) = probe { probe.retired(); }
            }
            retained_registry()
                .lock()
                .unwrap_or_else(|poisoned| poisoned.into_inner())
                .retain(|entry| !Arc::ptr_eq(entry, &worker_cell));
        })
        .map(|_| cell)
}

impl ProcessOwner {
    fn new(
        child: Child,
        stdin: Option<PipeWriter>,
        stdout: PipeReader,
        stderr: PipeReader,
        permit: ActivePermit,
    ) -> Self {
        Self {
            _permit: permit,
            child,
            stdin,
            stdout,
            stderr,
            out: Vec::new(),
            err: Vec::new(),
            exit: None,
            diagnostics: Vec::new(),
            #[cfg(test)]
            retirement_probe: None,
            #[cfg(test)]
            retirement_panic_probe: None,
        }
    }

    fn supervise(
        &mut self,
        deadline: Option<Instant>,
        limit: usize,
        program: &str,
        cancellation: Option<&child::Cancellation>,
    ) -> Result<ProcessReport, (ProcessCause, ProcessReport)> {
        let mut cause = None;
        loop {
            if cause.is_some() {
                break;
            }
            if cancellation.is_some_and(child::Cancellation::requested) {
                if self.exit.is_none() {
                    match self.child.try_wait() {
                        Ok(Some(status)) => self.exit = Some(status),
                        Ok(None) => {
                            if let Err(error) = self.child.kill() {
                                // The child may have exited between the observation and kill.
                                match self.child.try_wait() {
                                    Ok(Some(status)) => self.exit = Some(status),
                                    _ => cause = Some(io_cause("kill child", program, &error)),
                                }
                            }
                        }
                        Err(error) => cause = Some(io_cause("observe child before kill", program, &error)),
                    }
                }
                // Stop submitting I/O immediately. Descendants may retain pipe handles
                // after the exact child exits, so cancellation must enter bounded cleanup.
                break;
            }
            if cause.is_none() {
                cause = observe_read_step(
                    &mut [
                        (&mut self.stdout, &mut self.out),
                        (&mut self.stderr, &mut self.err),
                    ],
                    limit,
                    deadline,
                    program,
                );
            }
            if cause.is_none() {
                if let Some(writer) = self.stdin.as_mut() {
                    if let Err(error) = advance_stdin(writer) {
                        cause = Some(io_cause("write child stdin", program, &error));
                    }
                    #[cfg(test)]
                    if let Some(control) = cancellation {
                        if let Some(probe) = control.probe() {
                            probe.observe_and_gate(writer, control);
                        }
                    }
                }
            }
            if self.stdin.as_ref().is_some_and(PipeWriter::is_finished) {
                self.stdin.take();
            }
            if cause.is_some()
                || (self.exit.is_some()
                    && self.stdin.is_none()
                    && self.stdout.reached_eof()
                    && self.stderr.reached_eof())
            {
                break;
            }
            // A synchronous read can leave its pipe ready for another read. Rearm it
            // before waiting on other handles so a full child pipe cannot stall us.
            if (!self.stdout.is_pending() && !self.stdout.reached_eof())
                || (!self.stderr.is_pending() && !self.stderr.reached_eof())
                || self
                    .stdin
                    .as_ref()
                    .is_some_and(|writer| !writer.is_pending() && !writer.is_finished())
            {
                continue;
            }
            let mut handles = Vec::with_capacity(4);
            if self.stdout.is_pending() {
                handles.push(self.stdout.event_handle());
            }
            if self.stderr.is_pending() {
                handles.push(self.stderr.event_handle());
            }
            if let Some(writer) = self.stdin.as_ref().filter(|writer| writer.is_pending()) {
                handles.push(writer.event_handle());
            }
            if self.exit.is_none() {
                handles.push(self.child.as_raw_handle() as HANDLE);
            }
            if let Some(control) = cancellation {
                handles.push(control.handle());
            }
            if handles.is_empty() {
                continue;
            }
            let wait_ms = deadline
                .map(|end| {
                    let left = end.saturating_duration_since(Instant::now());
                    if left.is_zero() {
                        0
                    } else {
                        left.as_millis().clamp(1, u32::MAX as u128) as u32
                    }
                })
                .unwrap_or(u32::MAX);
            // A failed SetEvent must not strand a cancellation request indefinitely.
            let wait_ms = if cancellation.is_some() { wait_ms.min(1_000) } else { wait_ms };
            // SAFETY: every waited handle remains owned and live across the wait.
            let wait = unsafe {
                WaitForMultipleObjects(handles.len() as u32, handles.as_ptr(), 0, wait_ms)
            };
            if wait == WAIT_TIMEOUT {
                continue;
            }
            if wait == WAIT_FAILED
                || wait < WAIT_OBJECT_0
                || wait >= WAIT_OBJECT_0 + handles.len() as u32
            {
                cause = Some(io_cause(
                    "wait for child output",
                    program,
                    &std_io::Error::last_os_error(),
                ));
                break;
            }
            let signaled = handles[(wait - WAIT_OBJECT_0) as usize];
            if self.stdout.is_pending() && signaled == self.stdout.event_handle() {
                match self.stdout.finish_read() {
                    Ok(bytes) => {
                        if append_bounded(&mut self.out, &bytes, limit) {
                            cause = Some(ProcessCause::OutputLimit(format!(
                                "stdout for `{program}` exceeded max_output of {limit} bytes"
                            )));
                        }
                    }
                    Err(error) => cause = Some(io_cause("read child stdout", program, &error)),
                }
            } else if self.stderr.is_pending() && signaled == self.stderr.event_handle() {
                match self.stderr.finish_read() {
                    Ok(bytes) => {
                        if append_bounded(&mut self.err, &bytes, limit) {
                            cause = Some(ProcessCause::OutputLimit(format!(
                                "stderr for `{program}` exceeded max_output of {limit} bytes"
                            )));
                        }
                    }
                    Err(error) => cause = Some(io_cause("read child stderr", program, &error)),
                }
            } else if self
                .stdin
                .as_ref()
                .is_some_and(|writer| writer.is_pending() && signaled == writer.event_handle())
            {
                if let Err(error) = self
                    .stdin
                    .as_mut()
                    .expect("pending stdin owner")
                    .finish_write()
                {
                    cause = Some(io_cause("write child stdin", program, &error));
                }
            } else if cancellation.is_some_and(|control| signaled == control.handle()) {
                continue;
            } else if self.exit.is_none() {
                match self.child.try_wait() {
                    Ok(status) => self.exit = status,
                    Err(error) => cause = Some(io_cause("wait for child", program, &error)),
                }
            }
        }
        if cause.is_some() && self.exit.is_none() {
            if let Err(error) = self.child.kill() {
                self.diagnostics.push(ProcessDiagnostic::new(
                    "kill",
                    Some(error.kind()),
                    error.to_string(),
                ));
            }
        }
        if let Some(writer) = self.stdin.as_mut() {
            #[cfg(not(test))]
            let outcome = writer.cancel_and_join_bounded(2_000);
            #[cfg(test)]
            let outcome = if cancellation.and_then(child::Cancellation::probe).is_some_and(child::PendingProbe::skip_cancellation) {
                stdin::CancelWrite { completed: false, errors: Vec::new() }
            } else {
                writer.cancel_and_join_bounded(2_000)
            };
            #[cfg(test)]
            if let Some(probe) = cancellation.and_then(child::Cancellation::probe) {
                probe.completed(outcome.completed && outcome.errors.is_empty());
            }
            if !outcome.completed {
                self.diagnostics.push(ProcessDiagnostic::new(
                    "cancel stdin",
                    Some(std_io::ErrorKind::TimedOut),
                    "overlapped stdin operation remains pending after cancellation",
                ));
            }
            for error in outcome.errors {
                self.diagnostics.push(ProcessDiagnostic::new(
                    "cancel stdin",
                    Some(error.kind()),
                    error.to_string(),
                ));
            }
            if outcome.completed {
                self.stdin.take();
            }
        }
        if self.exit.is_none() {
            // A failed termination request must never lead to an unbounded caller-side wait.
            // SAFETY: this owner holds the live child handle for this bounded OS wait.
            let wait = unsafe { WaitForSingleObject(self.child.as_raw_handle() as HANDLE, 10_000) };
            if wait == WAIT_OBJECT_0 {
                match self.child.wait() {
                    Ok(status) => self.exit = Some(status),
                    Err(error) => self.diagnostics.push(ProcessDiagnostic::new(
                        "reap",
                        Some(error.kind()),
                        error.to_string(),
                    )),
                }
            } else {
                self.diagnostics.push(ProcessDiagnostic::new(
                    "wait for child cleanup",
                    Some(if wait == WAIT_TIMEOUT {
                        std_io::ErrorKind::TimedOut
                    } else {
                        std_io::ErrorKind::Other
                    }),
                    format!("exact child handle did not signal: wait={wait:#x}"),
                ));
            }
        }
        for (name, reader, output) in [
            ("cancel stdout", &mut self.stdout, &mut self.out),
            ("cancel stderr", &mut self.stderr, &mut self.err),
        ] {
            let outcome = reader.cancel_and_join_bounded(2_000);
            if append_bounded(output, &outcome.bytes, limit) {
                cause.get_or_insert_with(|| {
                    ProcessCause::OutputLimit(format!(
                        "output for `{program}` exceeded max_output of {limit} bytes"
                    ))
                });
            }
            if !outcome.completed {
                self.diagnostics.push(ProcessDiagnostic::new(
                    name,
                    Some(std_io::ErrorKind::TimedOut),
                    "overlapped operation remains pending after cancellation",
                ));
            }
            for error in outcome.errors {
                self.diagnostics.push(ProcessDiagnostic::new(
                    name,
                    Some(error.kind()),
                    error.to_string(),
                ));
            }
        }
        let owned_work_pending = self.has_pending_cleanup();
        if owned_work_pending {
            self.diagnostics.push(ProcessDiagnostic::new(
                "retain cleanup custody",
                None,
                "child or overlapped operation remains active; cleanup service retains ownership",
            ));
            let report = self.snapshot(false);
            let primary = cause.unwrap_or_else(|| ProcessCause::Io {
                op: "complete process cleanup",
                target: program.into(),
                kind: std_io::ErrorKind::Other,
                message: "native cleanup remains incomplete".into(),
            });
            return Err((primary, report));
        }
        let cleanup_verified = self.diagnostics.is_empty();
        let timed_out =
            cleanup_verified && matches!(cause.as_ref(), Some(ProcessCause::Timeout(_)));
        let report = self.snapshot(timed_out);
        match (cause, cleanup_verified) {
            (Some(cause), _) => Err((cause, report)),
            (None, true) => Ok(report),
            (None, false) => Err((
                ProcessCause::Io {
                    op: "complete process cleanup",
                    target: program.into(),
                    kind: std_io::ErrorKind::Other,
                    message: "native cleanup produced diagnostics".into(),
                },
                report,
            )),
        }
    }

    fn snapshot(&self, timed_out: bool) -> ProcessReport {
        ProcessReport::new(
            self.out.clone(),
            self.err.clone(),
            self.stdout.reached_eof(),
            self.stderr.reached_eof(),
            self.exit
                .as_ref()
                .and_then(ExitStatus::code)
                .map(ProcessExit::Code),
            timed_out,
            self.diagnostics.clone(),
        )
    }

    fn has_pending_cleanup(&self) -> bool {
        self.exit.is_none()
            || self.stdout.is_pending()
            || self.stderr.is_pending()
            || self.stdin.as_ref().is_some_and(PipeWriter::is_pending)
    }

    fn finish_in_background(&mut self) {
        #[cfg(test)]
        if self.retirement_panic_probe.as_ref().is_some_and(|probe| {
            !probe.swap(true, Ordering::AcqRel)
        }) {
            panic!("deliberate per-owner cleanup panic");
        }
        while self.exit.is_none() {
            if let Ok(Some(status)) = self.child.try_wait() {
                self.exit = Some(status);
                break;
            }
            let _ = self.child.kill();
            // SAFETY: this worker retains the exact process handle and uses its signal, not an
            // elapsed sleep, as evidence that waiting and reaping may proceed.
            let wait = unsafe { WaitForSingleObject(self.child.as_raw_handle() as HANDLE, 1_000) };
            if wait == WAIT_OBJECT_0 {
                if let Ok(status) = self.child.wait() {
                    self.exit = Some(status);
                }
            }
        }
        while self.stdout.is_pending()
            || self.stderr.is_pending()
            || self.stdin.as_ref().is_some_and(PipeWriter::is_pending)
        {
            if let Some(writer) = self.stdin.as_mut().filter(|writer| writer.is_pending()) {
                let _ = writer.cancel_and_join_bounded(1_000);
            }
            if self.stdout.is_pending() {
                let _ = self.stdout.cancel_and_join_bounded(1_000);
            }
            if self.stderr.is_pending() {
                let _ = self.stderr.cancel_and_join_bounded(1_000);
            }
        }
    }
}

fn advance_stdin(writer: &mut PipeWriter) -> std_io::Result<()> {
    if !writer.is_pending() && !writer.is_finished() {
        writer.start_write()?;
    }
    if writer.is_pending() {
        // SAFETY: the writer owns its live event for this nonblocking observation.
        let wait = unsafe { WaitForSingleObject(writer.event_handle(), 0) };
        if wait == WAIT_OBJECT_0 {
            writer.finish_write()?;
        } else if wait != WAIT_TIMEOUT {
            return Err(if wait == WAIT_FAILED {
                std_io::Error::last_os_error()
            } else {
                std_io::Error::new(
                    std_io::ErrorKind::Other,
                    format!("unexpected stdin event wait: {wait:#x}"),
                )
            });
        }
    }
    Ok(())
}

fn append_bounded(output: &mut Vec<u8>, bytes: &[u8], limit: usize) -> bool {
    let space = limit.saturating_sub(output.len());
    output.extend_from_slice(&bytes[..bytes.len().min(space)]);
    bytes.len() > space
}

/// Observe each ready read before committing an expired deadline, so overflow visible
/// in the same step wins. A cause committed by an earlier step is never passed here.
fn observe_read_step(
    streams: &mut [(&mut PipeReader, &mut Vec<u8>)],
    limit: usize,
    deadline: Option<Instant>,
    program: &str,
) -> Option<ProcessCause> {
    let mut overflow = false;
    let mut read_error = None;
    for (reader, output) in streams {
        if !reader.is_pending() && !reader.reached_eof() {
            match reader.start_read() {
                Ok(Some(bytes)) => overflow |= append_bounded(output, &bytes, limit),
                Ok(None) => {}
                Err(error) => {
                    read_error
                        .get_or_insert_with(|| io_cause("read child output", program, &error));
                }
            }
        }
        if reader.is_pending() {
            // SAFETY: the reader owns its live event for this nonblocking observation.
            let wait = unsafe { WaitForSingleObject(reader.event_handle(), 0) };
            if wait == WAIT_OBJECT_0 {
                match reader.finish_read() {
                    Ok(bytes) => overflow |= append_bounded(output, &bytes, limit),
                    Err(error) => {
                        read_error
                            .get_or_insert_with(|| io_cause("read child output", program, &error));
                    }
                }
            } else if wait != WAIT_TIMEOUT {
                let error = if wait == WAIT_FAILED {
                    std_io::Error::last_os_error()
                } else {
                    std_io::Error::new(
                        std_io::ErrorKind::Other,
                        format!("unexpected pipe event wait: {wait:#x}"),
                    )
                };
                read_error.get_or_insert_with(|| io_cause("observe child output", program, &error));
            }
        }
    }
    if overflow {
        Some(ProcessCause::OutputLimit(format!(
            "output for `{program}` exceeded max_output of {limit} bytes"
        )))
    } else if read_error.is_some() {
        read_error
    } else if deadline.is_some_and(|end| Instant::now() >= end) {
        Some(ProcessCause::Timeout(format!(
            "process `{program}` exceeded its deadline"
        )))
    } else {
        None
    }
}

fn io_cause(op: &'static str, target: &str, error: &std_io::Error) -> ProcessCause {
    ProcessCause::Io {
        op,
        target: target.into(),
        kind: error.kind(),
        message: error.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs::File;
    use std::io::Write;
    use std::os::windows::io::{FromRawHandle, OwnedHandle, RawHandle};
    use windows_sys::Win32::Foundation::{DuplicateHandle, DUPLICATE_SAME_ACCESS};
    use windows_sys::Win32::System::Threading::{GetCurrentProcess, TerminateProcess};

    #[test]
    fn windows_cleanup_panic_fixture() {
        let Some(root) = std::env::var_os("RHAI_WINDOWS_CLEANUP_PANIC_FIXTURE") else { return; };
        let root = std::path::Path::new(&root);
        std::fs::write(root.join("ready"), format!("{}\n", std::process::id())).unwrap();
        let deadline = Instant::now() + Duration::from_secs(20);
        while Instant::now() < deadline {
            if root.join("release").exists() { return; }
            thread::sleep(Duration::from_millis(10));
        }
        panic!("cleanup panic fixture was not released");
    }

    struct CleanupFixtureGuard {
        handle: Option<OwnedHandle>,
        root: std::path::PathBuf,
    }

    struct PendingFixtureSpawn {
        child: Option<Child>,
        root: std::path::PathBuf,
    }

    impl Drop for PendingFixtureSpawn {
        fn drop(&mut self) {
            let Some(mut child) = self.child.take() else { return; };
            let raw = child.as_raw_handle() as HANDLE;
            // SAFETY: the exact child remains owned through bounded termination.
            if unsafe { WaitForSingleObject(raw, 0) } != WAIT_OBJECT_0 { let _ = child.kill(); }
            if unsafe { WaitForSingleObject(raw, 10_000) } == WAIT_OBJECT_0 {
                let _ = child.wait();
                let _ = std::fs::remove_dir_all(&self.root);
            } else {
                eprintln!("unconfirmed cleanup fixture spawn; preserve exact handle and root");
                std::mem::forget(child);
            }
        }
    }

    impl Drop for CleanupFixtureGuard {
        fn drop(&mut self) {
            let Some(handle) = self.handle.take() else { return; };
            let raw = handle.as_raw_handle() as HANDLE;
            // SAFETY: this guard owns the exact duplicated child handle.
            if unsafe { WaitForSingleObject(raw, 0) } != WAIT_OBJECT_0 {
                unsafe { TerminateProcess(raw, 1); }
            }
            if unsafe { WaitForSingleObject(raw, 10_000) } == WAIT_OBJECT_0 {
                let _ = std::fs::remove_dir_all(&self.root);
            } else {
                eprintln!("cleanup panic fixture exit unconfirmed; preserve exact handle and root");
                std::mem::forget(handle);
            }
        }
    }

    #[test]
    fn windows_cleanup_panic_preserves_exact_owner_and_permit() {
        let nonce = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos();
        let root = std::env::temp_dir().join(format!("rhai-cleanup-panic-{}-{nonce}", std::process::id()));
        std::fs::create_dir(&root).unwrap();
        let child = Command::new(std::env::current_exe().unwrap())
            .args(["--exact", "packages::sys::process::windows::tests::windows_cleanup_panic_fixture", "--nocapture", "--quiet"])
            .env_clear().env("RHAI_WINDOWS_CLEANUP_PANIC_FIXTURE", &root)
            .stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null())
            .spawn().expect("start gated cleanup panic fixture");
        let mut pending = PendingFixtureSpawn { child: Some(child), root: root.clone() };
        let child = pending.child.as_ref().unwrap();
        let pid = child.id();
        let mut duplicate = std::ptr::null_mut();
        // SAFETY: child owns the original live handle; the duplicate is independently owned.
        assert_ne!(unsafe { DuplicateHandle(GetCurrentProcess(), child.as_raw_handle() as HANDLE,
            GetCurrentProcess(), &mut duplicate, 0, 0, DUPLICATE_SAME_ACCESS) }, 0);
        let exact = unsafe { OwnedHandle::from_raw_handle(duplicate as RawHandle) };
        let guard = CleanupFixtureGuard { handle: Some(exact), root: root.clone() };
        let child = pending.child.take().unwrap();
        drop(pending);
        let deadline = Instant::now() + Duration::from_secs(5);
        loop {
            match std::fs::read_to_string(root.join("ready")) {
                Ok(value) => { assert_eq!(value.trim().parse::<u32>().unwrap(), pid); break; }
                Err(error) if error.kind() == std_io::ErrorKind::NotFound && Instant::now() < deadline => thread::sleep(Duration::from_millis(10)),
                Err(error) => panic!("cleanup fixture readiness: {error}"),
            }
        }
        assert_eq!(unsafe { WaitForSingleObject(guard.handle.as_ref().unwrap().as_raw_handle() as HANDLE, 0) }, WAIT_TIMEOUT);
        let (stdout, stdout_writer) = PipeReader::pair().unwrap();
        let (stderr, stderr_writer) = PipeReader::pair().unwrap();
        drop(stdout_writer); drop(stderr_writer);
        let probe = Arc::new(std::sync::atomic::AtomicBool::new(false));
        let mut owner = ProcessOwner::new(child, None, stdout, stderr, ActivePermit::acquire().unwrap());
        owner.retirement_panic_probe = Some(Arc::clone(&probe));
        let cell = retain_for_cleanup_inner(owner).expect("start cleanup worker");
        let deadline = Instant::now() + Duration::from_secs(3);
        while !probe.load(Ordering::Acquire) && Instant::now() < deadline { thread::sleep(Duration::from_millis(10)); }
        assert!(probe.load(Ordering::Acquire), "per-owner cleanup panic was not reached");
        let mut retained = None;
        while Instant::now() < deadline {
            {
                let registry = retained_registry().lock().unwrap_or_else(|p| p.into_inner());
                if registry.iter().any(|entry| Arc::ptr_eq(entry, &cell)) {
                    if let Some(owner) = cell.lock().unwrap_or_else(|p| p.into_inner()).take() {
                        retained = Some(owner);
                    }
                }
            }
            if retained.is_some() { break; }
            thread::sleep(Duration::from_millis(10));
        }
        let owner_was_retained = retained.is_some();
        assert!(owner_was_retained, "cleanup worker must preserve exact owner and permit after panic");
        let mut owner = retained.unwrap();
        assert_eq!(owner.child.id(), pid);
        assert_eq!(unsafe { WaitForSingleObject(guard.handle.as_ref().unwrap().as_raw_handle() as HANDLE, 0) }, WAIT_TIMEOUT);
        owner.child.kill().expect("terminate exact retained child");
        assert_eq!(unsafe { WaitForSingleObject(guard.handle.as_ref().unwrap().as_raw_handle() as HANDLE, 10_000) }, WAIT_OBJECT_0,
            "exact retained child did not terminate");
        owner.child.wait().expect("reap exact retained child");
        assert_eq!(unsafe { WaitForSingleObject(guard.handle.as_ref().unwrap().as_raw_handle() as HANDLE, 0) }, WAIT_OBJECT_0);
        retained_registry().lock().unwrap_or_else(|p| p.into_inner()).retain(|entry| !Arc::ptr_eq(entry, &cell));
        drop(owner);
        drop(guard);
        eprintln!("windows_cleanup_panic_readback exact_child_reaped=true owner_retained=true");
        if std::env::var_os("RHAI_WINDOWS_CLEANUP_PANIC_WRONG_EXPECTATION").is_some() {
            assert!(!owner_was_retained, "deliberately wrong cleanup custody expectation");
        }
    }

    #[test]
    fn windows_ready_overflow_wins_over_expired_deadline() {
        let (mut reader, writer) = PipeReader::pair().expect("create native pipe");
        assert!(reader.start_read().expect("start pending read").is_none());
        let mut writer = File::from(writer);
        writer.write_all(b"abcde").expect("write overflowing bytes");
        // SAFETY: reader owns its event for the bounded readiness wait.
        assert_eq!(
            unsafe { WaitForSingleObject(reader.event_handle(), 2_000) },
            WAIT_OBJECT_0
        );
        let mut captured = Vec::new();
        let cause = observe_read_step(
            &mut [(&mut reader, &mut captured)],
            3,
            Some(Instant::now()),
            "fixture",
        );
        if std::env::var_os("RHAI_WINDOWS_OVERLAP_WRONG_EXPECTATION").is_some() {
            assert!(
                matches!(cause, Some(ProcessCause::Timeout(_))),
                "deliberately wrong overlap expectation"
            );
        }
        assert!(
            matches!(cause, Some(ProcessCause::OutputLimit(_))),
            "overflow must win at an expired deadline: {cause:?}"
        );
        assert_eq!(captured, b"abc");
        assert!(!reader.is_pending());
    }

    #[test]
    fn windows_deadline_overflow_is_denied() {
        let near_limit = Instant::now()
            .checked_add(Duration::from_secs(u64::MAX / 2))
            .expect("first half of the Windows Instant range is representable");
        let result = deadline_after(near_limit, Some(Duration::from_secs(u64::MAX / 2 + 2)));
        if std::env::var_os("RHAI_WINDOWS_DEADLINE_WRONG_EXPECTATION").is_some() {
            assert!(
                result.is_ok(),
                "deliberately wrong deadline overflow expectation"
            );
        } else {
            assert!(matches!(result, Err(SysError::Denied(_))));
        }
    }
}
