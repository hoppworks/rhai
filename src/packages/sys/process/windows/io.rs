//! Parent-owned, overlapped Windows pipe reads.
//!
//! A pending `ReadFile` borrows both the boxed buffer and boxed `OVERLAPPED`. Neither may be
//! moved or freed until `GetOverlappedResult` has observed completion, including cancellation.

use std::io;
use std::os::windows::io::{AsRawHandle, FromRawHandle, OwnedHandle, RawHandle};
use std::ptr;
use windows_sys::Win32::Foundation::{
    ERROR_BROKEN_PIPE, ERROR_HANDLE_EOF, ERROR_IO_INCOMPLETE, ERROR_IO_PENDING, ERROR_NOT_FOUND,
    ERROR_NO_DATA, ERROR_OPERATION_ABORTED, ERROR_PIPE_CONNECTED, GENERIC_WRITE, HANDLE,
    INVALID_HANDLE_VALUE, WAIT_OBJECT_0, WAIT_TIMEOUT,
};
use windows_sys::Win32::Security::Cryptography::{
    BCryptGenRandom, BCRYPT_USE_SYSTEM_PREFERRED_RNG,
};
use windows_sys::Win32::Storage::FileSystem::{
    CreateFileW, ReadFile, FILE_ATTRIBUTE_NORMAL, FILE_FLAG_FIRST_PIPE_INSTANCE,
    FILE_FLAG_OVERLAPPED, OPEN_EXISTING, PIPE_ACCESS_INBOUND,
};
use windows_sys::Win32::System::Pipes::{
    ConnectNamedPipe, CreateNamedPipeW, PIPE_READMODE_BYTE, PIPE_REJECT_REMOTE_CLIENTS,
    PIPE_TYPE_BYTE, PIPE_WAIT,
};
use windows_sys::Win32::System::Threading::{CreateEventW, ResetEvent, WaitForSingleObject};
use windows_sys::Win32::System::IO::{CancelIoEx, GetOverlappedResult, OVERLAPPED};

const READ_CHUNK: usize = 8192;

/// An owned parent endpoint. The child endpoint is returned separately for `Stdio` transfer.
pub(super) struct PipeReader {
    server: OwnedHandle,
    event: OwnedHandle,
    operation: Box<OVERLAPPED>,
    buffer: Box<[u8; READ_CHUNK]>,
    pending: bool,
    eof: bool,
}

/// Outcome of one bounded cancellation attempt. Incomplete operations retain their
/// kernel-borrowed storage; completed reads may still have delivered bytes.
pub(super) struct CancelRead {
    pub completed: bool,
    pub bytes: Vec<u8>,
    pub errors: Vec<io::Error>,
}

// SAFETY: the kernel borrows only the boxed buffer and OVERLAPPED allocations, whose addresses
// remain stable when this owner moves. No Rust reference is shared across threads; the cleanup
// worker takes exclusive ownership and uses CancelIoEx, which may target another thread's I/O.
unsafe impl Send for PipeReader {}

