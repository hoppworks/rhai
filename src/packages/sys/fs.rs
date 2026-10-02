//! Filesystem functions of the `sys` package.
//!
//! Confinement is delegated to [`cap_std`]: every configured root is opened as a
//! [`Dir`] and all operations take paths relative to it. `cap-std` resolves symbolic
//! links and `..` components against the real filesystem and refuses anything that
//! would leave the root, so the checks here are only the first, lexical line of defence.
//!
//! One consequence: inside a confined root, symbolic links must have relative targets.
//! `cap-std` treats an absolute link target as an escape attempt even when it points back
//! into the root, and the operation fails with [`SysError::Denied`].

use super::config::{FsAccess, FsPolicy};
use super::error::SysError;
use super::{reg, SysState};
use crate::{Dynamic, EvalAltResult, Locked, Map, Module, NativeCallContext, Shared, INT};
use cap_std::ambient_authority;
use cap_std::fs::{Dir, OpenOptions};
use std::io::{self, Read, Seek, SeekFrom, Write};
use std::path::{Component, Path, PathBuf};

type Res<T> = Result<T, Box<EvalAltResult>>;

/// A configured root, opened.
pub(super) struct OpenRoot {
    /// Absolute path as configured (after joining with the current directory).
    given: PathBuf,
    /// Canonical form of `given`, for matching absolute script paths.
    canonical: PathBuf,
    dir: Dir,
    access: FsAccess,
}

/// Filesystem policy with roots opened.
pub(super) enum FsState {
    Roots(Vec<OpenRoot>),
    Unrestricted(FsAccess),
}

type FileHandle = Shared<Locked<std::fs::File>>;

impl FsState {
    pub(super) fn open(policy: &FsPolicy) -> Result<Self, SysError> {
        match policy {
            FsPolicy::Unrestricted(access) => Ok(Self::Unrestricted(*access)),
            FsPolicy::Roots(roots) => {
                let mut opened = Vec::with_capacity(roots.len());
                for root in roots {
                    let given = if root.path.is_absolute() {
                        root.path.clone()
                    } else {
                        std::env::current_dir()
                            .map_err(|e| SysError::io("get current directory", ".", &e))?
                            .join(&root.path)
                    };
                    let target = || given.display().to_string();
                    let canonical = strip_verbatim(
                        std::fs::canonicalize(&given)
                            .map_err(|e| SysError::io("open root", target(), &e))?,
                    );
                    let dir = Dir::open_ambient_dir(&given, ambient_authority())
                        .map_err(|e| SysError::io("open root", target(), &e))?;
                    opened.push(OpenRoot {
                        given,
                        canonical,
                        dir,
                        access: root.access,
                    });
                }
                Ok(Self::Roots(opened))
            }
        }
    }
}

/// What an operation needs from the root it touches.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Need {
    Read,
    Write,
    Delete,
}

impl Need {
    fn satisfied_by(self, access: FsAccess) -> bool {
        match self {
            Self::Read => true,
            Self::Write => access >= FsAccess::ReadWrite,
            Self::Delete => access >= FsAccess::ReadWriteDelete,
        }
    }
    const fn describe(self) -> &'static str {
        match self {
            Self::Read => "read",
            Self::Write => "write",
            Self::Delete => "delete",
        }
    }
}

/// A script path resolved either to a host path or to a path inside a configured root.
struct Resolved<'a> {
    /// Present only for configured, capability-confined roots. Unrestricted operations use
    /// `host_path` directly and must not acquire an unrelated ambient directory handle.
    dir: Option<&'a Dir>,
    rel: PathBuf,
    /// Original OS path in unrestricted mode; those operations must follow host semantics.
    host_path: Option<PathBuf>,
    /// Index of the root, or `usize::MAX` in unrestricted mode.
    root: usize,
}

impl Resolved<'_> {
    /// Get the directory authority for a configured-root operation.
    fn dir(&self) -> &Dir {
        self.dir
            .as_ref()
            .expect("confined filesystem path has a root directory")
    }
}

