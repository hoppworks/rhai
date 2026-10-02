"""Conservative, bounded Darwin process inventory for private runtime closure.

The libproc interfaces used here are private Apple interfaces. Callers must
record the SDK/toolchain identity and treat any ABI or readback ambiguity as an
incomplete cleanup. Native calls are synchronous: deadline checks before and
after each call detect an overrun only after return and cannot interrupt a
stalled kernel call. This module never signals processes.
"""
import ctypes
import os
import time
from pathlib import Path

PROC_ALL_PIDS = 1
PROC_PIDTBSDINFO = 3
PROC_PIDTASKINFO = 4
MAX_PID_BUFFER_BYTES = 4 * 1024 * 1024
MAX_LIST_RETRIES = 3
PIDPATH_BYTES = 4096


class ProcBsdInfo(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_uint32), ("status", ctypes.c_uint32),
        ("xstatus", ctypes.c_uint32), ("pid", ctypes.c_uint32),
        ("ppid", ctypes.c_uint32), ("uid", ctypes.c_uint32),
        ("gid", ctypes.c_uint32), ("ruid", ctypes.c_uint32),
        ("rgid", ctypes.c_uint32), ("svuid", ctypes.c_uint32),
        ("svgid", ctypes.c_uint32), ("reserved", ctypes.c_uint32),
        ("comm", ctypes.c_char * 16), ("name", ctypes.c_char * 32),
        ("nfiles", ctypes.c_uint32), ("pgid", ctypes.c_uint32),
        ("pjobc", ctypes.c_uint32), ("ttydev", ctypes.c_uint32),
        ("tty_pgid", ctypes.c_uint32), ("nice", ctypes.c_int32),
        ("start_seconds", ctypes.c_uint64), ("start_microseconds", ctypes.c_uint64),
    ]


class ProcTaskInfo(ctypes.Structure):
    _fields_ = [
        ("virtual_size", ctypes.c_uint64), ("resident_size", ctypes.c_uint64),
        ("total_user", ctypes.c_uint64), ("total_system", ctypes.c_uint64),
        ("threads_user", ctypes.c_uint64), ("threads_system", ctypes.c_uint64),
        ("policy", ctypes.c_int32), ("faults", ctypes.c_int32),
        ("pageins", ctypes.c_int32), ("cow_faults", ctypes.c_int32),
        ("messages_sent", ctypes.c_int32), ("messages_received", ctypes.c_int32),
        ("syscalls_mach", ctypes.c_int32), ("syscalls_unix", ctypes.c_int32),
        ("context_switches", ctypes.c_int32), ("thread_count", ctypes.c_int32),
        ("running_threads", ctypes.c_int32), ("priority", ctypes.c_int32),
    ]


class IncompleteProcessReadback(RuntimeError):
    pass


