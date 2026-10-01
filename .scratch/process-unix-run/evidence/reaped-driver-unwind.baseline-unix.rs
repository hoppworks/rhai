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
use std::process::{Child, ChildStderr, ChildStdin, ChildStdout, Command, Stdio};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, Condvar, Mutex};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};

const MAX_RETAINED_EXECUTIONS: usize = 64;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum OwnerPhase {
    Launching,
    Caller,
    CleanupPending,
    Service,
    Quarantined,
}

struct OwnerRecord {
    child: Option<Child>,
    phase: OwnerPhase,
    pump_finished: bool,
    reaped: bool,
    retired: Option<Arc<AtomicBool>>,
    #[cfg(test)]
    service_gate: Option<Arc<AtomicBool>>,
}

struct OwnerRegistry {
    records: Mutex<Vec<Arc<Mutex<OwnerRecord>>>>,
    changed: Condvar,
    outstanding: AtomicUsize,
    closing: AtomicBool,
    worker_done: AtomicBool,
    worker: Mutex<Option<JoinHandle<()>>>,
}

/// Package-local retained ownership for executions whose caller cannot finish cleanup.
/// The worker owns only OS child records and synchronization primitives.
pub(in crate::packages::sys) struct CleanupService {
    registry: Arc<OwnerRegistry>,
}

impl CleanupService {
    pub(in crate::packages::sys) fn new() -> Self {
        Self {
            registry: Arc::new(OwnerRegistry {
                records: Mutex::new(Vec::new()),
                changed: Condvar::new(),
                outstanding: AtomicUsize::new(0),
                closing: AtomicBool::new(false),
                worker_done: AtomicBool::new(true),
                worker: Mutex::new(None),
            }),
        }
    }

    fn reserve(
        &self,
        retired: Option<Arc<AtomicBool>>,
        #[cfg(test)] service_gate: Option<Arc<AtomicBool>>,
    ) -> io::Result<LaunchReservation> {
        self.ensure_worker()?;
        let mut current = self.registry.outstanding.load(Ordering::Acquire);
        loop {
            if current >= MAX_RETAINED_EXECUTIONS {
                return Err(io::Error::new(
                    io::ErrorKind::WouldBlock,
                    "process cleanup capacity is full",
                ));
            }
            match self.registry.outstanding.compare_exchange_weak(
                current,
                current + 1,
                Ordering::AcqRel,
                Ordering::Acquire,
            ) {
                Ok(_) => break,
                Err(next) => current = next,
            }
        }
        let record = Arc::new(Mutex::new(OwnerRecord {
            child: None,
            phase: OwnerPhase::Launching,
            pump_finished: false,
            reaped: false,
            retired,
            #[cfg(test)]
            service_gate,
        }));
        self.registry
            .records
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
            .push(record.clone());
        Ok(LaunchReservation {
            registry: self.registry.clone(),
            record,
            active: true,
        })
    }

    fn ensure_worker(&self) -> io::Result<()> {
        let mut worker = self
            .registry
            .worker
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        if worker.is_some() {
            return Ok(());
        }
        self.registry.closing.store(false, Ordering::Release);
        self.registry.worker_done.store(false, Ordering::Release);
        let registry = self.registry.clone();
        let handle = thread::Builder::new()
            .name("rhai-sys-process-cleanup".into())
            .spawn(move || cleanup_worker(registry))?;
        *worker = Some(handle);
        Ok(())
    }
}

impl Drop for CleanupService {
    fn drop(&mut self) {
        self.registry.closing.store(true, Ordering::Release);
        self.registry.changed.notify_all();
        // Dropping the JoinHandle is non-blocking. The worker owns the registry until every
        // retained child is reaped or quarantined; it exits itself after package closure.
    }
}

fn cleanup_worker(registry: Arc<OwnerRegistry>) {
    loop {
        let records = registry
            .records
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
            .clone();
        let mut progressed = false;
        for record in records {
            let mut child = {
                let mut owner = record
                    .lock()
                    .unwrap_or_else(|poisoned| poisoned.into_inner());
                if owner.phase != OwnerPhase::CleanupPending || !owner.pump_finished {
                    continue;
                }
                #[cfg(test)]
                if owner
                    .service_gate
                    .as_ref()
                    .is_some_and(|gate| !gate.load(Ordering::Acquire))
                {
                    continue;
                }
                owner.phase = OwnerPhase::Service;
                owner.child.take()
            };
            let Some(mut child_value) = child.take() else {
                continue;
            };
            let observation = child_value.try_wait();
            let (retire, quarantined) = match observation {
                Ok(Some(_)) => (true, false),
                Ok(None) => (false, false),
                Err(error) if error.raw_os_error() == Some(libc::ECHILD) => (false, true),
                Err(_) => (false, false),
            };
            if retire {
                let retired = record
                    .lock()
                    .unwrap_or_else(|poisoned| poisoned.into_inner())
                    .retired
                    .clone();
                if let Some(retired) = retired {
                    retired.store(true, Ordering::Release);
                }
                registry
                    .records
                    .lock()
                    .unwrap_or_else(|poisoned| poisoned.into_inner())
                    .retain(|candidate| !Arc::ptr_eq(candidate, &record));
                registry.outstanding.fetch_sub(1, Ordering::AcqRel);
                progressed = true;
            } else {
                let mut owner = record
                    .lock()
                    .unwrap_or_else(|poisoned| poisoned.into_inner());
                owner.child = Some(child_value);
                owner.phase = if quarantined {
                    OwnerPhase::Quarantined
                } else {
                    OwnerPhase::CleanupPending
                };
            }
        }
        if registry.closing.load(Ordering::Acquire)
            && registry.outstanding.load(Ordering::Acquire) == 0
        {
            registry.worker_done.store(true, Ordering::Release);
            return;
        }
        if !progressed {
            let guard = registry
                .records
                .lock()
                .unwrap_or_else(|poisoned| poisoned.into_inner());
            let _ = registry
                .changed
                .wait_timeout(guard, Duration::from_millis(20))
                .unwrap_or_else(|poisoned| poisoned.into_inner());
        }
    }
}

struct LaunchReservation {
    registry: Arc<OwnerRegistry>,
    record: Arc<Mutex<OwnerRecord>>,
    active: bool,
}

impl LaunchReservation {
    fn adopt(&mut self, child: Child) {
        let mut owner = self
            .record
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        owner.child = Some(child);
        owner.phase = OwnerPhase::Caller;
    }

    fn drive(&mut self) -> DriverToken<'_> {
        let child = {
            let mut owner = self
                .record
                .lock()
                .unwrap_or_else(|poisoned| poisoned.into_inner());
            debug_assert_eq!(owner.phase, OwnerPhase::Caller);
            owner.child.take().expect("adopted process child")
        };
        DriverToken {
            reservation: self,
            child: Some(child),
            completed: false,
            termination_attempted: false,
            reaped: false,
            exit_status: None,
        }
    }

    fn finish(&mut self) {
        if !self.active {
            return;
        }
        self.registry
            .records
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
            .retain(|candidate| !Arc::ptr_eq(candidate, &self.record));
        self.registry.outstanding.fetch_sub(1, Ordering::AcqRel);
        self.active = false;
    }

    fn handoff(&mut self, child: Child) {
        {
            let mut owner = self
                .record
                .lock()
                .unwrap_or_else(|poisoned| poisoned.into_inner());
            owner.child = Some(child);
            owner.phase = OwnerPhase::CleanupPending;
        }
        self.registry.changed.notify_all();
        self.active = false;
    }
}