/// Turn a Windows verbatim path (`\\?\C:\dir`) back into its ordinary spelling (`C:\dir`),
/// so that it can be compared with paths scripts write. `std::fs::canonicalize` always
/// returns the verbatim form on Windows. Other paths are returned unchanged.
fn strip_verbatim(path: PathBuf) -> PathBuf {
    #[cfg(windows)]
    {
        use std::path::Prefix;
        let mut components = path.components();
        if let Some(Component::Prefix(prefix)) = components.next() {
            let rest: PathBuf = components.collect();
            match prefix.kind() {
                Prefix::VerbatimDisk(drive) => {
                    let mut out = PathBuf::from(format!("{}:\\", drive as char));
                    out.push(rest);
                    return out;
                }
                Prefix::VerbatimUNC(server, share) => {
                    let mut out = PathBuf::from(format!(
                        "\\\\{}\\{}\\",
                        server.to_string_lossy(),
                        share.to_string_lossy()
                    ));
                    out.push(rest);
                    return out;
                }
                _ => (),
            }
        }
    }
    path
}

/// Return the spelling of a root with a known OS prefix alias, when one exists.
fn prefix_alias(path: &Path) -> Option<PathBuf> {
    #[cfg(target_os = "macos")]
    {
        let private_var = Path::new("/private/var");
        let var = Path::new("/var");
        if let Ok(rest) = path.strip_prefix(private_var) {
            return Some(var.join(rest));
        }
        if let Ok(rest) = path.strip_prefix(var) {
            return Some(private_var.join(rest));
        }
    }
    let _ = path;
    None
}

/// Refuse a relative path that lexically climbs above its start.
fn check_relative(path: &str, rel: &Path) -> Result<(), SysError> {
    let mut depth: isize = 0;
    for c in rel.components() {
        match c {
            Component::Normal(..) => depth += 1,
            Component::CurDir => (),
            Component::ParentDir => {
                depth -= 1;
                if depth < 0 {
                    return Err(SysError::Denied(format!("path `{path}` escapes its root")));
                }
            }
            Component::Prefix(..) | Component::RootDir => {
                return Err(SysError::Denied(format!("path `{path}` escapes its root")));
            }
        }
    }
    Ok(())
}

impl FsState {
    fn resolve(&self, path: &str, need: Need) -> Result<Resolved<'_>, SysError> {
        let p = Path::new(if path.is_empty() { "." } else { path });

        match self {
            Self::Unrestricted(access) => {
                if !need.satisfied_by(*access) {
                    return Err(SysError::Denied(format!(
                        "filesystem access is {access:?}, `{path}` needs {}",
                        need.describe()
                    )));
                }
                Ok(Resolved {
                    dir: None,
                    rel: PathBuf::from("."),
                    // `std::fs` accepts relative paths directly. Do not require resolving cwd
                    // merely to route an unrestricted operation through its host path.
                    host_path: Some(p.to_path_buf()),
                    root: usize::MAX,
                })
            }
            Self::Roots(roots) => {
                let (ix, rel) = if p.is_absolute() {
                    let mut best: Option<(usize, &Path)> = None;
                    for (i, root) in roots.iter().enumerate() {
                        let mut aliases = vec![root.given.as_path(), root.canonical.as_path()];
                        let given_alias = prefix_alias(&root.given);
                        let canonical_alias = prefix_alias(&root.canonical);
                        aliases.extend(given_alias.iter().map(PathBuf::as_path));
                        aliases.extend(canonical_alias.iter().map(PathBuf::as_path));
                        let hit = aliases.iter().find_map(|alias| p.strip_prefix(alias).ok());
                        if let Some(rel) = hit {
                            let depth = root.canonical.components().count();
                            let better = best.map_or(true, |(b, ..)| {
                                depth > roots[b].canonical.components().count()
                            });
                            if better {
                                best = Some((i, rel));
                            }
                        }
                    }
                    let Some((i, rel)) = best else {
                        return Err(SysError::Denied(format!(
                            "path `{path}` is outside every configured root"
                        )));
                    };
                    (i, rel.to_path_buf())
                } else {
                    if roots.is_empty() {
                        return Err(SysError::Denied(
                            "no filesystem root is configured".to_string(),
                        ));
                    }
                    (0, p.to_path_buf())
                };

                check_relative(path, &rel)?;

                let root = &roots[ix];
                if !need.satisfied_by(root.access) {
                    return Err(SysError::Denied(format!(
                        "root `{}` is {:?}, `{path}` needs {}",
                        root.given.display(),
                        root.access,
                        need.describe()
                    )));
                }

                let rel = if rel.as_os_str().is_empty() {
                    PathBuf::from(".")
                } else {
                    rel
                };

                Ok(Resolved {
                    dir: Some(&root.dir),
                    rel,
                    host_path: None,
                    root: ix,
                })
            }
        }
    }

    /// Open a child working directory through the configured filesystem capability. Retaining
    /// this directory handle lets the process launcher change directory by descriptor without
    /// reopening a pathname after policy validation.
    pub(super) fn open_process_cwd(&self, path: &str) -> Result<Dir, SysError> {
        let resolved = self.resolve(path, Need::Read)?;
        let unrestricted = resolved.host_path.is_some();
        let directory = if let Some(host_path) = resolved.host_path {
            Dir::open_ambient_dir(host_path, ambient_authority())
        } else {
            resolved.dir().open_dir(&resolved.rel)
        };
        directory.map_err(|e| {
            if unrestricted {
                SysError::io("open process working directory", path, &e)
            } else {
                map_io("open process working directory", path, &e)
            }
        })
    }
}

