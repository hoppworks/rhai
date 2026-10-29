//! Windows process argument and environment encoding for managed launches.

use super::Options;
use std::cmp::Ordering;
use std::io;
use std::os::windows::ffi::OsStrExt;
use windows_sys::Win32::Globalization::{
    CompareStringOrdinal, CSTR_EQUAL, CSTR_GREATER_THAN, CSTR_LESS_THAN,
};

pub(super) fn command_line(program: &str, args: &[String]) -> io::Result<Vec<u16>> {
    if program.contains(['\0', '"']) {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "invalid Windows program name",
        ));
    }
    let mut result = Vec::new();
    result.push(b'"' as u16);
    result.extend(program.encode_utf16());
    result.push(b'"' as u16);
    for arg in args {
        if arg.contains('\0') {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "argument contains NUL",
            ));
        }
        result.push(b' ' as u16);
        let quoted = arg.is_empty() || arg.contains([' ', '\t']);
        if quoted {
            result.push(b'"' as u16);
        }
        let mut slashes = 0usize;
        for unit in arg.encode_utf16() {
            match unit {
                92 => {
                    slashes += 1;
                    result.push(unit);
                }
                34 => {
                    result.extend(std::iter::repeat(92u16).take(slashes + 1));
                    result.push(unit);
                    slashes = 0;
                }
                _ => {
                    result.push(unit);
                    slashes = 0;
                }
            }
        }
        if quoted {
            result.extend(std::iter::repeat(92u16).take(slashes));
            result.push(b'"' as u16);
        }
    }
    result.push(0);
    if result.len() > 32_767 {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "Windows command line exceeds 32767 UTF-16 units",
        ));
    }
    Ok(result)
}

/// Match the batch-file argument boundary used by Rust's Windows Command on
/// our sys-feature MSRV. Batch arguments are parsed by cmd.exe, not the C CRT.
pub(super) fn batch_command_line(script: &[u16], args: &[String]) -> io::Result<Vec<u16>> {
    if script.len() < 2
        || script.last() != Some(&0)
        || script[..script.len() - 1].contains(&0)
        || script[..script.len() - 1].contains(&(b'"' as u16))
        || script[script.len() - 2] == b'\\' as u16
    {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "invalid batch file name"));
    }
    let mut result: Vec<u16> = "cmd.exe /e:ON /v:OFF /d /c \"\"".encode_utf16().collect();
    result.extend_from_slice(&script[..script.len() - 1]);
    result.push(b'"' as u16);
    for arg in args {
        if arg.contains(['\0', '\r', '\n']) {
            return Err(io::Error::new(io::ErrorKind::InvalidInput, "invalid batch argument"));
        }
        result.push(b' ' as u16);
        let quote = arg.is_empty()
            || arg.ends_with('\\')
            || arg.chars().any(|ch| {
                ch.is_control()
                    || (ch.is_ascii()
                        && !(ch.is_ascii_alphanumeric() || r"#$*+-./:?@\_".contains(ch)))
            });
        if quote {
            result.push(b'"' as u16);
        }
        let mut slashes = 0usize;
        for unit in arg.encode_utf16() {
            if unit == b'\\' as u16 {
                slashes += 1;
            } else {
                if unit == b'"' as u16 {
                    result.extend(std::iter::repeat(b'\\' as u16).take(slashes));
                    result.push(b'"' as u16);
                } else if unit == b'%' as u16 {
                    result.extend("%%cd:~,".encode_utf16());
                }
                slashes = 0;
            }
            result.push(unit);
        }
        if quote {
            result.extend(std::iter::repeat(b'\\' as u16).take(slashes));
            result.push(b'"' as u16);
        }
    }
    result.push(b'"' as u16);
    result.push(0);
    if result.len() > 32_767 {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "Windows command line exceeds 32767 UTF-16 units"));
    }
    Ok(result)
}

type Entry = (Vec<u16>, Vec<u16>);

fn compare(a: &[u16], b: &[u16]) -> io::Result<Ordering> {
    if a.is_empty() || b.is_empty() {
        return Ok(a.len().cmp(&b.len()));
    }
    let alen = i32::try_from(a.len())
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "environment key too long"))?;
    let blen = i32::try_from(b.len())
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "environment key too long"))?;
    // SAFETY: UTF-16 slices are live and lengths match; Windows supplies case folding.
    match unsafe { CompareStringOrdinal(a.as_ptr(), alen, b.as_ptr(), blen, 1) } {
        CSTR_LESS_THAN => Ok(Ordering::Less),
        CSTR_EQUAL => Ok(Ordering::Equal),
        CSTR_GREATER_THAN => Ok(Ordering::Greater),
        _ => Err(io::Error::last_os_error()),
    }
}

fn insert(entries: &mut Vec<Entry>, key: Vec<u16>, value: Vec<u16>) -> io::Result<()> {
    let mut index = 0;
    while index < entries.len() {
        match compare(&entries[index].0, &key)? {
            Ordering::Less => index += 1,
            Ordering::Equal => {
                entries[index] = (key, value);
                return Ok(());
            }
            Ordering::Greater => break,
        }
    }
    entries.insert(index, (key, value));
    Ok(())
}

/// `None` inherits unchanged; otherwise return a sorted, double-NUL-terminated block.
pub(super) fn environment(options: &Options) -> io::Result<Option<Vec<u16>>> {
    if !options.env_clear && options.env.is_empty() && options.env_remove.is_empty() {
        return Ok(None);
    }
    let mut entries = Vec::new();
    if !options.env_clear {
        for (key, value) in std::env::vars_os() {
            insert(
                &mut entries,
                key.encode_wide().collect(),
                value.encode_wide().collect(),
            )?;
        }
    }
    for key in &options.env_remove {
        if key.is_empty() || key.contains(['\0', '=']) {
            return Err(io::Error::new(io::ErrorKind::InvalidInput, "invalid child environment key"));
        }
        let key: Vec<u16> = key.encode_utf16().collect();
        let mut index = 0;
        while index < entries.len() {
            if compare(&entries[index].0, &key)? == Ordering::Equal {
                entries.remove(index);
                break;
            }
            index += 1;
        }
    }
    for (key, value) in &options.env {
        if key.contains('\0') || value.contains('\0') {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "invalid child environment entry",
            ));
        }
        insert(
            &mut entries,
            key.encode_utf16().collect(),
            value.encode_utf16().collect(),
        )?;
    }
    let mut block = Vec::new();
    for (key, value) in entries {
        block.extend(key);
        block.push(b'=' as u16);
        block.extend(value);
        block.push(0);
    }
    if block.is_empty() {
        block.push(0);
    }
    block.push(0);
    Ok(Some(block))
}
