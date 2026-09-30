//! Host-side configuration for the `sys` package.

use std::path::{Path, PathBuf};

/// What a script may do inside a filesystem root.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum FsAccess {
    /// Read files, list directories, query metadata.
    Read,
    /// [`Read`][FsAccess::Read] plus create, write, append, rename and copy.
    /// Removing a single file or an empty directory is included.
    ReadWrite,
    /// [`ReadWrite`][FsAccess::ReadWrite] plus recursive deletion (`remove_dir_all`).
    ReadWriteDelete,
}

/// Which environment variables a script may read.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub enum EnvPolicy {
    /// No variable is visible. `env_var` returns `()`, `env_vars` returns an empty map.
    #[default]
    None,
    /// Only the listed variables are visible.
    AllowList(Vec<String>),
    /// Every variable of the host process is visible.
    All,
}

impl EnvPolicy {
    /// Is the variable visible under this policy?
    #[must_use]
    pub fn allows(&self, name: &str) -> bool {
        match self {
            Self::None => false,
            Self::AllowList(list) => list.iter().any(|n| n == name),
            Self::All => true,
        }
    }
}

/// Which programs a script may run.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub enum ProgramPolicy {
    /// No program may be run.
    #[default]
    None,
    /// Only the listed programs may be run. Entries are compared verbatim against the
    /// program string the script passes, so a list entry may be a bare name (resolved via
    /// `PATH`) or an absolute path.
    AllowList(Vec<String>),
    /// Any program may be run.
    Any,
}

impl ProgramPolicy {
    /// May the program be run under this policy?
    #[must_use]
    pub fn allows(&self, program: &str) -> bool {
        match self {
            Self::None => false,
            Self::AllowList(list) => list.iter().any(|p| p == program),
            Self::Any => true,
        }
    }
}

/// One filesystem root a script may access.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FsRoot {
    /// Directory on the host. Relative paths are resolved against the current directory
    /// when the package is created.
    pub path: PathBuf,
    /// Access level inside the root.
    pub access: FsAccess,
}

/// Which parts of the filesystem a script may access.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FsPolicy {
    /// Access is confined to the listed roots. An empty list denies everything.
    Roots(Vec<FsRoot>),
    /// The whole filesystem, without confinement. For trusted scripts only.
    Unrestricted(FsAccess),
}

impl Default for FsPolicy {
    #[inline]
    fn default() -> Self {
        Self::Roots(Vec::new())
    }
}

/// Configuration for the [`SysPackage`][super::SysPackage].
///
/// The default configuration denies everything. Grant capabilities with the builder methods.
///
/// # Example
///
/// ```
/// use rhai::packages::sys::{SysConfig, FsAccess, EnvPolicy, ProgramPolicy};
///
/// let cfg = SysConfig::default()
///     .fs_root("./data", FsAccess::ReadWrite)
///     .env(EnvPolicy::AllowList(vec!["HOME".into()]))
///     .programs(ProgramPolicy::AllowList(vec!["git".into()]));
/// ```
#[derive(Debug, Clone, PartialEq)]
pub struct SysConfig {
    pub(crate) fs: FsPolicy,
    pub(crate) env: EnvPolicy,
    pub(crate) programs: ProgramPolicy,
    pub(crate) default_timeout: Option<f64>,
    pub(crate) max_output: usize,
    pub(crate) max_file_read: usize,
    pub(crate) kill_on_drop: bool,
    pub(crate) allow_batch_files: bool,
}

impl Default for SysConfig {
    fn default() -> Self {
        Self {
            fs: FsPolicy::default(),
            env: EnvPolicy::default(),
            programs: ProgramPolicy::default(),
            default_timeout: None,
            max_output: 8 * 1024 * 1024,
            max_file_read: 8 * 1024 * 1024,
            kill_on_drop: true,
            allow_batch_files: false,
        }
    }
}

impl SysConfig {
    /// A configuration that allows everything: the whole filesystem with
    /// [`FsAccess::ReadWriteDelete`], every environment variable and every program.
    ///
    /// Use only for scripts you trust as much as the host process itself.
    #[must_use]
    pub fn permissive() -> Self {
        Self {
            fs: FsPolicy::Unrestricted(FsAccess::ReadWriteDelete),
            env: EnvPolicy::All,
            programs: ProgramPolicy::Any,
            ..Self::default()
        }
    }

    /// Grant access to a directory and everything below it.
    ///
    /// Can be called several times. Relative script paths resolve against the first root;
    /// absolute script paths must lie inside one of the roots. Calling this after
    /// [`fs_unrestricted`][Self::fs_unrestricted] switches back to confined mode.
    #[must_use]
    pub fn fs_root(mut self, path: impl AsRef<Path>, access: FsAccess) -> Self {
        let root = FsRoot {
            path: path.as_ref().to_path_buf(),
            access,
        };
        match &mut self.fs {
            FsPolicy::Roots(roots) => roots.push(root),
            FsPolicy::Unrestricted(..) => self.fs = FsPolicy::Roots(vec![root]),
        }
        self
    }

    /// Grant access to the whole filesystem without confinement.
    #[must_use]
    pub fn fs_unrestricted(mut self, access: FsAccess) -> Self {
        self.fs = FsPolicy::Unrestricted(access);
        self
    }

    /// Set the environment-variable policy.
    #[must_use]
    pub fn env(mut self, policy: EnvPolicy) -> Self {
        self.env = policy;
        self
    }

    /// Set the program policy.
    #[must_use]
    pub fn programs(mut self, policy: ProgramPolicy) -> Self {
        self.programs = policy;
        self
    }

    /// Default timeout in seconds for `run` when the script gives none. `None` means no limit.
    #[must_use]
    pub const fn default_timeout(mut self, seconds: Option<f64>) -> Self {
        self.default_timeout = seconds;
        self
    }

    /// Maximum number of bytes captured per output stream of a child process.
    #[must_use]
    pub const fn max_output(mut self, bytes: usize) -> Self {
        self.max_output = bytes;
        self
    }

    /// Maximum number of bytes a single file-handle read may return. The default is 8 MiB.
    /// A value of zero disables bytes from streaming file-handle reads. In checked builds,
    /// a nonzero Engine string or array limit may lower this cap further.
    #[must_use]
    pub const fn max_file_read(mut self, bytes: usize) -> Self {
        self.max_file_read = bytes;
        self
    }

    /// Whether a spawned child is killed when the script drops its handle. Default `true`.
    #[must_use]
    pub const fn kill_on_drop(mut self, kill: bool) -> Self {
        self.kill_on_drop = kill;
        self
    }

    /// Allow running `.bat` and `.cmd` files on Windows. Default `false`.
    ///
    /// Batch files are interpreted by `cmd.exe`, which parses arguments itself. Rust's
    /// standard library escapes them correctly since 1.77.2 (CVE-2024-24576), but refusing
    /// them by default removes the whole class of problems.
    #[must_use]
    pub const fn allow_batch_files(mut self, allow: bool) -> Self {
        self.allow_batch_files = allow;
        self
    }
}