/// Map an I/O error from `cap-std`, turning its sandbox-escape error into `Denied`.
fn map_io(op: &'static str, path: &str, err: &io::Error) -> SysError {
    if err.kind() == io::ErrorKind::PermissionDenied
        && err.to_string().contains("outside of the filesystem")
    {
        SysError::Denied(format!("path `{path}` escapes its root"))
    } else {
        SysError::io(op, path, err)
    }
}

fn os_to_string(what: &str, s: std::ffi::OsString) -> Result<String, SysError> {
    s.into_string()
        .map_err(|s| SysError::NotUtf8(format!("{what} {s:?}")))
}

macro_rules! with_state {
    ($state:ident, $module:ident, $name:literal, $comments:expr, |$($arg:ident : $ty:ty),*| -> $ret:ty $body:block) => {{
        let st = $state.clone();
        reg($name, $comments).set_into_module($module, move |$($arg: $ty),*| -> $ret {
            let $state = &*st;
            $body
        });
    }};
}

#[derive(Default)]
struct FileMode {
    read: bool,
    write: bool,
    append: bool,
    create: bool,
    create_new: bool,
    truncate: bool,
}

/// Parse the upstream-compatible modes. The default `w+` deliberately does not truncate an
/// existing file.
fn file_mode(mode: &str) -> FileMode {
    let mut options = FileMode::default();
    match mode {
        "r" => options.read = true,
        "r+" => {
            options.read = true;
            options.write = true;
        }
        "w" => {
            options.write = true;
            options.create = true;
            options.truncate = true;
        }
        "wx" => {
            options.write = true;
            options.create_new = true;
        }
        "w+" => {
            options.read = true;
            options.write = true;
            options.create = true;
        }
        "a" => {
            options.append = true;
            options.create = true;
        }
        "ax" => {
            options.append = true;
            options.create_new = true;
        }
        "a+" => {
            options.read = true;
            options.append = true;
            options.create = true;
        }
        "ax+" => {
            options.read = true;
            options.append = true;
            options.create_new = true;
        }
        // Preserve the upstream invalid-mode behavior: let OpenOptions report that no
        // access mode was selected.
        _ => (),
    }
    options
}

impl FileMode {
    fn needs_write(&self) -> bool {
        self.write || self.append || self.create || self.create_new || self.truncate
    }

    fn apply_to_cap(&self, options: &mut OpenOptions) {
        options
            .read(self.read)
            .write(self.write)
            .append(self.append)
            .create(self.create)
            .create_new(self.create_new)
            .truncate(self.truncate);
    }

    fn apply_to_host(&self, options: &mut std::fs::OpenOptions) {
        options
            .read(self.read)
            .write(self.write)
            .append(self.append)
            .create(self.create)
            .create_new(self.create_new)
            .truncate(self.truncate);
    }
}

fn open_file(fs: &FsState, path: &str, mode: &str) -> Res<FileHandle> {
    let mode = file_mode(mode);
    if mode.read {
        // Read/write modes must be granted both capabilities before any create or
        // truncating open reaches the filesystem.
        fs.resolve(path, Need::Read)?;
    }
    let need = if mode.needs_write() {
        Need::Write
    } else {
        // Also route invalid modes through the configured authority before reporting their
        // empty-access OpenOptions error.
        Need::Read
    };
    let resolved = fs.resolve(path, need)?;
    let file = match &resolved.host_path {
        Some(host_path) => {
            let mut options = std::fs::OpenOptions::new();
            mode.apply_to_host(&mut options);
            options.open(host_path)
        }
        None => {
            let mut options = OpenOptions::new();
            mode.apply_to_cap(&mut options);
            resolved
                .dir()
                .open_with(&resolved.rel, &options)
                .map(cap_std::fs::File::into_std)
        }
    }
    .map_err(|e| map_io("open file", path, &e))?;
    Ok(Shared::new(Locked::new(file)))
}