impl PipeReader {
    pub(super) fn pair() -> io::Result<(Self, OwnedHandle)> {
        let mut nonce = [0u8; 16];
        // SAFETY: the system-preferred RNG accepts a null algorithm handle and this live buffer.
        let status = unsafe {
            BCryptGenRandom(
                ptr::null_mut(),
                nonce.as_mut_ptr(),
                nonce.len() as u32,
                BCRYPT_USE_SYSTEM_PREFERRED_RNG,
            )
        };
        if status != 0 {
            return Err(io::Error::new(
                io::ErrorKind::Other,
                format!("cannot allocate private pipe name: NTSTATUS {status:#x}"),
            ));
        }
        let mut name = String::from(r"\\.\pipe\rhai-sys-");
        for byte in nonce {
            use std::fmt::Write;
            write!(&mut name, "{byte:02x}").expect("writing to String cannot fail");
        }
        let wide: Vec<u16> = name.encode_utf16().chain(Some(0)).collect();
        // SAFETY: `wide` is NUL-terminated and remains live for the call. The OS owns the
        // returned handle until it is transferred to `OwnedHandle` below.
        let server_raw = unsafe {
            CreateNamedPipeW(
                wide.as_ptr(),
                PIPE_ACCESS_INBOUND | FILE_FLAG_OVERLAPPED | FILE_FLAG_FIRST_PIPE_INSTANCE,
                PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS,
                1,
                READ_CHUNK as u32,
                READ_CHUNK as u32,
                0,
                ptr::null(),
            )
        };
        let server = own_file_handle(server_raw)?;
        // Only this process knows the random pipe name. `Command` will create the inheritable
        // child-side duplicate when this owned endpoint becomes `Stdio`.
        // SAFETY: `wide` and `server` remain live across the client open.
        let client_raw = unsafe {
            CreateFileW(
                wide.as_ptr(),
                GENERIC_WRITE,
                0,
                ptr::null(),
                OPEN_EXISTING,
                FILE_ATTRIBUTE_NORMAL,
                ptr::null_mut(),
            )
        };
        let client = own_file_handle(client_raw)?;
        // SAFETY: the unnamed event has no borrowed security data and is owned on success.
        let event_raw = unsafe { CreateEventW(ptr::null(), 1, 0, ptr::null()) };
        let event = own_null_handle(event_raw)?;
        let mut operation = Box::new(OVERLAPPED::default());
        operation.hEvent = handle(&event);
        // A client can connect between server creation and this call. That precise race is
        // reported as ERROR_PIPE_CONNECTED and means the endpoint is ready for I/O.
        // SAFETY: server, event and boxed OVERLAPPED remain live until the connection finishes.
        let connected = unsafe { ConnectNamedPipe(handle(&server), operation.as_mut()) };
        if connected == 0 {
            let error = io::Error::last_os_error();
            match error.raw_os_error().map(|n| n as u32) {
                Some(ERROR_PIPE_CONNECTED) => {}
                Some(ERROR_IO_PENDING) => {
                    let mut transferred = 0;
                    // SAFETY: this waits for the outstanding connection before reusing the
                    // OVERLAPPED storage or releasing the event.
                    if unsafe {
                        GetOverlappedResult(
                            handle(&server),
                            operation.as_ref(),
                            &mut transferred,
                            1,
                        )
                    } == 0
                    {
                        return Err(io::Error::last_os_error());
                    }
                }
                _ => return Err(error),
            }
        }
        Ok((
            Self {
                server,
                event,
                operation,
                buffer: Box::new([0; READ_CHUNK]),
                pending: false,
                eof: false,
            },
            client,
        ))
    }

    pub(super) fn event_handle(&self) -> HANDLE {
        handle(&self.event)
    }

    pub(super) fn is_pending(&self) -> bool {
        self.pending
    }

    pub(super) fn reached_eof(&self) -> bool {
        self.eof
    }

    /// Begin one bounded read. `None` means the operation is pending; `Some` is a completed
    /// read, including an empty vector for EOF. Call `finish_read` only after its event signals.
    pub(super) fn start_read(&mut self) -> io::Result<Option<Vec<u8>>> {
        if self.pending {
            return Err(io::Error::new(
                io::ErrorKind::Other,
                "pipe read already pending",
            ));
        }
        if self.eof {
            return Ok(Some(Vec::new()));
        }
        // SAFETY: the owned event and operation are not in use by another I/O request.
        if unsafe { ResetEvent(handle(&self.event)) } == 0 {
            return Err(io::Error::last_os_error());
        }
        let mut transferred = 0;
        // SAFETY: boxed buffer and operation remain at stable addresses through completion.
        let completed = unsafe {
            ReadFile(
                handle(&self.server),
                self.buffer.as_mut_ptr(),
                READ_CHUNK as u32,
                &mut transferred,
                self.operation.as_mut(),
            )
        };
        if completed != 0 {
            return Ok(Some(self.completed_bytes(transferred)));
        }
        let error = io::Error::last_os_error();
        match error.raw_os_error().map(|n| n as u32) {
            Some(ERROR_IO_PENDING) => {
                self.pending = true;
                Ok(None)
            }
            Some(ERROR_BROKEN_PIPE | ERROR_HANDLE_EOF | ERROR_NO_DATA) => {
                self.eof = true;
                Ok(Some(Vec::new()))
            }
            _ => Err(error),
        }
    }

