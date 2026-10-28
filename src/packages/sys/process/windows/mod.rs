//! Native Windows process execution with cancellable, bounded output capture.

mod io;

use self::io::PipeReader;
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
        if !["env", "env_clear", "timeout", "max_output"].contains(&key.as_str()) {
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
        timeout,
        limit,
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
    let mut command = Command::new(program);
    command
        .args(args)
        .stdin(Stdio::null())
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
    let mut owner = ProcessOwner::new(child, stdout, stderr, permit);
    let supervised = catch_unwind(AssertUnwindSafe(|| {
        owner.supervise(deadline, options.limit, program)
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
    stdout: PipeReader,
    stderr: PipeReader,
    out: Vec<u8>,
    err: Vec<u8>,
    exit: Option<ExitStatus>,
    diagnostics: Vec<ProcessDiagnostic>,
}

type RetainedOwner = Arc<Mutex<Option<ProcessOwner>>>;
static RETAINED_CLEANUP: OnceLock<Mutex<Vec<RetainedOwner>>> = OnceLock::new();

fn retained_registry() -> &'static Mutex<Vec<RetainedOwner>> {
    RETAINED_CLEANUP.get_or_init(|| Mutex::new(Vec::new()))
}

fn retain_for_cleanup(owner: ProcessOwner) -> std_io::Result<()> {
    let cell = Arc::new(Mutex::new(Some(owner)));
    retained_registry()
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
        .push(Arc::clone(&cell));
    // The registry holds the owner even if thread creation fails. Once started, the worker
    // exclusively owns it until both child and pending I/O reach observed completion.
    thread::Builder::new()
        .name("rhai-windows-process-cleanup".into())
        .spawn(move || {
            let mut owner = cell
                .lock()
                .unwrap_or_else(|poisoned| poisoned.into_inner())
                .take()
                .expect("retained cleanup owner missing");
            owner.finish_in_background();
            retained_registry()
                .lock()
                .unwrap_or_else(|poisoned| poisoned.into_inner())
                .retain(|entry| !Arc::ptr_eq(entry, &cell));
        })
        .map(|_| ())
}

impl ProcessOwner {
    fn new(child: Child, stdout: PipeReader, stderr: PipeReader, permit: ActivePermit) -> Self {
        Self {
            _permit: permit,
            child,
            stdout,
            stderr,
            out: Vec::new(),
            err: Vec::new(),
            exit: None,
            diagnostics: Vec::new(),
        }
    }

    fn supervise(
        &mut self,
        deadline: Option<Instant>,
        limit: usize,
        program: &str,
    ) -> Result<ProcessReport, (ProcessCause, ProcessReport)> {
        let mut cause = None;
        loop {
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
            if cause.is_some()
                || (self.exit.is_some() && self.stdout.reached_eof() && self.stderr.reached_eof())
            {
                break;
            }
            // A synchronous read can leave its pipe ready for another read. Rearm it
            // before waiting on other handles so a full child pipe cannot stall us.
            if (!self.stdout.is_pending() && !self.stdout.reached_eof())
                || (!self.stderr.is_pending() && !self.stderr.reached_eof())
            {
                continue;
            }
            let mut handles = Vec::with_capacity(3);
            if self.stdout.is_pending() {
                handles.push(self.stdout.event_handle());
            }
            if self.stderr.is_pending() {
                handles.push(self.stderr.event_handle());
            }
            if self.exit.is_none() {
                handles.push(self.child.as_raw_handle() as HANDLE);
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
        let owned_work_pending =
            self.exit.is_none() || self.stdout.is_pending() || self.stderr.is_pending();
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
        self.exit.is_none() || self.stdout.is_pending() || self.stderr.is_pending()
    }

    fn finish_in_background(&mut self) {
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
        while self.stdout.is_pending() || self.stderr.is_pending() {
            if self.stdout.is_pending() {
                let _ = self.stdout.cancel_and_join_bounded(1_000);
            }
            if self.stderr.is_pending() {
                let _ = self.stderr.cancel_and_join_bounded(1_000);
            }
        }
    }
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
