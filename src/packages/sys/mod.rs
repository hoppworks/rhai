//! The `sys` package: host-controlled access to the environment, filesystem and child processes.
//!
//! Nothing in this package is registered by default. The host builds a [`SysConfig`], turns it
//! into a [`SysPackage`] and registers that with an [`Engine`][crate::Engine]. The default
//! configuration denies everything.
//!
//! # Example
//!
//! ```no_run
//! use rhai::Engine;
//! use rhai::packages::Package;
//! use rhai::packages::sys::{SysPackage, SysConfig, FsAccess, EnvPolicy};
//!
//! let cfg = SysConfig::default()
//!     .fs_root("./data", FsAccess::ReadWrite)
//!     .env(EnvPolicy::AllowList(vec!["HOME".into()]));
//!
//! let mut engine = Engine::new();
//! SysPackage::new(cfg).unwrap().register_into_engine(&mut engine);
//!
//! engine.run(r#"write_file("hello.txt", "hi from " + env_var("HOME"))"#).unwrap();
//! ```
//!
//! # Errors
//!
//! Every failure is raised as [`EvalAltResult::ErrorRuntime`][crate::EvalAltResult::ErrorRuntime]
//! carrying a [`SysError`] value, so scripts can catch it with `try`/`catch` and read its
//! `kind`, `message` and, for I/O errors, `io_kind`, `op` and `target`.

#[cfg(feature = "no_std")]
compile_error!("the `sys` feature requires `std`; it cannot be combined with `no_std`");

#[cfg(feature = "no_object")]
compile_error!("the `sys` feature requires object maps; it cannot be combined with `no_object`");

#[cfg(target_family = "wasm")]
compile_error!("the `sys` feature is not available on WASM targets");

mod config;
mod env;
mod error;
mod fs;
mod process;

pub use config::{EnvPolicy, FsAccess, FsPolicy, FsRoot, ProcessScope, ProgramPolicy, SysConfig};
pub use error::SysError;
pub use process::{ProcessCause, ProcessDiagnostic, ProcessExit, ProcessReport};

use crate::packages::Package;
use crate::{Module, Shared, SharedModule};

/// State shared by every function of one package instance.
///
/// Private fields are visible to the child modules `env` and `fs`.
struct SysState {
    config: SysConfig,
    fs: fs::FsState,
}

/// Start a registration for a volatile, non-mutating function with doc-comments.
#[allow(unused_variables)]
fn reg(name: &str, comments: &[&str]) -> crate::FuncRegistration {
    let r = crate::FuncRegistration::new(name).with_volatility(true);
    #[cfg(feature = "metadata")]
    let r = r.with_comments(comments);
    r
}

/// Package giving scripts access to the environment, filesystem and child processes,
/// limited by a [`SysConfig`].
///
/// Unlike the built-in packages, this one carries state, so it is created with
/// [`SysPackage::new`] rather than `Default`.
#[derive(Clone)]
pub struct SysPackage(SharedModule);

impl SysPackage {
    /// Create the package from a configuration.
    ///
    /// Fails when a configured filesystem root cannot be opened.
    pub fn new(config: SysConfig) -> Result<Self, SysError> {
        let fs = fs::FsState::open(&config.fs)?;
        let state: Shared<SysState> = Shared::new(SysState { config, fs });

        let mut module = Module::new();
        SysError::register(&mut module);
        process::ProcessReport::register(&mut module);
        process::register(&mut module, &state);
        env::register(&mut module, &state);
        fs::register(&mut module, &state);
        module.build_index();

        Ok(Self(module.into()))
    }
}

impl Package for SysPackage {
    /// This package registers its functions in [`SysPackage::new`] because they capture the
    /// configuration; `init` has nothing to do.
    fn init(_module: &mut Module) {}

    #[inline(always)]
    fn as_shared_module(&self) -> SharedModule {
        self.0.clone()
    }
}
