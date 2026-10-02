import ctypes
import importlib.util
import os
import struct
import time
import unittest
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).with_name("darwin-process-reader.py")
SPEC = importlib.util.spec_from_file_location("darwin_process_reader", PATH)
reader_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reader_module)


class FakeProc:
    def __init__(self, pids=(), paths=None, inaccessible=(), list_result=None,
                 identity_hook=None, list_hook=None, task_inaccessible=(), task_result=None,
                 resident_bytes=None):
        self.pids = list(pids)
        self.paths = paths or {}
        self.inaccessible = set(inaccessible)
        self.list_result = list_result
        self.identity_hook = identity_hook
        self.list_hook = list_hook
        self.task_inaccessible = set(task_inaccessible)
        self.task_result = task_result
        self.resident_bytes = resident_bytes or {}
        self.thread_counts = {}
        self.identity_calls = {}
        self.task_calls = {}
        self.task_sizes = {}
        self.list_calls = 0

    def proc_listpids(self, _kind, _info, buffer, size):
        self.list_calls += 1
        if self.list_hook:
            self.list_hook()
        raw = struct.pack("=" + "i" * len(self.pids), *self.pids) if self.pids else b""
        if raw:
            ctypes.memmove(buffer, raw[:size], min(len(raw), size))
        return self.list_result if self.list_result is not None else len(raw)

    def proc_pidinfo(self, pid, flavor, _arg, pointer, size):
        if flavor == reader_module.PROC_PIDTASKINFO:
            self.task_calls[pid] = self.task_calls.get(pid, 0) + 1
            self.task_sizes[pid] = size
            if pid in self.task_inaccessible or size != ctypes.sizeof(reader_module.ProcTaskInfo):
                return 0
            info = ctypes.cast(pointer, ctypes.POINTER(reader_module.ProcTaskInfo)).contents
            info.resident_size = self.resident_bytes.get(pid, 1024)
            info.thread_count = self.thread_counts.get(pid, 2)
            return size if self.task_result is None else self.task_result
        calls = self.identity_calls.get(pid, 0) + 1
        self.identity_calls[pid] = calls
        if self.identity_hook:
            self.identity_hook(pid, calls)
        if pid in self.inaccessible or size != ctypes.sizeof(reader_module.ProcBsdInfo):
            return 0
        info = ctypes.cast(pointer, ctypes.POINTER(reader_module.ProcBsdInfo)).contents
        info.pid = pid
        info.ppid = 1
        info.pgid = pid
        info.uid = os.getuid()
        info.status = 2
        info.start_seconds = 123
        info.start_microseconds = pid
        return size

    def proc_pidpath(self, pid, buffer, size):
        path = self.paths.get(pid, "/usr/bin/python3").encode() + b"\0"
        if len(path) > size:
            return -1
        ctypes.memmove(buffer, path, len(path))
        return len(path)


def fixture_pids(*pids):
    own = os.getpid()
    return (own,) + tuple(pid for pid in pids if pid != own)


