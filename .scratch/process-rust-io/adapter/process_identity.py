"""Platform-specific process start identities for exact-PID custody records."""
import ctypes
import ctypes.util
import errno
import sys
from pathlib import Path


class _ProcBsdInfo(ctypes.Structure):
    _fields_ = [
        ('flags', ctypes.c_uint32), ('status', ctypes.c_uint32),
        ('xstatus', ctypes.c_uint32), ('pid', ctypes.c_uint32),
        ('ppid', ctypes.c_uint32), ('uid', ctypes.c_uint32),
        ('gid', ctypes.c_uint32), ('ruid', ctypes.c_uint32),
        ('rgid', ctypes.c_uint32), ('svuid', ctypes.c_uint32),
        ('svgid', ctypes.c_uint32), ('rfu', ctypes.c_uint32),
        ('comm', ctypes.c_char * 16), ('name', ctypes.c_char * 32),
        ('nfiles', ctypes.c_uint32), ('pgid', ctypes.c_uint32),
        ('pjobc', ctypes.c_uint32), ('tdev', ctypes.c_uint32),
        ('tpgid', ctypes.c_uint32), ('nice', ctypes.c_int32),
        ('start_sec', ctypes.c_uint64), ('start_usec', ctypes.c_uint64),
    ]


def _darwin_process_start_identity(pid):
    library = ctypes.util.find_library('proc')
    if not library:
        raise RuntimeError('Darwin proc_pidinfo is unavailable')
    libproc = ctypes.CDLL(library, use_errno=True)
    fn = libproc.proc_pidinfo
    fn.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                   ctypes.c_void_p, ctypes.c_int]
    fn.restype = ctypes.c_int
    info = _ProcBsdInfo()
    ctypes.set_errno(0)
    size = fn(int(pid), 3, 0, ctypes.byref(info), ctypes.sizeof(info))
    if size == 0:
        code = ctypes.get_errno()
        if code == 0:
            raise RuntimeError(f'proc_pidinfo returned zero without an error for PID {pid}')
        raise OSError(code, 'proc_pidinfo identity lookup failed')
    if size != ctypes.sizeof(info) or info.pid != int(pid):
        raise RuntimeError(f'proc_pidinfo returned incomplete identity for PID {pid}: {size}')
    return [int(info.start_sec), int(info.start_usec)]


def parse_linux_stat(raw, expected_pid):
    """Return Linux /proc stat start ticks, parsing comm through its final ')'."""
    opening = raw.find('(')
    closing = raw.rfind(')')
    if opening <= 0 or closing <= opening or raw[closing + 1:closing + 2] != ' ':
        raise ValueError('malformed Linux /proc stat command field')
    try:
        pid = int(raw[:opening].strip())
    except ValueError as exc:
        raise ValueError('malformed Linux /proc stat PID') from exc
    if pid != int(expected_pid):
        raise ValueError('Linux /proc stat PID does not match requested PID')
    fields = raw[closing + 2:].split()
    if len(fields) < 20 or len(fields[0]) != 1:
        raise ValueError('truncated Linux /proc stat fields')
    try:
        start_ticks = int(fields[19])
    except ValueError as exc:
        raise ValueError('malformed Linux /proc stat start time') from exc
    if start_ticks < 0:
        raise ValueError('negative Linux /proc stat start time')
    return start_ticks


def parse_linux_boot_time(raw):
    values = []
    for line in raw.splitlines():
        fields = line.split()
        if fields and fields[0] == 'btime':
            if len(fields) != 2:
                raise ValueError('malformed Linux /proc/stat btime field')
            try:
                values.append(int(fields[1]))
            except ValueError as exc:
                raise ValueError('malformed Linux /proc/stat boot time') from exc
    if len(values) != 1 or values[0] < 0:
        raise ValueError('missing, duplicate, or invalid Linux /proc/stat boot time')
    return values[0]


def _linux_process_start_identity(pid, proc_root=Path('/proc')):
    pid = int(pid)
    if pid <= 0:
        raise ValueError('PID must be positive')
    try:
        raw = (proc_root / str(pid) / 'stat').read_text()
    except FileNotFoundError as exc:
        raise ProcessLookupError(pid, 'Linux process stat entry is absent') from exc
    start_ticks = parse_linux_stat(raw, pid)
    boot_time = parse_linux_boot_time((proc_root / 'stat').read_text())
    return [boot_time, start_ticks]


def process_start_identity(pid):
    if sys.platform == 'darwin':
        return _darwin_process_start_identity(pid)
    if sys.platform.startswith('linux'):
        return _linux_process_start_identity(pid)
    raise RuntimeError('process start identity is unsupported on ' + sys.platform)


def process_matches(pid, start_identity):
    try:
        return process_start_identity(pid) == start_identity
    except ProcessLookupError:
        return False
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return False
        raise