impl Drop for LaunchReservation {
    fn drop(&mut self) {
        if self.active {
            let (child, launching) = {
                let mut owner = self
                    .record
                    .lock()
                    .unwrap_or_else(|poisoned| poisoned.into_inner());
                (owner.child.take(), owner.phase == OwnerPhase::Launching)
            };
            if let Some(mut child) = child {
                child.stdin.take();
                child.stdout.take();
                child.stderr.take();
                let _ = child.kill();
                let mut owner = self
                    .record
                    .lock()
                    .unwrap_or_else(|poisoned| poisoned.into_inner());
                owner.child = Some(child);
                owner.phase = OwnerPhase::CleanupPending;
                owner.pump_finished = true;
                self.registry.changed.notify_all();
                self.active = false;
            } else if launching {
                self.finish();
            }
        }
    }
}

struct DriverToken<'a> {
    reservation: &'a mut LaunchReservation,
    child: Option<Child>,
    completed: bool,
    termination_attempted: bool,
    reaped: bool,
    exit_status: Option<std::process::ExitStatus>,
}

impl DriverToken<'_> {
    fn child_mut(&mut self) -> &mut Child {
        self.child.as_mut().expect("active process driver")
    }

    fn observe_reaped(&mut self, status: std::process::ExitStatus) {
        self.reaped = true;
        self.exit_status = Some(status);
        self.reservation
            .record
            .lock()
            .unwrap_or_else(|p| p.into_inner())
            .reaped = true;
    }

    fn relinquish(&mut self) {
        if let Some(child) = self.child.take() {
            self.reservation.handoff(child);
        }
        self.completed = true;
    }

    fn quarantine(&mut self) {
        if let Some(child) = self.child.take() {
            let mut owner = self
                .reservation
                .record
                .lock()
                .unwrap_or_else(|poisoned| poisoned.into_inner());
            owner.child = Some(child);
            owner.phase = OwnerPhase::Quarantined;
        }
        self.reservation.active = false;
        self.completed = true;
    }

    fn pump_guard(&self) -> PumpGuard {
        PumpGuard {
            record: self.reservation.record.clone(),
            registry: self.reservation.registry.clone(),
            finished: false,
        }
    }
}

impl Drop for DriverToken<'_> {
    fn drop(&mut self) {
        if !self.completed {
            if self.reaped {
                // A child already observed as reaped must never be waited or signaled again.
                self.child.take();
                self.reservation.active = false;
                self.completed = true;
                return;
            }
            if !self.termination_attempted {
                if let Some(child) = self.child.as_mut() {
                    let _ = child.kill();
                }
            }
            if let Some(mut child) = self.child.take() {
                child.stdin.take();
                child.stdout.take();
                child.stderr.take();
                self.reservation
                    .record
                    .lock()
                    .unwrap_or_else(|p| p.into_inner())
                    .pump_finished = true;
                self.reservation.handoff(child);
            }
        }
    }
}

struct PumpGuard {
    record: Arc<Mutex<OwnerRecord>>,
    registry: Arc<OwnerRegistry>,
    finished: bool,
}

impl PumpGuard {
    fn finish(&mut self) {
        if !self.finished {
            let reaped = {
                let mut record = self.record.lock().unwrap_or_else(|p| p.into_inner());
                record.pump_finished = true;
                record.reaped
            };
            if reaped {
                let retired = self
                    .record
                    .lock()
                    .unwrap_or_else(|p| p.into_inner())
                    .retired
                    .clone();
                if let Some(retired) = retired {
                    retired.store(true, Ordering::Release);
                }
                self.registry
                    .records
                    .lock()
                    .unwrap_or_else(|p| p.into_inner())
                    .retain(|candidate| !Arc::ptr_eq(candidate, &self.record));
                self.registry.outstanding.fetch_sub(1, Ordering::AcqRel);
            }
            self.registry.changed.notify_all();
            self.finished = true;
        }
    }
}

impl Drop for PumpGuard {
    fn drop(&mut self) {
        self.finish();
    }
}

/// Private, per-execution fault adapter used only by host unit tests.
///
/// The plan is consumed immediately before spawn and then carried with that exact execution;
/// there is no script-visible switch and no process-global fault state.
#[derive(Default)]
struct ExecutionFaults {
    #[cfg(test)]
    refuse_kill_once: bool,
    #[cfg(test)]
    fail_cleanup_wait_once: bool,
    #[cfg(test)]
    fail_configure_pipe_once: bool,
    #[cfg(test)]
    configure_pipe_gate: Option<std::path::PathBuf>,
    #[cfg(test)]
    retired: Option<std::sync::Arc<std::sync::atomic::AtomicBool>>,
    #[cfg(test)]
    service_gate: Option<std::sync::Arc<std::sync::atomic::AtomicBool>>,
    #[cfg(test)]
    interrupt_polls_remaining: usize,
    #[cfg(test)]
    injected_poll_interrupts: Option<std::sync::Arc<std::sync::atomic::AtomicUsize>>,
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

    #[cfg(test)]
    fn interrupt_poll(&mut self) -> bool {
        if self.interrupt_polls_remaining == 0 {
            return false;
        }
        self.interrupt_polls_remaining -= 1;
        if let Some(count) = &self.injected_poll_interrupts {
            count.fetch_add(1, Ordering::AcqRel);
        }
        true
    }

    fn retirement_probe(&self) -> Option<Arc<AtomicBool>> {
        #[cfg(test)]
        {
            self.retired.clone()
        }
        #[cfg(not(test))]
        {
            None
        }
    }

    #[cfg(test)]
    fn service_gate_probe(&self) -> Option<Arc<AtomicBool>> {
        self.service_gate.clone()
    }

    fn cleanup_wait(&mut self, child: &mut Child) -> io::Result<Option<std::process::ExitStatus>> {
        #[cfg(test)]
        if self.fail_cleanup_wait_once {
            self.fail_cleanup_wait_once = false;
            return Err(io::Error::new(
                io::ErrorKind::Other,
                "injected non-consuming cleanup wait failure",
            ));
        }
        child.try_wait()
    }

    fn configure_pipe(&mut self, fd: RawFd) -> io::Result<()> {
        #[cfg(test)]
        if self.fail_configure_pipe_once {
            self.fail_configure_pipe_once = false;
            let gate = self
                .configure_pipe_gate
                .take()
                .expect("test setup fault must have a release gate");
            let deadline = std::time::Instant::now() + std::time::Duration::from_secs(5);
            while !gate.exists() {
                if std::time::Instant::now() >= deadline {
                    return Err(io::Error::new(
                        io::ErrorKind::TimedOut,
                        "fixture did not release injected pipe-configuration failure",
                    ));
                }
                std::thread::sleep(std::time::Duration::from_millis(5));
            }
            return Err(io::Error::new(
                io::ErrorKind::Other,
                "injected post-spawn pipe configuration failure",
            ));
        }
        set_nonblock(fd)
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
    let mut faults = ExecutionFaults::take_for_execution();
    let mut reservation = {
        #[cfg(test)]
        {
            state
                .cleanup
                .reserve(faults.retirement_probe(), faults.service_gate_probe())
        }
        #[cfg(not(test))]
        {
            state.cleanup.reserve(faults.retirement_probe())
        }
    }
    .map_err(|e| SysError::io("reserve process cleanup", program, &e))?;
    // The monotonic deadline begins immediately before process creation.
    let started = Instant::now();
    let child = command
        .spawn()
        .map_err(|e| SysError::io("spawn process", program, &e))?;
    // Put the OS owner in the retained registry before any post-spawn pipe operation.
    reservation.adopt(child);
    let driver = reservation.drive();
    let result = supervise(
        driver,
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
    let mut interrupted = 0;
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
                interrupted = 0;
                if consumed >= READ_BUDGET {
                    return Ok(ReadState::Pending);
                }
            }
            Err(e) if e.kind() == io::ErrorKind::WouldBlock => return Ok(ReadState::Pending),
            Err(e) if e.kind() == io::ErrorKind::Interrupted => {
                interrupted += 1;
                if interrupted >= 8 {
                    return Ok(ReadState::Pending);
                }
            }
            Err(e) => return Err(e),
        }
    }
}