fn file_lock_error(action: &'static str) -> SysError {
    SysError::io(
        action,
        "file handle",
        &io::Error::new(
            io::ErrorKind::Other,
            "file handle is already borrowed or poisoned",
        ),
    )
}

#[cfg(not(feature = "sync"))]
fn with_file_mut<T>(
    file: &FileHandle,
    action: &'static str,
    f: impl FnOnce(&mut std::fs::File) -> io::Result<T>,
) -> Res<T> {
    let mut guard = file.try_borrow_mut().map_err(|_| file_lock_error(action))?;
    f(&mut guard).map_err(|e| SysError::io(action, "file handle", &e).into())
}

#[cfg(feature = "sync")]
fn with_file_mut<T>(
    file: &FileHandle,
    action: &'static str,
    f: impl FnOnce(&mut std::fs::File) -> io::Result<T>,
) -> Res<T> {
    let mut guard = file.write().map_err(|_| file_lock_error(action))?;
    f(&mut guard).map_err(|e| SysError::io(action, "file handle", &e).into())
}

fn read_file_bytes(
    file: &FileHandle,
    requested: INT,
    host_limit: usize,
    engine_limit: usize,
    action: &'static str,
) -> Res<Vec<u8>> {
    if requested < 0 {
        return Err(SysError::io(
            action,
            "file handle",
            &io::Error::new(
                io::ErrorKind::InvalidInput,
                "read length cannot be negative",
            ),
        )
        .into());
    }

    let mut limit = host_limit;
    if engine_limit > 0 {
        limit = limit.min(engine_limit);
    }
    if requested > 0 {
        // A positive INT may not fit usize on 32-bit targets. The host/engine cap is
        // already representable as usize, so saturating the request at usize::MAX is safe.
        let requested = usize::try_from(requested).unwrap_or(usize::MAX);
        limit = limit.min(requested);
    }
    if limit == 0 {
        return Ok(Vec::new());
    }

    let mut bytes = Vec::new();
    bytes.try_reserve_exact(limit).map_err(|e| {
        SysError::io(
            action,
            "file handle",
            &io::Error::new(io::ErrorKind::Other, e),
        )
    })?;
    let count = with_file_mut(file, action, |file| {
        if requested == 0 && engine_limit == 0 {
            file.take(limit as u64).read_to_end(&mut bytes)
        } else {
            bytes.resize(limit, 0);
            file.read(&mut bytes)
        }
    })?;
    if requested != 0 || engine_limit != 0 {
        bytes.truncate(count);
    }
    Ok(bytes)
}

