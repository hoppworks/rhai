//! Native Unix child execution for the synchronous run contract.
use super::{ProcessCause, ProcessExit, ProcessReport};
use crate::packages::sys::{config::*, error::SysError, SysState};
use crate::{Array, Blob, Dynamic, ImmutableString, Map, Module, NativeCallContext, Shared, INT};
use std::ffi::OsStr;
use std::io::{self, Read, Write};
use std::os::fd::{AsRawFd, RawFd};
use std::os::unix::process::{CommandExt, ExitStatusExt};
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};

type Res<T> = Result<T, Box<crate::EvalAltResult>>;

pub(super) fn register(module: &mut Module, state: &Shared<SysState>) {
    let st = state.clone();
    crate::packages::sys::reg(
        "run_raw",
        &["/// Run a child program and return exact stdout and stderr bytes."],
    )
    .set_into_module(
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
    crate::packages::sys::reg("run", &["/// Run a child program with arguments."]).set_into_module(
        module,
        move |ctx: NativeCallContext, program: &str, args: Array| -> Res<Map> {
            let args = parse_args(args)?;
            run_map(&ctx, &st, program, &args, Map::new(), false)
        },
    );
}

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
    let known = [
        "cwd",
        "env",
        "env_clear",
        "env_remove",
        "stdin",
        "timeout",
        "max_output",
    ];
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
        Some(v) => {
            if let Some(bytes) = v.clone().try_cast::<Blob>() {
                Some(bytes)
            } else if let Some(text) = v.try_cast::<ImmutableString>() {
                Some(text.as_bytes().to_vec())
            } else {
                return Err(SysError::Denied(
                    "process option `stdin` must be a string or blob".into(),
                )
                .into());
            }
        }
    };
    let timeout = match options.remove("timeout") {
        None => state.config.default_timeout,
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
            if raw {
                ctx.engine().max_array_size()
            } else {
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

fn read_ready<R: Read>(
    reader: &mut R,
    output: &mut Vec<u8>,
    limit: usize,
) -> io::Result<ReadState> {
    let mut buf = [0u8; 8192];
    loop {
        let remaining = limit.saturating_sub(output.len());
        let count = if remaining == 0 {
            1
        } else {
            remaining.min(buf.len())
        };
        match reader.read(&mut buf[..count]) {
            Ok(0) => return Ok(ReadState::Eof),
            Ok(n) => {
                let keep = n.min(remaining);
                output.extend_from_slice(&buf[..keep]);
                if n > keep {
                    return Ok(ReadState::Overflow);
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
                        )
                    }
                }
            }
        }
        // Drain readable bytes first so observed output overflow wins when it coincides with
        // deadline expiry; otherwise the deadline owns the cancellation.
        if expired {
            return fail(
                child,
                program,
                ProcessCause::Timeout(format!("process `{program}` exceeded deadline")),
                out,
                err,
                out_eof,
                err_eof,
            );
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
) -> Result<ProcessReport, (ProcessCause, ProcessReport)> {
    let timed_out = matches!(&cause, ProcessCause::Timeout(_));
    let mut diagnostics = vec![];
    if let Err(e) = child.kill() {
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
    Err((
        cause,
        ProcessReport::new(out, err, out_eof, err_eof, exit, timed_out, diagnostics),
    ))
}