fn supervise(
    mut driver: DriverToken<'_>,
    program: &str,
    input: Option<Vec<u8>>,
    limit: usize,
    timeout: Option<Duration>,
    started: Instant,
    faults: &mut ExecutionFaults,
) -> Result<ProcessReport, (ProcessCause, ProcessReport)> {
    let mut pump_guard = driver.pump_guard();
    let child = driver.child_mut();
    let mut stdout = Some(child.stdout.take().unwrap());
    let mut stderr = Some(child.stderr.take().unwrap());
    let mut stdin = child.stdin.take();
    let outfd = stdout.as_ref().unwrap().as_raw_fd();
    let errfd = stderr.as_ref().unwrap().as_raw_fd();
    let infd = stdin.as_ref().map(AsRawFd::as_raw_fd);
    for fd in [Some(outfd), Some(errfd), infd].into_iter().flatten() {
        if let Err(e) = faults.configure_pipe(fd) {
            return fail(
                &mut driver,
                &mut stdin,
                &mut stdout,
                &mut stderr,
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
        let mut expired = timeout.is_some_and(|t| started.elapsed() >= t);
        if !driver.reaped {
            match driver.child_mut().try_wait() {
                Ok(s) => {
                    if let Some(value) = s.as_ref() {
                        driver.observe_reaped(value.clone());
                    }
                    status = s;
                }
                Err(e) => {
                    return fail(
                        &mut driver,
                        &mut stdin,
                        &mut stdout,
                        &mut stderr,
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
                        e.raw_os_error() == Some(libc::ECHILD),
                    )
                }
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
        #[cfg(test)]
        let injected_interrupt = faults.interrupt_poll();
        #[cfg(test)]
        let rc = if injected_interrupt {
            -1
        } else {
            unsafe { libc::poll(fds.as_mut_ptr(), fds.len() as libc::nfds_t, millis) }
        };
        #[cfg(not(test))]
        let rc = unsafe { libc::poll(fds.as_mut_ptr(), fds.len() as libc::nfds_t, millis) };
        if rc < 0 {
            #[cfg(test)]
            let e = if injected_interrupt {
                io::Error::new(io::ErrorKind::Interrupted, "injected poll interruption")
            } else {
                io::Error::last_os_error()
            };
            #[cfg(not(test))]
            let e = io::Error::last_os_error();
            if e.kind() == io::ErrorKind::Interrupted {
                expired = timeout.is_some_and(|t| started.elapsed() >= t);
                if !expired {
                    thread::sleep(Duration::from_millis(1));
                    continue;
                }
                // An interrupted poll has no usable readiness result. Let the ordinary
                // timeout cleanup run without treating indeterminate revents as output.
                for descriptor in &mut fds {
                    descriptor.revents = 0;
                }
            } else {
                return fail(
                    &mut driver,
                    &mut stdin,
                    &mut stdout,
                    &mut stderr,
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
                    false,
                );
            }
        }
        if fds[0].revents != 0 {
            match read_ready(stdout.as_mut().unwrap(), &mut out, limit) {
                Ok(ReadState::Overflow) => {
                    return fail(
                        &mut driver,
                        &mut stdin,
                        &mut stdout,
                        &mut stderr,
                        ProcessCause::OutputLimit(format!(
                            "process `{program}` exceeded {limit} output bytes"
                        )),
                        out,
                        err,
                        out_eof,
                        err_eof,
                        faults,
                        false,
                    )
                }
                Ok(ReadState::Eof) => out_eof = true,
                Ok(ReadState::Pending) => {}
                Err(e) => {
                    return fail(
                        &mut driver,
                        &mut stdin,
                        &mut stdout,
                        &mut stderr,
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
                        false,
                    )
                }
            }
        }
        if fds[1].revents != 0 {
            match read_ready(stderr.as_mut().unwrap(), &mut err, limit) {
                Ok(ReadState::Overflow) => {
                    return fail(
                        &mut driver,
                        &mut stdin,
                        &mut stdout,
                        &mut stderr,
                        ProcessCause::OutputLimit(format!(
                            "process `{program}` exceeded {limit} output bytes"
                        )),
                        out,
                        err,
                        out_eof,
                        err_eof,
                        faults,
                        false,
                    )
                }
                Ok(ReadState::Eof) => err_eof = true,
                Ok(ReadState::Pending) => {}
                Err(e) => {
                    return fail(
                        &mut driver,
                        &mut stdin,
                        &mut stdout,
                        &mut stderr,
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
                        false,
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
                            &mut driver,
                            &mut stdin,
                            &mut stdout,
                            &mut stderr,
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
                            false,
                        )
                    }
                }
            }
        }
        // Drain readable bytes first so observed output overflow wins when it coincides with
        // deadline expiry; otherwise the deadline owns the cancellation.
        if expired {
            let (cause, report) = fail(
                &mut driver,
                &mut stdin,
                &mut stdout,
                &mut stderr,
                ProcessCause::Timeout(format!("process `{program}` exceeded deadline")),
                out,
                err,
                out_eof,
                err_eof,
                faults,
                false,
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
    driver.observe_reaped(status.clone());
    let exit = status
        .code()
        .map(ProcessExit::Code)
        .or_else(|| status.signal().map(ProcessExit::Signal));
    drop(stdin);
    drop(stdout);
    drop(stderr);
    pump_guard.finish();
    driver.completed = true;
    driver.reservation.active = false;
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
    driver: &mut DriverToken<'_>,
    stdin: &mut Option<ChildStdin>,
    stdout: &mut Option<ChildStdout>,
    stderr: &mut Option<ChildStderr>,
    cause: ProcessCause,
    out: Vec<u8>,
    err: Vec<u8>,
    out_eof: bool,
    err_eof: bool,
    faults: &mut ExecutionFaults,
    mut identity_lost: bool,
) -> Result<ProcessReport, (ProcessCause, ProcessReport)> {
    // Stop every pipe operation before signaling or observing cleanup. No caller-side I/O
    // endpoint remains active once this execution commits to its primary failure.
    stdin.take();
    stdout.take();
    stderr.take();
    let is_timeout = matches!(&cause, ProcessCause::Timeout(_));
    let mut diagnostics = vec![];
    if identity_lost {
        diagnostics.push(super::ProcessDiagnostic::new(
            "reap child",
            None,
            "child custody was lost; owner quarantined",
        ));
    } else if !driver.reaped {
        driver.termination_attempted = true;
        if let Err(e) = faults.kill(driver.child_mut()) {
            diagnostics.push(super::ProcessDiagnostic::new(
                "kill child",
                Some(e.kind()),
                e.to_string(),
            ));
        }
    }
    let cleanup_deadline = Instant::now() + Duration::from_secs(1);
    let mut status = driver.exit_status.clone();
    let mut interrupted = 0u8;
    while !identity_lost && !driver.reaped && Instant::now() < cleanup_deadline {
        match faults.cleanup_wait(driver.child_mut()) {
            Ok(Some(value)) => {
                driver.observe_reaped(value.clone());
                status = Some(value);
                break;
            }
            Ok(None) => thread::sleep(Duration::from_millis(10)),
            Err(error) if error.raw_os_error() == Some(libc::ECHILD) => {
                identity_lost = true;
                diagnostics.push(super::ProcessDiagnostic::new(
                    "reap child",
                    Some(error.kind()),
                    "child custody was lost; owner quarantined",
                ));
                break;
            }
            Err(error) if error.kind() == io::ErrorKind::Interrupted => {
                interrupted = interrupted.saturating_add(1);
                if interrupted >= 8 {
                    diagnostics.push(super::ProcessDiagnostic::new(
                        "reap child",
                        Some(error.kind()),
                        "cleanup wait remained interrupted; owner retained",
                    ));
                    break;
                }
                thread::sleep(Duration::from_millis(10));
            }
            Err(error) => {
                diagnostics.push(super::ProcessDiagnostic::new(
                    "reap child",
                    Some(error.kind()),
                    error.to_string(),
                ));
                // This is an operational, non-consuming failure. Do not retry in the same
                // foreground pass: freeze the incomplete report and hand the Child to service.
                break;
            }
        }
    }
    if status.is_none() {
        if !diagnostics.iter().any(|d| d.operation() == "reap child") {
            diagnostics.push(super::ProcessDiagnostic::new(
                "reap child",
                None,
                "cleanup remains pending under retained process ownership",
            ));
        }
        if identity_lost {
            driver.quarantine();
        } else {
            driver.relinquish();
        }
    } else if driver.reaped {
        driver.completed = true;
        driver.reservation.active = false;
    }
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
    use super::{read_ready, CleanupService, ExecutionFaults, ReadState};
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
    use std::panic::{catch_unwind, AssertUnwindSafe};
    use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
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
                fail_cleanup_wait_once: false,
                fail_configure_pipe_once: false,
                configure_pipe_gate: None,
                retired: Some(Arc::clone(&retired)),
                service_gate: None,
                interrupt_polls_remaining: 0,
                injected_poll_interrupts: None,
            });
            assert!(previous.is_none(), "an execution fault was already armed");
        });
        retired
    }

    fn fail_cleanup_wait_for_next_execution() -> (Arc<AtomicBool>, Arc<AtomicBool>) {
        let retired = Arc::new(AtomicBool::new(false));
        let service_gate = Arc::new(AtomicBool::new(false));
        NEXT_EXECUTION_FAULTS.with(|next| {
            let previous = next.borrow_mut().replace(ExecutionFaults {
                refuse_kill_once: false,
                fail_cleanup_wait_once: true,
                fail_configure_pipe_once: false,
                configure_pipe_gate: None,
                retired: Some(Arc::clone(&retired)),
                service_gate: Some(Arc::clone(&service_gate)),
                interrupt_polls_remaining: 0,
                injected_poll_interrupts: None,
            });
            assert!(previous.is_none(), "an execution fault was already armed");
        });
        (retired, service_gate)
    }

    fn fail_pipe_setup_for_next_execution(gate: PathBuf) -> Arc<AtomicBool> {
        let retired = Arc::new(AtomicBool::new(false));
        NEXT_EXECUTION_FAULTS.with(|next| {
            let previous = next.borrow_mut().replace(ExecutionFaults {
                refuse_kill_once: false,
                fail_cleanup_wait_once: false,
                fail_configure_pipe_once: true,
                configure_pipe_gate: Some(gate),
                retired: Some(Arc::clone(&retired)),
                service_gate: None,
                interrupt_polls_remaining: 0,
                injected_poll_interrupts: None,
            });
            assert!(previous.is_none(), "an execution fault was already armed");
        });
        retired
    }

    #[cfg(not(feature = "no_float"))]
    fn interrupt_polls_for_next_execution(count: usize) -> Arc<std::sync::atomic::AtomicUsize> {
        let observed = Arc::new(std::sync::atomic::AtomicUsize::new(0));
        NEXT_EXECUTION_FAULTS.with(|next| {
            let previous = next.borrow_mut().replace(ExecutionFaults {
                refuse_kill_once: false,
                fail_cleanup_wait_once: false,
                fail_configure_pipe_once: false,
                configure_pipe_gate: None,
                retired: None,
                service_gate: None,
                interrupt_polls_remaining: count,
                injected_poll_interrupts: Some(Arc::clone(&observed)),
            });
            assert!(previous.is_none(), "an execution fault was already armed");
        });
        observed
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

    fn register_completed_service_child(
        service: &CleanupService,
        cleanup_guard: &mut ReleaseServiceOwnersOnDrop,
        retired: Arc<AtomicBool>,
        service_gate: Arc<AtomicBool>,
    ) -> i32 {
        let guard_retired = Arc::clone(&retired);
        let guard_gate = Arc::clone(&service_gate);
        let mut reservation = service
            .reserve(Some(retired), Some(service_gate))
            .expect("reserve service fairness child");
        cleanup_guard.owners.push((guard_gate, guard_retired));
        let child = Command::new("/bin/sh")
            .args(["-c", "exit 0"])
            .spawn()
            .expect("spawn service fairness child");
        let pid = child.id() as i32;
        reservation.adopt(child);
        let mut driver = reservation.drive();
        driver.relinquish();
        drop(driver);
        {
            let mut owner = reservation.record.lock().unwrap();
            owner.pump_finished = true;
            owner.phase = super::OwnerPhase::CleanupPending;
        }
        service.registry.changed.notify_all();
        pid
    }

    fn wait_for_retired(retired: &AtomicBool, deadline: Instant, message: &str) {
        while !retired.load(Ordering::Acquire) && Instant::now() < deadline {
            thread::sleep(Duration::from_millis(5));
        }
        assert!(retired.load(Ordering::Acquire), "{message}");
    }

    #[test]
    fn reaped_driver_unwind_retires_completed_owner_once() {
        let service = CleanupService::new();
        let retired = Arc::new(AtomicBool::new(false));
        let child_pid = Arc::new(AtomicUsize::new(0));
        let registry = service.registry.clone();
        let pid_receipt = Arc::clone(&child_pid);
        let result = catch_unwind(AssertUnwindSafe(|| {
            let mut reservation = service
                .reserve(Some(Arc::clone(&retired)), None)
                .expect("reserve direct child cleanup slot");
            let child = Command::new("/bin/sh")
                .args(["-c", "exit 0"])
                .stdin(Stdio::null())
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .expect("spawn reaped-driver fixture");
            let pid = child.id() as i32;
            pid_receipt.store(pid as usize, Ordering::Release);
            reservation.adopt(child);
            let owner_record = Arc::clone(&reservation.record);
            let mut driver = reservation.drive();
            let status = driver.child_mut().wait().expect("wait for fixture child");
            assert!(status.success(), "fixture child did not exit successfully");
            driver.observe_reaped(status);
            {
                let mut owner = owner_record
                    .lock()
                    .unwrap_or_else(|poisoned| poisoned.into_inner());
                owner.pump_finished = true;
            }
            eprintln!("reaped-driver-unwind child_pid={pid} has_been_waited=true");
            panic!("injected caller unwind after child reap and pump completion");
        }));
        assert!(result.is_err(), "fixture did not exercise caller unwind");
        let pid = child_pid.load(Ordering::Acquire) as i32;
        assert!(pid > 0, "fixture child PID was not recorded");
        assert_pid_reaped(pid);
        eprintln!("reaped-driver-unwind child_pid={pid} reap=ESRCH");
        assert!(
            retired.load(Ordering::Acquire),
            "reaped owner slot was not retired"
        );
        assert_eq!(registry.outstanding.load(Ordering::Acquire), 0);
        assert!(registry.records.lock().unwrap().is_empty());
        drop(service);
        wait_for_retired(
            &registry.worker_done,
            Instant::now() + Duration::from_secs(1),
            "cleanup worker did not stop after unwind retirement",
        );
    }


    fn assert_pid_present(pid: i32) {
        let result = unsafe { libc::kill(pid, 0) };
        assert_eq!(
            result, 0,
            "expected retained child pid={pid} to remain unreaped"
        );
    }

    struct ReleaseServiceOwnersOnDrop {
        registry: Arc<super::OwnerRegistry>,
        owners: Vec<(Arc<AtomicBool>, Arc<AtomicBool>)>,
    }

    impl Drop for ReleaseServiceOwnersOnDrop {
        fn drop(&mut self) {
            for (gate, _) in &self.owners {
                gate.store(true, Ordering::Release);
            }
            self.registry.changed.notify_all();
            let deadline = Instant::now() + Duration::from_secs(3);
            while self
                .owners
                .iter()
                .any(|(_, retired)| !retired.load(Ordering::Acquire))
                && Instant::now() < deadline
            {
                thread::sleep(Duration::from_millis(5));
            }
        }
    }

    #[test]
    fn cleanup_service_progresses_past_a_stalled_owner() {
        let service = CleanupService::new();
        let registry = service.registry.clone();
        let mut cleanup_guard = ReleaseServiceOwnersOnDrop {
            registry: registry.clone(),
            owners: Vec::new(),
        };
        let first_retired = Arc::new(AtomicBool::new(false));
        let first_gate = Arc::new(AtomicBool::new(false));
        let first_pid = register_completed_service_child(
            &service,
            &mut cleanup_guard,
            first_retired.clone(),
            first_gate.clone(),
        );
        eprintln!("owner_service_child first pid={first_pid}");

        let second_retired = Arc::new(AtomicBool::new(false));
        let second_gate = Arc::new(AtomicBool::new(true));
        let second_pid = register_completed_service_child(
            &service,
            &mut cleanup_guard,
            second_retired.clone(),
            second_gate.clone(),
        );
        eprintln!("owner_service_child second pid={second_pid}");
        wait_for_retired(
            &second_retired,
            Instant::now() + Duration::from_secs(3),
            "stalled owner prevented another retained child from being reaped",
        );
        assert_pid_present(first_pid);
        assert_pid_reaped(second_pid);
        eprintln!("owner_service_checkpoint first_pid={first_pid} first_retired={} second_pid={second_pid} second=ESRCH", first_retired.load(Ordering::Acquire));
        assert!(!first_retired.load(Ordering::Acquire));

        first_gate.store(true, Ordering::Release);
        registry.changed.notify_all();
        wait_for_retired(
            &first_retired,
            Instant::now() + Duration::from_secs(3),
            "released retained child was not reaped",
        );
        assert_pid_reaped(first_pid);
        eprintln!("owner_service_final first_pid={first_pid} second_pid={second_pid} both=ESRCH");

        drop(cleanup_guard);
        drop(service);
        wait_for_retired(
            &registry.worker_done,
            Instant::now() + Duration::from_secs(1),
            "cleanup worker did not stop after all retained owners retired",
        );
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
        setup_gate: Option<PathBuf>,
    }

    impl NestedTestChild {
        fn try_wait(&mut self) -> io::Result<Option<std::process::ExitStatus>> {
            self.child.try_wait()
        }
    }

    impl Drop for NestedTestChild {
        fn drop(&mut self) {
            // Always unblock the shell fixture before terminating the exact nested test process.
            if let Some(gate) = &self.setup_gate {
                let _ = fs::write(gate, b"release\n");
            }
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

    struct ReleaseFifoOnDrop {
        fifo: Option<PathBuf>,
        record: PathBuf,
    }

    impl ReleaseFifoOnDrop {
        fn finish(&mut self) {
            self.fifo = None;
        }
    }

    impl Drop for ReleaseFifoOnDrop {
        fn drop(&mut self) {
            if let Some(path) = self.fifo.take() {
                let _ = release_fifo(&path);
                if let Ok(pid) = record_pid(&self.record) {
                    let deadline = Instant::now() + Duration::from_secs(2);
                    loop {
                        // SAFETY: checks only the exact PID atomically written by this fixture.
                        if unsafe { libc::kill(pid, 0) } == -1
                            && io::Error::last_os_error().raw_os_error() == Some(libc::ESRCH)
                        {
                            eprintln!("interrupted-poll unwind_cleanup pid={pid} reap=ESRCH");
                            break;
                        }
                        if Instant::now() >= deadline {
                            eprintln!("interrupted-poll unwind_cleanup pid={pid} reap=unconfirmed");
                            break;
                        }
                        thread::sleep(Duration::from_millis(10));
                    }
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
        send_fifo_message(path, b"release\n")
    }

    fn send_fifo_message(path: &Path, message: &[u8]) -> io::Result<()> {
        let deadline = Instant::now() + Duration::from_secs(2);
        loop {
            match try_write_fifo(path, message) {
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
        try_write_fifo(path, b"release\n")
    }

    fn try_write_fifo(path: &Path, message: &[u8]) -> io::Result<()> {
        let mut fifo = OpenOptions::new()
            .write(true)
            .custom_flags(libc::O_NONBLOCK)
            .open(path)?;
        fifo.write_all(message)
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

    fn record_field_pid(path: &Path, field: &str) -> io::Result<i32> {
        let record = fs::read_to_string(path)?;
        let prefix = format!("{field}=");
        let value = record
            .split_whitespace()
            .find_map(|part| part.strip_prefix(&prefix))
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "invalid PID record"))?;
        value
            .parse::<i32>()
            .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))
    }

    fn map_bool(map: &crate::Map, key: &str) -> bool {
        map.get(key)
            .expect("process result map key missing")
            .clone()
            .try_cast::<bool>()
            .expect("process result map key has wrong type")
    }

    fn map_int(map: &crate::Map, key: &str) -> crate::INT {
        map.get(key)
            .expect("process result map key missing")
            .clone()
            .try_cast::<crate::INT>()
            .expect("process result map key has wrong type")
    }

    fn map_string<'a>(map: &'a crate::Map, key: &str) -> String {
        map.get(key)
            .expect("process result map key missing")
            .clone()
            .try_cast::<String>()
            .expect("process result map key has wrong type")
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

    #[cfg(not(feature = "no_float"))]
    #[test]
    fn interrupted_poll_does_not_skip_public_deadline() {
        const INTERRUPTIONS: usize = 3_000;
        let fixture = FixtureDir::new();
        let record = fixture.0.join("child-record");
        let release = fixture.0.join("release.fifo");
        create_fifo(&release);
        let mut release_on_unwind = ReleaseFifoOnDrop {
            fifo: Some(release.clone()),
            record: record.clone(),
        };
        let observed = interrupt_polls_for_next_execution(INTERRUPTIONS);

        let mut engine = Engine::new();
        let package = SysPackage::new(
            SysConfig::default()
                .programs(ProgramPolicy::Any)
                .max_output(1024),
        )
        .unwrap();
        package.register_into_engine(&mut engine);
        let shell = "tmp=\"$RHAI_TEST_POLL_RECORD.tmp\"; printf 'child-pid=%s child-ready=1\\n' \"$$\" > \"$tmp\"; mv \"$tmp\" \"$RHAI_TEST_POLL_RECORD\"; IFS= read -r value < \"$RHAI_TEST_POLL_RELEASE\"";
        let script = format!(
            "run(\"/bin/sh\", [\"-c\", {}], #{{ timeout: 0.1, max_output: 1024, env: #{{ \"RHAI_TEST_POLL_RECORD\": {}, \"RHAI_TEST_POLL_RELEASE\": {} }} }})",
            quote_rhai(shell),
            quote_rhai(record.to_str().unwrap()),
            quote_rhai(release.to_str().unwrap()),
        );

        let started = Instant::now();
        let result = engine.eval::<crate::Map>(&script);
        let elapsed = started.elapsed();
        let child_pid = record_pid(&record).expect("child readiness/PID record missing");
        assert!(
            observed.load(Ordering::Acquire) > 0,
            "per-execution interrupted-poll adapter was bypassed"
        );
        assert!(observed.load(Ordering::Acquire) <= INTERRUPTIONS);
        let result = result.expect("timeout should return the public process result map");
        assert!(
            map_bool(&result, "timed_out"),
            "public run missed its deadline"
        );
        assert_pid_reaped(child_pid);
        release_on_unwind.finish();
        println!(
            "interrupted-poll child_pid={child_pid} reap=ESRCH elapsed_ms={} injected={}",
            elapsed.as_millis(),
            observed.load(Ordering::Acquire)
        );
        assert!(
            elapsed < Duration::from_millis(1500),
            "poll EINTR handling delayed a 100ms public deadline: elapsed_ms={} injected={}",
            elapsed.as_millis(),
            observed.load(Ordering::Acquire)
        );
        drop(result);
        drop(engine);
        drop(package);
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
        format!(
            "\"{}\"",
            value
                .replace('\\', "\\\\")
                .replace('"', "\\\"")
                .replace('\r', "\\r")
                .replace('\n', "\\n")
                .replace('\t', "\\t")
        )
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
    fn run_inner_wait_failure_case() {
        let record = PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_RECORD").unwrap());
        let returned = PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_RETURNED").unwrap());
        let release = PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_RELEASE").unwrap());
        let (retired, service_gate) = fail_cleanup_wait_for_next_execution();
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
            "public run blocked after a non-consuming wait failure"
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
        let error = result.expect_err("deadline must return an incomplete-cleanup error");
        let sys_error = match error.as_ref() {
            EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>().unwrap(),
            other => panic!("expected SysError::Process, got {other:?}"),
        };
        let (cause_snapshot, report_snapshot) = match &sys_error {
            SysError::Process { cause, report } => {
                assert!(matches!(cause, ProcessCause::Timeout(_)));
                (cause.clone(), report.clone())
            }
            other => panic!("expected timeout process error, got {other:?}"),
        };
        assert!(
            report_snapshot.exit_code().is_none() && report_snapshot.exit_signal().is_none(),
            "non-consuming wait failure must publish an unavailable exit snapshot"
        );
        assert!(!report_snapshot.timed_out());
        assert!(!report_snapshot.stdout_complete() && !report_snapshot.stderr_complete());
        assert!(report_snapshot
            .cleanup_diagnostics()
            .iter()
            .any(|diagnostic| {
                diagnostic.operation() == "reap child"
                    && diagnostic
                        .message()
                        .contains("injected non-consuming cleanup wait failure")
            }));
        assert!(
            !retired.load(Ordering::Acquire),
            "owner retired before service observation"
        );

        println!(
            "retained-owner-wait child_record={} pid={child_pid}",
            record.display()
        );
        assert_pid_alive(child_pid);
        service_gate.store(true, Ordering::Release);
        let cleanup_deadline = Instant::now() + Duration::from_secs(3);
        while !retired.load(Ordering::Acquire) && Instant::now() < cleanup_deadline {
            thread::sleep(Duration::from_millis(5));
        }
        assert!(
            retired.load(Ordering::Acquire),
            "service did not reap and retire the child"
        );
        assert_pid_reaped(child_pid);
        match &sys_error {
            SysError::Process { cause, report } => {
                assert_eq!(
                    cause, &cause_snapshot,
                    "primary cause changed after cleanup"
                );
                assert_eq!(
                    report, &report_snapshot,
                    "published report changed after cleanup"
                );
            }
            other => panic!("primary error changed after cleanup: {other:?}"),
        }
        println!("retained-owner-wait child_pid={child_pid} reap=ESRCH");
        drop(error);
        drop(sys_error);
        drop(engine);
        drop(package);
    }

    #[cfg(not(feature = "no_float"))]
    #[test]
    fn non_consuming_cleanup_wait_failure_publishes_frozen_snapshot() {
        const CHILD_ROLE: &str = "RHAI_TEST_OWNER_WAIT_CHILD_ROLE";
        const TEST_NAME: &str = "packages::sys::process::unix::tests::non_consuming_cleanup_wait_failure_publishes_frozen_snapshot";

        if std::env::var_os(CHILD_ROLE).is_some() {
            run_inner_wait_failure_case();
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
            setup_gate: None,
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
                panic!("nested wait-failure test exceeded its external watchdog");
            }
            thread::sleep(Duration::from_millis(10));
        };
        if record.exists() {
            let pid = record_pid(&record).unwrap();
            println!(
                "retained-owner-wait child_record={} pid={pid}",
                record.display()
            );
            wait_for_pid_reaped(pid);
            println!("retained-owner-wait child_pid={pid} reap=ESRCH");
        }
        assert!(
            !watchdog_released_fixture,
            "external watchdog had to release the child"
        );
        assert!(
            status.success(),
            "nested incomplete-cleanup contract failed: {status}"
        );
    }

    fn run_inner_pipe_setup_failure_case() {
        let record = PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_RECORD").unwrap());
        let release = PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_RELEASE").unwrap());
        let setup_gate = PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_SETUP_GATE").unwrap());
        let retired = fail_pipe_setup_for_next_execution(setup_gate);
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
            "run(\"/bin/sh\", [\"-c\", {}], #{{ env: #{{ \"RHAI_TEST_OWNER_RECORD\": {}, \"RHAI_TEST_OWNER_RELEASE\": {} }} }})",
            quote_rhai(&shell),
            quote_rhai(record.to_str().unwrap()),
            quote_rhai(release.to_str().unwrap()),
        );
        let result = engine.eval::<crate::Map>(&script);
        let error = result.expect_err("injected post-spawn setup failure must remain catchable");
        let sys_error = match error.as_ref() {
            EvalAltResult::ErrorRuntime(value, _) => value.clone().try_cast::<SysError>().unwrap(),
            other => panic!("expected SysError::Process, got {other:?}"),
        };
        let (cause_is_configure_io, report_incomplete) = match &sys_error {
            SysError::Process { cause, report } => (
                matches!(
                    cause,
                    ProcessCause::Io {
                        op: "configure process pipe",
                        kind: io::ErrorKind::Other,
                        message,
                        ..
                    } if message == "injected post-spawn pipe configuration failure"
                ),
                !report.timed_out()
                    && !report.stdout_complete()
                    && !report.stderr_complete()
                    && report.stdout_bytes().is_empty()
                    && report.stderr_bytes().is_empty(),
            ),
            other => panic!("expected process setup error, got {other:?}"),
        };
        assert!(
            retired.load(Ordering::Acquire),
            "setup-failed owner did not retire after the child was reaped"
        );
        let record_deadline = Instant::now() + Duration::from_secs(1);
        let child_pid = loop {
            if record.exists() {
                break record_pid(&record).unwrap();
            }
            assert!(
                Instant::now() < record_deadline,
                "setup-failed child readiness record missing"
            );
            thread::sleep(Duration::from_millis(5));
        };
        assert_pid_reaped(child_pid);
        println!("setup-failure child_pid={child_pid} reap=ESRCH owner_retired=true");
        drop(error);
        drop(sys_error);
        drop(engine);
        drop(package);
        assert!(
            cause_is_configure_io,
            "primary cause must remain configure-pipe Io"
        );
        assert!(
            report_incomplete,
            "setup failure must not fabricate EOF or timeout completion"
        );
    }

    #[test]
    fn post_spawn_pipe_setup_failure_preserves_cause_and_reaps_child() {
        const CHILD_ROLE: &str = "RHAI_TEST_OWNER_SETUP_CHILD_ROLE";
        const TEST_NAME: &str = "packages::sys::process::unix::tests::post_spawn_pipe_setup_failure_preserves_cause_and_reaps_child";

        if std::env::var_os(CHILD_ROLE).is_some() {
            run_inner_pipe_setup_failure_case();
            return;
        }

        let fixture = FixtureDir::new();
        let record = fixture.0.join("child-record");
        let release = fixture.0.join("release.fifo");
        let setup_gate = fixture.0.join("allow-setup-failure");
        create_fifo(&release);
        let nested = Command::new(std::env::current_exe().unwrap())
            .args(["--exact", TEST_NAME, "--nocapture"])
            .env(CHILD_ROLE, "inner")
            .env("RHAI_TEST_OWNER_RECORD", &record)
            .env("RHAI_TEST_OWNER_RELEASE", &release)
            .env("RHAI_TEST_OWNER_SETUP_GATE", &setup_gate)
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .spawn()
            .unwrap();
        let mut nested = NestedTestChild {
            child: nested,
            release: release.clone(),
            setup_gate: Some(setup_gate.clone()),
        };
        let started = Instant::now();
        let record_deadline = started + Duration::from_secs(3);
        while !record.exists() {
            if let Some(status) = nested.try_wait().unwrap() {
                panic!("nested setup-failure test exited before child readiness: {status}");
            }
            assert!(
                Instant::now() < record_deadline,
                "nested setup-failure child readiness watchdog expired"
            );
            thread::sleep(Duration::from_millis(10));
        }
        let child_pid = record_pid(&record).unwrap();
        assert_pid_alive(child_pid);
        fs::write(&setup_gate, b"allow\n").unwrap();
        let setup_release_started = Instant::now();
        let status = loop {
            if let Some(status) = nested.try_wait().unwrap() {
                break status;
            }
            assert!(
                started.elapsed() < Duration::from_secs(8),
                "nested setup-failure test exceeded its external watchdog"
            );
            thread::sleep(Duration::from_millis(10));
        };
        assert!(
            setup_release_started.elapsed() < Duration::from_secs(2),
            "public run did not return boundedly after setup failure was released"
        );
        wait_for_pid_reaped(child_pid);
        println!("setup-failure fixture child_pid={child_pid} reap=ESRCH");
        assert!(
            status.success(),
            "nested setup-failure test failed: {status}"
        );
    }

    #[cfg(not(feature = "no_float"))]
    fn run_inner_inherited_pipe_holder_case() {
        let child_record = PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_RECORD").unwrap());
        let holder_record =
            PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_HOLDER_RECORD").unwrap());
        let before_ack = PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_BEFORE_ACK").unwrap());
        let after_ack = PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_AFTER_ACK").unwrap());
        let holder_result =
            PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_HOLDER_RESULT").unwrap());
        let stdout_probe = PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_STDOUT_PROBE").unwrap());
        let stderr_probe = PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_STDERR_PROBE").unwrap());
        let probe_script = r#"import os, sys
fd = 1 if sys.argv[1] == "stdout" else 2
payload = b"x" if fd == 1 else b"y"
try:
    os.write(fd, payload)
    result = "write-ok"
except OSError as exc:
    result = f"errno={exc.errno}"
tmp = sys.argv[2] + ".tmp"
out = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
os.write(out, (result + "\n").encode())
os.close(out)
os.replace(tmp, sys.argv[2])
"#;
        let release = PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_RELEASE").unwrap());
        let api_started = PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_API_STARTED").unwrap());
        let api_returned = PathBuf::from(std::env::var_os("RHAI_TEST_OWNER_API_RETURNED").unwrap());
        let holder_script = concat!(
            "trap '' PIPE; ",
            "printf 'holder-ready-stdout\\n'; printf 'holder-ready-stderr\\n' >&2; ",
            "tmp=\"$RHAI_TEST_OWNER_HOLDER_RECORD.tmp\"; ",
            "printf 'holder-pid=%s holder-ready=1\\n' \"$$\" > \"$tmp\"; ",
            "mv \"$tmp\" \"$RHAI_TEST_OWNER_HOLDER_RECORD\"; ",
            "while IFS= read -r command < \"$RHAI_TEST_OWNER_RELEASE\"; do ",
            "case \"$command\" in ",
            "before:*) nonce=\"${command#*:}\"; tmp=\"$RHAI_TEST_OWNER_BEFORE_ACK.tmp\"; printf 'before:%s\\n' \"$nonce\" > \"$tmp\"; mv \"$tmp\" \"$RHAI_TEST_OWNER_BEFORE_ACK\" ;; ",
            "after:*) nonce=\"${command#*:}\"; tmp=\"$RHAI_TEST_OWNER_AFTER_ACK.tmp\"; printf 'after:%s\\n' \"$nonce\" > \"$tmp\"; mv \"$tmp\" \"$RHAI_TEST_OWNER_AFTER_ACK\" ;; ",
            "release) break ;; ",
            "esac; done; ",
            "/usr/bin/python3 -c \"$RHAI_TEST_OWNER_PROBE_SCRIPT\" stdout \"$RHAI_TEST_OWNER_STDOUT_PROBE\"; ",
            "/usr/bin/python3 -c \"$RHAI_TEST_OWNER_PROBE_SCRIPT\" stderr \"$RHAI_TEST_OWNER_STDERR_PROBE\"; ",
            "tmp=\"$RHAI_TEST_OWNER_HOLDER_RESULT.tmp\"; ",
            "printf 'probes-complete\\n' > \"$tmp\"; ",
            "mv \"$tmp\" \"$RHAI_TEST_OWNER_HOLDER_RESULT\""
        );
        let shell = concat!(
            "tmp=\"$RHAI_TEST_OWNER_RECORD.tmp\"; ",
            "printf 'child-pid=%s child-ready=1\\n' \"$$\" > \"$tmp\"; ",
            "mv \"$tmp\" \"$RHAI_TEST_OWNER_RECORD\"; ",
            "/bin/sh -c \"$RHAI_TEST_OWNER_HOLDER_SCRIPT\" & ",
            "while [ ! -f \"$RHAI_TEST_OWNER_HOLDER_RECORD\" ]; do :; done; ",
            "exit 0"
        );
        let mut engine = Engine::new();
        let package = SysPackage::new(
            SysConfig::default()
                .programs(ProgramPolicy::Any)
                .max_output(1024),
        )
        .unwrap();
        package.register_into_engine(&mut engine);
        let script = format!(
            "run(\"/bin/sh\", [\"-c\", {}], #{{ timeout: 2.0, max_output: 1024, env: #{{ \"RHAI_TEST_OWNER_RECORD\": {}, \"RHAI_TEST_OWNER_HOLDER_RECORD\": {}, \"RHAI_TEST_OWNER_BEFORE_ACK\": {}, \"RHAI_TEST_OWNER_AFTER_ACK\": {}, \"RHAI_TEST_OWNER_HOLDER_RESULT\": {}, \"RHAI_TEST_OWNER_STDOUT_PROBE\": {}, \"RHAI_TEST_OWNER_STDERR_PROBE\": {}, \"RHAI_TEST_OWNER_PROBE_SCRIPT\": {}, \"RHAI_TEST_OWNER_RELEASE\": {}, \"RHAI_TEST_OWNER_HOLDER_SCRIPT\": {} }} }})",
            quote_rhai(shell),
            quote_rhai(child_record.to_str().unwrap()),
            quote_rhai(holder_record.to_str().unwrap()),
            quote_rhai(before_ack.to_str().unwrap()),
            quote_rhai(after_ack.to_str().unwrap()),
            quote_rhai(holder_result.to_str().unwrap()),
            quote_rhai(stdout_probe.to_str().unwrap()),
            quote_rhai(stderr_probe.to_str().unwrap()),
            quote_rhai(probe_script),
            quote_rhai(release.to_str().unwrap()),
            quote_rhai(holder_script),
        );
        assert!(
            !script.contains('\n') && !script.contains('\r') && !script.contains('\t'),
            "Rhai string quoting must escape control characters in fixture values"
        );
        assert!(
            script.contains("import os, sys\\nfd = 1"),
            "multiline helper must survive Rhai string quoting"
        );
        fs::write(&api_started, b"api-started\n").unwrap();
        let started = Instant::now();
        let result = engine.eval::<crate::Map>(&script).unwrap();
        let returned_tmp = api_returned.with_extension("tmp");
        fs::write(&returned_tmp, b"api-returned\n").unwrap();
        fs::rename(&returned_tmp, &api_returned).unwrap();
        assert!(
            started.elapsed() < Duration::from_secs(5),
            "public run did not return after deadline with inherited pipe holders"
        );
        assert!(map_bool(&result, "timed_out"));
        assert_eq!(map_int(&result, "code"), 0);
        assert!(map_bool(&result, "success"));
        assert!(!map_bool(&result, "stdout_complete"));
        assert!(!map_bool(&result, "stderr_complete"));
        assert_eq!(map_string(&result, "stdout"), "holder-ready-stdout\n");
        assert_eq!(map_string(&result, "stderr"), "holder-ready-stderr\n");
        println!("inherited-pipe captured_stdout_ready=true captured_stderr_ready=true");

        let child_pid = record_pid(&child_record).unwrap();
        let holder_pid = record_field_pid(&holder_record, "holder-pid").unwrap();
        assert_pid_reaped(child_pid);
        assert_pid_alive(holder_pid);
        assert!(
            !holder_result.exists(),
            "holder completed before fixture released its owned control FIFO"
        );
        println!(
            "inherited-pipe timeout child_pid={child_pid} child_reap=ESRCH holder_pid={holder_pid} holder_live=true stdout_complete=false stderr_complete=false"
        );

        drop(result);
        drop(engine);
        drop(package);
        assert!(
            before_ack.exists(),
            "pre-timeout challenge was not answered before the API returned"
        );
        assert_eq!(
            fs::read_to_string(&before_ack).unwrap(),
            "before:nonce-before-timeout\n"
        );
        send_fifo_message(&release, b"after:nonce-after-return\n").unwrap();
        let ack_deadline = Instant::now() + Duration::from_secs(1);
        while !after_ack.exists() && Instant::now() < ack_deadline {
            thread::sleep(Duration::from_millis(5));
        }
        assert!(
            after_ack.exists(),
            "live holder did not answer fixture probe"
        );
        let ack = fs::read_to_string(&after_ack).unwrap();
        assert_eq!(ack, "after:nonce-after-return\n");
        println!("inherited-pipe post-return challenge=after:nonce-after-return answered=true");
        send_fifo_message(&release, b"release\n").unwrap();

        let result_deadline = Instant::now() + Duration::from_secs(2);
        while !holder_result.exists() && Instant::now() < result_deadline {
            thread::sleep(Duration::from_millis(5));
        }
        assert!(
            holder_result.exists(),
            "holder did not publish pipe probe result"
        );
        assert_eq!(
            fs::read_to_string(&holder_result).unwrap(),
            "probes-complete\n"
        );
        let stdout_outcome = fs::read_to_string(&stdout_probe).unwrap();
        let stderr_outcome = fs::read_to_string(&stderr_probe).unwrap();
        let pipe_probe = format!(
            "stdout={} stderr={}\n",
            stdout_outcome.trim(),
            stderr_outcome.trim()
        );
        wait_for_pid_reaped(holder_pid);
        println!("inherited-pipe holder_pid={holder_pid} probe={pipe_probe:?} reap=ESRCH");
        assert_eq!(
            pipe_probe, "stdout=errno=32 stderr=errno=32\n",
            "public run must cancel both local pipe read endpoints before returning"
        );
    }

    #[cfg(not(feature = "no_float"))]
    #[test]
    fn inherited_pipe_holder_is_alive_at_timeout_and_fixture_releases_it() {
        const CHILD_ROLE: &str = "RHAI_TEST_OWNER_INHERITED_PIPE_CHILD_ROLE";
        const TEST_NAME: &str = "packages::sys::process::unix::tests::inherited_pipe_holder_is_alive_at_timeout_and_fixture_releases_it";

        if std::env::var_os(CHILD_ROLE).is_some() {
            run_inner_inherited_pipe_holder_case();
            return;
        }

        let fixture = FixtureDir::new();
        let child_record = fixture.0.join("direct-child");
        let holder_record = fixture.0.join("pipe-holder");
        let before_ack = fixture.0.join("before-ack");
        let after_ack = fixture.0.join("after-ack");
        let holder_result = fixture.0.join("holder-result");
        let stdout_probe = fixture.0.join("stdout-probe");
        let stderr_probe = fixture.0.join("stderr-probe");
        let api_started = fixture.0.join("api-started");
        let api_returned = fixture.0.join("api-returned");
        let release = fixture.0.join("release.fifo");
        create_fifo(&release);
        let nested = Command::new(std::env::current_exe().unwrap())
            .args(["--exact", TEST_NAME, "--nocapture"])
            .env(CHILD_ROLE, "inner")
            .env("RHAI_TEST_OWNER_RECORD", &child_record)
            .env("RHAI_TEST_OWNER_HOLDER_RECORD", &holder_record)
            .env("RHAI_TEST_OWNER_BEFORE_ACK", &before_ack)
            .env("RHAI_TEST_OWNER_AFTER_ACK", &after_ack)
            .env("RHAI_TEST_OWNER_HOLDER_RESULT", &holder_result)
            .env("RHAI_TEST_OWNER_STDOUT_PROBE", &stdout_probe)
            .env("RHAI_TEST_OWNER_STDERR_PROBE", &stderr_probe)
            .env("RHAI_TEST_OWNER_RELEASE", &release)
            .env("RHAI_TEST_OWNER_API_STARTED", &api_started)
            .env("RHAI_TEST_OWNER_API_RETURNED", &api_returned)
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .spawn()
            .unwrap();
        let mut nested = NestedTestChild {
            child: nested,
            release: release.clone(),
            setup_gate: None,
        };
        let started = Instant::now();
        let readiness_deadline = started + Duration::from_secs(4);
        while !holder_record.exists() || !api_started.exists() {
            if let Some(status) = nested.try_wait().unwrap() {
                panic!("nested inherited-pipe test exited before holder readiness: {status}");
            }
            assert!(
                Instant::now() < readiness_deadline,
                "inherited-pipe holder readiness watchdog expired"
            );
            thread::sleep(Duration::from_millis(10));
        }
        let holder_pid = record_field_pid(&holder_record, "holder-pid").unwrap();
        assert_pid_alive(holder_pid);
        send_fifo_message(&release, b"before:nonce-before-timeout\n").unwrap();
        let ack_deadline = Instant::now() + Duration::from_secs(1);
        while !before_ack.exists() && Instant::now() < ack_deadline {
            thread::sleep(Duration::from_millis(5));
        }
        assert!(
            before_ack.exists(),
            "holder was not operational before timeout"
        );
        assert_eq!(
            fs::read_to_string(&before_ack).unwrap(),
            "before:nonce-before-timeout\n"
        );
        assert!(
            !api_returned.exists(),
            "public API returned before the pre-timeout holder challenge was answered"
        );
        println!("inherited-pipe fixture holder_pid={holder_pid} alive=true challenge=before:nonce-before-timeout answered=true");

        let status = loop {
            if let Some(status) = nested.try_wait().unwrap() {
                break status;
            }
            assert!(
                started.elapsed() < Duration::from_secs(8),
                "nested inherited-pipe test exceeded its external watchdog"
            );
            thread::sleep(Duration::from_millis(10));
        };
        assert!(
            status.success(),
            "nested inherited-pipe test failed: {status}"
        );
        assert_eq!(fs::read_to_string(&api_returned).unwrap(), "api-returned\n");
        println!("inherited-pipe fixture api_returned_after_pre_ack=true");
        wait_for_pid_reaped(holder_pid);
        let child_pid = record_pid(&child_record).unwrap();
        wait_for_pid_reaped(child_pid);
        println!("inherited-pipe outer child_pid={child_pid} holder_pid={holder_pid} both=ESRCH");
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
            setup_gate: None,
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
