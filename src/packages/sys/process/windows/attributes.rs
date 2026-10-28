//! Scoped process-creation attributes for atomic managed-job assignment.

use super::job::ManagedJob;
use std::io;
use std::mem::{size_of, size_of_val};
use std::ptr;
use windows_sys::Win32::Foundation::{ERROR_INSUFFICIENT_BUFFER, HANDLE};
use windows_sys::Win32::System::Threading::{
    DeleteProcThreadAttributeList, InitializeProcThreadAttributeList, UpdateProcThreadAttribute,
    LPPROC_THREAD_ATTRIBUTE_LIST, PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
    PROC_THREAD_ATTRIBUTE_JOB_LIST,
};

struct AttributeList {
    // `usize` provides pointer alignment for the opaque Windows allocation.
    storage: Vec<usize>,
}

impl AttributeList {
    fn new() -> io::Result<Self> {
        let mut bytes = 0;
        // SAFETY: this documented sizing call has a null list and a writable size.
        let result =
            unsafe { InitializeProcThreadAttributeList(ptr::null_mut(), 2, 0, &mut bytes) };
        if result != 0
            || io::Error::last_os_error().raw_os_error() != Some(ERROR_INSUFFICIENT_BUFFER as i32)
            || bytes == 0
        {
            return Err(io::Error::new(
                io::ErrorKind::Other,
                "unexpected Windows attribute-list sizing result",
            ));
        }
        let words = bytes.checked_add(size_of::<usize>() - 1).ok_or_else(|| {
            io::Error::new(io::ErrorKind::OutOfMemory, "attribute-list size overflow")
        })? / size_of::<usize>();
        let mut storage = vec![0usize; words];
        // SAFETY: storage is aligned and large enough; it remains allocated through Delete.
        if unsafe {
            InitializeProcThreadAttributeList(storage.as_mut_ptr().cast(), 2, 0, &mut bytes)
        } == 0
        {
            return Err(io::Error::last_os_error());
        }
        Ok(Self { storage })
    }

    fn pointer(&mut self) -> LPPROC_THREAD_ATTRIBUTE_LIST {
        self.storage.as_mut_ptr().cast()
    }

    fn add(&mut self, attribute: u32, value: &[HANDLE]) -> io::Result<()> {
        // SAFETY: list is initialized and value remains live until the caller deletes the list.
        if unsafe {
            UpdateProcThreadAttribute(
                self.pointer(),
                0,
                attribute as usize,
                value.as_ptr().cast(),
                size_of_val(value),
                ptr::null_mut(),
                ptr::null(),
            )
        } == 0
        {
            return Err(io::Error::last_os_error());
        }
        Ok(())
    }
}

impl Drop for AttributeList {
    fn drop(&mut self) {
        // SAFETY: only successfully initialized lists reach this destructor, exactly once.
        unsafe { DeleteProcThreadAttributeList(self.pointer()) };
    }
}

/// Calls `create` while the list and both referenced handle arrays are alive.
/// The caller must pass only inheritable handles intended for the child.
pub(super) fn with_managed_attributes<T>(
    job: &ManagedJob,
    inherited: &[HANDLE],
    create: impl FnOnce(LPPROC_THREAD_ATTRIBUTE_LIST) -> io::Result<T>,
) -> io::Result<T> {
    if inherited.is_empty() {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "managed process requires an explicit inherited-handle list",
        ));
    }
    let job_handles = [job.handle()];
    let mut list = AttributeList::new()?;
    list.add(PROC_THREAD_ATTRIBUTE_JOB_LIST, &job_handles)?;
    list.add(PROC_THREAD_ATTRIBUTE_HANDLE_LIST, inherited)?;
    create(list.pointer())
}
