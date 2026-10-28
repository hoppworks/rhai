//! Bounded capture of exact process handles from one owned Windows job.
//!
//! A snapshot alone cannot establish that every process ever assigned was captured.
//! The caller must separately prove capture completeness before accepting job closure.

use super::job::ManagedJob;
use std::collections::BTreeMap;
use std::io;
use std::os::windows::io::{AsRawHandle, FromRawHandle, OwnedHandle, RawHandle};
use std::ptr;
use windows_sys::Win32::Foundation::{
    DuplicateHandle, DUPLICATE_SAME_ACCESS, HANDLE, WAIT_FAILED, WAIT_OBJECT_0, WAIT_TIMEOUT,
};
use windows_sys::Win32::System::JobObjects::{
    IsProcessInJob, JobObjectBasicProcessIdList, QueryInformationJobObject,
};
use windows_sys::Win32::System::Threading::{
    GetCurrentProcess, OpenProcess, WaitForSingleObject, PROCESS_QUERY_LIMITED_INFORMATION,
    PROCESS_SYNCHRONIZE,
};

const MAX_CAPTURED_MEMBERS: usize = 256;

#[repr(C)]
struct ProcessList {
    assigned: u32,
    listed: u32,
    ids: [usize; MAX_CAPTURED_MEMBERS],
}

/// Handles are never replaced based on a fresh PID lookup; holding each handle
/// prevents identity reuse while this capture remains live.
#[derive(Default)]
pub(super) struct CapturedMembers {
    handles: BTreeMap<u32, OwnedHandle>,
}

