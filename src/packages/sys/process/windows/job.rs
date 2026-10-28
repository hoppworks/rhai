//! Exact owned Windows Job handle for managed process lifetimes.

use std::io;
use std::os::windows::io::{AsRawHandle, FromRawHandle, OwnedHandle, RawHandle};
use std::ptr;
use windows_sys::Win32::Foundation::HANDLE;
use windows_sys::Win32::System::JobObjects::{
    CreateJobObjectW, JobObjectBasicAccountingInformation, JobObjectExtendedLimitInformation,
    QueryInformationJobObject, SetInformationJobObject, TerminateJobObject,
    JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
};

/// Owns one private, non-inheritable job. Closing the final handle requests termination;
/// successful termination must still be established independently with `active_processes`.
pub(super) struct ManagedJob(OwnedHandle);

impl ManagedJob {
    #[cfg(feature = "testing-environ")]
    pub(super) fn diagnostic_members(&self) -> String {
        use windows_sys::Win32::System::JobObjects::JobObjectBasicProcessIdList;
        #[repr(C)]
        struct ProcessList {
            assigned: u32,
            listed: u32,
            ids: [usize; 32],
        }
        let mut list = ProcessList {
            assigned: 0,
            listed: 0,
            ids: [0; 32],
        };
        // SAFETY: the owned job and aligned, writable bounded list remain live.
        let ok = unsafe {
            QueryInformationJobObject(
                self.handle(),
                JobObjectBasicProcessIdList,
                &mut list as *mut _ as *mut _,
                std::mem::size_of_val(&list) as u32,
                ptr::null_mut(),
            )
        };
        if ok == 0 {
            format!(
                "query_failed={} assigned={} listed={}",
                io::Error::last_os_error(),
                list.assigned,
                list.listed
            )
        } else if list.listed <= list.ids.len() as u32 {
            format!(
                "complete={} assigned={} listed={} ids={:?}",
                list.assigned == list.listed,
                list.assigned,
                list.listed,
                &list.ids[..list.listed as usize]
            )
        } else {
            format!(
                "inconsistent_counts assigned={} listed={}",
                list.assigned, list.listed
            )
        }
    }
    pub(super) fn new() -> io::Result<Self> {
        // SAFETY: null attributes and name request a private unnamed non-inheritable job.
        let raw = unsafe { CreateJobObjectW(ptr::null(), ptr::null()) };
        if raw.is_null() {
            return Err(io::Error::last_os_error());
        }
        // SAFETY: CreateJobObjectW returned a fresh owned handle.
        let job = Self(unsafe { OwnedHandle::from_raw_handle(raw as RawHandle) });
        let mut limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION::default();
        limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        // SAFETY: the exact job and correctly sized limit structure remain live for the call.
        if unsafe {
            SetInformationJobObject(
                job.handle(),
                JobObjectExtendedLimitInformation,
                &limits as *const _ as *const _,
                std::mem::size_of_val(&limits) as u32,
            )
        } == 0
        {
            return Err(io::Error::last_os_error());
        }
        Ok(job)
    }
    pub(super) fn handle(&self) -> HANDLE {
        self.0.as_raw_handle() as HANDLE
    }
    pub(super) fn terminate(&self) -> io::Result<()> {
        // SAFETY: this is the exact owned Job handle.
        if unsafe { TerminateJobObject(self.handle(), 1) } != 0 {
            Ok(())
        } else {
            Err(io::Error::last_os_error())
        }
    }
    pub(super) fn active_processes(&self) -> io::Result<u32> {
        self.process_counts().map(|(active, _)| active)
    }

    /// Return instantaneous active and cumulative associated-process counts.
    pub(super) fn process_counts(&self) -> io::Result<(u32, u32)> {
        let mut accounting = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION::default();
        // SAFETY: the exact job and writable, correctly sized accounting object are live.
        if unsafe {
            QueryInformationJobObject(
                self.handle(),
                JobObjectBasicAccountingInformation,
                &mut accounting as *mut _ as *mut _,
                std::mem::size_of_val(&accounting) as u32,
                ptr::null_mut(),
            )
        } == 0
        {
            return Err(io::Error::last_os_error());
        }
        Ok((accounting.ActiveProcesses, accounting.TotalProcesses))
    }
}
