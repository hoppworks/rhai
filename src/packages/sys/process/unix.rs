//! Native Unix child execution for the synchronous run contract.
use super::{ProcessCause, ProcessExit, ProcessReport};
use crate::packages::sys::{config::*, error::SysError, SysState};
#[cfg(not(feature = "no_index"))]
use crate::{Array, Blob};
use crate::{Dynamic, ImmutableString, Map, Module, NativeCallContext, Shared, INT};
use std::ffi::OsStr;
use std::io::{self, Read, Write};
use std::os::fd::{AsRawFd, RawFd};
use std::os::unix::process::{CommandExt, ExitStatusExt};
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};

/// Private, per-execution fault adapter used only by host unit tests.
///
/// The plan is consumed immediately before spawn and then carried with that exact execution;
/// there is no script-visible switch and no process-global fault state.
#[derive(Default)]
struct ExecutionFaults {
    #[cfg(test)]
    refuse_kill_once: bool,
    #[cfg(test)]
    retired: Option<std::sync::Arc<std::sync::atomic::AtomicBool>>,
}

impl ExecutionFaults {
    fn take_for_execution() -> Self {
        #[cfg(test)]
        {
            return tests::take_execution_faults();
        }
        #[cfg(not(test))]
        Self::default()
    }

    fn kill(&mut self, child: &mut Child) -> io::Result<()> {
        #[cfg(test)]
        if self.refuse_kill_once {
            self.refuse_kill_once = false;
            return Err(io::Error::new(
                io::ErrorKind::PermissionDenied,
                "injected one-shot termination refusal",
            ));
        }
        child.kill()
    }
}

type Res<T> = Result<T, Box<crate::EvalAltResult>>;

pub(super) fn register(module: &mut Module, state: &Shared<SysState>) {
    #[cfg(not(feature = "no_index"))]
    {
        let st = state.clone();
        crate::packages::sys::reg("run_raw", &["/// Run a child program."]).set_into_module(
            module,
            move |ctx: NativeCallContext, program: &str| -> Res<Map> {
                run_map(&ctx, &st, program, &[], Map::new(), true)
            },
        );
        let st = state.clone();
        crate::packages::sys::reg("run_raw", &["/// Run a child program with options."])
            .set_into_module(
                module,
                move |ctx: NativeCallContext, program: &str, options: Map| -> Res<Map> {
                    run_map(&ctx, &st, program, &[], options, true)
                },
            );
        let st = state.clone();
        crate::packages::sys::reg(
            "run_raw",
            &["/// Run a child program with arguments and options."],
        )
        .set_into_module(
            module,
            move |ctx: NativeCallContext, program: &str, args: Array, options: Map| -> Res<Map> {
                let args = parse_args(args)?;
                run_map(&ctx, &st, program, &args, options, true)
            },
        );
        let st = state.clone();
        crate::packages::sys::reg("run_raw", &["/// Run a child program with arguments."])
            .set_into_module(
                module,
                move |ctx: NativeCallContext, program: &str, args: Array| -> Res<Map> {
                    let args = parse_args(args)?;
                    run_map(&ctx, &st, program, &args, Map::new(), true)
                },
            );
    }
    let st = state.clone();
    crate::packages::sys::reg(
        "run",
        &["/// Run a child program and return lossy UTF-8 stdout and stderr."],
    )
    .set_into_module(
        module,
        move |ctx: NativeCallContext, program: &str| -> Res<Map> {
            run_map(&ctx, &st, program, &[], Map::new(), false)
        },
    );
    let st = state.clone();
    crate::packages::sys::reg("run", &["/// Run a child program with options."]).set_into_module(
        module,
        move |ctx: NativeCallContext, program: &str, options: Map| -> Res<Map> {
            run_map(&ctx, &st, program, &[], options, false)
        },
    );
    #[cfg(not(feature = "no_index"))]
    {
        let st = state.clone();
        crate::packages::sys::reg(
            "run",
            &["/// Run a child program with arguments and options."],
        )
        .set_into_module(
            module,
            move |ctx: NativeCallContext, program: &str, args: Array, options: Map| -> Res<Map> {
                let args = parse_args(args)?;
                run_map(&ctx, &st, program, &args, options, false)
            },
        );
        let st = state.clone();
        crate::packages::sys::reg("run", &["/// Run a child program with arguments."])
            .set_into_module(
                module,
                move |ctx: NativeCallContext, program: &str, args: Array| -> Res<Map> {
                    let args = parse_args(args)?;
                    run_map(&ctx, &st, program, &args, Map::new(), false)
                },
            );
    }
}

