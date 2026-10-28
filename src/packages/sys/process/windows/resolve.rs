//! Resolve a Windows executable before passing it as an explicit application name.

use super::Options;
use std::ffi::{OsStr, OsString};
use std::io;
use std::os::windows::ffi::{OsStrExt, OsStringExt};
use std::path::{Path, PathBuf};
use std::ptr;
use windows_sys::Win32::Storage::FileSystem::GetFullPathNameW;
use windows_sys::Win32::System::SystemInformation::{GetSystemDirectoryW, GetWindowsDirectoryW};

fn wide(value: &OsStr) -> io::Result<Vec<u16>> {
    let mut result: Vec<u16> = value.encode_wide().collect();
    if result.contains(&0) {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "program contains NUL",
        ));
    }
    result.push(0);
    Ok(result)
}

fn absolute(path: &Path) -> io::Result<Vec<u16>> {
    let name = wide(path.as_os_str())?;
    let mut buffer = vec![0u16; 260];
    loop {
        // SAFETY: name is NUL-terminated and buffer is writable for its stated length.
        let n = unsafe {
            GetFullPathNameW(
                name.as_ptr(),
                buffer.len() as u32,
                buffer.as_mut_ptr(),
                ptr::null_mut(),
            )
        } as usize;
        if n == 0 {
            return Err(io::Error::last_os_error());
        }
        if n < buffer.len() {
            buffer.truncate(n);
            buffer.push(0);
            return Ok(buffer);
        }
        if n > 32_768 {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "program path is too long",
            ));
        }
        buffer.resize(n + 1, 0);
    }
}

fn system_directory(query: unsafe extern "system" fn(*mut u16, u32) -> u32) -> io::Result<PathBuf> {
    let mut buffer = vec![0u16; 260];
    loop {
        // SAFETY: buffer is writable for the declared length.
        let n = unsafe { query(buffer.as_mut_ptr(), buffer.len() as u32) } as usize;
        if n == 0 {
            return Err(io::Error::last_os_error());
        }
        if n < buffer.len() {
            return Ok(PathBuf::from(OsString::from_wide(&buffer[..n])));
        }
        if n > 32_768 {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "system directory is too long",
            ));
        }
        buffer.resize(n + 1, 0);
    }
}

/// Use the system command interpreter for an explicitly permitted batch file.
/// Never select an interpreter from the script's environment or PATH.
pub(super) fn command_prompt() -> io::Result<Vec<u16>> {
    let system = system_directory(GetSystemDirectoryW)?;
    wide(system.join("cmd.exe").as_os_str())
}

fn exists(path: &Path) -> Option<Vec<u16>> {
    std::fs::symlink_metadata(path).ok()?;
    absolute(path).ok()
}

/// Resolve normal executables using the standard Windows Command search order.
/// Native path equivalence and batch command-interpreter semantics remain open.
pub(super) fn resolve_program(program: &str, options: &Options) -> io::Result<Vec<u16>> {
    let name = Path::new(program);
    let trailing_separator =
        program.ends_with('\\') || (!program.starts_with(r"\\?\") && program.ends_with('/'));
    if program.is_empty() || trailing_separator || program.contains('\0') {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "program path has no valid file name",
        ));
    }
    let simple = !program.contains(['\\', '/']);
    if !simple {
        if program.to_ascii_lowercase().ends_with(".exe") {
            return absolute(name);
        }
        let mut with_exe = name.as_os_str().to_os_string();
        with_exe.push(".exe");
        return exists(Path::new(&with_exe)).map_or_else(|| absolute(name), Ok);
    }
    let mut filename = OsString::from(program);
    if !program.contains('.') {
        filename.push(".exe");
    }
    let parent_path = std::env::var_os("PATH");
    let changed_env = options.env_clear || !options.env.is_empty();
    let explicit_path = options
        .env
        .iter()
        .rev()
        .find(|(key, _)| key.eq_ignore_ascii_case("PATH"))
        .map(|(_, value)| OsString::from(value));
    let child_path =
        explicit_path.or_else(|| (!options.env_clear).then(|| parent_path.clone()).flatten());
    let mut directories = Vec::new();
    if changed_env {
        if let Some(paths) = child_path.as_ref() {
            directories.extend(std::env::split_paths(paths).filter(|p| !p.as_os_str().is_empty()));
        }
    }
    if let Ok(executable) = std::env::current_exe() {
        if let Some(parent) = executable.parent() {
            directories.push(parent.to_path_buf());
        }
    }
    // CreateProcess also searches the calling process's current directory for
    // a simple name. The child's configured cwd does not replace this entry.
    directories.push(std::env::current_dir()?);
    for query in [
        GetSystemDirectoryW as unsafe extern "system" fn(*mut u16, u32) -> u32,
        GetWindowsDirectoryW,
    ] {
        if let Ok(directory) = system_directory(query) {
            directories.push(directory);
        }
    }
    if let Some(paths) = parent_path.as_ref() {
        directories.extend(std::env::split_paths(paths).filter(|p| !p.as_os_str().is_empty()));
    }
    directories
        .into_iter()
        .find_map(|dir| exists(&dir.join(&filename)))
        .ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, "program not found"))
}