class ReaderTests(unittest.TestCase):
    def test_ctypes_structs_and_libproc_signatures_match_active_sdk_declarations(self):
        # Values below are transcribed from the installed arm64 MacOSX SDK's
        # sys/proc_info.h and libproc.h. This is a layout/signature test only;
        # it never loads or calls the native library.
        self.assertEqual(reader_module.PROC_ALL_PIDS, 1)
        self.assertEqual(reader_module.PROC_PIDTBSDINFO, 3)
        self.assertEqual(reader_module.PROC_PIDTASKINFO, 4)
        bsd = reader_module.ProcBsdInfo
        self.assertEqual(ctypes.sizeof(bsd), 136)
        self.assertEqual(tuple((name, getattr(bsd, name).offset) for name, _ in bsd._fields_), (
            ("flags", 0), ("status", 4), ("xstatus", 8), ("pid", 12),
            ("ppid", 16), ("uid", 20), ("gid", 24), ("ruid", 28),
            ("rgid", 32), ("svuid", 36), ("svgid", 40), ("reserved", 44),
            ("comm", 48), ("name", 64), ("nfiles", 96), ("pgid", 100),
            ("pjobc", 104), ("ttydev", 108), ("tty_pgid", 112),
            ("nice", 116), ("start_seconds", 120), ("start_microseconds", 128),
        ))
        self.assertEqual(tuple(field_type for _name, field_type in bsd._fields_),
                         (ctypes.c_uint32,) * 12 +
                         (ctypes.c_char * 16, ctypes.c_char * 32) +
                         (ctypes.c_uint32,) * 5 +
                         (ctypes.c_int32, ctypes.c_uint64, ctypes.c_uint64))
        task = reader_module.ProcTaskInfo
        self.assertEqual(ctypes.sizeof(task), 96)
        self.assertEqual(tuple((name, getattr(task, name).offset) for name, _ in task._fields_), (
            ("virtual_size", 0), ("resident_size", 8), ("total_user", 16),
            ("total_system", 24), ("threads_user", 32), ("threads_system", 40),
            ("policy", 48), ("faults", 52), ("pageins", 56), ("cow_faults", 60),
            ("messages_sent", 64), ("messages_received", 68),
            ("syscalls_mach", 72), ("syscalls_unix", 76),
            ("context_switches", 80), ("thread_count", 84),
            ("running_threads", 88), ("priority", 92),
        ))
        self.assertEqual(tuple(field_type for _name, field_type in task._fields_),
                         (ctypes.c_uint64,) * 6 + (ctypes.c_int32,) * 12)

        class Function:
            argtypes = None
            restype = None

        class Library:
            proc_listpids = Function()
            proc_pidinfo = Function()
            proc_pidpath = Function()

        library = Library()
        with patch.object(reader_module.os, "uname", return_value=type("Uname", (), {"sysname": "Darwin"})()), \
                patch.object(reader_module.ctypes, "CDLL", return_value=library) as load:
            self.assertIs(reader_module.DarwinProcessReader._load_api(), library)
        load.assert_called_once_with("/usr/lib/libproc.dylib", use_errno=True)
        self.assertEqual(library.proc_listpids.argtypes,
                         [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_int])
        self.assertIs(library.proc_listpids.restype, ctypes.c_int)
        self.assertEqual(library.proc_pidinfo.argtypes,
                         [ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                          ctypes.c_void_p, ctypes.c_int])
        self.assertIs(library.proc_pidinfo.restype, ctypes.c_int)
        self.assertEqual(library.proc_pidpath.argtypes,
                         [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32])
        self.assertIs(library.proc_pidpath.restype, ctypes.c_int)

    def reader(self, api, max_list_bytes=reader_module.MAX_PID_BUFFER_BYTES):
        return reader_module.DarwinProcessReader(api, uid=os.getuid(), max_list_bytes=max_list_bytes)

    def test_bsdinfo_layout_matches_transcribed_sdk_fields(self):
        self.assertEqual(ctypes.sizeof(reader_module.ProcBsdInfo), 136)
        self.assertEqual(reader_module.ProcBsdInfo.start_seconds.offset, 120)

    def test_taskinfo_layout_and_resident_kib_conversion(self):
        self.assertEqual(ctypes.sizeof(reader_module.ProcTaskInfo), 96)
        self.assertEqual(reader_module.ProcTaskInfo.resident_size.offset, 8)
        rows = [{"rss_bytes": 1024}, {"rss_bytes": 1025}]
        self.assertEqual(reader_module.resident_kib(rows), 3)

    def test_taskinfo_query_uses_exact_sdk_structure_length(self):
        api = FakeProc(fixture_pids(101))
        self.reader(api).complete_listing(time.monotonic() + 1)
        self.assertEqual(set(api.task_sizes.values()), {ctypes.sizeof(reader_module.ProcTaskInfo)})

    def test_complete_listing_exports_identity_bracketed_task_count(self):
        api = FakeProc(fixture_pids(101))
        api.thread_counts[101] = 4
        rows = self.reader(api).complete_listing(time.monotonic() + 1)
        row = next(row for row in rows if row["pid"] == 101)
        self.assertEqual(row["thread_count"], 4)
        self.assertEqual(api.identity_calls[101], 2)

    def test_managed_task_sample_requires_exact_identity_and_positive_count(self):
        api = FakeProc(fixture_pids(101))
        api.thread_counts[101] = 4
        reader = self.reader(api)
        expected = {"pid": 101, "start_seconds": 123, "start_microseconds": 101}
        sample = reader.managed_task_sample(101, expected, time.monotonic() + 1)
        self.assertEqual(sample["thread_count"], 4)
        with self.assertRaises(reader_module.IncompleteProcessReadback):
            reader.managed_task_sample(101, {**expected, "start_microseconds": 102}, time.monotonic() + 1)

    def test_zero_thread_count_is_inaccessible_for_managed_task_observation(self):
        api = FakeProc(fixture_pids(101))
        api.thread_counts[101] = 0
        with self.assertRaises(reader_module.IncompleteProcessReadback):
            self.reader(api).managed_task_sample(101,
                {"pid": 101, "start_seconds": 123, "start_microseconds": 101},
                time.monotonic() + 1)

    def test_exact_taskinfo_length_is_required(self):
        api = FakeProc(fixture_pids(101), task_result=ctypes.sizeof(reader_module.ProcTaskInfo) - 1)
        with self.assertRaises(reader_module.IncompleteProcessReadback):
            self.reader(api).complete_listing(time.monotonic() + 1)
        self.assertEqual(api.list_calls, reader_module.MAX_LIST_RETRIES)

    def test_taskinfo_is_bracketed_by_full_identity_including_microseconds(self):
        changed = {"done": False}

        class RacingProc(FakeProc):
            def proc_pidinfo(self, pid, flavor, arg, pointer, size):
                result = super().proc_pidinfo(pid, flavor, arg, pointer, size)
                if (flavor == reader_module.PROC_PIDTBSDINFO and pid == 101
                        and self.identity_calls[pid] == 2 and not changed["done"]):
                    ctypes.cast(pointer, ctypes.POINTER(reader_module.ProcBsdInfo)).contents.start_microseconds += 1
                    changed["done"] = True
                return result

        api = RacingProc(fixture_pids(101))
        rows = self.reader(api).complete_listing(time.monotonic() + 1)
        self.assertTrue(changed["done"])
        self.assertEqual(api.list_calls, 2)
        self.assertEqual([row["pid"] for row in rows], list(fixture_pids(101)))

    def test_inaccessible_task_row_is_not_treated_as_disappeared_or_zero_rss(self):
        api = FakeProc(fixture_pids(101), task_inaccessible=(101,))
        with self.assertRaises(reader_module.IncompleteProcessReadback):
            self.reader(api).complete_listing(time.monotonic() + 1)
        self.assertEqual(api.list_calls, reader_module.MAX_LIST_RETRIES)

    def test_candidate_filter_uses_private_runtime_and_true(self):
        runtime = Path("/private/tmp/owned-run")
        api = FakeProc(fixture_pids(101, 102, 103), {
            101: str(runtime / "target/debug/deps/test-host"),
            102: "/usr/bin/true",
            103: "/usr/bin/python3",
        })
        candidates = self.reader(api).runtime_candidates(runtime, time.monotonic() + 1)
        self.assertEqual([row["pid"] for row in candidates], [101, 102])
        self.assertEqual(candidates[0]["start_microseconds"], 101)

    def test_zero_bytes_is_ambiguous_and_rejected(self):
        with self.assertRaises(reader_module.IncompleteProcessReadback):
            self.reader(FakeProc(list_result=0)).complete_listing(time.monotonic() + 1)

    def test_exact_capacity_retries_with_larger_buffer(self):
        # 1024 PIDs occupy the initial 4096-byte buffer; the second call
        # receives enough room and must include the current Python process.
        pids = fixture_pids(*range(1, 1024))
        api = FakeProc(pids)
        rows = self.reader(api, max_list_bytes=8192).complete_listing(time.monotonic() + 2)
        self.assertEqual(api.list_calls, 2)
        self.assertEqual(len(rows), len(pids))

    def test_buffer_cap_fails_closed(self):
        api = FakeProc(fixture_pids(*range(1, 1024)))
        with self.assertRaises(reader_module.IncompleteProcessReadback):
            self.reader(api, max_list_bytes=4096).complete_listing(time.monotonic() + 1)
        self.assertEqual(api.list_calls, 1)

    def test_missing_self_pid_fails_closed(self):
        with self.assertRaises(reader_module.IncompleteProcessReadback):
            self.reader(FakeProc((101,))).complete_listing(time.monotonic() + 1)

    def test_partial_pid_bytes_fail_closed(self):
        with self.assertRaises(reader_module.IncompleteProcessReadback):
            self.reader(FakeProc(list_result=3)).complete_listing(time.monotonic() + 1)

    def test_inaccessible_row_retries_then_fails_closed(self):
        api = FakeProc(fixture_pids(101), inaccessible=(101,))
        with self.assertRaises(reader_module.IncompleteProcessReadback):
            self.reader(api).complete_listing(time.monotonic() + 1)
        self.assertEqual(api.list_calls, reader_module.MAX_LIST_RETRIES)

    def test_identity_race_retries_whole_listing(self):
        # Mutate the second BSD snapshot on the first inventory, then restore
        # a stable identity for the second inventory.
        changed = {"done": False}
        class RacingProc(FakeProc):
            def proc_pidinfo(self, pid, flavor, arg, pointer, size):
                result = super().proc_pidinfo(pid, flavor, arg, pointer, size)
                if pid == 101 and self.identity_calls[pid] == 2 and not changed["done"]:
                    ctypes.cast(pointer, ctypes.POINTER(reader_module.ProcBsdInfo)).contents.start_seconds += 1
                    changed["done"] = True
                return result
        api = RacingProc(fixture_pids(101))
        rows = self.reader(api).complete_listing(time.monotonic() + 1)
        self.assertTrue(changed["done"])
        self.assertEqual(api.list_calls, 2)
        self.assertEqual([row["pid"] for row in rows], list(fixture_pids(101)))

    def test_deadline_expired_before_list_does_not_call_api(self):
        api = FakeProc(fixture_pids(101))
        with self.assertRaises(reader_module.IncompleteProcessReadback):
            self.reader(api).complete_listing(time.monotonic() - 1)
        self.assertEqual(api.list_calls, 0)

    def test_deadline_crossed_during_list_is_rejected(self):
        api = FakeProc(fixture_pids(101), list_hook=lambda: time.sleep(0.02))
        with self.assertRaises(reader_module.IncompleteProcessReadback):
            self.reader(api).complete_listing(time.monotonic() + 0.005)

    def test_deadline_crossed_by_candidate_observation_is_not_counted(self):
        class SlowEmptyReader:
            def runtime_candidates(self, _runtime, _deadline):
                time.sleep(0.02)
                return []
        with self.assertRaises(reader_module.IncompleteProcessReadback):
            reader_module.candidate_absence(
                SlowEmptyReader(), "/private/tmp/owned-run", time.monotonic() + 0.005,
            )

    def test_absence_requires_two_complete_observations(self):
        class EmptyReader:
            def __init__(self): self.calls = 0
            def runtime_candidates(self, _runtime, _deadline):
                self.calls += 1
                return []
        fake = EmptyReader()
        receipt = reader_module.candidate_absence(fake, "/private/tmp/owned-run", time.monotonic() + 1)
        self.assertTrue(receipt["complete"])
        self.assertEqual(fake.calls, 2)

    def test_one_absence_observation_is_rejected(self):
        with self.assertRaises(ValueError):
            reader_module.candidate_absence(object(), "/private/tmp/owned-run", time.monotonic() + 1, 1)


if __name__ == "__main__":
    unittest.main()
