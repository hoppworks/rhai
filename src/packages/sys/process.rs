//! Immutable process result snapshots and diagnostics.

use crate::{Dynamic, ImmutableString, Module, INT};
use std::io;

#[cfg(unix)]
mod unix;

/// Final status of a process when one is available.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProcessExit {
    /// The process exited with this numeric status.
    Code(i32),
    /// On Unix, the process was terminated by this signal number.
    Signal(i32),
}

/// A secondary failure encountered while cleaning up a process.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProcessDiagnostic {
    operation: String,
    io_kind: Option<io::ErrorKind>,
    message: String,
}

impl ProcessDiagnostic {
    /// Create a cleanup diagnostic suitable for a process report.
    pub fn new(
        operation: impl Into<String>,
        io_kind: Option<io::ErrorKind>,
        message: impl Into<String>,
    ) -> Self {
        Self {
            operation: operation.into(),
            io_kind,
            message: message.into(),
        }
    }
    /// Cleanup operation that failed.
    pub fn operation(&self) -> &str {
        &self.operation
    }
    /// Underlying I/O error kind, when the failure came from I/O.
    pub fn io_kind(&self) -> Option<io::ErrorKind> {
        self.io_kind
    }
    /// Human-readable failure detail.
    pub fn message(&self) -> &str {
        &self.message
    }
}

/// Owned snapshot of captured process output and completion state.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProcessReport {
    stdout: Vec<u8>,
    stderr: Vec<u8>,
    stdout_complete: bool,
    stderr_complete: bool,
    exit: Option<ProcessExit>,
    timed_out: bool,
    cleanup_diagnostics: Vec<ProcessDiagnostic>,
}

impl ProcessReport {
    /// Construct an owned process snapshot.
    pub fn new(
        stdout: Vec<u8>,
        stderr: Vec<u8>,
        stdout_complete: bool,
        stderr_complete: bool,
        exit: Option<ProcessExit>,
        timed_out: bool,
        cleanup_diagnostics: Vec<ProcessDiagnostic>,
    ) -> Self {
        Self {
            stdout,
            stderr,
            stdout_complete,
            stderr_complete,
            exit,
            timed_out,
            cleanup_diagnostics,
        }
    }
    /// Captured stdout bytes.
    pub fn stdout_bytes(&self) -> &[u8] {
        &self.stdout
    }
    /// Captured stderr bytes.
    pub fn stderr_bytes(&self) -> &[u8] {
        &self.stderr
    }
    /// Captured stdout decoded lossily as UTF-8.
    pub fn stdout(&self) -> String {
        String::from_utf8_lossy(&self.stdout).into_owned()
    }
    /// Captured stderr decoded lossily as UTF-8.
    pub fn stderr(&self) -> String {
        String::from_utf8_lossy(&self.stderr).into_owned()
    }
    /// Whether stdout capture reached EOF.
    pub const fn stdout_complete(&self) -> bool {
        self.stdout_complete
    }
    /// Whether stderr capture reached EOF.
    pub const fn stderr_complete(&self) -> bool {
        self.stderr_complete
    }
    /// Exit code, if the process exited normally.
    pub fn exit_code(&self) -> Option<i32> {
        match self.exit {
            Some(ProcessExit::Code(c)) => Some(c),
            _ => None,
        }
    }
    /// Unix signal number, if the process was signaled.
    pub fn exit_signal(&self) -> Option<i32> {
        match self.exit {
            Some(ProcessExit::Signal(s)) => Some(s),
            _ => None,
        }
    }
    /// Whether the configured deadline expired.
    pub const fn timed_out(&self) -> bool {
        self.timed_out
    }
    /// Ordered cleanup diagnostics.
    pub fn cleanup_diagnostics(&self) -> &[ProcessDiagnostic] {
        &self.cleanup_diagnostics
    }
    /// One cleanup diagnostic by index, or `None` when out of range.
    pub fn cleanup_diagnostic(&self, index: usize) -> Option<&ProcessDiagnostic> {
        self.cleanup_diagnostics.get(index)
    }
}

/// Register process execution functions supported by this target.
pub(super) fn register(module: &mut Module, state: &crate::Shared<super::SysState>) {
    #[cfg(unix)]
    unix::register(module, state);
}

/// Primary failure cause for an operation that produced a process report.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProcessCause {
    /// An operating-system I/O error.
    Io {
        /// Operation that failed.
        op: &'static str,
        /// Program or resource involved.
        target: String,
        /// Operating-system error category.
        kind: io::ErrorKind,
        /// Human-readable operating-system error detail.
        message: String,
    },
    /// A process exceeded its configured deadline.
    Timeout(String),
    /// A process exceeded its configured output limit.
    OutputLimit(String),
}