#[cfg(not(feature = "no_index"))]
fn parse_args(args: Array) -> Res<Vec<String>> {
    args.into_iter()
        .map(|arg| {
            arg.try_cast::<ImmutableString>()
                .map(|s| s.to_string())
                .ok_or_else(|| SysError::Denied("process arguments must be strings".into()).into())
        })
        .collect()
}

struct Options {
    cwd: Option<String>,
    env: Vec<(String, String)>,
    env_remove: Vec<String>,
    env_clear: bool,
    stdin: Option<Vec<u8>>,
    timeout: Option<Duration>,
    limit: usize,
}

fn parse_options(state: &SysState, mut options: Map, engine_limit: usize) -> Res<Options> {
    let mut known = vec!["cwd", "env", "env_clear", "stdin", "timeout", "max_output"];
    #[cfg(not(feature = "no_index"))]
    known.push("env_remove");
    for key in options.keys() {
        if !known.contains(&key.as_str()) {
            return Err(SysError::Denied(format!("unknown process option `{key}`")).into());
        }
    }
    let string = |key: &str, options: &mut Map| -> Res<Option<String>> {
        options
            .remove(key)
            .map(|v| {
                v.try_cast::<ImmutableString>()
                    .map(|s| s.to_string())
                    .ok_or_else(|| {
                        SysError::Denied(format!("process option `{key}` must be a string")).into()
                    })
            })
            .transpose()
    };
    let cwd = string("cwd", &mut options)?;
    let env_clear = match options.remove("env_clear") {
        None => false,
        Some(v) => v
            .try_cast::<bool>()
            .ok_or_else(|| SysError::Denied("process option `env_clear` must be a bool".into()))?,
    };
    #[cfg(not(feature = "no_index"))]
    let env_remove = match options.remove("env_remove") {
        None => vec![],
        Some(v) => v
            .try_cast::<Array>()
            .ok_or_else(|| SysError::Denied("process option `env_remove` must be an array".into()))?
            .into_iter()
            .map(|v| {
                v.try_cast::<ImmutableString>()
                    .map(|s| s.to_string())
                    .ok_or_else(|| {
                        SysError::Denied("env_remove entries must be strings".into()).into()
                    })
            })
            .collect::<Res<Vec<_>>>()?,
    };
    #[cfg(feature = "no_index")]
    let env_remove: Vec<String> = Vec::new();
    let env = match options.remove("env") {
        None => vec![],
        Some(v) => v
            .try_cast::<Map>()
            .ok_or_else(|| SysError::Denied("process option `env` must be a map".into()))?
            .into_iter()
            .map(|(k, v)| {
                v.try_cast::<ImmutableString>()
                    .map(|s| (k.to_string(), s.to_string()))
                    .ok_or_else(|| {
                        SysError::Denied("environment values must be strings".into()).into()
                    })
            })
            .collect::<Res<Vec<_>>>()?,
    };
    let stdin = match options.remove("stdin") {
        None => None,
        Some(v) if v.is_unit() => None,
        Some(v) => Some(parse_stdin(v)?),
    };
    let timeout = match options.remove("timeout") {
        None => state.config.default_timeout,
        Some(v) if v.is_unit() => None,
        Some(v) => Some(
            v.clone()
                .try_cast::<INT>()
                .map(|n| n as f64)
                .or_else(|| {
                    #[cfg(not(feature = "no_float"))]
                    {
                        v.try_cast::<crate::FLOAT>().map(|n| n as f64)
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
        .map(|v| {
            v.try_cast::<INT>()
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
    let limit = if engine_limit == 0 {
        requested.min(state.config.max_output)
    } else {
        requested.min(state.config.max_output).min(engine_limit)
    };
    Ok(Options {
        cwd,
        env,
        env_remove,
        env_clear,
        stdin,
        timeout,
        limit,
    })
}

#[cfg(not(feature = "no_index"))]
fn parse_stdin(value: Dynamic) -> Res<Vec<u8>> {
    value
        .clone()
        .try_cast::<Blob>()
        .or_else(|| {
            value
                .try_cast::<ImmutableString>()
                .map(|s| s.as_bytes().to_vec())
        })
        .ok_or_else(|| {
            SysError::Denied("process option `stdin` must be a string or blob".into()).into()
        })
}

#[cfg(feature = "no_index")]
fn parse_stdin(value: Dynamic) -> Res<Vec<u8>> {
    value
        .try_cast::<ImmutableString>()
        .map(|s| s.as_bytes().to_vec())
        .ok_or_else(|| SysError::Denied("process option `stdin` must be a string".into()).into())
}

fn run_map(
    ctx: &NativeCallContext,
    state: &Shared<SysState>,
    program: &str,
    args: &[String],
    opts: Map,
    raw: bool,
) -> Res<Map> {
    if !state.config.programs.allows(program) {
        return Err(SysError::Denied(format!("program `{program}` is not allowed")).into());
    }
    if state.config.process_scope != ProcessScope::DirectChild {
        return Err(SysError::Denied(
            "Managed process scope is not supported by this target".into(),
        )
        .into());
    }
    let engine_limit = {
        #[cfg(not(feature = "unchecked"))]
        {
            #[cfg(not(feature = "no_index"))]
            if raw {
                ctx.engine().max_array_size()
            } else {
                ctx.engine().max_string_size()
            }
            #[cfg(feature = "no_index")]
            {
                let _ = raw;
                ctx.engine().max_string_size()
            }
        }
        #[cfg(feature = "unchecked")]
        {
            let _ = raw;
            0
        }
    };
    let options = parse_options(state, opts, engine_limit)?;
    let cwd = options
        .cwd
        .as_deref()
        .map(|p| state.fs.open_process_cwd(p))
        .transpose()?;
    let mut command = Command::new(OsStr::new(program));
    command
        .args(args)
        .stdin(if options.stdin.is_some() {
            Stdio::piped()
        } else {
            Stdio::null()
        })
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    if options.env_clear {
        command.env_clear();
    }
    for key in options.env_remove {
        command.env_remove(key);
    }
    for (key, value) in options.env {
        command.env(key, value);
    }
    if let Some(dir) = cwd.as_ref() {
        let fd = dir.as_raw_fd();
        // SAFETY: the closure only invokes async-signal-safe fchdir on a parent-owned open fd.
        unsafe {
            command.pre_exec(move || {
                if libc::fchdir(fd) == 0 {
                    Ok(())
                } else {
                    Err(io::Error::last_os_error())
                }
            });
        }
    }
    // The monotonic deadline begins immediately before process creation.
    let started = Instant::now();
    let mut faults = ExecutionFaults::take_for_execution();
    let mut child = command
        .spawn()
        .map_err(|e| SysError::io("spawn process", program, &e))?;
    let result = supervise(
        &mut child,
        program,
        options.stdin,
        options.limit,
        options.timeout,
        started,
        &mut faults,
    );
    let _keep_cwd_open_until_spawn_returned = cwd;
    let report = match result {
        Ok(report) => report,
        Err((cause, report)) => return Err(SysError::Process { cause, report }.into()),
    };
    if !raw && engine_limit > 0 {
        let stdout = report.stdout();
        let stderr = report.stderr();
        if stdout.len() > engine_limit || stderr.len() > engine_limit {
            return Err(SysError::Process {
                cause: ProcessCause::OutputLimit(format!(
                    "decoded process output exceeded the engine string limit of {engine_limit} bytes"
                )),
                report,
            }
            .into());
        }
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
    map.insert(
        "signal".into(),
        report
            .exit_signal()
            .map(|n| Dynamic::from_int(n as INT))
            .unwrap_or(Dynamic::UNIT),
    );
    map.insert("timed_out".into(), Dynamic::from(report.timed_out()));
    map.insert(
        "stdout_complete".into(),
        Dynamic::from(report.stdout_complete()),
    );
    map.insert(
        "stderr_complete".into(),
        Dynamic::from(report.stderr_complete()),
    );
    #[cfg(not(feature = "no_index"))]
    if raw {
        map.insert(
            "stdout".into(),
            Dynamic::from(report.stdout_bytes().to_vec()),
        );
        map.insert(
            "stderr".into(),
            Dynamic::from(report.stderr_bytes().to_vec()),
        );
    } else {
        map.insert("stdout".into(), Dynamic::from(report.stdout()));
        map.insert("stderr".into(), Dynamic::from(report.stderr()));
    }
    #[cfg(feature = "no_index")]
    {
        map.insert("stdout".into(), Dynamic::from(report.stdout()));
        map.insert("stderr".into(), Dynamic::from(report.stderr()));
    }
    Ok(map)
}

fn set_nonblock(fd: RawFd) -> io::Result<()> {
    // SAFETY: fcntl reads/updates flags for an owned pipe descriptor.
    let flags = unsafe { libc::fcntl(fd, libc::F_GETFL) };
    if flags < 0 {
        return Err(io::Error::last_os_error());
    }
    if unsafe { libc::fcntl(fd, libc::F_SETFL, flags | libc::O_NONBLOCK) } < 0 {
        return Err(io::Error::last_os_error());
    }
    Ok(())
}
#[derive(Clone, Copy)]
enum ReadState {
    Pending,
    Eof,
    Overflow,
}

const READ_BUDGET: usize = 64 * 1024;

fn read_ready<R: Read>(
    reader: &mut R,
    output: &mut Vec<u8>,
    limit: usize,
) -> io::Result<ReadState> {
    let mut buf = [0u8; 8192];
    let mut consumed = 0;
    loop {
        let remaining = limit.saturating_sub(output.len());
        let count = if remaining == 0 {
            1
        } else {
            remaining.min(buf.len()).min(READ_BUDGET - consumed)
        };
        match reader.read(&mut buf[..count]) {
            Ok(0) => return Ok(ReadState::Eof),
            Ok(n) => {
                let keep = n.min(remaining);
                output.extend_from_slice(&buf[..keep]);
                if n > keep {
                    return Ok(ReadState::Overflow);
                }
                consumed += n;
                if consumed >= READ_BUDGET {
                    return Ok(ReadState::Pending);
                }
            }
            Err(e) if e.kind() == io::ErrorKind::WouldBlock => return Ok(ReadState::Pending),
            Err(e) if e.kind() == io::ErrorKind::Interrupted => continue,
            Err(e) => return Err(e),
        }
    }
}

fn supervise(
    child: &mut Child,
    program: &str,
    input: Option<Vec<u8>>,
    limit: usize,
    timeout: Option<Duration>,
    started: Instant,
    faults: &mut ExecutionFaults,
) -> Result<ProcessReport, (ProcessCause, ProcessReport)> {
    let mut stdout = child.stdout.take().unwrap();
    let mut stderr = child.stderr.take().unwrap();
    let mut stdin = child.stdin.take();
    let outfd = stdout.as_raw_fd();
    let errfd = stderr.as_raw_fd();
    let infd = stdin.as_ref().map(AsRawFd::as_raw_fd);
    for fd in [Some(outfd), Some(errfd), infd].into_iter().flatten() {
        if let Err(e) = set_nonblock(fd) {
            return fail(
                child,
                program,
                ProcessCause::Io {
                    op: "configure process pipe",
                    target: program.into(),
                    kind: e.kind(),
                    message: e.to_string(),
                },
                vec![],
                vec![],
                false,
                false,
                faults,
            );
        }
    }
    let mut pending = input.unwrap_or_default();
    let mut offset = 0usize;
    let mut out = Vec::new();
    let mut err = Vec::new();
    let (mut out_eof, mut err_eof) = (false, false);
    let mut status = None;
    loop {
        let expired = timeout.is_some_and(|t| started.elapsed() >= t);
        match child.try_wait() {
            Ok(s) => status = s,
            Err(e) => {
                return fail(
                    child,
                    program,
                    ProcessCause::Io {
                        op: "wait for process",
                        target: program.into(),
                        kind: e.kind(),
                        message: e.to_string(),
                    },
                    out,
                    err,
                    out_eof,
                    err_eof,
                    faults,
                )
            }
        }
        if status.is_some() && out_eof && err_eof {
            break;
        }
        if let Some(fd) = infd {
            if offset >= pending.len() {
                stdin.take();
                let _ = fd;
            }
        }
        let mut fds = [
            libc::pollfd {
                fd: if out_eof { -1 } else { outfd },
                events: libc::POLLIN,
                revents: 0,
            },
            libc::pollfd {
                fd: if err_eof { -1 } else { errfd },
                events: libc::POLLIN,
                revents: 0,
            },
            libc::pollfd {
                fd: if stdin.is_some() && offset < pending.len() {
                    infd.unwrap()
                } else {
                    -1
                },
                events: libc::POLLOUT,
                revents: 0,
            },
        ];
        let millis = if expired {
            0
        } else {
            timeout
                .map(|t| {
                    t.saturating_sub(started.elapsed())
                        .min(Duration::from_millis(100))
                        .as_millis() as i32
                })
                .unwrap_or(100)
        };
        // SAFETY: fds points to three initialized poll descriptors for owned pipe FDs.
        let rc = unsafe { libc::poll(fds.as_mut_ptr(), fds.len() as libc::nfds_t, millis) };
        if rc < 0 {
            let e = io::Error::last_os_error();
            if e.kind() == io::ErrorKind::Interrupted {
                continue;
            }
            return fail(
                child,
                program,
                ProcessCause::Io {
                    op: "poll process pipes",
                    target: program.into(),
                    kind: e.kind(),
                    message: e.to_string(),
                },
                out,
                err,
                out_eof,
                err_eof,
                faults,
            );
        }
        if fds[0].revents != 0 {
            match read_ready(&mut stdout, &mut out, limit) {
                Ok(ReadState::Overflow) => {
                    return fail(
                        child,
                        program,
                        ProcessCause::OutputLimit(format!(
                            "process `{program}` exceeded {limit} output bytes"
                        )),
                        out,
                        err,
                        out_eof,
                        err_eof,
                        faults,
                    )
                }
                Ok(ReadState::Eof) => out_eof = true,
                Ok(ReadState::Pending) => {}
                Err(e) => {
                    return fail(
                        child,
                        program,
                        ProcessCause::Io {
                            op: "read process stdout",
                            target: program.into(),
                            kind: e.kind(),
                            message: e.to_string(),
                        },
                        out,
                        err,
                        out_eof,
                        err_eof,
                        faults,
                    )
                }
            }
        }
        if fds[1].revents != 0 {
            match read_ready(&mut stderr, &mut err, limit) {
                Ok(ReadState::Overflow) => {
                    return fail(
                        child,
                        program,
                        ProcessCause::OutputLimit(format!(
                            "process `{program}` exceeded {limit} output bytes"
                        )),
                        out,
                        err,
                        out_eof,
                        err_eof,
                        faults,
                    )
                }
                Ok(ReadState::Eof) => err_eof = true,
                Ok(ReadState::Pending) => {}
                Err(e) => {
                    return fail(
                        child,
                        program,
                        ProcessCause::Io {
                            op: "read process stderr",
                            target: program.into(),
                            kind: e.kind(),
                            message: e.to_string(),
                        },
                        out,
                        err,
                        out_eof,
                        err_eof,
                        faults,
                    )
                }
            }
        }
        if fds[2].revents != 0 {
            if let Some(pipe) = stdin.as_mut() {
                match pipe.write(&pending[offset..]) {
                    Ok(0) => {}
                    Ok(n) => offset += n,
                    Err(e)
                        if e.kind() == io::ErrorKind::WouldBlock
                            || e.kind() == io::ErrorKind::Interrupted => {}
                    Err(e) => {
                        return fail(
                            child,
                            program,
                            ProcessCause::Io {
                                op: "write process stdin",
                                target: program.into(),
                                kind: e.kind(),
                                message: e.to_string(),
                            },
                            out,
                            err,
                            out_eof,
                            err_eof,
                            faults,
                        )
                    }
                }
            }
        }
        // Drain readable bytes first so observed output overflow wins when it coincides with
        // deadline expiry; otherwise the deadline owns the cancellation.
        if expired {
            let (cause, report) = fail(
                child,
                program,
                ProcessCause::Timeout(format!("process `{program}` exceeded deadline")),
                out,
                err,
                out_eof,
                err_eof,
                faults,
            )
            .unwrap_err();
            return if report.timed_out() {
                Ok(report)
            } else {
                Err((cause, report))
            };
        }
    }
    let status = status.unwrap();
    let exit = status
        .code()
        .map(ProcessExit::Code)
        .or_else(|| status.signal().map(ProcessExit::Signal));
    Ok(ProcessReport::new(
        out,
        err,
        true,
        true,
        exit,
        false,
        vec![],
    ))
}

fn fail(
    child: &mut Child,
    program: &str,
    cause: ProcessCause,
    out: Vec<u8>,
    err: Vec<u8>,
    out_eof: bool,
    err_eof: bool,
    faults: &mut ExecutionFaults,
) -> Result<ProcessReport, (ProcessCause, ProcessReport)> {
    let is_timeout = matches!(&cause, ProcessCause::Timeout(_));
    let mut diagnostics = vec![];
    if let Err(e) = faults.kill(child) {
        if e.kind() != io::ErrorKind::InvalidInput {
            diagnostics.push(super::ProcessDiagnostic::new(
                "kill child",
                Some(e.kind()),
                e.to_string(),
            ));
        }
    }
    let status = match child.wait() {
        Ok(s) => Some(s),
        Err(e) => {
            diagnostics.push(super::ProcessDiagnostic::new(
                "reap child",
                Some(e.kind()),
                e.to_string(),
            ));
            None
        }
    };
    let exit = status.and_then(|s| {
        s.code()
            .map(ProcessExit::Code)
            .or_else(|| s.signal().map(ProcessExit::Signal))
    });
    let timed_out = is_timeout && diagnostics.is_empty() && exit.is_some();
    Err((
        cause,
        ProcessReport::new(out, err, out_eof, err_eof, exit, timed_out, diagnostics),
    ))
}

#[cfg(test)]
mod tests {
    use super::{read_ready, ExecutionFaults, ReadState};
    use crate::packages::sys::{ProcessCause, ProgramPolicy, SysConfig, SysError, SysPackage};
    use crate::packages::Package;
    use crate::{Engine, EvalAltResult};
    use std::cell::RefCell;
    use std::ffi::CString;
    use std::fs::{self, OpenOptions};
    use std::io::{self, Read, Write};
    use std::os::unix::ffi::OsStrExt;
    use std::os::unix::fs::OpenOptionsExt;
    use std::path::{Path, PathBuf};
    use std::process::{Child, Command, Stdio};
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::sync::Arc;
    use std::thread;
    use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

    const EXPECTED_READ_BUDGET: usize = 64 * 1024;

    thread_local! {
        static NEXT_EXECUTION_FAULTS: RefCell<Option<ExecutionFaults>> = const { RefCell::new(None) };
    }

    pub(super) fn take_execution_faults() -> ExecutionFaults {
        NEXT_EXECUTION_FAULTS.with(|next| next.borrow_mut().take().unwrap_or_default())
    }

    fn refuse_kill_for_next_execution() -> Arc<AtomicBool> {
        let retired = Arc::new(AtomicBool::new(false));
        NEXT_EXECUTION_FAULTS.with(|next| {
            let previous = next.borrow_mut().replace(ExecutionFaults {
                refuse_kill_once: true,
                retired: Some(Arc::clone(&retired)),
            });
            assert!(previous.is_none(), "an execution fault was already armed");
        });
        retired
    }

    struct AlwaysReadyReader;

    impl Read for AlwaysReadyReader {
        fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
            buffer.fill(b'x');
            Ok(buffer.len())
        }
    }

    #[test]
    fn read_ready_yields_after_budget_for_always_ready_reader() {
        let mut reader = AlwaysReadyReader;
        let mut output = Vec::new();
        let state = read_ready(&mut reader, &mut output, EXPECTED_READ_BUDGET * 8).unwrap();

        assert!(matches!(state, ReadState::Pending));
        assert!(
            output.len() > 0 && output.len() <= EXPECTED_READ_BUDGET,
            "read step exceeded its byte budget: {} > {}",
            output.len(),
            EXPECTED_READ_BUDGET
        );
        assert!(output.iter().all(|byte| *byte == b'x'));
    }

    struct FixtureDir(PathBuf);

    impl FixtureDir {
        fn new() -> Self {
            let nonce = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos();
            let path = std::env::temp_dir()
                .join(format!("rhai-process-owner-{}-{nonce}", std::process::id()));
            fs::create_dir(&path).unwrap();
            Self(path)
        }
    }

    impl Drop for FixtureDir {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }

    struct NestedTestChild {
        child: Child,
        release: PathBuf,
    }

    impl NestedTestChild {
        fn try_wait(&mut self) -> io::Result<Option<std::process::ExitStatus>> {
            self.child.try_wait()
        }
    }

    impl Drop for NestedTestChild {
        fn drop(&mut self) {
            // Always unblock the shell fixture before terminating the exact nested test process.
            let _ = release_fifo(&self.release);
            let deadline = Instant::now() + Duration::from_secs(1);
            loop {
                match self.child.try_wait() {
                    Ok(Some(_)) => return,
                    Ok(None) if Instant::now() < deadline => {
                        thread::sleep(Duration::from_millis(10));
                    }
                    Ok(None) => break,
                    Err(_) => return,
                }
            }
            let _ = self.child.kill();
            let reap_deadline = Instant::now() + Duration::from_secs(1);
            while Instant::now() < reap_deadline {
                match self.child.try_wait() {
                    Ok(Some(_)) => return,
                    Ok(None) => thread::sleep(Duration::from_millis(10)),
                    Err(_) => return,
                }
            }
        }
    }

    fn create_fifo(path: &Path) {
        let path = CString::new(path.as_os_str().as_bytes()).unwrap();
        // SAFETY: path is a live NUL-terminated path and mode is a valid permission mask.
        assert_eq!(unsafe { libc::mkfifo(path.as_ptr(), 0o600) }, 0);
    }

    fn release_fifo(path: &Path) -> io::Result<()> {
        let deadline = Instant::now() + Duration::from_secs(2);
        loop {
            match try_release_fifo(path) {
                Ok(()) => return Ok(()),
                Err(error)
                    if matches!(error.raw_os_error(), Some(libc::ENXIO) | Some(libc::ENOENT))
                        && Instant::now() < deadline =>
                {
                    thread::sleep(Duration::from_millis(5));
                }
                Err(error) => return Err(error),
            }
        }
    }

    fn try_release_fifo(path: &Path) -> io::Result<()> {
        let mut fifo = OpenOptions::new()
            .write(true)
            .custom_flags(libc::O_NONBLOCK)
            .open(path)?;
        fifo.write_all(b"release\n")
    }

    fn record_pid(path: &Path) -> io::Result<i32> {
        let record = fs::read_to_string(path)?;
        let value = record
            .strip_prefix("child-pid=")
            .and_then(|value| value.split_whitespace().next())
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "invalid child record"))?;
        value
            .parse::<i32>()
            .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))
    }

    fn assert_pid_alive(pid: i32) {
        // SAFETY: signal zero queries the exact recorded child PID and sends no signal.
        assert_eq!(
            unsafe { libc::kill(pid, 0) },
            0,
            "recorded child {pid} is not alive"
        );
    }

    fn assert_pid_reaped(pid: i32) {
        // SAFETY: signal zero queries only the exact, independently recorded child PID.
        assert_eq!(unsafe { libc::kill(pid, 0) }, -1);
        assert_eq!(io::Error::last_os_error().raw_os_error(), Some(libc::ESRCH));
    }

    fn wait_for_pid_reaped(pid: i32) {
        let deadline = Instant::now() + Duration::from_secs(2);
        loop {
            // SAFETY: signal zero queries only the exact PID from this fixture's atomic record.
            if unsafe { libc::kill(pid, 0) } == -1
                && io::Error::last_os_error().raw_os_error() == Some(libc::ESRCH)
            {
                return;
            }
            assert!(
                Instant::now() < deadline,
                "recorded child {pid} was not reaped"
            );
            thread::sleep(Duration::from_millis(10));
        }
    }

    fn quote_rhai(value: &str) -> String {
        format!("\"{}\"", value.replace('\\', "\\\\").replace('"', "\\\""))
    }

    #[cfg(not(feature = "no_float"))]
    fn run_inner_retained_owner_case() {
        let record = PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_RECORD").unwrap());
        let returned = PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_RETURNED").unwrap());
        let release = PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_RELEASE").unwrap());
        let retired = refuse_kill_for_next_execution();
        let mut engine = Engine::new();
        let package = SysPackage::new(
            SysConfig::default()
                .programs(ProgramPolicy::Any)
                .max_output(1024),
        )
        .unwrap();
        package.register_into_engine(&mut engine);

        let shell = format!(
            "tmp=\"$RHAI_TEST_OWNER_RECORD.tmp\"; printf 'child-pid=%s child-ready=1\\n' \"$$\" > \"$tmp\"; mv \"$tmp\" \"$RHAI_TEST_OWNER_RECORD\"; IFS= read -r value < \"$RHAI_TEST_OWNER_RELEASE\""
        );
        let script = format!(
            "run(\"/bin/sh\", #{{ stdin: {}, timeout: 0.1, max_output: 1024, env: #{{ \"RHAI_TEST_OWNER_RECORD\": {}, \"RHAI_TEST_OWNER_RELEASE\": {} }} }})",
            quote_rhai(&shell),
            quote_rhai(record.to_str().unwrap()),
            quote_rhai(release.to_str().unwrap()),
        );
        let started = Instant::now();
        let result = engine.eval::<crate::Map>(&script);
        assert!(
            started.elapsed() < Duration::from_secs(2),
            "public run blocked after termination refusal instead of returning boundedly"
        );
        let marker_tmp = returned.with_extension("tmp");
        fs::write(&marker_tmp, b"public-returned\n").unwrap();
        fs::rename(&marker_tmp, &returned).unwrap();
        let record_deadline = Instant::now() + Duration::from_secs(1);
        let child_pid = loop {
            if record.exists() {
                break record_pid(&record).unwrap();
            }
            assert!(
                Instant::now() < record_deadline,
                "child readiness record missing"
            );
            thread::sleep(Duration::from_millis(5));
        };
        let error = result.expect_err("deadline with refused termination must return an error");
        let sys_error = match error.as_ref() {
            EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>().unwrap(),
            other => panic!("expected SysError::Process, got {other:?}"),
        };
        let report = match &sys_error {
            SysError::Process { cause, report } => {
                assert!(matches!(cause, ProcessCause::Timeout(_)));
                report.clone()
            }
            other => panic!("expected timeout process error, got {other:?}"),
        };
        assert!(
            !report.timed_out(),
            "cleanup refusal cannot certify timeout completion"
        );
        assert!(!report.stdout_complete() && !report.stderr_complete());
        assert!(report
            .cleanup_diagnostics()
            .iter()
            .any(|diagnostic| diagnostic
                .message()
                .contains("injected one-shot termination refusal")));
        assert!(
            !retired.load(Ordering::Acquire),
            "owner retired while its child was live"
        );

        drop(sys_error);
        drop(report);
        drop(error);
        drop(engine);
        drop(package);
        assert_pid_alive(child_pid);
        assert!(
            !retired.load(Ordering::Acquire),
            "package drop discarded retained custody"
        );

        release_fifo(&release).unwrap();
        let cleanup_deadline = Instant::now() + Duration::from_secs(3);
        while !retired.load(Ordering::Acquire) && Instant::now() < cleanup_deadline {
            thread::sleep(Duration::from_millis(5));
        }
        assert!(
            retired.load(Ordering::Acquire),
            "retained owner did not retire after reap"
        );
        assert_pid_reaped(child_pid);
    }

    #[cfg(not(feature = "no_float"))]
    #[test]
    fn kill_refusal_returns_boundedly_and_retains_real_child_after_package_drop() {
        const CHILD_ROLE: &str = "RHAI_TEST_OWNER_CHILD_ROLE";
        const TEST_NAME: &str = "packages::sys::process::unix::tests::kill_refusal_returns_boundedly_and_retains_real_child_after_package_drop";

        if std::env::var_os(CHILD_ROLE).is_some() {
            run_inner_retained_owner_case();
            return;
        }

        let fixture = FixtureDir::new();
        let record = fixture.0.join("child-record");
        let returned = fixture.0.join("public-returned");
        let release = fixture.0.join("release.fifo");
        create_fifo(&release);
        let nested = Command::new(std::env::current_exe().unwrap())
            .args(["--exact", TEST_NAME, "--nocapture"])
            .env(CHILD_ROLE, "inner")
            .env("RHAI_TEST_OWNER_RECORD", &record)
            .env("RHAI_TEST_OWNER_RETURNED", &returned)
            .env("RHAI_TEST_OWNER_RELEASE", &release)
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .spawn()
            .unwrap();
        let mut nested = NestedTestChild {
            child: nested,
            release: release.clone(),
        };
        let started = Instant::now();
        let mut watchdog_released_fixture = false;
        let status = loop {
            if let Some(status) = nested.try_wait().unwrap() {
                break status;
            }
            if started.elapsed() >= Duration::from_secs(3)
                && !returned.exists()
                && !watchdog_released_fixture
            {
                assert!(
                    record.exists(),
                    "nested test did not publish child readiness"
                );
                let pid = record_pid(&record).unwrap();
                assert_pid_alive(pid);
                release_fifo(&release).unwrap();
                watchdog_released_fixture = true;
            }
            if started.elapsed() >= Duration::from_secs(8) {
                panic!("nested retained-owner test exceeded its external watchdog");
            }
            thread::sleep(Duration::from_millis(10));
        };
        if record.exists() {
            let pid = record_pid(&record).unwrap();
            println!(
                "retained-owner-red child_record={} pid={pid}",
                record.display()
            );
            wait_for_pid_reaped(pid);
            println!("retained-owner-red child_pid={pid} reap=ESRCH");
        }
        assert!(
            !watchdog_released_fixture,
            "external watchdog had to release the child; public run did not return boundedly"
        );
        assert!(
            status.success(),
            "nested retained-owner contract failed: {status}"
        );
    }
}