fn register_file_handle(module: &mut Module, max_file_read: usize) {
    module.set_custom_type::<FileHandle>("FileHandle");
    reg(
        "read_string",
        &["/// Read up to the requested bytes from the current cursor as strict UTF-8. A zero or omitted length reads up to EOF or the configured cap."],
    )
    .set_into_module(module, move |ctx: NativeCallContext, file: FileHandle| -> Res<String> {
        #[cfg(not(feature = "unchecked"))]
        let engine_limit = ctx.engine().max_string_size();
        #[cfg(feature = "unchecked")]
        let engine_limit = 0;
        let bytes = read_file_bytes(
            &file,
            0,
            max_file_read,
            engine_limit,
            "read file",
        )?;
        String::from_utf8(bytes).map_err(|e| {
            SysError::io(
                "read file as string",
                "file handle",
                &io::Error::new(io::ErrorKind::InvalidData, e),
            )
            .into()
        })
    });
    reg(
        "read_string",
        &["/// Read up to `len` bytes from the current cursor as strict UTF-8. A zero length reads up to EOF or the configured cap."],
    )
    .set_into_module(module, move |ctx: NativeCallContext, file: FileHandle, len: INT| -> Res<String> {
        #[cfg(not(feature = "unchecked"))]
        let engine_limit = ctx.engine().max_string_size();
        #[cfg(feature = "unchecked")]
        let engine_limit = 0;
        let bytes = read_file_bytes(
            &file,
            len,
            max_file_read,
            engine_limit,
            "read file",
        )?;
        String::from_utf8(bytes).map_err(|e| {
            SysError::io(
                "read file as string",
                "file handle",
                &io::Error::new(io::ErrorKind::InvalidData, e),
            )
            .into()
        })
    });

    #[cfg(not(feature = "no_index"))]
    {
        reg(
            "read_blob",
            &["/// Read up to the requested bytes from the current cursor as a BLOB. A zero or omitted length reads up to EOF or the configured cap."],
        )
        .set_into_module(module, move |ctx: NativeCallContext, file: FileHandle| -> Res<crate::Blob> {
            #[cfg(not(feature = "unchecked"))]
            let engine_limit = ctx.engine().max_array_size();
            #[cfg(feature = "unchecked")]
            let engine_limit = 0;
            read_file_bytes(
                &file,
                0,
                max_file_read,
                engine_limit,
                "read file as blob",
            )
        });
        reg(
            "read_blob",
            &["/// Read up to `len` bytes from the current cursor as a BLOB. A zero length reads up to EOF or the configured cap."],
        )
        .set_into_module(module, move |ctx: NativeCallContext, file: FileHandle, len: INT| -> Res<crate::Blob> {
            #[cfg(not(feature = "unchecked"))]
            let engine_limit = ctx.engine().max_array_size();
            #[cfg(feature = "unchecked")]
            let engine_limit = 0;
            read_file_bytes(
                &file,
                len,
                max_file_read,
                engine_limit,
                "read file as blob",
            )
        });
    }

    reg(
        "write",
        &["/// Write one string to the file and return the number of bytes written."],
    )
    .set_into_module(module, |file: FileHandle, data: &str| -> Res<INT> {
        let count = with_file_mut(&file, "write file", |file| file.write(data.as_bytes()))?;
        INT::try_from(count).map_err(|_| {
            SysError::io(
                "write file",
                "file handle",
                &io::Error::new(io::ErrorKind::Other, "written byte count does not fit INT"),
            )
            .into()
        })
    });

    #[cfg(not(feature = "no_index"))]
    reg(
        "write",
        &["/// Write one BLOB to the file and return the number of bytes written."],
    )
    .set_into_module(module, |file: FileHandle, data: crate::Blob| -> Res<INT> {
        let count = with_file_mut(&file, "write file", |file| file.write(&data))?;
        INT::try_from(count).map_err(|_| {
            SysError::io(
                "write file",
                "file handle",
                &io::Error::new(io::ErrorKind::Other, "written byte count does not fit INT"),
            )
            .into()
        })
    });

    reg(
        "seek",
        &["/// Seek to an absolute byte position, clamping negative positions to zero."],
    )
    .set_into_module(module, |file: FileHandle, position: INT| -> Res<()> {
        let position = u64::try_from(position.max(0)).expect("non-negative INT fits u64");
        with_file_mut(&file, "seek file", |file| {
            file.seek(SeekFrom::Start(position))
        })?;
        Ok(())
    });

    reg(
        "position",
        &["/// Return the current byte position of the file cursor."],
    )
    .set_into_module(module, |file: FileHandle| -> Res<INT> {
        let position = with_file_mut(&file, "get file position", |file| file.stream_position())?;
        INT::try_from(position).map_err(|_| {
            SysError::io(
                "get file position",
                "file handle",
                &io::Error::new(io::ErrorKind::Other, "file position does not fit INT"),
            )
            .into()
        })
    });
}