    pub(super) fn finish_read(&mut self) -> io::Result<Vec<u8>> {
        if !self.pending {
            return Err(io::Error::new(io::ErrorKind::Other, "no pending pipe read"));
        }
        let mut transferred = 0;
        // SAFETY: the caller has observed the event, and storage remains stable until this
        // completion query returns.
        let completed = unsafe {
            GetOverlappedResult(
                handle(&self.server),
                self.operation.as_ref(),
                &mut transferred,
                0,
            )
        };
        if completed == 0 {
            let error = io::Error::last_os_error();
            if error.raw_os_error().map(|n| n as u32) == Some(ERROR_IO_INCOMPLETE) {
                return Err(error);
            }
            self.pending = false;
            return match error.raw_os_error().map(|n| n as u32) {
                Some(ERROR_BROKEN_PIPE | ERROR_HANDLE_EOF | ERROR_NO_DATA) => {
                    self.eof = true;
                    Ok(Vec::new())
                }
                _ => Err(error),
            };
        }
        self.pending = false;
        Ok(self.completed_bytes(transferred))
    }

    /// Observe completion without discarding bytes that won a race with cancellation.
    /// An incomplete outcome requires the caller to retain this entire owner and retry.
    pub(super) fn cancel_and_join_bounded(&mut self, wait_ms: u32) -> CancelRead {
        if !self.pending {
            return CancelRead {
                completed: true,
                bytes: Vec::new(),
                errors: Vec::new(),
            };
        }
        // SAFETY: operation belongs to this handle and remains live until the completion query.
        let cancelled = unsafe { CancelIoEx(handle(&self.server), self.operation.as_ref()) };
        let mut errors = Vec::new();
        if cancelled == 0 {
            let error = io::Error::last_os_error();
            if error.raw_os_error().map(|n| n as u32) != Some(ERROR_NOT_FOUND) {
                errors.push(error);
            }
        }
        // SAFETY: this owner keeps the event and operation live for the bounded wait.
        let wait = unsafe { WaitForSingleObject(handle(&self.event), wait_ms) };
        if wait == WAIT_TIMEOUT {
            return CancelRead {
                completed: false,
                bytes: Vec::new(),
                errors,
            };
        }
        if wait != WAIT_OBJECT_0 {
            errors.push(io::Error::last_os_error());
            return CancelRead {
                completed: false,
                bytes: Vec::new(),
                errors,
            };
        }
        let mut transferred = 0;
        // SAFETY: the event signaled and storage remains live for this completion query.
        let completed = unsafe {
            GetOverlappedResult(
                handle(&self.server),
                self.operation.as_ref(),
                &mut transferred,
                0,
            )
        };
        if completed == 0 {
            let error = io::Error::last_os_error();
            if error.raw_os_error().map(|n| n as u32) == Some(ERROR_IO_INCOMPLETE) {
                return CancelRead {
                    completed: false,
                    bytes: Vec::new(),
                    errors,
                };
            }
            self.pending = false;
            match error.raw_os_error().map(|n| n as u32) {
                Some(ERROR_BROKEN_PIPE | ERROR_HANDLE_EOF | ERROR_NO_DATA) => self.eof = true,
                Some(ERROR_OPERATION_ABORTED) => {}
                _ => errors.push(error),
            }
            return CancelRead {
                completed: true,
                bytes: Vec::new(),
                errors,
            };
        }
        self.pending = false;
        let bytes = self.completed_bytes(transferred);
        CancelRead {
            completed: true,
            bytes,
            errors,
        }
    }

    fn completed_bytes(&mut self, transferred: u32) -> Vec<u8> {
        if transferred == 0 {
            self.eof = true;
        }
        self.buffer[..transferred as usize].to_vec()
    }
}

impl Drop for PipeReader {
    fn drop(&mut self) {
        // Pending kernel I/O borrows `operation` and `buffer`. Never release them while pending,
        // including when a caller unwinds before its explicit cancellation path. Normal callers
        // use the bounded method and transfer unresolved ownership to the cleanup service.
        while self.pending {
            let _ = self.cancel_and_join_bounded(1_000);
        }
    }
}

fn handle(value: &OwnedHandle) -> HANDLE {
    value.as_raw_handle() as HANDLE
}

