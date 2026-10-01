"""Darwin process identity helpers for exact-PID custody records."""
import ctypes
import ctypes.util
import errno


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


def process_start_identity(pid):
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


def process_matches(pid, start_identity):
    try:
        return process_start_identity(pid) == start_identity
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return False
        raise