pub(super) fn register(module: &mut Module, state: &Shared<SysState>) {
    register_file_handle(module, state.config.max_file_read);

    with_state!(state, module, "open_file", &["/// Open a file read/write with the default `w+` mode, creating it without truncating existing content."], |path: &str| -> Res<FileHandle> {
        open_file(&state.fs, path, "w+")
    });
    with_state!(
        state,
        module,
        "open_file",
        &["/// Open a file with one of `r`, `r+`, `w`, `wx`, `w+`, `a`, `ax`, `a+` or `ax+`."],
        |path: &str, mode: &str| -> Res<FileHandle> { open_file(&state.fs, path, mode) }
    );

    with_state!(
        state,
        module,
        "read_file",
        &[
            "/// Read a whole file as a string. Invalid UTF-8 is replaced with U+FFFD.",
            "///",
            "/// # Example",
            "///",
            "/// ```rhai",
            "/// let text = read_file(\"notes.txt\");",
            "///",
            "/// print(text.len());",
            "/// ```",
        ],
        |path: &str| -> Res<String> {
            let r = state.fs.resolve(path, Need::Read)?;
            let bytes = match &r.host_path {
                Some(path) => std::fs::read(path),
                None => r.dir().read(&r.rel),
            }
            .map_err(|e| map_io("read file", path, &e))?;
            Ok(String::from_utf8_lossy(&bytes).into_owned())
        }
    );

    #[cfg(not(feature = "no_index"))]
    with_state!(
        state,
        module,
        "read_file_blob",
        &["/// Read a whole file as a BLOB."],
        |path: &str| -> Res<crate::Blob> {
            let r = state.fs.resolve(path, Need::Read)?;
            match &r.host_path {
                Some(path) => std::fs::read(path),
                None => r.dir().read(&r.rel),
            }
            .map_err(|e| map_io("read file", path, &e).into())
        }
    );

    with_state!(
        state,
        module,
        "write_file",
        &[
            "/// Write a string to a file, creating it or truncating existing content.",
            "///",
            "/// # Example",
            "///",
            "/// ```rhai",
            "/// write_file(\"out.txt\", \"hello\");",
            "///",
            "/// print(read_file(\"out.txt\"));      // prints \"hello\"",
            "/// ```",
        ],
        |path: &str, data: &str| -> Res<()> {
            let r = state.fs.resolve(path, Need::Write)?;
            match &r.host_path {
                Some(path) => std::fs::write(path, data.as_bytes()),
                None => r.dir().write(&r.rel, data.as_bytes()),
            }
            .map_err(|e| map_io("write file", path, &e).into())
        }
    );

    #[cfg(not(feature = "no_index"))]
    with_state!(
        state,
        module,
        "write_file",
        &["/// Write a BLOB to a file, creating it or truncating existing content."],
        |path: &str, data: crate::Blob| -> Res<()> {
            let r = state.fs.resolve(path, Need::Write)?;
            match &r.host_path {
                Some(path) => std::fs::write(path, &data),
                None => r.dir().write(&r.rel, &data),
            }
            .map_err(|e| map_io("write file", path, &e).into())
        }
    );

    with_state!(
        state,
        module,
        "append_file",
        &[
            "/// Append a string to a file, creating it when missing.",
            "///",
            "/// # Example",
            "///",
            "/// ```rhai",
            "/// append_file(\"log.txt\", \"one\\n\");",
            "/// append_file(\"log.txt\", \"two\\n\");",
            "/// ```",
        ],
        |path: &str, data: &str| -> Res<()> { append(&state.fs, path, data.as_bytes()) }
    );

    #[cfg(not(feature = "no_index"))]
    with_state!(
        state,
        module,
        "append_file",
        &["/// Append a BLOB to a file, creating it when missing."],
        |path: &str, data: crate::Blob| -> Res<()> { append(&state.fs, path, &data) }
    );

    with_state!(
        state,
        module,
        "exists",
        &[
            "/// Return `true` when the path exists (following symbolic links).",
            "///",
            "/// # Example",
            "///",
            "/// ```rhai",
            "/// if !exists(\"config.toml\") { write_file(\"config.toml\", \"\"); }",
            "/// ```",
        ],
        |path: &str| -> Res<bool> { Ok(meta(&state.fs, path)?.is_some()) }
    );

    with_state!(
        state,
        module,
        "is_file",
        &["/// Return `true` when the path exists and is a regular file."],
        |path: &str| -> Res<bool> { Ok(meta(&state.fs, path)?.map_or(false, |m| m.0)) }
    );

    with_state!(
        state,
        module,
        "is_dir",
        &["/// Return `true` when the path exists and is a directory."],
        |path: &str| -> Res<bool> { Ok(meta(&state.fs, path)?.map_or(false, |m| m.1)) }
    );

    with_state!(state, module, "metadata",
        &[
            "/// Return an object map describing the path: `size`, `is_file`, `is_dir`, `is_symlink`,",
            "/// `readonly` and `modified` (seconds since the Unix epoch, or `()` when unavailable).",
            "///",
            "/// # Example",
            "///",
            "/// ```rhai",
            "/// let m = metadata(\"data.bin\");",
            "///",
            "/// print(m.size);          // prints the size in bytes",
            "/// print(m.is_dir);        // prints false",
            "/// ```",
        ],
        |path: &str| -> Res<Map> {
            let r = state.fs.resolve(path, Need::Read)?;
            let (size, is_file, is_dir, is_symlink, readonly, modified) = match &r.host_path {
                Some(host_path) => {
                    let m = std::fs::metadata(host_path).map_err(|e| map_io("read metadata of", path, &e))?;
                    let sm = std::fs::symlink_metadata(host_path).map_err(|e| map_io("read metadata of", path, &e))?;
                    (m.len(), m.is_file(), m.is_dir(), sm.file_type().is_symlink(), m.permissions().readonly(), m.modified())
                }
                None => {
                    let m = r.dir().metadata(&r.rel).map_err(|e| map_io("read metadata of", path, &e))?;
                    let sm = r.dir().symlink_metadata(&r.rel).map_err(|e| map_io("read metadata of", path, &e))?;
                    (m.len(), m.is_file(), m.is_dir(), sm.file_type().is_symlink(), m.permissions().readonly(), m.modified().map(|t| t.into_std()))
                }
            };
            let modified: Dynamic = match modified {
                Ok(t) => match t.duration_since(std::time::UNIX_EPOCH) {
                    Ok(d) => INT::try_from(d.as_secs()).map_or(Dynamic::UNIT, Into::into),
                    Err(..) => Dynamic::UNIT,
                },
                Err(..) => Dynamic::UNIT,
            };
            let mut map = Map::new();
            map.insert("size".into(), INT::try_from(size).unwrap_or(INT::MAX).into());
            map.insert("is_file".into(), is_file.into());
            map.insert("is_dir".into(), is_dir.into());
            map.insert("is_symlink".into(), is_symlink.into());
            map.insert("readonly".into(), readonly.into());
            map.insert("modified".into(), modified);
            Ok(map)
        });

    #[cfg(not(feature = "no_index"))]
    with_state!(
        state,
        module,
        "read_dir",
        &[
            "/// Return the names of the entries of a directory, sorted, without `.` and `..`.",
            "///",
            "/// # Example",
            "///",
            "/// ```rhai",
            "/// for name in read_dir(\".\") {",
            "///     if is_dir(name) { print(name + \"/\"); } else { print(name); }",
            "/// }",
            "/// ```",
        ],
        |path: &str| -> Res<crate::Array> {
            let r = state.fs.resolve(path, Need::Read)?;
            let mut names = Vec::new();
            match &r.host_path {
                Some(host_path) => {
                    for entry in std::fs::read_dir(host_path)
                        .map_err(|e| map_io("read directory", path, &e))?
                    {
                        let entry = entry.map_err(|e| map_io("read directory", path, &e))?;
                        names.push(os_to_string("directory entry", entry.file_name())?);
                    }
                }
                None => {
                    for entry in r
                        .dir()
                        .read_dir(&r.rel)
                        .map_err(|e| map_io("read directory", path, &e))?
                    {
                        let entry = entry.map_err(|e| map_io("read directory", path, &e))?;
                        names.push(os_to_string("directory entry", entry.file_name())?);
                    }
                }
            }
            names.sort_unstable();
            Ok(names.into_iter().map(Into::into).collect())
        }
    );

    with_state!(
        state,
        module,
        "create_dir",
        &["/// Create a directory. The parent must exist."],
        |path: &str| -> Res<()> {
            let r = state.fs.resolve(path, Need::Write)?;
            match &r.host_path {
                Some(path) => std::fs::create_dir(path),
                None => r.dir().create_dir(&r.rel),
            }
            .map_err(|e| map_io("create directory", path, &e).into())
        }
    );

    with_state!(
        state,
        module,
        "create_dir_all",
        &[
            "/// Create a directory and every missing parent.",
            "///",
            "/// # Example",
            "///",
            "/// ```rhai",
            "/// create_dir_all(\"build/output/logs\");",
            "/// ```",
        ],
        |path: &str| -> Res<()> {
            let r = state.fs.resolve(path, Need::Write)?;
            match &r.host_path {
                Some(path) => std::fs::create_dir_all(path),
                None => r.dir().create_dir_all(&r.rel),
            }
            .map_err(|e| map_io("create directory", path, &e).into())
        }
    );

    with_state!(
        state,
        module,
        "remove_file",
        &["/// Remove a file."],
        |path: &str| -> Res<()> {
            let r = state.fs.resolve(path, Need::Write)?;
            match &r.host_path {
                Some(path) => std::fs::remove_file(path),
                None => r.dir().remove_file(&r.rel),
            }
            .map_err(|e| map_io("remove file", path, &e).into())
        }
    );

    with_state!(
        state,
        module,
        "remove_dir",
        &["/// Remove an empty directory."],
        |path: &str| -> Res<()> {
            let r = state.fs.resolve(path, Need::Write)?;
            match &r.host_path {
                Some(path) => std::fs::remove_dir(path),
                None => r.dir().remove_dir(&r.rel),
            }
            .map_err(|e| map_io("remove directory", path, &e).into())
        }
    );

    with_state!(
        state,
        module,
        "remove_dir_all",
        &[
            "/// Remove a directory and everything below it. Needs `FsAccess::ReadWriteDelete`.",
            "///",
            "/// # Example",
            "///",
            "/// ```rhai",
            "/// remove_dir_all(\"build\");",
            "/// ```",
        ],
        |path: &str| -> Res<()> {
            let r = state.fs.resolve(path, Need::Delete)?;
            match &r.host_path {
                Some(path) => std::fs::remove_dir_all(path),
                None => r.dir().remove_dir_all(&r.rel),
            }
            .map_err(|e| map_io("remove directory", path, &e).into())
        }
    );

    with_state!(
        state,
        module,
        "rename",
        &[
            "/// Rename or move a file or directory. Both paths must lie inside the same root.",
            "///",
            "/// # Example",
            "///",
            "/// ```rhai",
            "/// rename(\"draft.txt\", \"final.txt\");",
            "/// ```",
        ],
        |from: &str, to: &str| -> Res<()> {
            let a = state.fs.resolve(from, Need::Write)?;
            let b = state.fs.resolve(to, Need::Write)?;
            if a.root != b.root {
                return Err(SysError::Denied(format!(
                    "cannot rename `{from}` to `{to}`: different roots"
                ))
                .into());
            }
            match (&a.host_path, &b.host_path) {
                (Some(from), Some(to)) => std::fs::rename(from, to),
                _ => a.dir().rename(&a.rel, b.dir(), &b.rel),
            }
            .map_err(|e| map_io("rename", from, &e).into())
        }
    );

    with_state!(
        state,
        module,
        "copy_file",
        &[
            "/// Copy a file. The destination is created or truncated.",
            "///",
            "/// # Example",
            "///",
            "/// ```rhai",
            "/// copy_file(\"template.txt\", \"copy.txt\");",
            "/// ```",
        ],
        |from: &str, to: &str| -> Res<()> {
            let a = state.fs.resolve(from, Need::Read)?;
            let b = state.fs.resolve(to, Need::Write)?;
            match (&a.host_path, &b.host_path) {
                (Some(from_path), Some(to_path)) => std::fs::copy(from_path, to_path).map(|_| ()),
                _ => a.dir().copy(&a.rel, b.dir(), &b.rel).map(|_| ()),
            }
            .map_err(|e| map_io("copy", from, &e).into())
        }
    );
}

