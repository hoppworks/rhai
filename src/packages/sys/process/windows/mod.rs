//! Native Windows process execution with cancellable, bounded output capture.

#[allow(dead_code)]
mod attributes;
#[allow(dead_code)]
mod encoding;
mod io;
#[allow(dead_code)]
mod job;
#[allow(dead_code)]
mod launch;
#[allow(dead_code)]
mod members;
mod native_child;
#[allow(dead_code)]
mod resolve;
mod stdin;
mod child;

pub use child::ProcessChild;

use self::io::PipeReader;
use self::native_child::OwnedChild;
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

/// Prepare both run and spawn through the same Windows argument boundary.
/// A permitted batch file must use cmd.exe's quoting rules, while ordinary
/// executables retain the CRT argument encoding.
fn managed_input(
    program: &str,
    args: &[String],
    options: &Options,
) -> Res<(Vec<u16>, Vec<u16>, Option<Vec<u16>>)> {
    let resolved = resolve::resolve_program(program, options)
        .map_err(|error| SysError::io("resolve program", program, &error))?;
    // Resolution may select `name.cmd.exe` for a requested `name.cmd` path.
    // The interpreter choice follows the executable that will actually start.
    let batch = matches!(
        resolved.len().checked_sub(5).and_then(|start| resolved.get(start..)),
        Some([46, 98 | 66, 97 | 65, 116 | 84, 0] | [46, 99 | 67, 109 | 77, 100 | 68, 0])
    );
    let (application, command_line) = if batch {
        (
            resolve::command_prompt()
                .map_err(|error| SysError::io("resolve command prompt", program, &error))?,
            encoding::batch_command_line(&resolved, args)
                .map_err(|error| SysError::io("encode batch arguments", program, &error))?,
        )
    } else {
        (
            resolved,
            encoding::command_line(program, args)
                .map_err(|error| SysError::io("encode arguments", program, &error))?,
        )
    };
    let environment = encoding::environment(options)
        .map_err(|error| SysError::io("encode environment", program, &error))?;
    Ok((application, command_line, environment))
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
    env_remove: Vec<String>,
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
    #[allow(unused_mut)]
    let mut known = vec!["env", "env_clear", "stdin", "timeout", "max_output"];
    #[cfg(not(feature = "no_index"))]
    known.push("env_remove");
    for key in options.keys() {
        if !known.contains(&key.as_str()) {
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
    #[cfg(not(feature = "no_index"))]
    let env_remove = match options.remove("env_remove") {
        None => Vec::new(),
        Some(value) => value
            .try_cast::<Array>()
            .ok_or_else(|| SysError::Denied("process option `env_remove` must be an array".into()))?
            .into_iter()
            .map(|value| -> Res<String> {
                let text = value.try_cast::<ImmutableString>()
                    .ok_or_else(|| SysError::Denied("env_remove entries must be strings".into()))?;
                if text.is_empty() || text.contains(['\0', '=']) {
                    return Err(SysError::Denied("invalid env_remove key".into()).into());
                }
                Ok(text.to_string())
            })
            .collect::<Res<Vec<_>>>()?,
    };
    #[cfg(feature = "no_index")]
    let env_remove: Vec<String> = Vec::new();
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
        env_remove,
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
    let mut options = parse_options(state, options, engine_limit)?;
    let managed = state.config.process_scope == ProcessScope::Managed;
    let managed_input = if managed {
        Some(self::managed_input(program, &args, &options)?)
    } else {
        None
    };
    let permit = ActivePermit::acquire()?;
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
    let deadline = deadline_after(Instant::now(), options.timeout)?;
    let mut owner = if let Some((application, mut command_line, environment)) = managed_input {
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
        for key in &options.env_remove {
            command.env_remove(key);
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
    child: OwnedChild,
    job: Option<Arc<job::ManagedJob>>,
    members: Option<members::CapturedMembers>,
    membership_uncertain: bool,
    job_termination_requested: bool,
    job_closed: bool,
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
    #[cfg(test)]
    terminate_failures_remaining: usize,
    #[cfg(test)]
    termination_attempts: Option<Arc<AtomicUsize>>,
    #[cfg(test)]
    accounting_failures_remaining: usize,
    #[cfg(test)]
    accounting_failures_observed: Option<Arc<AtomicUsize>>,
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
            if catch_unwind(AssertUnwindSafe(|| owner.finish_in_background())).is_err() {
                // Preserve the exact owner, including pending I/O, Job and permit, when
                // cleanup cannot complete. Do not drop it or claim retirement after a panic.
                let mut slot = worker_cell.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
                if slot.is_none() {
                    *slot = Some(owner);
                } else {
                    // An unexpected competing owner must not cause either owner to be dropped.
                    std::mem::forget(owner);
                }
                return;
            }
            if owner.has_pending_cleanup() {
                // A missing lifetime member or an OS cleanup that did not finish
                // cannot be turned into success by dropping the last Job handle.
                // Retain custody without a permanently polling worker thread.
                let mut slot = worker_cell.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
                *slot = Some(owner);
                return;
            }
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
        Self::with_owned_child(child.into(), None, stdin, stdout, stderr, permit)
    }

    // A managed launch transfers its exact process and job handles together before
    // the suspended thread is resumed; an attached job is never presumed closed.
    #[allow(dead_code)]
    fn with_owned_child(
        child: OwnedChild,
        job: Option<Arc<job::ManagedJob>>,
        stdin: Option<PipeWriter>,
        stdout: PipeReader,
        stderr: PipeReader,
        permit: ActivePermit,
    ) -> Self {
        let job_closed = job.is_none();
        let members = job.as_ref().map(|_| members::CapturedMembers::default());
        Self {
            _permit: permit,
            child,
            job,
            members,
            membership_uncertain: false,
            job_termination_requested: false,
            job_closed,
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
            #[cfg(test)]
            terminate_failures_remaining: 0,
            #[cfg(test)]
            termination_attempts: None,
            #[cfg(test)]
            accounting_failures_remaining: 0,
            #[cfg(test)]
            accounting_failures_observed: None,
        }
    }

    fn seed_managed_root(&mut self) -> std_io::Result<()> {
        self.members
            .as_mut()
            .ok_or_else(|| std_io::Error::new(std_io::ErrorKind::Other, "managed capture missing"))?
            .seed_root(self.child.id(), self.child.as_raw_handle() as HANDLE)
    }

    fn capture_managed_members(&mut self) -> std_io::Result<()> {
        if self.membership_uncertain {
            return Err(std_io::Error::new(
                std_io::ErrorKind::Other,
                "managed lifetime membership remains unverified",
            ));
        }
        if let Some(job) = self.job.as_ref() {
            let result = self
                .members
                .as_mut()
                .ok_or_else(|| std_io::Error::new(std_io::ErrorKind::Other, "managed capture missing"))?
                .capture(job);
            if result.is_err() {
                self.membership_uncertain = true;
            }
            result?;
        }
        Ok(())
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
            if self.job.is_some() && !self.job_termination_requested {
                if let Err(error) = self.capture_managed_members() {
                    cause = Some(io_cause("capture managed members", program, &error));
                    break;
                }
            }
            // A managed task ends when its direct child does, even when a descendant
            // keeps an inherited pipe open. Stop the job before waiting for that EOF.
            if self.exit.is_some() && self.job.is_some() && !self.job_termination_requested {
                if let Err(error) = self.request_job_termination() {
                    cause = Some(io_cause("terminate managed job", program, &error));
                    break;
                }
            }
            if cancellation.is_some_and(child::Cancellation::requested) {
                if self.job.is_some() {
                    break;
                }
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
            // Ready I/O can otherwise continuously outrank the child handle. Preserve
            // an already observed overflow/timeout before checking the exact child.
            if cause.is_none() && self.job.is_some() && self.exit.is_none() {
                match self.child.try_wait() {
                    Ok(Some(status)) => {
                        self.exit = Some(status);
                        // Request job termination before a silent descendant can
                        // leave the next wait blocked on inherited pipe handles.
                        continue;
                    }
                    Ok(None) => {}
                    Err(error) => cause = Some(io_cause("observe managed child", program, &error)),
                }
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
            // Observe new managed members even when the primary process and pipes
            // remain quiet; the final count still detects members missed here.
            let wait_ms = if self.job.is_some() { wait_ms.min(100) } else { wait_ms };
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
        if self.job.is_some() && !self.job_termination_requested {
            if let Err(error) = self.request_job_termination() {
                self.diagnostics.push(ProcessDiagnostic::new(
                    "terminate managed job",
                    Some(error.kind()),
                    error.to_string(),
                ));
            }
        }
        if cause.is_some() && self.exit.is_none() && self.job.is_none() {
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
        if self.job.is_some() {
            let deadline = Instant::now() + Duration::from_secs(2);
            loop {
                match self.observe_job_closed() {
                    Ok(true) => break,
                    Ok(false) if Instant::now() < deadline => {
                        thread::sleep(Duration::from_millis(10));
                    }
                    Ok(false) => {
                        self.diagnostics.push(ProcessDiagnostic::new(
                            "wait for managed job cleanup",
                            Some(std_io::ErrorKind::TimedOut),
                            "job still contains active processes after bounded cleanup",
                        ));
                        break;
                    }
                    Err(error) => {
                        self.diagnostics.push(ProcessDiagnostic::new(
                            "observe managed job cleanup",
                            Some(error.kind()),
                            error.to_string(),
                        ));
                        break;
                    }
                }
            }
        }
        let owned_work_pending = self.has_pending_cleanup();
        if owned_work_pending {
            self.diagnostics.push(ProcessDiagnostic::new(
                "retain cleanup custody",
                None,
                "child, managed job or overlapped operation remains active; cleanup service retains ownership",
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
            || !self.job_closed
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
        let job_deadline = Instant::now() + Duration::from_secs(30);
        // Keep exact handles and the Job until both membership and termination
        // are proven. An irrecoverably incomplete capture is retained without spin.
        while !self.job_closed && Instant::now() < job_deadline {
            if !self.job_termination_requested {
                let _ = self.request_job_termination();
            }
            if self.membership_uncertain {
                // Capture uncertainty bars a closure claim, but must not stop
                // bounded retries of a failed termination request. Keep the
                // exact Job and permit in the registry after this deadline.
                if self.job_termination_requested {
                    break;
                }
                thread::sleep(Duration::from_millis(100));
                continue;
            }
            match self.observe_job_closed() {
                Ok(true) => break,
                Ok(false) => thread::sleep(Duration::from_millis(100)),
                Err(_) if !self.job_termination_requested => {
                    // A failed accounting read cannot suppress a still-needed
                    // termination retry for a possibly live descendant.
                    thread::sleep(Duration::from_millis(100));
                }
                Err(_) => break,
            }
        }
        // Even a permanently refused Job request must leave time to stop and
        // reap the exact direct child. Keep the original deadline when it is
        // still ahead, and grant this phase a finite fallback otherwise.
        let child_deadline = job_deadline.max(Instant::now() + Duration::from_secs(5));
        while self.exit.is_none() && Instant::now() < child_deadline {
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
        let io_deadline = job_deadline.max(Instant::now() + Duration::from_secs(5));
        while self.stdout.is_pending()
            || self.stderr.is_pending()
            || self.stdin.as_ref().is_some_and(PipeWriter::is_pending)
        {
            if Instant::now() >= io_deadline {
                break;
            }
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

    fn request_job_termination(&mut self) -> std_io::Result<()> {
        if let Some(job) = self.job.as_ref().map(Arc::clone) {
            // Snapshot before termination removes members from the PID list.
            // Capture failure does not prevent a best-effort termination request.
            let capture_error = self.capture_managed_members().err();
            #[cfg(feature = "testing-environ")]
            if std::env::var_os("RHAI_DEBUG_JOB_MEMBERS").is_some() {
                use std::io::Write;
                let _ = writeln!(std::io::stderr().lock(), "[DEBUG-owner38] phase=before parent={} job={:?} {}", self.child.id(), job.handle(), job.diagnostic_members());
            }
            #[cfg(test)]
            if let Some(attempts) = &self.termination_attempts {
                attempts.fetch_add(1, Ordering::AcqRel);
            }
            #[cfg(test)]
            let termination = if self.terminate_failures_remaining > 0 {
                self.terminate_failures_remaining -= 1;
                Err(std_io::Error::new(
                    std_io::ErrorKind::PermissionDenied,
                    "injected one-shot Job termination refusal",
                ))
            } else {
                job.terminate()
            };
            #[cfg(not(test))]
            let termination = job.terminate();
            if termination.is_ok() {
                self.job_termination_requested = true;
            }
            termination?;
            if let Some(error) = capture_error {
                return Err(error);
            }
        }
        Ok(())
    }

    fn observe_job_closed(&mut self) -> std_io::Result<bool> {
        if let Some(job) = self.job.as_ref() {
            if self.membership_uncertain {
                return Err(std_io::Error::new(
                    std_io::ErrorKind::Other,
                    "managed lifetime membership remains unverified",
                ));
            }
            #[cfg(test)]
            if self.accounting_failures_remaining > 0 {
                self.accounting_failures_remaining -= 1;
                if let Some(observed) = &self.accounting_failures_observed {
                    observed.fetch_add(1, Ordering::AcqRel);
                }
                return Err(std_io::Error::new(
                    std_io::ErrorKind::Other,
                    "injected one-shot Job accounting observation error",
                ));
            }
            let active = job.active_processes()?;
            #[cfg(feature = "testing-environ")]
            if std::env::var_os("RHAI_DEBUG_JOB_MEMBERS").is_some() {
                use std::io::Write;
                let _ = writeln!(std::io::stderr().lock(), "[DEBUG-owner38] phase=account parent={} job={:?} active={active} {}", self.child.id(), job.handle(), job.diagnostic_members());
            }
            let closed = self
                .members
                .as_ref()
                .ok_or_else(|| std_io::Error::new(std_io::ErrorKind::Other, "managed capture missing"))?
                .candidate_closed(job);
            match closed {
                Ok(closed) => self.job_closed = closed,
                Err(error) => {
                    self.membership_uncertain = true;
                    return Err(error);
                }
            }
        }
        Ok(self.job_closed)
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
    use windows_sys::Win32::System::JobObjects::AssignProcessToJobObject;
    use windows_sys::Win32::System::Threading::{GetCurrentProcess, TerminateProcess};

    #[test]
    fn windows_cleanup_panic_fixture() {
        let Some(root) = std::env::var_os("RHAI_WINDOWS_CLEANUP_PANIC_FIXTURE") else { return; };
        let root = std::path::Path::new(&root);
        std::fs::write(root.join("ready"), format!("{}\n", std::process::id())).unwrap();
        let fixture_seconds = std::env::var("RHAI_WINDOWS_CLEANUP_PANIC_FIXTURE_SECONDS")
            .ok()
            .map(|value| value.parse::<u64>().expect("fixture duration must be an integer"))
            .unwrap_or(20);
        let deadline = Instant::now() + Duration::from_secs(fixture_seconds);
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
    fn windows_background_retries_failed_job_termination_and_retains_uncertain_owner() {
        let nonce = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = std::env::temp_dir().join(format!(
            "rhai-managed-retry-{}-{nonce}",
            std::process::id()
        ));
        std::fs::create_dir(&root).unwrap();
        let child = Command::new(std::env::current_exe().unwrap())
            .args([
                "--exact",
                "packages::sys::process::windows::tests::windows_cleanup_panic_fixture",
                "--nocapture",
                "--quiet",
            ])
            .env_clear()
            .env("RHAI_WINDOWS_CLEANUP_PANIC_FIXTURE", &root)
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("start gated Job fixture");
        let mut pending = PendingFixtureSpawn {
            child: Some(child),
            root: root.clone(),
        };
        let child = pending.child.as_ref().unwrap();
        let mut duplicate = std::ptr::null_mut();
        // SAFETY: the exact live child handle is duplicated for independent readback.
        assert_ne!(unsafe {
            DuplicateHandle(
                GetCurrentProcess(),
                child.as_raw_handle() as HANDLE,
                GetCurrentProcess(),
                &mut duplicate,
                0,
                0,
                DUPLICATE_SAME_ACCESS,
            )
        }, 0);
        let guard = CleanupFixtureGuard {
            handle: Some(unsafe { OwnedHandle::from_raw_handle(duplicate as RawHandle) }),
            root: root.clone(),
        };
        let job = Arc::new(job::ManagedJob::new().expect("create private managed Job"));
        // SAFETY: the Job and exact fixture process handles are live; this fixture
        // performs no descendant work before assignment.
        assert_ne!(unsafe {
            AssignProcessToJobObject(job.handle(), child.as_raw_handle() as HANDLE)
        }, 0);
        let child = pending.child.take().unwrap();
        drop(pending);
        let deadline = Instant::now() + Duration::from_secs(5);
        loop {
            match std::fs::read_to_string(root.join("ready")) {
                Ok(value) => {
                    assert_eq!(value.trim().parse::<u32>().unwrap(), child.id());
                    break;
                }
                Err(error)
                    if error.kind() == std_io::ErrorKind::NotFound && Instant::now() < deadline =>
                {
                    thread::sleep(Duration::from_millis(10));
                }
                Err(error) => panic!("Job fixture readiness: {error}"),
            }
        }
        assert_eq!(unsafe {
            WaitForSingleObject(guard.handle.as_ref().unwrap().as_raw_handle() as HANDLE, 0)
        }, WAIT_TIMEOUT);
        let (stdout, stdout_writer) = PipeReader::pair().unwrap();
        let (stderr, stderr_writer) = PipeReader::pair().unwrap();
        drop(stdout_writer);
        drop(stderr_writer);
        let attempts = Arc::new(AtomicUsize::new(0));
        let mut owner = ProcessOwner::with_owned_child(
            child.into(),
            Some(job),
            None,
            stdout,
            stderr,
            ActivePermit::acquire().unwrap(),
        );
        owner.seed_managed_root().expect("capture exact root before cleanup");
        owner.membership_uncertain = true;
        owner.terminate_failures_remaining = 1;
        owner.termination_attempts = Some(Arc::clone(&attempts));
        let cell = retain_for_cleanup_inner(owner).expect("start bounded cleanup worker");
        let deadline = Instant::now() + Duration::from_secs(5);
        let mut retained = None;
        while Instant::now() < deadline {
            if attempts.load(Ordering::Acquire) >= 2 {
                retained = cell.lock().unwrap_or_else(|p| p.into_inner()).take();
                if retained.is_some() {
                    break;
                }
            }
            thread::sleep(Duration::from_millis(10));
        }
        let mut owner = retained.expect("uncertain owner remains in registry after bounded retry");
        assert_eq!(attempts.load(Ordering::Acquire), 2);
        assert!(owner.job_termination_requested);
        assert!(!owner.job_closed && owner.membership_uncertain);
        assert!(owner.has_pending_cleanup());
        assert_eq!(unsafe {
            WaitForSingleObject(guard.handle.as_ref().unwrap().as_raw_handle() as HANDLE, 0)
        }, WAIT_OBJECT_0, "exact Job child must be stopped before readback");
        owner.membership_uncertain = false;
        assert!(owner.observe_job_closed().expect("verify exact Job closure"));
        assert!(!owner.has_pending_cleanup());
        retained_registry()
            .lock()
            .unwrap_or_else(|p| p.into_inner())
            .retain(|entry| !Arc::ptr_eq(entry, &cell));
        drop(owner);
        drop(guard);
        eprintln!("windows_managed_retry_readback attempts=2 exact_child_stopped=true owner_retained=true");
        if std::env::var_os("RHAI_WINDOWS_MANAGED_RETRY_WRONG_EXPECTATION").is_some() {
            assert_eq!(attempts.load(Ordering::Acquire), 1,
                "deliberately wrong managed termination retry expectation");
        }
    }

    #[test]
    fn windows_background_retains_owner_after_persistent_job_termination_refusal() {
        let nonce = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = std::env::temp_dir().join(format!(
            "rhai-managed-permanent-refusal-{}-{nonce}",
            std::process::id()
        ));
        std::fs::create_dir(&root).unwrap();
        let child = Command::new(std::env::current_exe().unwrap())
            .args([
                "--exact",
                "packages::sys::process::windows::tests::windows_cleanup_panic_fixture",
                "--nocapture",
                "--quiet",
            ])
            .env_clear()
            .env("RHAI_WINDOWS_CLEANUP_PANIC_FIXTURE", &root)
            .env("RHAI_WINDOWS_CLEANUP_PANIC_FIXTURE_SECONDS", "60")
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("start gated Job fixture");
        let mut pending = PendingFixtureSpawn {
            child: Some(child),
            root: root.clone(),
        };
        let child = pending.child.as_ref().unwrap();
        let pid = child.id();
        let mut duplicate = std::ptr::null_mut();
        // SAFETY: the exact live child handle is duplicated for independent readback.
        assert_ne!(unsafe {
            DuplicateHandle(
                GetCurrentProcess(),
                child.as_raw_handle() as HANDLE,
                GetCurrentProcess(),
                &mut duplicate,
                0,
                0,
                DUPLICATE_SAME_ACCESS,
            )
        }, 0);
        let guard = CleanupFixtureGuard {
            handle: Some(unsafe { OwnedHandle::from_raw_handle(duplicate as RawHandle) }),
            root: root.clone(),
        };
        let job = Arc::new(job::ManagedJob::new().expect("create private managed Job"));
        // SAFETY: the gated fixture has not created descendants before Job admission.
        assert_ne!(unsafe {
            AssignProcessToJobObject(job.handle(), child.as_raw_handle() as HANDLE)
        }, 0);
        let child = pending.child.take().unwrap();
        drop(pending);
        let ready_deadline = Instant::now() + Duration::from_secs(5);
        loop {
            match std::fs::read_to_string(root.join("ready")) {
                Ok(value) => {
                    assert_eq!(value.trim().parse::<u32>().unwrap(), pid);
                    break;
                }
                Err(error)
                    if error.kind() == std_io::ErrorKind::NotFound
                        && Instant::now() < ready_deadline =>
                {
                    thread::sleep(Duration::from_millis(10));
                }
                Err(error) => panic!("Job fixture readiness: {error}"),
            }
        }
        let exact = guard.handle.as_ref().unwrap().as_raw_handle() as HANDLE;
        assert_eq!(unsafe { WaitForSingleObject(exact, 0) }, WAIT_TIMEOUT);
        let (stdout, stdout_writer) = PipeReader::pair().unwrap();
        let (stderr, stderr_writer) = PipeReader::pair().unwrap();
        drop(stdout_writer);
        drop(stderr_writer);
        let attempts = Arc::new(AtomicUsize::new(0));
        let mut owner = ProcessOwner::with_owned_child(
            child.into(),
            Some(job),
            None,
            stdout,
            stderr,
            ActivePermit::acquire().unwrap(),
        );
        owner.seed_managed_root().expect("capture exact root before cleanup");
        owner.terminate_failures_remaining = usize::MAX;
        owner.termination_attempts = Some(Arc::clone(&attempts));
        let started = Instant::now();
        let cell = retain_for_cleanup_inner(owner).expect("start bounded cleanup worker");
        let retry_deadline = started + Duration::from_secs(5);
        while attempts.load(Ordering::Acquire) < 2 && Instant::now() < retry_deadline {
            thread::sleep(Duration::from_millis(10));
        }
        assert!(attempts.load(Ordering::Acquire) >= 2, "permanent refusal was not retried");
        assert_eq!(unsafe { WaitForSingleObject(exact, 0) }, WAIT_TIMEOUT,
            "the exact child must still be live while Job termination is refused");

        let bounded_deadline = started + Duration::from_secs(45);
        let mut retained = None;
        while Instant::now() < bounded_deadline {
            retained = cell.lock().unwrap_or_else(|p| p.into_inner()).take();
            if retained.is_some() { break; }
            thread::sleep(Duration::from_millis(20));
        }
        let mut owner = retained.expect("cleanup worker must return exact owner after bounded refusal");
        let attempt_count = attempts.load(Ordering::Acquire);
        assert!(attempt_count >= 2);
        assert!(!owner.job_termination_requested && !owner.job_closed);
        assert!(owner.has_pending_cleanup(), "failed Job termination cannot claim closure");
        assert_eq!(owner.child.id(), pid);
        assert_eq!(unsafe { WaitForSingleObject(exact, 0) }, WAIT_OBJECT_0,
            "exact child must be stopped by bounded fallback cleanup");
        assert!(owner.observe_job_closed().expect("prove exact Job closure"));
        assert!(!owner.has_pending_cleanup());
        retained_registry()
            .lock()
            .unwrap_or_else(|p| p.into_inner())
            .retain(|entry| !Arc::ptr_eq(entry, &cell));
        drop(owner);
        drop(guard);
        eprintln!("windows_managed_permanent_refusal_readback attempts={attempt_count} exact_child_stopped=true owner_retained=true bounded=true");
        if std::env::var_os("RHAI_WINDOWS_PERMANENT_REFUSAL_WRONG_EXPECTATION").is_some() {
            assert_eq!(attempt_count, 0,
                "deliberately wrong permanent Job refusal expectation");
        }
    }

    #[test]
    fn windows_background_retries_after_job_accounting_observation_error() {
        let nonce = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = std::env::temp_dir().join(format!(
            "rhai-managed-accounting-{}-{nonce}",
            std::process::id()
        ));
        std::fs::create_dir(&root).unwrap();
        let child = Command::new(std::env::current_exe().unwrap())
            .args([
                "--exact",
                "packages::sys::process::windows::tests::windows_cleanup_panic_fixture",
                "--nocapture",
                "--quiet",
            ])
            .env_clear()
            .env("RHAI_WINDOWS_CLEANUP_PANIC_FIXTURE", &root)
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("start gated Job fixture");
        let mut pending = PendingFixtureSpawn {
            child: Some(child),
            root: root.clone(),
        };
        let child = pending.child.as_ref().unwrap();
        let pid = child.id();
        let mut duplicate = std::ptr::null_mut();
        // SAFETY: the exact live child handle is duplicated for independent readback.
        assert_ne!(unsafe {
            DuplicateHandle(
                GetCurrentProcess(),
                child.as_raw_handle() as HANDLE,
                GetCurrentProcess(),
                &mut duplicate,
                0,
                0,
                DUPLICATE_SAME_ACCESS,
            )
        }, 0);
        let guard = CleanupFixtureGuard {
            handle: Some(unsafe { OwnedHandle::from_raw_handle(duplicate as RawHandle) }),
            root: root.clone(),
        };
        let job = Arc::new(job::ManagedJob::new().expect("create private managed Job"));
        // SAFETY: both exact handles are live and the gated fixture creates no descendants.
        assert_ne!(unsafe {
            AssignProcessToJobObject(job.handle(), child.as_raw_handle() as HANDLE)
        }, 0);
        let child = pending.child.take().unwrap();
        drop(pending);
        let deadline = Instant::now() + Duration::from_secs(5);
        loop {
            match std::fs::read_to_string(root.join("ready")) {
                Ok(value) => {
                    assert_eq!(value.trim().parse::<u32>().unwrap(), pid);
                    break;
                }
                Err(error)
                    if error.kind() == std_io::ErrorKind::NotFound && Instant::now() < deadline =>
                {
                    thread::sleep(Duration::from_millis(10));
                }
                Err(error) => panic!("Job fixture readiness: {error}"),
            }
        }
        assert_eq!(unsafe {
            WaitForSingleObject(guard.handle.as_ref().unwrap().as_raw_handle() as HANDLE, 0)
        }, WAIT_TIMEOUT);
        let (stdout, stdout_writer) = PipeReader::pair().unwrap();
        let (stderr, stderr_writer) = PipeReader::pair().unwrap();
        drop(stdout_writer);
        drop(stderr_writer);
        let attempts = Arc::new(AtomicUsize::new(0));
        let accounting_errors = Arc::new(AtomicUsize::new(0));
        let mut owner = ProcessOwner::with_owned_child(
            child.into(),
            Some(job),
            None,
            stdout,
            stderr,
            ActivePermit::acquire().unwrap(),
        );
        owner.seed_managed_root().expect("capture exact root before cleanup");
        owner.terminate_failures_remaining = 1;
        owner.termination_attempts = Some(Arc::clone(&attempts));
        owner.accounting_failures_remaining = 1;
        owner.accounting_failures_observed = Some(Arc::clone(&accounting_errors));
        let cell = retain_for_cleanup_inner(owner).expect("start bounded cleanup worker");
        let deadline = Instant::now() + Duration::from_secs(5);
        loop {
            let retired = !retained_registry()
                .lock()
                .unwrap_or_else(|p| p.into_inner())
                .iter()
                .any(|entry| Arc::ptr_eq(entry, &cell));
            if retired {
                break;
            }
            assert!(Instant::now() < deadline, "Job owner did not finish bounded retry");
            thread::sleep(Duration::from_millis(10));
        }
        assert_eq!(accounting_errors.load(Ordering::Acquire), 1);
        assert_eq!(attempts.load(Ordering::Acquire), 2);
        assert_eq!(unsafe {
            WaitForSingleObject(guard.handle.as_ref().unwrap().as_raw_handle() as HANDLE, 0)
        }, WAIT_OBJECT_0, "exact Job child must be stopped after retry");
        drop(guard);
        eprintln!("windows_managed_accounting_retry_readback attempts=2 accounting_errors=1 exact_child_stopped=true owner_retired=true");
        if std::env::var_os("RHAI_WINDOWS_ACCOUNTING_RETRY_WRONG_EXPECTATION").is_some() {
            assert_eq!(attempts.load(Ordering::Acquire), 1,
                "deliberately wrong Job accounting retry expectation");
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
