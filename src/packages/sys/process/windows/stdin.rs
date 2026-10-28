//! Parent-owned, overlapped writes to a child's standard input.

use super::io::pipe_pair;
use std::io;
use std::os::windows::io::{AsRawHandle, OwnedHandle};
use windows_sys::Win32::Foundation::{
    ERROR_BROKEN_PIPE, ERROR_IO_INCOMPLETE, ERROR_IO_PENDING, ERROR_NOT_FOUND, ERROR_NO_DATA,
    ERROR_OPERATION_ABORTED, GENERIC_READ, HANDLE, WAIT_OBJECT_0, WAIT_TIMEOUT,
};
use windows_sys::Win32::Storage::FileSystem::{WriteFile, PIPE_ACCESS_OUTBOUND};
use windows_sys::Win32::System::Threading::{ResetEvent, WaitForSingleObject};
use windows_sys::Win32::System::IO::{CancelIoEx, GetOverlappedResult, OVERLAPPED};

const WRITE_CHUNK: usize = 8192;

pub(super) struct PipeWriter {
    server: Option<OwnedHandle>,
    event: OwnedHandle,
    operation: Box<OVERLAPPED>,
    input: Vec<u8>,
    offset: usize,
    requested: usize,
    pending: bool,
}

pub(super) struct CancelWrite {
    pub completed: bool,
    pub errors: Vec<io::Error>,
}

// SAFETY: the input allocation and boxed OVERLAPPED stay stable until completion is observed.
// The owner moves exclusively to the cleanup worker; no Rust reference is shared concurrently.
unsafe impl Send for PipeWriter {}

impl PipeWriter {
    pub(super) fn pair(input: Vec<u8>) -> io::Result<(Self, OwnedHandle)> {
        let (server, client, event, operation) = pipe_pair(PIPE_ACCESS_OUTBOUND, GENERIC_READ)?;
        Ok((
            Self {
                server: Some(server),
                event,
                operation,
                input,
                offset: 0,
                requested: 0,
                pending: false,
            },
            client,
        ))
    }

    pub(super) fn is_pending(&self) -> bool {
        self.pending
    }
    pub(super) fn is_finished(&self) -> bool {
        self.server.is_none()
    }
    pub(super) fn event_handle(&self) -> HANDLE {
        self.event.as_raw_handle() as HANDLE
    }

    /// Submit at most one bounded write. The backing input must not move until completion.
    pub(super) fn start_write(&mut self) -> io::Result<()> {
        if self.pending {
            return Err(io::Error::new(
                io::ErrorKind::Other,
                "stdin write already pending",
            ));
        }
        let Some(server) = self.server.as_ref() else {
            return Ok(());
        };
        if self.offset == self.input.len() {
            self.server.take();
            return Ok(());
        }
        // SAFETY: this event and OVERLAPPED are owned and have no outstanding operation.
        if unsafe { ResetEvent(self.event_handle()) } == 0 {
            return Err(io::Error::last_os_error());
        }
        self.requested = (self.input.len() - self.offset).min(WRITE_CHUNK);
        let mut transferred = 0;
        // SAFETY: input allocation and OVERLAPPED remain live and stable while pending.
        let result = unsafe {
            WriteFile(
                server.as_raw_handle() as HANDLE,
                self.input.as_ptr().add(self.offset),
                self.requested as u32,
                &mut transferred,
                self.operation.as_mut(),
            )
        };
        if result != 0 {
            return self.advance(transferred);
        }
        let error = io::Error::last_os_error();
        if error.raw_os_error().map(|n| n as u32) == Some(ERROR_IO_PENDING) {
            self.pending = true;
            Ok(())
        } else {
            self.server.take();
            Err(error)
        }
    }

    pub(super) fn finish_write(&mut self) -> io::Result<()> {
        if !self.pending {
            return Err(io::Error::new(
                io::ErrorKind::Other,
                "no pending stdin write",
            ));
        }
        let mut transferred = 0;
        // SAFETY: the event was observed and the server, input and OVERLAPPED remain owned.
        let result = unsafe {
            GetOverlappedResult(
                self.server.as_ref().unwrap().as_raw_handle() as HANDLE,
                self.operation.as_ref(),
                &mut transferred,
                0,
            )
        };
        if result == 0 {
            let error = io::Error::last_os_error();
            if error.raw_os_error().map(|n| n as u32) != Some(ERROR_IO_INCOMPLETE) {
                self.pending = false;
                self.server.take();
            }
            return Err(error);
        }
        self.pending = false;
        self.advance(transferred)
    }

    fn advance(&mut self, transferred: u32) -> io::Result<()> {
        let transferred = transferred as usize;
        if transferred == 0 || transferred > self.requested {
            self.server.take();
            return Err(io::Error::new(
                if transferred == 0 {
                    io::ErrorKind::WriteZero
                } else {
                    io::ErrorKind::InvalidData
                },
                "invalid stdin write completion",
            ));
        }
        self.offset += transferred;
        if self.offset == self.input.len() {
            self.server.take();
        }
        Ok(())
    }

