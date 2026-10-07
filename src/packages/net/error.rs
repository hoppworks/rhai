//! Catchable errors for script-visible network operations.

use crate::plugin::*;
use crate::{Dynamic, EvalAltResult, Module, Position};
use std::error::Error;
use std::fmt;
use std::io;

/// Error raised by functions in [`super::NetPackage`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NetError {
    kind: &'static str,
    message: String,
    io_kind: Option<io::ErrorKind>,
    op: &'static str,
    target: String,
    partial_bytes: usize,
}

impl NetError {
    pub(crate) fn invalid(
        op: &'static str,
        target: impl Into<String>,
        message: impl Into<String>,
    ) -> Self {
        Self {
            kind: "InvalidInput",
            message: message.into(),
            io_kind: Some(io::ErrorKind::InvalidInput),
            op,
            target: target.into(),
            partial_bytes: 0,
        }
    }

    pub(crate) fn resource_limit(
        op: &'static str,
        target: impl Into<String>,
        message: impl Into<String>,
    ) -> Self {
        Self {
            kind: "ResourceLimit",
            message: message.into(),
            io_kind: None,
            op,
            target: target.into(),
            partial_bytes: 0,
        }
    }

    pub(crate) fn denied(
        op: &'static str,
        target: impl Into<String>,
        message: impl Into<String>,
    ) -> Self {
        Self {
            kind: "Denied",
            message: message.into(),
            io_kind: None,
            op,
            target: target.into(),
            partial_bytes: 0,
        }
    }

    pub(crate) fn io(op: &'static str, target: impl Into<String>, source: &io::Error) -> Self {
        let kind = if matches!(
            source.kind(),
            io::ErrorKind::TimedOut | io::ErrorKind::WouldBlock
        ) {
            "Timeout"
        } else {
            "Io"
        };
        Self {
            kind,
            message: source.to_string(),
            io_kind: Some(source.kind()),
            op,
            target: target.into(),
            partial_bytes: 0,
        }
    }

    pub(crate) fn with_partial_bytes(mut self, partial_bytes: usize) -> Self {
        self.partial_bytes = partial_bytes;
        self
    }

    /// Error category such as `Denied`, `InvalidInput`, `Io` or `Timeout`.
    #[must_use]
    pub fn kind(&self) -> &'static str {
        self.kind
    }

    /// Human-readable explanation of the error.
    #[must_use]
    pub fn message(&self) -> &str {
        &self.message
    }

    /// Underlying I/O category, when an operating-system or validation error supplies one.
    #[must_use]
    pub fn io_kind(&self) -> Option<io::ErrorKind> {
        self.io_kind
    }

    /// Operation that failed.
    #[must_use]
    pub fn op(&self) -> &'static str {
        self.op
    }

    /// Numeric endpoint involved in the operation.
    #[must_use]
    pub fn target(&self) -> &str {
        &self.target
    }

    /// Number of bytes captured before an operation failed.
    #[must_use]
    pub fn partial_bytes(&self) -> crate::INT {
        self.partial_bytes as crate::INT
    }

    pub(super) fn register(module: &mut Module) {
        module.set_custom_type::<Self>("NetError");
        combine_with_exported_module!(module, "net_error", net_error_functions);
    }
}

#[export_module]
mod net_error_functions {
    /// Primary error category, such as `Denied`, `InvalidInput`, `Io` or `Timeout`.
    #[rhai_fn(name = "kind", get = "kind", pure)]
    pub fn kind(err: &mut NetError) -> ImmutableString {
        err.kind().into()
    }

    /// Human-readable explanation of the error.
    #[rhai_fn(name = "message", get = "message", pure)]
    pub fn message(err: &mut NetError) -> ImmutableString {
        err.message().into()
    }

    /// Underlying I/O error kind, or unit when there is no I/O error kind.
    #[rhai_fn(name = "io_kind", get = "io_kind", pure)]
    pub fn io_kind(err: &mut NetError) -> Dynamic {
        err.io_kind()
            .map(|kind| format!("{kind:?}").into())
            .unwrap_or(Dynamic::UNIT)
    }

    /// Operation that failed, or unit when unavailable.
    #[rhai_fn(name = "op", get = "op", pure)]
    pub fn op(err: &mut NetError) -> ImmutableString {
        err.op().into()
    }

    /// Resource target involved in the failed operation.
    #[rhai_fn(name = "target", get = "target", pure)]
    pub fn target(err: &mut NetError) -> ImmutableString {
        err.target().into()
    }

    /// Bytes received or accepted before failure; this is not peer acknowledgement.
    #[rhai_fn(name = "partial_bytes", get = "partial_bytes", pure)]
    pub fn partial_bytes(err: &mut NetError) -> crate::INT {
        err.partial_bytes()
    }

    #[rhai_fn(name = "to_string", pure)]
    pub fn to_string(err: &mut NetError) -> ImmutableString {
        err.to_string().into()
    }
}

impl fmt::Display for NetError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if let Some(kind) = self.io_kind {
            write!(
                f,
                "{} ({kind:?}): cannot {} `{}`: {}",
                self.kind, self.op, self.target, self.message
            )
        } else {
            write!(
                f,
                "{}: cannot {} `{}`: {}",
                self.kind, self.op, self.target, self.message
            )
        }
    }
}

impl Error for NetError {}

impl From<NetError> for Box<EvalAltResult> {
    fn from(error: NetError) -> Self {
        EvalAltResult::ErrorRuntime(Dynamic::from(error), Position::NONE).into()
    }
}