impl ProcessCause {
    pub(crate) const fn kind(&self) -> &'static str {
        match self {
            Self::Io { .. } => "Io",
            Self::Timeout(..) => "Timeout",
            Self::OutputLimit(..) => "OutputLimit",
        }
    }
    pub(crate) fn io_kind(&self) -> Option<io::ErrorKind> {
        if let Self::Io { kind, .. } = self {
            Some(*kind)
        } else {
            None
        }
    }
    pub(crate) fn op(&self) -> Option<&'static str> {
        if let Self::Io { op, .. } = self {
            Some(*op)
        } else {
            None
        }
    }
    pub(crate) fn target(&self) -> Option<&str> {
        if let Self::Io { target, .. } = self {
            Some(target)
        } else {
            None
        }
    }
    pub(crate) fn display(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io {
                op,
                target,
                kind,
                message,
            } => write!(f, "Io ({kind:?}): cannot {op} `{target}`: {message}"),
            Self::Timeout(msg) => write!(f, "Timeout: {msg}"),
            Self::OutputLimit(msg) => write!(f, "OutputLimit: {msg}"),
        }
    }
}

impl ProcessReport {
    pub(super) fn register(module: &mut Module) {
        module.set_custom_type::<Self>("ProcessReport");
        module.set_custom_type::<ProcessDiagnostic>("ProcessDiagnostic");
        macro_rules! getter {
            ($name:literal, $doc:expr, $func:expr) => {{
                let r = crate::FuncRegistration::new(crate::engine::make_getter($name))
                    .with_purity(true)
                    .with_volatility(false);
                #[cfg(feature = "metadata")]
                let r = r.with_comments($doc);
                r.set_into_module(module, $func);
            }};
        }
        getter!(
            "stdout",
            &["Captured stdout decoded lossily as UTF-8."],
            |r: &mut Self| -> ImmutableString { r.stdout().into() }
        );
        getter!(
            "stderr",
            &["Captured stderr decoded lossily as UTF-8."],
            |r: &mut Self| -> ImmutableString { r.stderr().into() }
        );
        getter!(
            "stdout_complete",
            &["Whether stdout capture reached EOF."],
            |r: &mut Self| r.stdout_complete
        );
        getter!(
            "stderr_complete",
            &["Whether stderr capture reached EOF."],
            |r: &mut Self| r.stderr_complete
        );
        getter!(
            "exit_code",
            &["Normal exit code, or `()`."],
            |r: &mut Self| -> Dynamic {
                r.exit_code()
                    .map(|n| Dynamic::from_int(n as INT))
                    .unwrap_or(Dynamic::UNIT)
            }
        );
        getter!(
            "exit_signal",
            &["Unix signal number, or `()`."],
            |r: &mut Self| -> Dynamic {
                r.exit_signal()
                    .map(|n| Dynamic::from_int(n as INT))
                    .unwrap_or(Dynamic::UNIT)
            }
        );
        getter!(
            "timed_out",
            &["Whether the process deadline expired."],
            |r: &mut Self| r.timed_out
        );
        let method = crate::FuncRegistration::new("cleanup_diagnostic")
            .with_purity(true)
            .with_volatility(false);
        #[cfg(feature = "metadata")]
        let method = method.with_comments(&[
            "Get one cleanup diagnostic by index; returns `()` when out of range.",
        ]);
        method.set_into_module(module, |r: &mut Self, index: INT| -> Dynamic {
            usize::try_from(index)
                .ok()
                .and_then(|i| r.cleanup_diagnostic(i))
                .cloned()
                .map(Dynamic::from)
                .unwrap_or(Dynamic::UNIT)
        });
        getter!(
            "operation",
            &["Cleanup operation that failed."],
            |d: &mut ProcessDiagnostic| -> ImmutableString { d.operation.clone().into() }
        );
        getter!(
            "message",
            &["Human-readable cleanup failure detail."],
            |d: &mut ProcessDiagnostic| -> ImmutableString { d.message.clone().into() }
        );
        getter!(
            "io_kind",
            &["Underlying I/O error kind, or `()`."],
            |d: &mut ProcessDiagnostic| -> Dynamic {
                d.io_kind
                    .map(|kind| format!("{kind:?}").into())
                    .unwrap_or(Dynamic::UNIT)
            }
        );
        #[cfg(not(feature = "no_index"))]
        {
            getter!(
                "stdout_bytes",
                &["Copy of captured stdout bytes."],
                |r: &mut Self| -> crate::Blob { r.stdout.clone() }
            );
            getter!(
                "stderr_bytes",
                &["Copy of captured stderr bytes."],
                |r: &mut Self| -> crate::Blob { r.stderr.clone() }
            );
            getter!(
                "cleanup_diagnostics",
                &["Copy of the ordered cleanup diagnostics."],
                |r: &mut Self| -> crate::Array {
                    r.cleanup_diagnostics
                        .iter()
                        .cloned()
                        .map(Dynamic::from)
                        .collect()
                }
            );
        }
    }
}
