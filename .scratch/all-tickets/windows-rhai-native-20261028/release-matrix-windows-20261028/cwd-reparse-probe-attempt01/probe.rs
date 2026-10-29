#![cfg(all(windows, feature = "sys"))]
//! Native, scoped investigation of a pinned directory and an in-place junction.
//! This does not by itself exercise or accept the Rhai cwd implementation.

mod sys_support;

use cap_std::ambient_authority;
use cap_std::fs::Dir;
use std::ffi::c_void;
use std::os::windows::fs::{MetadataExt, OpenOptionsExt};
use std::os::windows::io::AsRawHandle;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};
use sys_support::TempDir;

const FILE_WRITE_ATTRIBUTES: u32 = 0x100;
const FILE_SHARE_READ_WRITE: u32 = 0x3;
const FILE_FLAG_BACKUP_SEMANTICS: u32 = 0x0200_0000;
const FILE_FLAG_OPEN_REPARSE_POINT: u32 = 0x0020_0000;
const IO_REPARSE_TAG_MOUNT_POINT: u32 = 0xA000_0003;
const FSCTL_SET_REPARSE_POINT: u32 = 0x0009_00A4;
const FSCTL_DELETE_REPARSE_POINT: u32 = 0x0009_00AC;

#[link(name = "kernel32")]
extern "system" {
    fn DeviceIoControl(handle: *mut c_void, code: u32, input: *mut c_void, input_size: u32, output: *mut c_void, output_size: u32, returned: *mut u32, overlapped: *mut c_void) -> i32;
}

fn control(handle: &std::fs::File, code: u32, buffer: &mut [u8]) -> std::io::Result<()> {
    let mut returned = 0;
    let ok = unsafe { DeviceIoControl(handle.as_raw_handle().cast(), code, buffer.as_mut_ptr().cast(), buffer.len() as u32, std::ptr::null_mut(), 0, &mut returned, std::ptr::null_mut()) };
    if ok == 0 {
        Err(std::io::Error::last_os_error())
    } else {
        Ok(())
    }
}

fn mount_point(target: &Path) -> Vec<u8> {
    let target = target.to_str().expect("UTF-8 test target");
    assert!(target.as_bytes().get(1) == Some(&b':'), "local drive path required");
    let substitute: Vec<u16> = format!(r"\??\{target}").encode_utf16().collect();
    let printable: Vec<u16> = target.encode_utf16().collect();
    let substitute_bytes = u16::try_from(substitute.len() * 2).unwrap();
    let printable_bytes = u16::try_from(printable.len() * 2).unwrap();
    let print_offset = substitute_bytes.checked_add(2).unwrap();
    let body_len = 8u16
        .checked_add(substitute_bytes)
        .unwrap()
        .checked_add(2)
        .unwrap()
        .checked_add(printable_bytes)
        .unwrap()
        .checked_add(2)
        .unwrap();
    let mut buffer = Vec::with_capacity(8 + body_len as usize);
    buffer.extend_from_slice(&IO_REPARSE_TAG_MOUNT_POINT.to_le_bytes());
    buffer.extend_from_slice(&body_len.to_le_bytes());
    buffer.extend_from_slice(&0u16.to_le_bytes());
    buffer.extend_from_slice(&0u16.to_le_bytes());
    buffer.extend_from_slice(&substitute_bytes.to_le_bytes());
    buffer.extend_from_slice(&print_offset.to_le_bytes());
    buffer.extend_from_slice(&printable_bytes.to_le_bytes());
    for unit in substitute.into_iter().chain([0]).chain(printable).chain([0]) {
        buffer.extend_from_slice(&unit.to_le_bytes());
    }
    assert_eq!(buffer.len(), 8 + body_len as usize);
    buffer
}

struct Fixture {
    root: Option<TempDir>,
    junction: Option<std::fs::File>,
    junction_active: bool,
    child: Option<Child>,
    child_stopped: bool,
}
impl Drop for Fixture {
    fn drop(&mut self) {
        if let Some(child) = self.child.as_mut() {
            if !self.child_stopped {
                match child.try_wait() {
                    Ok(Some(_)) => self.child_stopped = true,
                    _ => {
                        if let Err(error) = child.kill() {
                            eprintln!("exact probe child termination failed: {error}");
                        }
                        let deadline = Instant::now() + Duration::from_secs(10);
                        loop {
                            match child.try_wait() {
                                Ok(Some(_)) => {
                                    self.child_stopped = true;
                                    break;
                                }
                                Ok(None) if Instant::now() < deadline => thread::sleep(Duration::from_millis(10)),
                                other => {
                                    eprintln!("exact probe child exit unconfirmed: {other:?}");
                                    break;
                                }
                            }
                        }
                    }
                }
            }
        }
        if self.junction_active {
            let mut header = [0u8; 8];
            header[..4].copy_from_slice(&IO_REPARSE_TAG_MOUNT_POINT.to_le_bytes());
            if let Some(handle) = self.junction.as_ref() {
                match control(handle, FSCTL_DELETE_REPARSE_POINT, &mut header) {
                    Ok(()) => match self.root.as_ref().and_then(|root| std::fs::symlink_metadata(root.path().join("allowed")).ok()) {
                        Some(metadata) if metadata.file_attributes() & 0x400 == 0 => {
                            self.junction_active = false;
                            eprintln!("windows_reparse_probe_cleanup exact_junction_removed=true");
                        }
                        _ => eprintln!("test junction removal not independently confirmed"),
                    },
                    Err(error) => eprintln!("failed to remove exact test junction: {error}"),
                }
            }
        }
        // Close the mutation handle before attempting to remove its directory.
        self.junction.take();
        if self.junction_active || !self.child_stopped {
            if let Some(root) = self.root.take() {
                eprintln!("preserving reparse probe fixture {} for outer custody", root.path().display());
                std::mem::forget(root);
            }
        }
    }
}