class DarwinProcessReader:
    """Read a complete listing, retrying identities changed mid-observation."""

    def __init__(self, api=None, uid=None, max_list_bytes=MAX_PID_BUFFER_BYTES):
        self.api = api if api is not None else self._load_api()
        self.uid = os.getuid() if uid is None else uid
        self.max_list_bytes = max_list_bytes

    @staticmethod
    def _load_api():
        if os.uname().sysname != "Darwin":
            raise IncompleteProcessReadback("Darwin libproc is unavailable on this platform")
        lib = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
        lib.proc_listpids.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_int]
        lib.proc_listpids.restype = ctypes.c_int
        lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
        lib.proc_pidinfo.restype = ctypes.c_int
        lib.proc_pidpath.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
        lib.proc_pidpath.restype = ctypes.c_int
        return lib

    @staticmethod
    def _check_deadline(deadline, operation):
        if time.monotonic() >= deadline:
            raise IncompleteProcessReadback("deadline expired " + operation)

    def _pid_list(self, deadline):
        capacity = 4096
        while capacity <= self.max_list_bytes:
            self._check_deadline(deadline, "before proc_listpids")
            buf = ctypes.create_string_buffer(capacity)
            returned = self.api.proc_listpids(PROC_ALL_PIDS, 0, buf, capacity)
            self._check_deadline(deadline, "after proc_listpids")
            if returned < 0:
                raise IncompleteProcessReadback("proc_listpids failed")
            if returned == 0:
                raise IncompleteProcessReadback("proc_listpids returned no bytes; empty and error are ambiguous")
            if returned % ctypes.sizeof(ctypes.c_int):
                raise IncompleteProcessReadback("proc_listpids returned a partial PID")
            if returned >= capacity:
                capacity *= 2
                continue
            values = (ctypes.c_int * (returned // ctypes.sizeof(ctypes.c_int))).from_buffer_copy(buf.raw[:returned])
            pids = []
            for index, pid in enumerate(values):
                if index % 256 == 0:
                    self._check_deadline(deadline, "while parsing process list")
                if pid > 0:
                    pids.append(pid)
            if len(pids) != len(set(pids)):
                raise IncompleteProcessReadback("proc_listpids returned duplicate PIDs")
            if os.getpid() not in pids:
                raise IncompleteProcessReadback("complete process list omitted the reader itself")
            return pids
        raise IncompleteProcessReadback("proc_listpids exceeded the bounded buffer")

    def _identity(self, pid, deadline):
        self._check_deadline(deadline, "before proc_pidinfo")
        info = ProcBsdInfo()
        got = self.api.proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, ctypes.byref(info), ctypes.sizeof(info))
        self._check_deadline(deadline, "after proc_pidinfo")
        if got != ctypes.sizeof(info) or info.pid != pid:
            return None
        task_sample = self._task_sample(pid, deadline)
        if task_sample is None:
            return None
        resident_bytes, thread_count = task_sample
        path = None
        if info.uid == self.uid:
            path = self._path(pid, deadline)
            if path is None:
                return None
        # A PID can be reused between the BSD identity and executable-path
        # queries. Read identity again so an old start tuple is never paired
        # with a new process image.
        self._check_deadline(deadline, "before identity confirmation")
        confirm = ProcBsdInfo()
        got = self.api.proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, ctypes.byref(confirm), ctypes.sizeof(confirm))
        self._check_deadline(deadline, "after identity confirmation")
        if got != ctypes.sizeof(confirm) or (
            confirm.pid, confirm.uid, confirm.start_seconds, confirm.start_microseconds,
            confirm.ppid, confirm.pgid,
        ) != (
            info.pid, info.uid, info.start_seconds, info.start_microseconds,
            info.ppid, info.pgid,
        ):
            return None
        row = {
            "pid": pid, "uid": info.uid, "ppid": info.ppid, "pgid": info.pgid,
            "status": info.status, "start_seconds": info.start_seconds,
            "start_microseconds": info.start_microseconds, "rss_bytes": resident_bytes,
            "thread_count": thread_count,
        }
        if path is None:
            row["foreign"] = True
        else:
            row["path"] = path
        return row

    def _task_sample(self, pid, deadline):
        self._check_deadline(deadline, "before PROC_PIDTASKINFO")
        info = ProcTaskInfo()
        got = self.api.proc_pidinfo(pid, PROC_PIDTASKINFO, 0, ctypes.byref(info), ctypes.sizeof(info))
        self._check_deadline(deadline, "after PROC_PIDTASKINFO")
        if got != ctypes.sizeof(info):
            return None
        if info.thread_count <= 0:
            return None
        return int(info.resident_size), int(info.thread_count)

    def managed_task_sample(self, pid, expected_identity, deadline):
        """Return an identity-bracketed task sample or fail closed on any mismatch."""
        row = self._identity(pid, deadline)
        if row is None or any(row.get(key) != expected_identity.get(key)
                              for key in ("pid", "start_seconds", "start_microseconds")):
            raise IncompleteProcessReadback("Managed task sample identity changed or became inaccessible")
        if type(row.get("thread_count")) is not int or row["thread_count"] <= 0:
            raise IncompleteProcessReadback("Managed task sample has an invalid task count")
        return row

    def _path(self, pid, deadline):
        path_buf = ctypes.create_string_buffer(PIDPATH_BYTES)
        self._check_deadline(deadline, "before proc_pidpath")
        path_len = self.api.proc_pidpath(pid, path_buf, PIDPATH_BYTES)
        self._check_deadline(deadline, "after proc_pidpath")
        if path_len <= 0 or path_len >= PIDPATH_BYTES:
            return None
        try:
            path = os.fsdecode(path_buf.raw[:path_len].split(b"\0", 1)[0])
        except UnicodeError:
            return None
        return path if path.startswith("/") else None

    def complete_listing(self, deadline):
        """Return one internally consistent listing, or fail closed at deadline."""
        for _attempt in range(MAX_LIST_RETRIES):
            self._check_deadline(deadline, "before complete process listing")
            pids = self._pid_list(deadline)
            rows = []
            changed = False
            for pid in pids:
                row = self._identity(pid, deadline)
                if row is None:
                    changed = True
                    break
                rows.append(row)
            if not changed:
                self._check_deadline(deadline, "after complete process listing")
                return rows
        raise IncompleteProcessReadback("process identities changed or became inaccessible during all bounded complete-list retries")

    def runtime_candidates(self, runtime, deadline):
        runtime = str(Path(runtime).resolve())
        prefix = runtime.rstrip(os.sep) + os.sep
        matches = []
        for row in self.complete_listing(deadline):
            self._check_deadline(deadline, "while filtering process candidates")
            if row.get("foreign"):
                continue
            path = row["path"]
            if path == "/usr/bin/true" or path == runtime or path.startswith(prefix):
                matches.append(row)
        return matches

    @staticmethod
    def resident_kib(rows):
        return resident_kib(rows)


def candidate_absence(reader, runtime, deadline, required_empty_observations=2):
    """Require repeated complete candidate-free listings within the deadline."""
    if required_empty_observations < 2:
        raise ValueError("at least two complete observations are required")
    empty = 0
    observations = 0
    while time.monotonic() < deadline:
        live = reader.runtime_candidates(runtime, deadline)
        if time.monotonic() >= deadline:
            raise IncompleteProcessReadback("candidate observation completed after its deadline")
        observations += 1
        if live:
            empty = 0
        else:
            empty += 1
            if empty >= required_empty_observations:
                return {"complete": True, "observations": observations, "candidates": []}
    raise IncompleteProcessReadback("candidate absence was not established before the deadline")


def resident_kib(rows):
    """Sum resident bytes and round up so a partial KiB cannot undercount."""
    total = 0
    for row in rows:
        value = row.get("rss_bytes")
        if not isinstance(value, int) or value < 0:
            raise IncompleteProcessReadback("process row has invalid resident-byte sample")
        total += value
    return (total + 1023) // 1024