    /// Stop input and keep all borrowed storage alive until cancellation is observed.
    pub(super) fn cancel_and_join_bounded(&mut self, wait_ms: u32) -> CancelWrite {
        if !self.pending {
            self.server.take();
            return CancelWrite {
                completed: true,
                errors: Vec::new(),
            };
        }
        let server = self
            .server
            .as_ref()
            .expect("pending stdin has a server")
            .as_raw_handle() as HANDLE;
        let mut errors = Vec::new();
        // SAFETY: this exact operation belongs to the still-owned server handle.
        if unsafe { CancelIoEx(server, self.operation.as_ref()) } == 0 {
            let error = io::Error::last_os_error();
            if error.raw_os_error().map(|n| n as u32) != Some(ERROR_NOT_FOUND) {
                errors.push(error);
            }
        }
        // SAFETY: the event and operation stay alive throughout the bounded wait.
        let wait = unsafe { WaitForSingleObject(self.event_handle(), wait_ms) };
        if wait == WAIT_TIMEOUT {
            return CancelWrite {
                completed: false,
                errors,
            };
        }
        if wait != WAIT_OBJECT_0 {
            errors.push(io::Error::last_os_error());
            return CancelWrite {
                completed: false,
                errors,
            };
        }
        let mut transferred = 0;
        // SAFETY: storage is still owned until this exact completion query returns.
        let result =
            unsafe { GetOverlappedResult(server, self.operation.as_ref(), &mut transferred, 0) };
        if result == 0 {
            let error = io::Error::last_os_error();
            if error.raw_os_error().map(|n| n as u32) == Some(ERROR_IO_INCOMPLETE) {
                return CancelWrite {
                    completed: false,
                    errors,
                };
            }
            self.pending = false;
            match error.raw_os_error().map(|n| n as u32) {
                Some(ERROR_OPERATION_ABORTED | ERROR_BROKEN_PIPE | ERROR_NO_DATA) => {}
                _ => errors.push(error),
            }
        } else {
            self.pending = false;
            if let Err(error) = self.advance(transferred) {
                errors.push(error);
            }
        }
        self.server.take();
        CancelWrite {
            completed: true,
            errors,
        }
    }
}

impl Drop for PipeWriter {
    fn drop(&mut self) {
        while self.pending {
            let _ = self.cancel_and_join_bounded(1_000);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs::File;
    use std::io::Read;
    use std::thread;

    #[test]
    fn writer_transfers_bounded_chunks_and_closes_for_eof() {
        let expected: Vec<u8> = (0..32_769).map(|n| (n % 251) as u8).collect();
        let (mut writer, child) = PipeWriter::pair(expected.clone()).unwrap();
        let reader = thread::spawn(move || {
            let mut bytes = Vec::new();
            File::from(child).read_to_end(&mut bytes).unwrap();
            bytes
        });
        while !writer.is_finished() {
            if !writer.is_pending() {
                writer.start_write().unwrap();
            }
            if writer.is_pending() {
                // SAFETY: writer retains its event throughout this bounded wait.
                assert_eq!(
                    unsafe { WaitForSingleObject(writer.event_handle(), 5_000) },
                    WAIT_OBJECT_0
                );
                writer.finish_write().unwrap();
            }
        }
        assert_eq!(reader.join().unwrap(), expected);
    }

    #[test]
    fn writer_cancels_a_blocked_write_before_releasing_storage() {
        let (mut writer, child) = PipeWriter::pair(vec![b'A'; 1_048_576]).unwrap();
        for _ in 0..256 {
            if writer.is_pending() {
                break;
            }
            assert!(
                !writer.is_finished(),
                "pipe unexpectedly accepted all input without a reader"
            );
            writer.start_write().unwrap();
        }
        assert!(
            writer.is_pending(),
            "blocked pipe did not produce a pending write"
        );
        let outcome = writer.cancel_and_join_bounded(5_000);
        assert!(outcome.completed, "cancelled write remained pending");
        assert!(
            outcome.errors.is_empty(),
            "cancellation errors: {:?}",
            outcome.errors
        );
        assert!(!writer.is_pending() && writer.is_finished());
        let mut received = Vec::new();
        File::from(child).read_to_end(&mut received).unwrap();
        assert!(received.len() < 1_048_576 && received.iter().all(|byte| *byte == b'A'));
    }

    #[test]
    fn writer_reports_child_pipe_closure_and_zero_progress() {
        let (mut writer, child) = PipeWriter::pair(vec![1, 2, 3]).unwrap();
        drop(child);
        let error = match writer.start_write() {
            Err(error) => error,
            Ok(()) if writer.is_pending() => {
                // SAFETY: writer retains its event throughout this bounded wait.
                assert_eq!(
                    unsafe { WaitForSingleObject(writer.event_handle(), 5_000) },
                    WAIT_OBJECT_0
                );
                writer
                    .finish_write()
                    .expect_err("closed child pipe must fail")
            }
            Ok(()) => panic!("closed child pipe accepted the complete input"),
        };
        assert_eq!(error.kind(), io::ErrorKind::BrokenPipe);
        let (mut writer, _child) = PipeWriter::pair(vec![1]).unwrap();
        writer.requested = 1;
        assert_eq!(
            writer.advance(0).unwrap_err().kind(),
            io::ErrorKind::WriteZero
        );
    }
}
