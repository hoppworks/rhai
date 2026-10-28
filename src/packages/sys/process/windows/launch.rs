//! Suspended Windows launch with custody before the first user instruction.

use super::{attributes, job::ManagedJob, native_child::OwnedChild, retain_for_cleanup};
use super::{ActivePermit, PipeReader, PipeWriter, ProcessOwner};
use std::io;
use std::os::windows::ffi::OsStringExt;
use std::os::windows::io::{AsRawHandle, FromRawHandle, OwnedHandle, RawHandle};
use std::ptr;
use std::sync::Arc;
use windows_sys::Win32::Foundation::{DuplicateHandle, DUPLICATE_SAME_ACCESS, HANDLE};
use windows_sys::Win32::System::JobObjects::IsProcessInJob;
use windows_sys::Win32::System::Threading::{
    CreateProcessW, GetCurrentProcess, ResumeThread, CREATE_SUSPENDED, CREATE_UNICODE_ENVIRONMENT,
    EXTENDED_STARTUPINFO_PRESENT, PROCESS_INFORMATION, STARTF_USESTDHANDLES, STARTUPINFOEXW,
};

/// Holds both job and exact process ownership while the primary thread is suspended.
/// Dropping an incomplete launch transfers custody to the existing cleanup service.
pub(super) struct SuspendedOwner {
    owner: Option<ProcessOwner>,
    thread: OwnedHandle,
}

/// Transfer the child-side pipe endpoints into short-lived inheritable duplicates.
/// The original endpoints and partially-created duplicates close on every error path.
pub(super) fn child_stdio(
    stdin: Option<OwnedHandle>,
    stdout: OwnedHandle,
    stderr: OwnedHandle,
) -> io::Result<[OwnedHandle; 3]> {
    let input = match stdin {
        Some(input) => input,
        None => std::fs::OpenOptions::new()
            .read(true)
            .open(r"\\.\NUL")?
            .into(),
    };
    Ok([
        inheritable_duplicate(&input)?,
        inheritable_duplicate(&stdout)?,
        inheritable_duplicate(&stderr)?,
    ])
}

fn inheritable_duplicate(source: &OwnedHandle) -> io::Result<OwnedHandle> {
    // SAFETY: the current-process pseudo handle and source remain valid for the call.
    let current = unsafe { GetCurrentProcess() };
    let mut duplicate = ptr::null_mut();
    // SAFETY: source is an owned live handle; duplicate points to writable storage.
    if unsafe {
        DuplicateHandle(
            current,
            source.as_raw_handle() as HANDLE,
            current,
            &mut duplicate,
            0,
            1,
            DUPLICATE_SAME_ACCESS,
        )
    } == 0
    {
        return Err(io::Error::last_os_error());
    }
    // SAFETY: a successful DuplicateHandle returned a fresh owned handle.
    Ok(unsafe { OwnedHandle::from_raw_handle(duplicate as RawHandle) })
}

impl Drop for SuspendedOwner {
    fn drop(&mut self) {
        if let Some(owner) = self.owner.take() {
            let _ = retain_for_cleanup(owner);
        }
    }
}

impl SuspendedOwner {
    /// Verify exact job membership before executing any child instructions.
    pub(super) fn resume(mut self) -> io::Result<ProcessOwner> {
        let owner = self.owner.as_mut().expect("suspended owner present");
        let mut member = 0;
        // SAFETY: both exact handles are retained by owner and member is writable.
        if unsafe {
            IsProcessInJob(
                owner.child.as_raw_handle() as HANDLE,
                owner.job.as_ref().expect("managed job present").handle(),
                &mut member,
            )
        } == 0
        {
            return Err(io::Error::last_os_error());
        }
        if member == 0 {
            return Err(io::Error::new(
                io::ErrorKind::Other,
                "child is not in its managed job",
            ));
        }
        // Establish a lifetime handle before the first user instruction can
        // create and exit additional Job members.
        owner.seed_managed_root()?;
        // SAFETY: the exact owned primary thread was created suspended and is live.
        let previous = unsafe { ResumeThread(self.thread.as_raw_handle() as HANDLE) };
        if previous == u32::MAX {
            return Err(io::Error::last_os_error());
        }
        if previous != 1 {
            return Err(io::Error::new(
                io::ErrorKind::Other,
                format!("unexpected initial thread suspend count {previous}"),
            ));
        }
        Ok(self.owner.take().expect("suspended owner present"))
    }
}