fn append(fs: &FsState, path: &str, data: &[u8]) -> Res<()> {
    let r = fs.resolve(path, Need::Write)?;
    if let Some(host_path) = &r.host_path {
        let mut file = std::fs::OpenOptions::new()
            .append(true)
            .create(true)
            .open(host_path)
            .map_err(|e| map_io("append to file", path, &e))?;
        file.write_all(data)
            .map_err(|e| map_io("append to file", path, &e))?;
    } else {
        let mut file = r
            .dir()
            .open_with(&r.rel, OpenOptions::new().append(true).create(true))
            .map_err(|e| map_io("append to file", path, &e))?;
        file.write_all(data)
            .map_err(|e| map_io("append to file", path, &e))?;
    }
    Ok(())
}

/// Metadata of a path, `None` when it does not exist.
fn meta(fs: &FsState, path: &str) -> Res<Option<(bool, bool)>> {
    let r = fs.resolve(path, Need::Read)?;
    let result = match &r.host_path {
        Some(path) => std::fs::metadata(path).map(|m| (m.is_file(), m.is_dir())),
        None => r.dir().metadata(&r.rel).map(|m| (m.is_file(), m.is_dir())),
    };
    match result {
        Ok(m) => Ok(Some(m)),
        Err(e) if e.kind() == io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(map_io("read metadata of", path, &e).into()),
    }
}