fn own_file_handle(raw: HANDLE) -> io::Result<OwnedHandle> {
    if raw == INVALID_HANDLE_VALUE {
        Err(io::Error::last_os_error())
    } else {
        // SAFETY: the successful Windows API call transferred one fresh handle to this owner.
        Ok(unsafe { OwnedHandle::from_raw_handle(raw as RawHandle) })
    }
}

fn own_null_handle(raw: HANDLE) -> io::Result<OwnedHandle> {
    if raw.is_null() {
        Err(io::Error::last_os_error())
    } else {
        // SAFETY: the successful Windows API call transferred one fresh handle to this owner.
        Ok(unsafe { OwnedHandle::from_raw_handle(raw as RawHandle) })
    }
}

#[cfg(test)]
mod tests {
    use super::PipeReader;
    use std::fs::File;
    use std::io::Write;
    use windows_sys::Win32::Foundation::WAIT_OBJECT_0;
    use windows_sys::Win32::System::Threading::WaitForSingleObject;

    #[test]
    fn overlapped_pipe_reads_child_side_bytes_and_eof() {
        let (mut reader, child_end) = PipeReader::pair().expect("create pipe pair");
        let mut child = File::from(child_end);
        child.write_all(&[0, 65, 255]).expect("write exact bytes");
        drop(child);

        let mut captured = Vec::new();
        while !reader.reached_eof() {
            let bytes = match reader.start_read().expect("start overlapped read") {
                Some(bytes) => bytes,
                None => {
                    // SAFETY: the reader owns this live event for the full bounded wait.
                    let wait = unsafe { WaitForSingleObject(reader.event_handle(), 2_000) };
                    assert_eq!(wait, WAIT_OBJECT_0, "pipe read did not complete");
                    reader.finish_read().expect("finish overlapped read")
                }
            };
            captured.extend(bytes);
        }
        assert_eq!(captured, [0, 65, 255]);
        assert!(!reader.is_pending());
    }

    #[test]
    fn held_child_pipe_can_cancel_pending_read_without_eof() {
        let (mut reader, _child_end) = PipeReader::pair().expect("create pipe pair");
        assert!(reader
            .start_read()
            .expect("start overlapped read")
            .is_none());
        assert!(reader.is_pending());
        let outcome = reader.cancel_and_join_bounded(2_000);
        assert!(outcome.completed, "cancellation did not complete");
        assert!(
            outcome.errors.is_empty(),
            "cancellation errors: {:?}",
            outcome.errors
        );
        assert!(outcome.bytes.is_empty());
        assert!(!reader.is_pending());
        assert!(!reader.reached_eof());
    }

    #[test]
    fn cancellation_observes_completed_bytes_without_discarding_them() {
        let (mut reader, child_end) = PipeReader::pair().expect("create pipe pair");
        assert!(reader.start_read().unwrap().is_none());
        let mut child = File::from(child_end);
        child.write_all(&[0, 65, 255]).unwrap();
        // SAFETY: the owned event remains live throughout this bounded wait.
        assert_eq!(
            unsafe { WaitForSingleObject(reader.event_handle(), 2_000) },
            WAIT_OBJECT_0
        );
        let outcome = reader.cancel_and_join_bounded(2_000);
        assert!(outcome.completed);
        assert!(
            outcome.errors.is_empty(),
            "cancellation errors: {:?}",
            outcome.errors
        );
        assert_eq!(outcome.bytes, [0, 65, 255]);
        assert!(!reader.is_pending());
        assert!(!reader.reached_eof());
    }

    #[test]
    fn cancellation_observes_pipe_closure_as_eof() {
        let (mut reader, child_end) = PipeReader::pair().expect("create pipe pair");
        assert!(reader.start_read().unwrap().is_none());
        drop(child_end);
        // SAFETY: the owned event remains live throughout this bounded wait.
        assert_eq!(
            unsafe { WaitForSingleObject(reader.event_handle(), 2_000) },
            WAIT_OBJECT_0
        );
        let outcome = reader.cancel_and_join_bounded(2_000);
        assert!(outcome.completed);
        assert!(
            outcome.errors.is_empty(),
            "EOF cancellation errors: {:?}",
            outcome.errors
        );
        assert!(outcome.bytes.is_empty());
        assert!(!reader.is_pending());
        assert!(reader.reached_eof());
    }
}
