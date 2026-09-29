//! Error type for the `sys` package.

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
        }
    }

    /// Build an [`SysError::Io`] from an [`io::Error`].
    pub(crate) fn io(op: &'static str, target: impl Into<String>, source: io::Error) -> Self {
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
        module.set_getter_fn("kind", |e: &mut Self| Ok(e.kind().to_string()));
        module.set_getter_fn("message", |e: &mut Self| Ok(e.to_string()));
        module.set_getter_fn("io_kind", |e: &mut Self| {
            Ok(match e {
                Self::Io { kind, .. } => Dynamic::from(format!("{kind:?}")),
                _ => Dynamic::UNIT,
            })
        });
        module.set_getter_fn("op", |e: &mut Self| {
            Ok(match e {
                Self::Io { op, .. } => Dynamic::from(*op),
                _ => Dynamic::UNIT,
            })
        });
        module.set_getter_fn("target", |e: &mut Self| {
            Ok(match e {
                Self::Io { target, .. } => Dynamic::from(target.clone()),
                _ => Dynamic::UNIT,
            })
        });
        module.set_native_fn("to_string", |e: &mut Self| Ok(e.to_string()));
        module.set_native_fn("to_debug", |e: &mut Self| Ok(format!("{e:?}")));
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
