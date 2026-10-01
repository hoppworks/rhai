//! Error type for the `sys` package.

use super::process::{ProcessCause, ProcessReport};
use crate::plugin::*;
use crate::{Dynamic, EvalAltResult, Module, Position};
use std::error::Error;
use std::fmt;
use std::io;

/// Error raised by functions of the [`SysPackage`][super::SysPackage].
///
/// Every variant surfaces to scripts as [`EvalAltResult::ErrorRuntime`] carrying the
/// `SysError` value itself, so scripts can catch it with `try`/`catch` and inspect it:
///
/// ```rhai
/// try {
///     read_file("missing.txt");
/// } catch (err) {
///     print(err.kind);       // "Io"
///     print(err.io_kind);    // "NotFound"
///     print(err.message);    // "Io (NotFound): cannot read file `missing.txt`: ..."
/// }
/// ```
///
/// Hosts recover the value with `Dynamic::try_cast::<SysError>()` on the payload of
/// [`EvalAltResult::ErrorRuntime`].
///
/// A [`SysError::Io`] stores the [`io::ErrorKind`] and message rather than the
/// [`io::Error`] itself so that the value is `Clone` and can live inside a [`Dynamic`].
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum SysError {
    /// The host configuration does not allow the operation.
    Denied(String),
    /// The operating system reported an error.
    Io {
        /// What was attempted, e.g. `read file`.
        op: &'static str,
        /// The path or program involved.
        target: String,
        /// Kind of the underlying [`io::Error`].
        kind: io::ErrorKind,
        /// Message of the underlying [`io::Error`].
        message: String,
    },
    /// A child process did not finish within the configured timeout.
    Timeout(String),
    /// A child process produced more output than the configured limit.
    OutputLimit(String),
    /// A path, file name or environment value is not valid UTF-8.
    NotUtf8(String),
    /// A process operation failed; the report preserves the observed partial result.
    Process {
        /// Primary process failure.
        cause: ProcessCause,
        /// Captured process output and cleanup snapshot.
        report: ProcessReport,
    },
}

impl SysError {
    /// Name of the variant, e.g. `Denied`.
    #[must_use]
    pub const fn kind(&self) -> &'static str {
        match self {
            Self::Denied(..) => "Denied",
            Self::Io { .. } => "Io",
            Self::Timeout(..) => "Timeout",
            Self::OutputLimit(..) => "OutputLimit",
            Self::NotUtf8(..) => "NotUtf8",
            Self::Process { cause, .. } => cause.kind(),
        }
    }

    /// Build an [`SysError::Io`] from an [`io::Error`].
    pub(crate) fn io(op: &'static str, target: impl Into<String>, source: &io::Error) -> Self {
        Self::Io {
            op,
            target: target.into(),
            kind: source.kind(),
            message: source.to_string(),
        }
    }

    /// Register the type and its getters into a module.
    pub(super) fn register(module: &mut Module) {
        module.set_custom_type::<Self>("SysError");
        combine_with_exported_module!(module, "sys_error", sys_error_functions);
    }
}

#[export_module]
mod sys_error_functions {
    /// Name of the error variant: `Denied`, `Io`, `Timeout`, `OutputLimit` or `NotUtf8`.
    ///
    /// # Example
    ///
    /// ```rhai
    /// try {
    ///     read_file("missing.txt");
    /// } catch (err) {
    ///     print(err.kind);        // prints "Io"
    /// }
    /// ```
    #[rhai_fn(get = "kind", pure)]
    pub fn kind(err: &mut SysError) -> ImmutableString {
        err.kind().into()
    }
    /// Full error message, the same text that `to_string` and `print` produce.
    #[rhai_fn(get = "message", pure)]
    pub fn message(err: &mut SysError) -> ImmutableString {
        err.to_string().into()
    }
    /// For `Io` errors, the name of the underlying `std::io::ErrorKind` such as `NotFound`
    /// or `PermissionDenied`. `()` for other kinds.
    ///
    /// # Example
    ///
    /// ```rhai
    /// try {
    ///     read_file("missing.txt");
    /// } catch (err) {
    ///     if err.io_kind == "NotFound" { print("no such file"); }
    /// }
    /// ```
    #[rhai_fn(get = "io_kind", pure)]
    pub fn io_kind(err: &mut SysError) -> Dynamic {
        match err {
            SysError::Io { kind, .. } => format!("{kind:?}").into(),
            SysError::Process { cause, .. } => cause
                .io_kind()
                .map(|kind| format!("{kind:?}").into())
                .unwrap_or(Dynamic::UNIT),
            _ => Dynamic::UNIT,
        }
    }
    /// For `Io` errors, what was attempted, e.g. `read file`. `()` for other kinds.
    #[rhai_fn(get = "op", pure)]
    pub fn op(err: &mut SysError) -> Dynamic {
        match err {
            SysError::Io { op, .. } => (*op).into(),
            SysError::Process { cause, .. } => cause.op().map(Into::into).unwrap_or(Dynamic::UNIT),
            _ => Dynamic::UNIT,
        }
    }
    /// For `Io` errors, the path or program involved. `()` for other kinds.
    #[rhai_fn(get = "target", pure)]
    pub fn target(err: &mut SysError) -> Dynamic {
        match err {
            SysError::Io { target, .. } => target.clone().into(),
            SysError::Process { cause, .. } => cause
                .target()
                .map(|s| s.to_owned().into())
                .unwrap_or(Dynamic::UNIT),
            _ => Dynamic::UNIT,
        }
    }
    /// Convert the error into its message.
    #[rhai_fn(name = "to_string", pure)]
    pub fn to_string(err: &mut SysError) -> ImmutableString {
        err.to_string().into()
    }
    /// Convert the error into its debug representation.
    #[rhai_fn(name = "to_debug", pure)]
    pub fn to_debug(err: &mut SysError) -> ImmutableString {
        format!("{err:?}").into()
    }
    /// Process snapshot for process errors; `()` for other errors.
    #[rhai_fn(get = "process", pure)]
    pub fn process(err: &mut SysError) -> Dynamic {
        match err {
            SysError::Process { report, .. } => Dynamic::from(report.clone()),
            _ => Dynamic::UNIT,
        }
    }
}

impl fmt::Display for SysError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Denied(msg) => write!(f, "Denied: {msg}"),
            Self::Io {
                op,
                target,
                kind,
                message,
            } => write!(f, "Io ({kind:?}): cannot {op} `{target}`: {message}"),
            Self::Timeout(msg) => write!(f, "Timeout: {msg}"),
            Self::OutputLimit(msg) => write!(f, "OutputLimit: {msg}"),
            Self::NotUtf8(msg) => write!(f, "NotUtf8: {msg}"),
            Self::Process { cause, .. } => cause.display(f),
        }
    }
}

impl Error for SysError {}

impl From<SysError> for Box<EvalAltResult> {
    #[inline]
    fn from(err: SysError) -> Self {
        EvalAltResult::ErrorRuntime(Dynamic::from(err), Position::NONE).into()
    }
}
