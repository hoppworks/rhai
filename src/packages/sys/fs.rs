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
use crate::{Dynamic, EvalAltResult, Map, Module, Shared, INT};
use cap_std::ambient_authority;
use cap_std::fs::{Dir, OpenOptions};
use std::io::{self, Write};
use std::ops::Deref;
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
                    let given = normalize_absolute(&given);
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

/// A directory handle that is either borrowed from a root or opened ad hoc.
enum DirRef<'a> {
    Borrowed(&'a Dir),
    Owned(Dir),
}

impl Deref for DirRef<'_> {
    type Target = Dir;
    fn deref(&self) -> &Dir {
        match self {
            Self::Borrowed(d) => d,
            Self::Owned(d) => d,
        }
    }
}

/// A script path resolved to a directory handle plus a relative path inside it.
struct Resolved<'a> {
    dir: DirRef<'a>,
    rel: PathBuf,
    /// Index of the root, or `usize::MAX` in unrestricted mode.
    root: usize,
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

/// Lexically normalise an absolute path: drop `.`, fold `..`.
fn normalize_absolute(path: &Path) -> PathBuf {
    let mut out = PathBuf::new();
    for c in path.components() {
        match c {
            Component::Prefix(..) | Component::RootDir => out.push(c.as_os_str()),
            Component::CurDir => (),
            Component::ParentDir => {
                out.pop();
            }
            Component::Normal(s) => out.push(s),
        }
    }
    out
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
                let abs = if p.is_absolute() {
                    p.to_path_buf()
                } else {
                    std::env::current_dir()
                        .map_err(|e| SysError::io("get current directory", ".", &e))?
                        .join(p)
                };
                let abs = normalize_absolute(&abs);
                // Open the nearest existing ancestor (never the target itself, so that the
                // target can be removed or renamed) and address the rest relative to it.
                // This also lets operations that create several levels (`create_dir_all`) work.
                let mut base = abs.parent().unwrap_or(abs.as_path());
                while !base.is_dir() {
                    match base.parent() {
                        Some(parent) => base = parent,
                        None => break,
                    }
                }
                let rel = abs.strip_prefix(base).map_or_else(
                    |_| PathBuf::from("."),
                    |r| {
                        if r.as_os_str().is_empty() {
                            PathBuf::from(".")
                        } else {
                            r.to_path_buf()
                        }
                    },
                );
                let dir = Dir::open_ambient_dir(base, ambient_authority())
                    .map_err(|e| SysError::io("open directory", base.display().to_string(), &e))?;
                Ok(Resolved {
                    dir: DirRef::Owned(dir),
                    rel,
                    root: usize::MAX,
                })
            }
            Self::Roots(roots) => {
                let (ix, rel) = if p.is_absolute() {
                    let mut best: Option<(usize, &Path)> = None;
                    for (i, root) in roots.iter().enumerate() {
                        let hit = p
                            .strip_prefix(&root.given)
                            .or_else(|_| p.strip_prefix(&root.canonical));
                        if let Ok(rel) = hit {
                            let depth = root.given.components().count();
                            let better = best.map_or(true, |(b, ..)| {
                                depth > roots[b].given.components().count()
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
                    dir: DirRef::Borrowed(&root.dir),
                    rel,
                    root: ix,
                })
            }
        }
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

pub(super) fn register(module: &mut Module, state: &Shared<SysState>) {
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
            let bytes = r
                .dir
                .read(&r.rel)
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
            r.dir
                .read(&r.rel)
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
            r.dir
                .write(&r.rel, data.as_bytes())
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
            r.dir
                .write(&r.rel, &data)
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
        |path: &str| -> Res<bool> { Ok(meta(&state.fs, path)?.map_or(false, |m| m.is_file())) }
    );

    with_state!(
        state,
        module,
        "is_dir",
        &["/// Return `true` when the path exists and is a directory."],
        |path: &str| -> Res<bool> { Ok(meta(&state.fs, path)?.map_or(false, |m| m.is_dir())) }
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
            let m = r.dir.metadata(&r.rel).map_err(|e| map_io("read metadata of", path, &e))?;
            let sm = r.dir.symlink_metadata(&r.rel).map_err(|e| map_io("read metadata of", path, &e))?;
            let modified: Dynamic = match m.modified() {
                Ok(t) => match t.into_std().duration_since(std::time::UNIX_EPOCH) {
                    Ok(d) => INT::try_from(d.as_secs()).map_or(Dynamic::UNIT, Into::into),
                    Err(..) => Dynamic::UNIT,
                },
                Err(..) => Dynamic::UNIT,
            };
            let mut map = Map::new();
            map.insert("size".into(), INT::try_from(m.len()).unwrap_or(INT::MAX).into());
            map.insert("is_file".into(), m.is_file().into());
            map.insert("is_dir".into(), m.is_dir().into());
            map.insert("is_symlink".into(), sm.file_type().is_symlink().into());
            map.insert("readonly".into(), m.permissions().readonly().into());
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
            let entries = r
                .dir
                .read_dir(&r.rel)
                .map_err(|e| map_io("read directory", path, &e))?;
            let mut names = Vec::new();
            for entry in entries {
                let entry = entry.map_err(|e| map_io("read directory", path, &e))?;
                names.push(os_to_string("directory entry", entry.file_name())?);
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
            r.dir
                .create_dir(&r.rel)
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
            r.dir
                .create_dir_all(&r.rel)
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
            r.dir
                .remove_file(&r.rel)
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
            r.dir
                .remove_dir(&r.rel)
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
            r.dir
                .remove_dir_all(&r.rel)
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
            a.dir
                .rename(&a.rel, &b.dir, &b.rel)
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
            a.dir
                .copy(&a.rel, &b.dir, &b.rel)
                .map(|_| ())
                .map_err(|e| map_io("copy", from, &e).into())
        }
    );
}

fn append(fs: &FsState, path: &str, data: &[u8]) -> Res<()> {
    let r = fs.resolve(path, Need::Write)?;
    let mut file = r
        .dir
        .open_with(&r.rel, OpenOptions::new().append(true).create(true))
        .map_err(|e| map_io("append to file", path, &e))?;
    file.write_all(data)
        .map_err(|e| map_io("append to file", path, &e))?;
    Ok(())
}

/// Metadata of a path, `None` when it does not exist.
fn meta(fs: &FsState, path: &str) -> Res<Option<cap_std::fs::Metadata>> {
    let r = fs.resolve(path, Need::Read)?;
    match r.dir.metadata(&r.rel) {
        Ok(m) => Ok(Some(m)),
        Err(e) if e.kind() == io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(map_io("read metadata of", path, &e).into()),
    }
}