#[test]
fn windows_reparse_child_fixture() {
    let Some(record) = std::env::var_os("RHAI_WINDOWS_REPARSE_RECEIPT") else {
        return;
    };
    let result = match std::fs::read("outside-sentinel") {
        Ok(bytes) => bytes,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => b"missing".to_vec(),
        Err(error) => panic!("read relative child sentinel: {error}"),
    };
    std::fs::write(record, result).expect("write child cwd observation");
}

fn child_read(fixture: &mut Fixture, cwd: &Path, record: &Path) -> Vec<u8> {
    assert!(fixture.child.is_none(), "previous child must be retired");
    let child = Command::new(std::env::current_exe().unwrap())
        .args(["--exact", "windows_reparse_child_fixture", "--quiet"])
        .current_dir(cwd)
        .env("RHAI_WINDOWS_REPARSE_RECEIPT", record)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .expect("spawn exact cwd child");
    fixture.child_stopped = false;
    fixture.child = Some(child);
    let deadline = Instant::now() + Duration::from_secs(15);
    let status = loop {
        match fixture.child.as_mut().unwrap().try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) if Instant::now() < deadline => thread::sleep(Duration::from_millis(10)),
            Ok(None) => panic!("cwd child exceeded 15 seconds"),
            Err(error) => panic!("wait for cwd child: {error}"),
        }
    };
    fixture.child_stopped = true;
    fixture.child.take();
    assert!(status.success(), "cwd child failed: {status:?}");
    std::fs::read(record).expect("fresh child receipt")
}

#[test]
fn pinned_directory_can_become_a_junction_before_child_start() {
    let mut fixture = Fixture {
        root: Some(TempDir::new()),
        junction: None,
        junction_active: false,
        child: None,
        child_stopped: true,
    };
    let root: PathBuf = fixture.root.as_ref().unwrap().path().to_path_buf();
    std::fs::write(root.join("owner.marker"), b"rhai-reparse-probe-v1\n").unwrap();
    eprintln!("windows_reparse_probe_fixture_root={}", root.display());
    let allowed = root.join("allowed");
    let outside = root.join("outside");
    std::fs::create_dir(&allowed).unwrap();
    std::fs::create_dir(&outside).unwrap();
    std::fs::write(outside.join("outside-sentinel"), b"outside-only").unwrap();
    let pin = Dir::open_ambient_dir(&allowed, ambient_authority()).expect("pin allowed directory");
    assert_eq!(std::fs::rename(&allowed, root.join("moved")).unwrap_err().raw_os_error(), Some(32), "directory pin must refuse rename");
    let before = child_read(&mut fixture, &allowed, &root.join("before.txt"));
    assert_eq!(before, b"missing", "unmodified cwd cannot read the outside sentinel");
    let handle = std::fs::OpenOptions::new()
        .access_mode(FILE_WRITE_ATTRIBUTES)
        .share_mode(FILE_SHARE_READ_WRITE)
        .custom_flags(FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT)
        .open(&allowed)
        .expect("open exact directory for attribute mutation");
    fixture.junction = Some(handle);
    let mut data = mount_point(&outside);
    control(fixture.junction.as_ref().unwrap(), FSCTL_SET_REPARSE_POINT, &mut data).expect("set owned test junction while directory remains pinned");
    fixture.junction_active = true;
    let after = child_read(&mut fixture, &allowed, &root.join("after.txt"));
    eprintln!("windows_reparse_probe pinned=true before={before:?} after={after:?} exact_child_waited=true");
    assert_eq!(after, b"outside-only", "reopened path resolves to outside directory");
    if std::env::var_os("RHAI_WINDOWS_REPARSE_WRONG_EXPECTATION").is_some() {
        assert_ne!(after, b"outside-only", "REPARSE_WRONG_EXPECTATION");
    }
    drop(pin);
}