/// `command_line` and an optional environment block are mutable/terminated Windows
/// representations produced by the caller. Handles are the three explicitly
/// inheritable child endpoints, in stdin, stdout, stderr order.
#[allow(clippy::too_many_arguments)]
pub(super) fn create_suspended(
    job: ManagedJob,
    handles: [OwnedHandle; 3],
    application: &[u16],
    command_line: &mut [u16],
    environment: Option<&[u16]>,
    stdin: Option<PipeWriter>,
    stdout: PipeReader,
    stderr: PipeReader,
    permit: ActivePermit,
) -> io::Result<SuspendedOwner> {
    if application.len() < 2
        || application.last() != Some(&0)
        || application[..application.len() - 1].contains(&0)
        || !std::path::Path::new(&std::ffi::OsString::from_wide(
            &application[..application.len() - 1],
        ))
        .is_absolute()
    {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "application must be a resolved absolute Windows path",
        ));
    }
    if command_line.last() != Some(&0) || command_line[..command_line.len() - 1].contains(&0) {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "invalid Windows command line",
        ));
    }
    if environment.is_some_and(|block| block.len() < 2 || block[block.len() - 2..] != [0, 0]) {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "invalid Windows environment block",
        ));
    }
    let inherited = handles
        .each_ref()
        .map(|handle| handle.as_raw_handle() as HANDLE);
    let job = Arc::new(job);
    let owner_job = Arc::clone(&job);
    attributes::with_managed_attributes(&job, &inherited, move |list| {
        let mut information = PROCESS_INFORMATION::default();
        let mut startup = STARTUPINFOEXW::default();
        startup.StartupInfo.cb = std::mem::size_of::<STARTUPINFOEXW>() as u32;
        startup.StartupInfo.dwFlags = STARTF_USESTDHANDLES;
        startup.StartupInfo.hStdInput = inherited[0];
        startup.StartupInfo.hStdOutput = inherited[1];
        startup.StartupInfo.hStdError = inherited[2];
        startup.lpAttributeList = list;
        let environment = environment.map_or(ptr::null(), |block| block.as_ptr().cast());
        // SAFETY: all buffers, inherited handles and the attribute list remain live for
        // the call; the job list assigns membership before the suspended child starts.
        if unsafe {
            CreateProcessW(
                application.as_ptr(),
                command_line.as_mut_ptr(),
                ptr::null(),
                ptr::null(),
                1,
                EXTENDED_STARTUPINFO_PRESENT | CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT,
                environment,
                ptr::null(),
                &startup.StartupInfo,
                &mut information,
            )
        } == 0
        {
            return Err(io::Error::last_os_error());
        }
        // SAFETY: successful CreateProcessW returns fresh owned process and thread handles.
        // Establish cleanup custody before attribute-list teardown or returning to the caller.
        let process = unsafe { OwnedHandle::from_raw_handle(information.hProcess as RawHandle) };
        let thread = unsafe { OwnedHandle::from_raw_handle(information.hThread as RawHandle) };
        let child = OwnedChild::Native {
            process,
            pid: information.dwProcessId,
            exit: None,
        };
        let owner =
            ProcessOwner::with_owned_child(child, Some(owner_job), stdin, stdout, stderr, permit);
        Ok(SuspendedOwner {
            owner: Some(owner),
            thread,
        })
    })
}