impl CapturedMembers {
    /// Record the exact primary process before its suspended thread is resumed.
    pub(super) fn seed_root(&mut self, pid: u32, handle: HANDLE) -> io::Result<()> {
        if pid == 0 || handle.is_null() || !self.handles.is_empty() {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "invalid managed root handle",
            ));
        }
        let current = unsafe { GetCurrentProcess() };
        let mut duplicate = ptr::null_mut();
        // SAFETY: the primary process handle is owned by the suspended launch;
        // the successful duplicate is separately owned by this capture.
        if unsafe {
            DuplicateHandle(
                current,
                handle,
                current,
                &mut duplicate,
                0,
                0,
                DUPLICATE_SAME_ACCESS,
            )
        } == 0
        {
            return Err(io::Error::last_os_error());
        }
        self.handles
            .insert(pid, unsafe { OwnedHandle::from_raw_handle(duplicate as RawHandle) });
        Ok(())
    }

    /// Resolve a bounded membership snapshot to handles that are still in this job.
    /// An identity can change between the snapshot and `OpenProcess`; a successful
    /// call does not bind a handle retroactively to that earlier PID observation.
    /// Already captured handles remain owned by `self` on an error.
    pub(super) fn capture(&mut self, job: &ManagedJob) -> io::Result<()> {
        let mut list = ProcessList {
            assigned: 0,
            listed: 0,
            ids: [0; MAX_CAPTURED_MEMBERS],
        };
        // SAFETY: job is owned; list has correct C layout, alignment and writable size.
        if unsafe {
            QueryInformationJobObject(
                job.handle(),
                JobObjectBasicProcessIdList,
                &mut list as *mut _ as *mut _,
                std::mem::size_of_val(&list) as u32,
                ptr::null_mut(),
            )
        } == 0
        {
            return Err(io::Error::last_os_error());
        }
        if list.assigned != list.listed || list.listed as usize > MAX_CAPTURED_MEMBERS {
            return Err(io::Error::new(
                io::ErrorKind::Other,
                "incomplete managed job membership list",
            ));
        }
        for raw_pid in list.ids[..list.listed as usize].iter().copied() {
            let pid = u32::try_from(raw_pid).map_err(|_| {
                io::Error::new(io::ErrorKind::InvalidData, "invalid managed process id")
            })?;
            if pid == 0 {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidData,
                    "zero managed process id",
                ));
            }
            if self.handles.contains_key(&pid) {
                continue;
            }
            if self.handles.len() >= MAX_CAPTURED_MEMBERS {
                return Err(io::Error::new(
                    io::ErrorKind::Other,
                    "managed process handle capacity reached",
                ));
            }
            // SAFETY: the PID came from this owned job's bounded snapshot; no process is signaled.
            let raw = unsafe {
                OpenProcess(
                    PROCESS_SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION,
                    0,
                    pid,
                )
            };
            if raw.is_null() {
                return Err(io::Error::last_os_error());
            }
            // SAFETY: OpenProcess returned a fresh owned process handle.
            let handle = unsafe { OwnedHandle::from_raw_handle(raw as RawHandle) };
            let mut member = 0;
            // SAFETY: handle and job are live and member points to writable storage.
            if unsafe {
                IsProcessInJob(handle.as_raw_handle() as HANDLE, job.handle(), &mut member)
            } == 0
            {
                return Err(io::Error::last_os_error());
            }
            if member == 0 {
                return Err(io::Error::new(
                    io::ErrorKind::Other,
                    "captured process is no longer a member of its job",
                ));
            }
            self.handles.insert(pid, handle);
        }
        Ok(())
    }

    pub(super) fn len(&self) -> usize {
        self.handles.len()
    }

    /// A false result means at least one exact captured handle has not signaled.
    /// True for an empty or incomplete capture does not establish job closure.
    pub(super) fn all_signaled(&self) -> io::Result<bool> {
        let mut all = true;
        for handle in self.handles.values() {
            // SAFETY: each process handle remains owned for the nonblocking observation.
            match unsafe { WaitForSingleObject(handle.as_raw_handle() as HANDLE, 0) } {
                WAIT_OBJECT_0 => {}
                WAIT_TIMEOUT => all = false,
                WAIT_FAILED => return Err(io::Error::last_os_error()),
                other => {
                    return Err(io::Error::new(
                        io::ErrorKind::Other,
                        format!("unexpected process wait result {other:#x}"),
                    ))
                }
            }
        }
        Ok(all)
    }

    /// Candidate closure check for a private job after new assignments are barred.
    /// An unobserved association fails closed, including short-lived processes.
    /// Native race/fault proof is required before this can establish acceptance.
    pub(super) fn candidate_closed(&self, job: &ManagedJob) -> io::Result<bool> {
        let (active, total) = job.process_counts()?;
        if active != 0 {
            return Ok(false);
        }
        if total as usize != self.handles.len() {
            return Err(io::Error::new(
                io::ErrorKind::Other,
                "managed job lifetime membership was not completely captured",
            ));
        }
        if !self.all_signaled()? {
            return Ok(false);
        }
        let (active_after, total_after) = job.process_counts()?;
        if total_after != total {
            return Err(io::Error::new(
                io::ErrorKind::Other,
                "managed job membership changed during closure observation",
            ));
        }
        Ok(active_after == 0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;
    use std::process::{Child, Command, Stdio};
    use std::sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    };
    use std::thread;
    use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
    use windows_sys::Win32::System::JobObjects::{
        AssignProcessToJobObject, JobObjectExtendedLimitInformation, SetInformationJobObject,
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION, JOB_OBJECT_LIMIT_JOB_TIME,
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    };

    const RECORD_ENV: &str = "RHAI_WINDOWS_MEMBER_CAPTURE_RECORD";

    /// This owned fixture performs no descendant work before the parent assigns its job.
    #[test]
    fn capture_fixture() {
        let Ok(record) = std::env::var(RECORD_ENV) else {
            return;
        };
        let record = std::path::Path::new(&record);
        std::fs::write(record, format!("{}\n", std::process::id())).unwrap();
        let deadline = Instant::now() + Duration::from_secs(20);
        while Instant::now() < deadline {
            if record.with_extension("release").exists() {
                std::process::exit(0);
            }
            thread::sleep(Duration::from_millis(10));
        }
        panic!("member capture fixture timed out");
    }

    struct Fixture {
        child: Option<Child>,
        job: Option<ManagedJob>,
        root: PathBuf,
        record: PathBuf,
        retain_root: Arc<AtomicBool>,
    }
    impl Fixture {
        fn new() -> Self {
            let nonce = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos();
            let root = std::env::temp_dir()
                .join(format!("rhai-job-capture-{}-{nonce}", std::process::id()));
            std::fs::create_dir(&root).unwrap();
            let record = root.join("child.pid");
            let job = ManagedJob::new().expect("create private job");
            let child = Command::new(std::env::current_exe().unwrap())
                .args([
                    "--exact",
                    "packages::sys::process::windows::members::tests::capture_fixture",
                    "--nocapture",
                    "--quiet",
                ])
                .env_clear()
                .env(RECORD_ENV, &record)
                .stdin(Stdio::null())
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .expect("start gated capture fixture");
            let fixture = Self {
                child: Some(child),
                job: Some(job),
                root,
                record,
                retain_root: Arc::new(AtomicBool::new(false)),
            };
            // SAFETY: both exact handles are owned by fixture throughout the assignment.
            assert_ne!(
                unsafe {
                    AssignProcessToJobObject(
                        fixture.job().handle(),
                        fixture.child().as_raw_handle() as HANDLE,
                    )
                },
                0,
                "assign gated fixture to private job: {}",
                io::Error::last_os_error()
            );
            let deadline = Instant::now() + Duration::from_secs(5);
            loop {
                match std::fs::read_to_string(&fixture.record) {
                    Ok(value) => {
                        assert_eq!(value.trim().parse::<u32>().unwrap(), fixture.child().id());
                        break;
                    }
                    Err(error)
                        if error.kind() == io::ErrorKind::NotFound && Instant::now() < deadline =>
                    {
                        thread::sleep(Duration::from_millis(10))
                    }
                    Err(error) => panic!("capture fixture readiness: {error}"),
                }
            }
            fixture
        }
        fn child(&self) -> &Child {
            self.child.as_ref().unwrap()
        }
        fn job(&self) -> &ManagedJob {
            self.job.as_ref().unwrap()
        }
        fn wait(&mut self) {
            // SAFETY: fixture holds the exact child handle during this bounded wait.
            assert_eq!(
                unsafe { WaitForSingleObject(self.child().as_raw_handle() as HANDLE, 10_000) },
                WAIT_OBJECT_0
            );
            self.child
                .as_mut()
                .unwrap()
                .wait()
                .expect("observe direct child exit");
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            let Some(mut child) = self.child.take() else {
                return;
            };
            if self.retain_root.load(Ordering::Acquire) {
                if let Some(job) = self.job.as_ref() {
                    let _ = job.terminate();
                }
            }
            // SAFETY: child remains owned during both exact-handle observations.
            if unsafe { WaitForSingleObject(child.as_raw_handle() as HANDLE, 0) } != WAIT_OBJECT_0 {
                if let Some(job) = self.job.as_ref() {
                    let _ = job.terminate();
                }
                let _ = child.kill();
            }
            if unsafe { WaitForSingleObject(child.as_raw_handle() as HANDLE, 10_000) }
                != WAIT_OBJECT_0
            {
                eprintln!(
                    "capture fixture exit unconfirmed; retain handles and files for outer job"
                );
                std::mem::forget(child);
                if let Some(job) = self.job.take() {
                    std::mem::forget(job);
                }
                return;
            }
            let _ = child.wait();
            if self.retain_root.load(Ordering::Acquire) {
                if let Some(job) = self.job.take() {
                    std::mem::forget(job);
                }
                return;
            }
            let _ = std::fs::remove_dir_all(&self.root);
        }
    }

    #[test]
    fn captured_process_handle_requires_real_exit_before_candidate_closure() {
        let mut fixture = Fixture::new();
        let mut members = CapturedMembers::default();
        members
            .capture(fixture.job())
            .expect("capture owned fixture");
        assert_eq!(members.len(), 1);
        assert!(!members.all_signaled().unwrap());
        assert!(!members.candidate_closed(fixture.job()).unwrap());
        fixture
            .job()
            .terminate()
            .expect("terminate exact fixture job");
        fixture.wait();
        let deadline = Instant::now() + Duration::from_secs(5);
        let closed = loop {
            match members.candidate_closed(fixture.job()) {
                Ok(true) => break true,
                Ok(false) if Instant::now() < deadline => thread::sleep(Duration::from_millis(10)),
                other => panic!("captured fixture closure: {other:?}"),
            }
        };
        assert!(members.all_signaled().unwrap());
        eprintln!("windows_member_capture_readback captured=1 exact_handle_signaled=true");
        drop(members);
        drop(fixture);
        if std::env::var_os("RHAI_WINDOWS_MEMBER_CAPTURE_WRONG_EXPECTATION").is_some() {
            assert!(
                !closed,
                "deliberately wrong captured member closure expectation"
            );
        }
    }

    #[test]
    fn unobserved_lifetime_member_cannot_certify_candidate_closure() {
        let mut fixture = Fixture::new();
        std::fs::write(fixture.record.with_extension("release"), b"release\n").unwrap();
        fixture.wait();
        let members = CapturedMembers::default();
        let result = members.candidate_closed(fixture.job());
        assert!(
            result.is_err(),
            "an uncaptured association must remain unverified"
        );
        eprintln!("windows_member_capture_missing_readback unverified=true");
        drop(members);
        drop(fixture);
        if std::env::var_os("RHAI_WINDOWS_MEMBER_MISSING_WRONG_EXPECTATION").is_some() {
            assert!(
                result.is_ok(),
                "deliberately wrong uncaptured member expectation"
            );
        }
    }

    /// This fixture is an experiment: a normal Rhai host cannot be assumed to
    /// support re-executing itself as a controllable helper.
    #[test]
    fn cpu_limit_helper_fixture() {
        let Ok(root) = std::env::var("RHAI_WINDOWS_CPU_LIMIT_FIXTURE") else {
            return;
        };
        let root = std::path::Path::new(&root);
        std::fs::write(
            root.join("helper-ready"),
            format!("{}\n", std::process::id()),
        )
        .unwrap();
        let deadline = Instant::now() + Duration::from_secs(20);
        while Instant::now() < deadline {
            if root.join("helper-burn").exists() {
                while Instant::now() < deadline {
                    std::hint::spin_loop();
                }
                panic!("job CPU limit did not terminate the helper");
            }
            thread::sleep(Duration::from_millis(10));
        }
        panic!("job CPU limit helper was not triggered");
    }

    struct ExactFixtureChild {
        child: Option<Child>,
        retain_root: Arc<AtomicBool>,
    }

    impl ExactFixtureChild {
        fn child(&self) -> &Child {
            self.child.as_ref().expect("exact helper child")
        }
    }

    impl Drop for ExactFixtureChild {
        fn drop(&mut self) {
            let Some(mut child) = self.child.take() else {
                return;
            };
            // SAFETY: this guard retains the exact child handle for both observations.
            if unsafe { WaitForSingleObject(child.as_raw_handle() as HANDLE, 0) } != WAIT_OBJECT_0 {
                let _ = child.kill();
            }
            // SAFETY: the handle remains owned until the bounded observation completes.
            if unsafe { WaitForSingleObject(child.as_raw_handle() as HANDLE, 10_000) }
                == WAIT_OBJECT_0
            {
                let _ = child.wait();
            } else {
                eprintln!("CPU limit helper exit unconfirmed; outer job retains custody");
                self.retain_root.store(true, Ordering::Release);
                std::mem::forget(child);
            }
        }
    }

    /// A signaled job after its CPU limit is a different Windows mechanism from
    /// accounting reaching zero. This only tests held fixture handles and is not
    /// a general proof about processes that exited before the limit was set.
    #[test]
    fn job_cpu_limit_signal_is_observed_with_held_fixture_handles() {
        let mut fixture = Fixture::new();
        let helper = Command::new(std::env::current_exe().unwrap())
            .args([
                "--exact",
                "packages::sys::process::windows::members::tests::cpu_limit_helper_fixture",
                "--nocapture",
                "--quiet",
            ])
            .env_clear()
            .env("RHAI_WINDOWS_CPU_LIMIT_FIXTURE", &fixture.root)
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("start gated CPU limit helper");
        let mut helper = ExactFixtureChild {
            child: Some(helper),
            retain_root: Arc::clone(&fixture.retain_root),
        };
        // SAFETY: the helper is gated and both exact handles remain owned.
        assert_ne!(
            unsafe {
                AssignProcessToJobObject(
                    fixture.job().handle(),
                    helper.child().as_raw_handle() as HANDLE,
                )
            },
            0,
            "assign gated helper to private job: {}",
            io::Error::last_os_error()
        );
        let deadline = Instant::now() + Duration::from_secs(5);
        loop {
            match std::fs::read_to_string(fixture.root.join("helper-ready")) {
                Ok(value) => {
                    assert_eq!(value.trim().parse::<u32>().unwrap(), helper.child().id());
                    break;
                }
                Err(error)
                    if error.kind() == io::ErrorKind::NotFound && Instant::now() < deadline =>
                {
                    thread::sleep(Duration::from_millis(10));
                }
                Err(error) => panic!("CPU limit helper readiness: {error}"),
            }
        }
        assert_eq!(
            unsafe { WaitForSingleObject(fixture.child().as_raw_handle() as HANDLE, 0) },
            WAIT_TIMEOUT
        );
        assert_eq!(
            unsafe { WaitForSingleObject(helper.child().as_raw_handle() as HANDLE, 0) },
            WAIT_TIMEOUT
        );
        let mut limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION::default();
        limits.BasicLimitInformation.LimitFlags =
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_JOB_TIME;
        limits.BasicLimitInformation.PerJobUserTimeLimit = 1;
        // SAFETY: this private job and correctly sized limit structure remain live.
        assert_ne!(
            unsafe {
                SetInformationJobObject(
                    fixture.job().handle(),
                    JobObjectExtendedLimitInformation,
                    &limits as *const _ as *const _,
                    std::mem::size_of_val(&limits) as u32,
                )
            },
            0,
            "set private job CPU limit: {}",
            io::Error::last_os_error()
        );
        std::fs::write(fixture.root.join("helper-burn"), b"burn\n").unwrap();
        // SAFETY: fixture owns the job and exact process handles throughout these bounded waits.
        let job_wait = unsafe { WaitForSingleObject(fixture.job().handle(), 10_000) };
        let child_wait =
            unsafe { WaitForSingleObject(fixture.child().as_raw_handle() as HANDLE, 0) };
        let helper_wait =
            unsafe { WaitForSingleObject(helper.child().as_raw_handle() as HANDLE, 0) };
        eprintln!("windows_job_cpu_signal_readback job={job_wait:#x} child={child_wait:#x} helper={helper_wait:#x}");
        assert_eq!(
            job_wait, WAIT_OBJECT_0,
            "CPU-limited private job did not signal"
        );
        assert_eq!(
            child_wait, WAIT_OBJECT_0,
            "job signal preceded exact fixture exit"
        );
        assert_eq!(
            helper_wait, WAIT_OBJECT_0,
            "job signal preceded exact helper exit"
        );
        fixture.wait();
        helper
            .child
            .as_mut()
            .unwrap()
            .wait()
            .expect("reap CPU limit helper");
        drop(helper);
        drop(fixture);
        if std::env::var_os("RHAI_WINDOWS_CPU_LIMIT_WRONG_EXPECTATION").is_some() {
            assert_ne!(
                job_wait, WAIT_OBJECT_0,
                "deliberately wrong job CPU signal expectation"
            );
        }
    }
}
