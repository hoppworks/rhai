//! Exact process-handle operations shared by direct and managed Windows children.

use std::io;
use std::os::windows::io::{AsRawHandle, OwnedHandle, RawHandle};
use std::os::windows::process::ExitStatusExt;
use std::process::{Child, ExitStatus};
use windows_sys::Win32::Foundation::{HANDLE, WAIT_FAILED, WAIT_OBJECT_0, WAIT_TIMEOUT};
use windows_sys::Win32::System::Threading::{
    GetExitCodeProcess, TerminateProcess, WaitForSingleObject,
};

pub(super) enum OwnedChild {
    Direct(Child),
    // Managed creation will transfer the exact process handle before it is resumed.
    #[allow(dead_code)]
    Native {
        process: OwnedHandle,
        pid: u32,
        exit: Option<ExitStatus>,
    },
}

impl From<Child> for OwnedChild {
    fn from(child: Child) -> Self {
        Self::Direct(child)
    }
}

impl AsRawHandle for OwnedChild {
    fn as_raw_handle(&self) -> RawHandle {
        match self {
            Self::Direct(child) => child.as_raw_handle(),
            Self::Native { process, .. } => process.as_raw_handle(),
        }
    }
}

impl OwnedChild {
    pub(super) fn id(&self) -> u32 {
        match self {
            Self::Direct(child) => child.id(),
            Self::Native { pid, .. } => *pid,
        }
    }
    pub(super) fn try_wait(&mut self) -> io::Result<Option<ExitStatus>> {
        match self {
            Self::Direct(child) => child.try_wait(),
            Self::Native { process, exit, .. } => {
                if let Some(status) = exit {
                    return Ok(Some(*status));
                }
                // SAFETY: process remains exclusively owned throughout this observation.
                match unsafe { WaitForSingleObject(process.as_raw_handle() as HANDLE, 0) } {
                    WAIT_TIMEOUT => Ok(None),
                    WAIT_OBJECT_0 => {
                        let mut code = 0;
                        // SAFETY: process is a live owned process handle and code is writable.
                        if unsafe {
                            GetExitCodeProcess(process.as_raw_handle() as HANDLE, &mut code)
                        } == 0
                        {
                            return Err(io::Error::last_os_error());
                        }
                        let status = ExitStatus::from_raw(code);
                        *exit = Some(status);
                        Ok(Some(status))
                    }
                    WAIT_FAILED => Err(io::Error::last_os_error()),
                    other => Err(io::Error::new(
                        io::ErrorKind::Other,
                        format!("unexpected process wait result {other:#x}"),
                    )),
                }
            }
        }
    }
    pub(super) fn wait(&mut self) -> io::Result<ExitStatus> {
        if let Self::Direct(child) = self {
            return child.wait();
        }
        // SAFETY: this owner retains the exact process handle during the wait.
        match unsafe { WaitForSingleObject(self.as_raw_handle() as HANDLE, u32::MAX) } {
            WAIT_OBJECT_0 => self.try_wait()?.ok_or_else(|| {
                io::Error::new(
                    io::ErrorKind::Other,
                    "signaled process did not yield an exit status",
                )
            }),
            WAIT_FAILED => Err(io::Error::last_os_error()),
            other => Err(io::Error::new(
                io::ErrorKind::Other,
                format!("unexpected process wait result {other:#x}"),
            )),
        }
    }
    pub(super) fn kill(&mut self) -> io::Result<()> {
        match self {
            Self::Direct(child) => child.kill(),
            Self::Native { process, .. } => {
                // SAFETY: this is the exact process handle owned by this execution.
                if unsafe { TerminateProcess(process.as_raw_handle() as HANDLE, 1) } != 0 {
                    Ok(())
                } else {
                    Err(io::Error::last_os_error())
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;
    use std::process::{Command, Stdio};
    use std::thread;
    use std::time::{Duration, Instant};

    const FIXTURE_ENV: &str = "RHAI_WINDOWS_NATIVE_CHILD_RECORD";
    const FIXTURE_CODE_ENV: &str = "RHAI_WINDOWS_NATIVE_CHILD_EXIT";

    #[test]
    fn native_handle_fixture() {
        let Ok(record) = std::env::var(FIXTURE_ENV) else {
            return;
        };
        let path = std::path::Path::new(&record);
        let temporary = path.with_extension("tmp");
        std::fs::write(&temporary, format!("{}\n", std::process::id())).unwrap();
        std::fs::rename(temporary, path).unwrap();
        let deadline = Instant::now() + Duration::from_secs(20);
        while Instant::now() < deadline {
            if path.with_extension("release").exists() {
                std::process::exit(std::env::var(FIXTURE_CODE_ENV).unwrap().parse().unwrap());
            }
            thread::sleep(Duration::from_millis(10));
        }
        panic!("native handle fixture was not released");
    }

    struct ExactGuard(Option<OwnedChild>);
    impl Drop for ExactGuard {
        fn drop(&mut self) {
            let Some(mut child) = self.0.take() else {
                return;
            };
            match child.try_wait() {
                Ok(Some(_)) => return,
                Ok(None) => {}
                Err(error) => eprintln!("exact native fixture poll failed: {error}"),
            }
            if let Err(error) = child.kill() {
                eprintln!("exact native fixture kill failed: {error}");
            }
            // SAFETY: the guard retains the exact handle while observing termination.
            if unsafe { WaitForSingleObject(child.as_raw_handle() as HANDLE, 10_000) }
                != WAIT_OBJECT_0
            {
                eprintln!("exact native fixture exit remains unconfirmed; retain handle for outer job cleanup");
                std::mem::forget(child);
            }
        }
    }

    fn start_fixture(code: u32) -> (ExactGuard, PathBuf, PathBuf) {
        let nonce = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root =
            std::env::temp_dir().join(format!("rhai-native-handle-{}-{nonce}", std::process::id()));
        std::fs::create_dir(&root).unwrap();
        let record = root.join("child.pid");
        let child = Command::new(std::env::current_exe().unwrap())
            .args([
                "--exact",
                "packages::sys::process::windows::native_child::tests::native_handle_fixture",
                "--nocapture",
                "--quiet",
            ])
            .env_clear()
            .env(FIXTURE_ENV, &record)
            .env(FIXTURE_CODE_ENV, code.to_string())
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("start exact native handle fixture");
        let pid = child.id();
        let process: OwnedHandle = child.into();
        let guard = ExactGuard(Some(OwnedChild::Native {
            process,
            pid,
            exit: None,
        }));
        let deadline = Instant::now() + Duration::from_secs(5);
        loop {
            match std::fs::read_to_string(&record) {
                Ok(value) => {
                    assert_eq!(value.trim().parse::<u32>().unwrap(), pid);
                    break;
                }
                Err(error)
                    if error.kind() == io::ErrorKind::NotFound && Instant::now() < deadline =>
                {
                    thread::sleep(Duration::from_millis(10))
                }
                Err(error) => panic!("native handle fixture readiness: {error}"),
            }
        }
        (guard, root, record)
    }

    #[test]
    fn native_owned_handle_preserves_signaled_exit_259() {
        let (mut guard, root, record) = start_fixture(259);
        let child = guard.0.as_mut().unwrap();
        assert!(child.try_wait().unwrap().is_none());
        std::fs::write(record.with_extension("release"), b"release\n").unwrap();
        // SAFETY: guard owns the exact handle throughout the bounded observation.
        assert_eq!(
            unsafe { WaitForSingleObject(child.as_raw_handle() as HANDLE, 10_000) },
            WAIT_OBJECT_0
        );
        assert_eq!(child.try_wait().unwrap().unwrap().code(), Some(259));
        let observed_exit = child.wait().unwrap().code();
        assert_eq!(observed_exit, Some(259));
        eprintln!("windows_native_handle_readback exit=259 signaled=true cached=true");
        drop(guard);
        std::fs::remove_dir_all(root).unwrap();
        if std::env::var_os("RHAI_WINDOWS_NATIVE_HANDLE_WRONG_EXIT").is_some() {
            assert_eq!(
                observed_exit,
                Some(0),
                "deliberately wrong native handle exit expectation"
            );
        }
    }

    #[test]
    fn native_owned_handle_kills_exact_live_child() {
        let (mut guard, root, _) = start_fixture(0);
        let child = guard.0.as_mut().unwrap();
        assert!(child.try_wait().unwrap().is_none());
        child.kill().unwrap();
        // SAFETY: guard owns the exact handle throughout the bounded observation.
        assert_eq!(
            unsafe { WaitForSingleObject(child.as_raw_handle() as HANDLE, 10_000) },
            WAIT_OBJECT_0
        );
        let success = child.wait().unwrap().success();
        assert!(!success);
        eprintln!("windows_native_handle_kill_readback exact_handle_signaled=true");
        drop(guard);
        std::fs::remove_dir_all(root).unwrap();
        if std::env::var_os("RHAI_WINDOWS_NATIVE_HANDLE_WRONG_KILL").is_some() {
            assert!(success, "deliberately wrong exact native kill expectation");
        }
    }
}
