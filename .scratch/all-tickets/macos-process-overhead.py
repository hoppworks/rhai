import ctypes, errno, hashlib, importlib.util, json, os, platform, re, shutil, socket, sys, time
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
SOURCE_REF='00bed4a0dfeb103ff209ba4c76dac7ae797b7c56'
ARCHIVE_SHA='5414ea195ad00152b1eae36b3f4e10943ba5d9bf323baff6410cca0c5b4d8b98'
RUNTIME=Path(os.environ['AGENT_RUNTIME_DIR']).resolve()
BASE=Path(os.environ['RHAI_OVERHEAD_LOG_BASE']).absolute()
EVIDENCE=REPO/'.scratch/all-tickets/macos-process-overhead-evidence'
TOOL=Path('/Users/hoppworks/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
CARGO,RUSTC,RUSTDOC=(TOOL/n for n in ('cargo','rustc','rustdoc'))
SDKROOT=Path('/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
XCODE_TOOLS=Path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin')
LOCK_SHA='8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa'
OVERLAYS=['Cargo.toml','src/packages/sys/config.rs','src/packages/sys/mod.rs','src/packages/sys/process.rs','src/packages/sys/process/unix.rs','tests/sys_process.rs']
REVIEWED_BUILD_CANDIDATES={
    ('ahash','0.8.12'), ('cap-primitives','4.0.3'), ('cap-std','4.0.3'),
    ('const-random-macro','0.1.16'), ('crunchy','0.2.4'),
    ('getrandom','0.3.4'), ('io-extras','0.19.0'), ('io-lifetimes','2.0.4'),
    ('io-lifetimes','3.0.1'), ('libc','0.2.189'), ('num-traits','0.2.19'),
    ('paste','1.0.15'), ('portable-atomic','1.15.0'),
    ('proc-macro2','1.0.103'), ('quote','1.0.41'), ('rhai','1.26.1'),
    ('rhai_codegen','3.2.0'), ('rustix','1.1.5'), ('serde','1.0.229'),
    ('serde_core','1.0.229'), ('serde_derive','1.0.229'),
    ('serde_json','1.0.145'), ('smartstring','1.0.1'),
    ('tiny-keccak','2.0.2'), ('trybuild','1.0.90'), ('zerocopy','0.8.59'),
}
SOURCE_GRAPH_PREFLIGHT=None
LIMIT=1_572_864
MAX_DESCENDANTS=16
MAX_RSS_KIB=2*1024*1024

# This legacy harness still spawns setup commands and a nested measurement
# driver, so it does not meet cause-09 command custody. Keep it impossible to
# launch accidentally until the source audit and the sole-custodian adapter are
# independently reviewed. This is a source gate, not evidence of custody.
CUSTODY_READINESS = Path(__file__).with_name('macos-overhead-custody-readiness.json')
CUSTODY_IMPLEMENTATION_FROZEN = False
_WAITID = None
_RPC = None
_LAST_CUSTODY_RESULT = None
# Darwin idtype_t/waitid constants from the active SDK's sys/wait.h.
DARWIN_P_PID = 1
DARWIN_WNOHANG = 0x01
DARWIN_WEXITED = 0x04
DARWIN_WNOWAIT = 0x20

def require_launch_readiness():
    if CUSTODY_IMPLEMENTATION_FROZEN is not True:
        raise RuntimeError('macOS overhead source is NOT launch-ready: sole-custodian implementation is not frozen')
    try:
        readiness = __import__('json').loads(CUSTODY_READINESS.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise RuntimeError('macOS overhead source is NOT launch-ready: missing custody readiness record') from exc
    required = {
        'schema': 1,
        'status': 'reviewed-ready',
        'build_confinement_audit': 'complete',
        'darwin_process_abi_review': 'complete',
        'sole_spawner_reaper': 'complete',
        'escaped_leaf_readback': 'complete',
        'pure_controls': 'complete',
        'independent_source_review': 'complete',
    }
    if not isinstance(readiness, dict) or any(readiness.get(key) != value for key, value in required.items()):
        raise RuntimeError('macOS overhead source is NOT launch-ready: custody prerequisites are incomplete')

class _DarwinSigVal(ctypes.Union):
    _fields_ = [('sival_int', ctypes.c_int), ('sival_ptr', ctypes.c_void_p)]

class _DarwinSigInfo(ctypes.Structure):
    _fields_ = [('si_signo', ctypes.c_int), ('si_errno', ctypes.c_int),
                ('si_code', ctypes.c_int), ('si_pid', ctypes.c_int32),
                ('si_uid', ctypes.c_uint32), ('si_status', ctypes.c_int),
                ('si_addr', ctypes.c_void_p),
                ('si_value', _DarwinSigVal),
                ('si_band', ctypes.c_long), ('__pad', ctypes.c_ulong * 7)]

class _WaitResult:
    def __init__(self, pid, code, status):
        self.si_pid, self.si_code, self.si_status = pid, code, status

def require_nonreaping_waitid():
    """Resolve reviewed WNOWAIT support before any gated process is spawned."""
    global _WAITID
    if callable(getattr(os, 'waitid', None)):
        for name in ('P_PID', 'WEXITED', 'WNOHANG', 'WNOWAIT'):
            if not hasattr(os, name):
                raise RuntimeError('waitid lacks required constant os.' + name)
        _WAITID = os.waitid
        return
    if sys.platform != 'darwin' or ctypes.sizeof(_DarwinSigInfo) != 104:
        raise RuntimeError('no reviewed Darwin waitid/WNOWAIT ABI for this Python/platform')
    libc = ctypes.CDLL(None, use_errno=True)
    native = getattr(libc, 'waitid', None)
    if native is None:
        raise RuntimeError('native waitid symbol is unavailable')
    native.argtypes = (ctypes.c_int, ctypes.c_uint32,
                       ctypes.POINTER(_DarwinSigInfo), ctypes.c_int)
    native.restype = ctypes.c_int
    def waitid(pid):
        info = _DarwinSigInfo()
        while True:
            ctypes.set_errno(0)
            result = native(DARWIN_P_PID, pid, ctypes.byref(info),
                            DARWIN_WEXITED | DARWIN_WNOHANG | DARWIN_WNOWAIT)
            if result == 0:
                return None if info.si_pid == 0 else _WaitResult(info.si_pid, info.si_code, info.si_status)
            error = ctypes.get_errno()
            if error == errno.EINTR:
                continue
            raise OSError(error, os.strerror(error))
    _WAITID = waitid

def waitid_nonreap(pid):
    if _WAITID is None:
        raise RuntimeError('non-reaping waitid was not resolved')
    if hasattr(os, 'waitid'):
        return _WAITID(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
    return _WAITID(pid)

def build_environment(runtime):
    """Build a closed Cargo environment; inherited variables cannot alter custody."""
    runtime=Path(runtime).resolve()
    home=runtime/'home'
    tmp=runtime/'tmp'
    cargo_home=runtime/'cargo-home'
    rustup_home=runtime/'rustup-home'
    target=runtime/'target'
    for path in (home,tmp,cargo_home,rustup_home,target):
        path.mkdir(parents=True,exist_ok=True)
    return {
        'PATH':f'{TOOL}:/usr/bin:/bin:/usr/sbin:/sbin',
        'HOME':str(home),
        'TMPDIR':str(tmp), 'TMP':str(tmp), 'TEMP':str(tmp),
        'CARGO_HOME':str(cargo_home), 'RUSTUP_HOME':str(rustup_home),
        'CARGO_TARGET_DIR':str(target), 'CARGO_BUILD_JOBS':'2',
        'CARGO_INCREMENTAL':'0', 'CARGO_PROFILE_DEV_DEBUG':'0',
        'CARGO_PROFILE_TEST_DEBUG':'0', 'CARGO_TERM_COLOR':'never',
        'RUSTC':str(RUSTC), 'RUSTDOC':str(RUSTDOC),
        'SDKROOT':str(SDKROOT),
    }

def expected_tool_identity():
    return {
        'cargo_version': 'cargo 1.93.0 (083ac5135 2025-12-15)',
        'rustc_release': '1.93.0',
        'rustc_commit': '254b59607d4417e9dffbc307138ae5c86280fe4c',
        'rustc_host': 'aarch64-apple-darwin',
        'rustc_llvm': '21.1.8',
        'rustdoc_version': 'rustdoc 1.93.0 (254b59607 2026-01-19)',
        'xcrun_version': 'xcrun version 72.',
        'sdkroot': str(SDKROOT),
        'cc_path': str(XCODE_TOOLS/'cc'),
        'clang_path': str(XCODE_TOOLS/'clang'),
        'ld_path': str(XCODE_TOOLS/'ld'),
        'dsymutil_path': str(XCODE_TOOLS/'dsymutil'),
        'cc_identity': ('Apple clang version 21.0.0', 'Target: arm64-apple-darwin27.0.0',
                        f'InstalledDir: {XCODE_TOOLS}'),
        'clang_identity': ('Apple clang version 21.0.0', 'Target: arm64-apple-darwin27.0.0',
                           f'InstalledDir: {XCODE_TOOLS}'),
        'ld_identity': ('ld-27037.1', 'LLVM version 21.0.0', 'TAPI version 21.0.0'),
        'dsymutil_identity': ('Apple LLVM version 21.0.0',),
    }

def validate_tool_identity(actual):
    expected = expected_tool_identity()
    if not isinstance(actual, dict):
        raise RuntimeError('tool identity probe is not a mapping')
    for key, value in expected.items():
        if key not in actual:
            raise RuntimeError(f'tool identity probe omitted {key}')
        observed = actual[key]
        if isinstance(value, tuple):
            if observed != value and (not isinstance(observed, str) or any(part not in observed for part in value)):
                raise RuntimeError(f'tool identity mismatch for {key}')
        elif observed != value:
            raise RuntimeError(f'tool identity mismatch for {key}')

def verify_toolchain_identity(env, deadline):
    expected = expected_tool_identity()
    probes = [
        ('cargo_version', [str(CARGO), '--version'], 'cargo-version-preflight.out'),
        ('rustc', [str(RUSTC), '--version', '--verbose'], 'rustc-version-preflight.out'),
        ('rustdoc_version', [str(RUSTDOC), '--version'], 'rustdoc-version-preflight.out'),
        ('xcrun_version', ['/usr/bin/xcrun', '--version'], 'xcrun-version-preflight.out'),
        ('sdkroot', ['/usr/bin/xcrun', '--show-sdk-path'], 'xcrun-sdk-preflight.out'),
        ('cc_path', ['/usr/bin/xcrun', '--find', 'cc'], 'xcrun-cc-preflight.out'),
        ('clang_path', ['/usr/bin/xcrun', '--find', 'clang'], 'xcrun-clang-preflight.out'),
        ('ld_path', ['/usr/bin/xcrun', '--find', 'ld'], 'xcrun-ld-preflight.out'),
        ('dsymutil_path', ['/usr/bin/xcrun', '--find', 'dsymutil'], 'xcrun-dsymutil-preflight.out'),
        ('cc_identity', ['/usr/bin/cc', '--version'], 'cc-version-preflight.out'),
        ('clang_identity', ['/usr/bin/clang', '--version'], 'clang-version-preflight.out'),
        ('ld_identity', [str(XCODE_TOOLS/'ld'), '-v'], 'ld-version-preflight.out'),
        ('dsymutil_identity', ['/usr/bin/dsymutil', '--version'], 'dsymutil-version-preflight.out'),
    ]
    actual = {}
    for key, argv, filename in probes:
        left = deadline-time.monotonic()
        if left <= 0: raise TimeoutError('tool identity preflight exceeded work deadline')
        output = RUNTIME/filename
        status, data = run_anchored_command(argv, REPO, env, output,
            min(deadline, time.monotonic()+10), closure_deadline=deadline)
        if status: raise RuntimeError(f'tool identity command failed for {key}: status={status}')
        text = data.decode(errors='replace').strip()
        if key == 'rustc':
            fields = dict(line.split(': ', 1) for line in text.splitlines() if ': ' in line)
            actual.update({'rustc_release': fields.get('release'), 'rustc_commit': fields.get('commit-hash'),
                           'rustc_host': fields.get('host'), 'rustc_llvm': fields.get('LLVM version')})
        else:
            actual[key] = text
    validate_tool_identity(actual)
    print('tool_identity_preflight=passed', flush=True)

def parse_ps_snapshot(output):
    """Parse `ps -axo pid=,ppid=,pgid=,rss=,state=,lstart=` output."""
    rows={}
    for line in output.splitlines():
        fields=line.strip().split(None,5)
        if len(fields)!=6: raise RuntimeError('malformed process snapshot row')
        pid,ppid,pgid,rss,state,start=fields
        if not all(v.isdigit() for v in (pid,ppid,pgid,rss)) or not start:
            raise RuntimeError('invalid process snapshot identity or RSS')
        ident={'pid':int(pid),'ppid':int(ppid),'pgid':int(pgid),'rss_kib':int(rss),
               'state':state,'start':start}
        if ident['pid'] in rows: raise RuntimeError('duplicate PID in process snapshot')
        rows[ident['pid']]=ident
    return rows

def descendants(rows, root_pid):
    found=set(); parents={pid:row['ppid'] for pid,row in rows.items()}
    changed=True
    while changed:
        changed=False
        for pid,parent in parents.items():
            if pid!=root_pid and pid not in found and (parent==root_pid or parent in found):
                found.add(pid); changed=True
    return [rows[pid] for pid in sorted(found)]

def enforce_process_sample(live, rss_kib):
    count=max(0,len(live)-1)  # The first row is Cargo; cap its descendants separately.
    if count>MAX_DESCENDANTS: raise RuntimeError(f'sampled process descendants exceeded {MAX_DESCENDANTS}')
    if rss_kib>=MAX_RSS_KIB: raise RuntimeError(f'sampled process RSS reached {MAX_RSS_KIB} KiB')

def process_snapshot(root_pid, deadline, env, source, owned_pids=()):
    left=deadline-time.monotonic()
    if left<=0: raise TimeoutError('aggregate Cargo deadline expired during process sample')
    output=RUNTIME/'process-snapshot.out'
    status,data=run_anchored_command(['/bin/ps','-axo','pid=,ppid=,pgid=,rss=,state=,lstart='],source,env,output,min(deadline,time.monotonic()+5),closure_deadline=deadline)
    if status: raise RuntimeError(f'process snapshot failed status={status}: {data.decode(errors="replace").strip()}')
    rows=parse_ps_snapshot(data.decode(errors='replace'))
    if root_pid not in rows: raise RuntimeError('owned harness is absent from process snapshot')
    live=descendants(rows,root_pid)
    # The owned harness root is counted with all active child helper groups.
    live=[rows[root_pid],*live]
    for pid in owned_pids:
        if pid not in rows: raise RuntimeError('owned anchor absent from sampled process snapshot')
        if pid not in {row['pid'] for row in live}: live.append(rows[pid])
    return live,sum(row['rss_kib'] for row in live)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sample(deadline,env,source):
    for n in (1,2):
        left=deadline-time.monotonic()
        if left<=0: raise TimeoutError('aggregate Cargo deadline expired during storage sample')
        output=RUNTIME/'storage-sample.out'
        try: status,data=run_anchored_command(['/usr/bin/du','-sk',str(RUNTIME)],source,env,output,min(deadline,time.monotonic()+5),closure_deadline=deadline)
        except (TimeoutError,RuntimeError) as e:
            print(f'storage_sample_attempt={n} status=timeout detail={type(e).__name__}: {e}',flush=True)
            if n==2: raise
            time.sleep(min(.05,max(0,deadline-time.monotonic()))); continue
        text=data.decode(errors='replace')
        print(f'storage_sample_attempt={n} status={status} stdout={text.strip()!r}',flush=True)
        if status:
            if n==2: raise RuntimeError('two failed storage samples')
            time.sleep(min(.05,max(0,deadline-time.monotonic()))); continue
        f=text.strip().split(maxsplit=1)
        if len(f)!=2 or not f[0].isdigit() or f[1]!=str(RUNTIME): raise RuntimeError('invalid storage sample')
        k=int(f[0]); print(f'storage_sample_kib={k}',flush=True)
        if k>=LIMIT: raise RuntimeError(f'sampled storage reached {LIMIT} KiB')
        return k
    raise RuntimeError('no valid storage measurement')

def _rpc_line(conn, deadline):
    import select
    data=bytearray()
    while b'\n' not in data:
        left=deadline-time.monotonic()
        if left<=0: raise TimeoutError('custody response deadline expired')
        ready,_,_=select.select([conn],[],[],min(.1,left))
        if not ready: continue
        block=conn.recv(65536-len(data))
        if not block: raise RuntimeError('custodian closed RPC connection')
        data.extend(block)
        if len(data)>65535: raise RuntimeError('custody response exceeds frame limit')
    line,extra=bytes(data).split(b'\n',1)
    if extra: raise RuntimeError('custodian returned pipelined RPC frames')
    return json.loads(line)

def read_command_output(output_path, stderr_path=None, include_stderr=True):
    """Read the two custody streams without mixing machine-readable stdout."""
    output = Path(output_path)
    if not output.is_file() or output.is_symlink():
        raise RuntimeError('custodian output path is missing or invalid')
    stdout = output.read_bytes()
    stderr = b''
    if stderr_path is not None:
        error_output = Path(stderr_path)
        if not error_output.is_file() or error_output.is_symlink():
            raise RuntimeError('custodian stderr path is missing or invalid')
        stderr = error_output.read_bytes()
    return (stdout + stderr if include_stderr else stdout), stderr


def run_anchored_command(argv, cwd, env, output_path, deadline, stderr_path=None,
                         closure_deadline=None, monitor_resources=False,
                         include_stderr=True):
    """Request an exact child command from the sole-spawning outer custodian."""
    global _LAST_CUSTODY_RESULT
    if _RPC is None: raise RuntimeError('no scoped custodian RPC connection')
    command_deadline=min(deadline,closure_deadline) if closure_deadline is not None else deadline
    request={'op':'command','argv':list(argv),'cwd':str(cwd),'env':env,
             'output':str(output_path),'stderr':str(stderr_path) if stderr_path else None,
             'deadline':command_deadline,'monitor_resources':monitor_resources}
    encoded=json.dumps(request,separators=(',',':')).encode()+b'\n'
    if len(encoded)>65535: raise RuntimeError('custody request exceeds frame limit')
    _RPC.sendall(encoded)
    response=_rpc_line(_RPC,command_deadline+5)
    _LAST_CUSTODY_RESULT=response
    if 'error' in response: raise RuntimeError('custodian command failed: '+response['error'])
    data, _stderr = read_command_output(response['output'], stderr_path, include_stderr)
    return response['status'],data

def emit(path,complete):
    b=path.read_bytes() if path.exists() else b''
    print(f'measurement_driver_output_begin path={path} complete={str(complete).lower()} bytes={len(b)} sha256={hashlib.sha256(b).hexdigest()}',flush=True)
    print(b.decode(errors='replace'),flush=True); print('measurement_driver_output_end',flush=True)

def _load_process_reader():
    reader_path=Path(__file__).with_name('darwin-process-reader.py')
    spec=importlib.util.spec_from_file_location('darwin_process_reader',reader_path)
    reader_module=importlib.util.module_from_spec(spec); spec.loader.exec_module(reader_module)
    return reader_module,reader_module.DarwinProcessReader()

def export_measurement_output(measurement_dir,status,output,parser):
    """Keep raw custody bytes, but export and parse measurement output as text."""
    if isinstance(output,bytes):
        text=output.decode(errors='replace')
    elif type(output) is str:
        text=output
    else:
        raise TypeError('measurement output must be bytes or text')
    measurement_dir.mkdir(parents=True,exist_ok=False)
    (measurement_dir/'cargo-output.log').write_text(text,encoding='utf-8')
    (measurement_dir/'cargo.status').write_text(f'{status}\n',encoding='ascii')
    if status!=0:
        return text,None,None
    samples=parser.parse_samples(text)
    summary=parser.summarize(samples)
    return text,samples,summary

def run(argv,path,deadline,env,source):
    print('cargo_argv='+repr(argv),flush=True); print('cargo_cwd='+str(source),flush=True); print('cargo_log='+str(path),flush=True)
    command_start=time.monotonic()
    cargo_deadline=min(deadline,command_start+540)
    status,out=run_anchored_command(argv,source,env,path,cargo_deadline,
        closure_deadline=deadline,monitor_resources=True)
    pgid=(_LAST_CUSTODY_RESULT or {}).get('pgid')
    if pgid is None: raise RuntimeError('custodian omitted direct Cargo group identity')
    print(f'cargo_status={status} cargo_pgid={pgid} cargo_elapsed_seconds={time.monotonic()-command_start:.3f}',flush=True)
    emit(path,True)
    reader_module,reader=_load_process_reader()
    absence=reader_module.candidate_absence(reader,RUNTIME,min(deadline,time.monotonic()+15))
    pgid_absent=0
    for _ in range(2):
        rows=reader.complete_listing(min(deadline,time.monotonic()+5))
        if any(row.get('pgid')==pgid for row in rows):
            raise RuntimeError('original command process group remains after custodian group closure')
        pgid_absent+=1
    print(f'escaped_leaf_candidate_absence={absence} original_pgid_absent_observations={pgid_absent}',flush=True)
    if status!=0: raise RuntimeError('direct Cargo measurement failed; no retry')
    return status,out.decode(errors='replace')

def run_control_only(control_case, env, deadline, source):
    """Run one finite setup/build workload and stop before the measurement path."""
    if control_case == 'setup':
        archive = RUNTIME/'setup-control.tar'
        status, _data = run_anchored_command(
            ['/usr/bin/git', '-C', str(REPO), 'archive', SOURCE_REF],
            REPO, env, archive, min(deadline, time.monotonic()+90), closure_deadline=deadline)
        if status or sha(archive) != ARCHIVE_SHA:
            raise RuntimeError('setup control archive did not match the frozen source')
        extracted = RUNTIME/'setup-control-source'
        extracted.mkdir()
        argv = ['/usr/bin/tar', '-xf', str(archive), '-C', str(extracted)]
        output = RUNTIME/'setup-control-tar.out'
    elif control_case == 'build':
        argv = cargo_build_argv('test', '--features', 'testing-environ,sys',
                                '--test', 'sys_process', '--no-run')
        output = RUNTIME/'build-control.out'
    elif control_case == 'managed':
        fixture_build = cargo_build_argv('test', '--features', 'testing-environ,sys',
            '--test', 'sys_process', '--no-run', '--message-format=json-render-diagnostics')
        fixture_log = RUNTIME/'managed-fixture-build.out'
        fixture_stderr = RUNTIME/'managed-fixture-build.stderr'
        status, data = run_anchored_command(fixture_build, source, env, fixture_log,
            min(deadline, time.monotonic()+540), stderr_path=fixture_stderr,
            closure_deadline=deadline, include_stderr=False)
        if status:
            raise RuntimeError(f'Managed fixture compile-only command failed status={status}')
        fixture = parse_managed_fixture_executable(data, RUNTIME)
        companion_source = Path(__file__).with_name('macos-managed-capture-companion.rs')
        if not companion_source.is_file():
            raise RuntimeError('Managed companion source is missing')
        examples = source/'examples'
        examples.mkdir(exist_ok=True)
        companion = examples/'macos-managed-capture-companion.rs'
        shutil.copyfile(companion_source, companion)
        companion_build = cargo_build_argv('build', '--offline',
            '--features', 'testing-environ,sys', '--example', 'macos-managed-capture-companion',
            '--message-format=json-render-diagnostics')
        companion_log = RUNTIME/'managed-companion-build.out'
        companion_stderr = RUNTIME/'managed-companion-build.stderr'
        status, data = run_anchored_command(companion_build, source, env, companion_log,
            min(deadline, time.monotonic()+540), stderr_path=companion_stderr,
            closure_deadline=deadline, include_stderr=False)
        if status:
            raise RuntimeError(f'Managed companion compile-only command failed status={status}')
        host = parse_managed_companion_executable(data, RUNTIME)
        ready = RUNTIME/'managed-host-ready.json'
        fixture_record = RUNTIME/'managed-fixture.record'
        complete = RUNTIME/'managed-host-complete'
        capture_progress = RUNTIME/'managed-capture-progress.json'
        argv = [str(host), str(fixture), str(ready), str(fixture_record),
                str(complete), str(capture_progress)]
        output = RUNTIME/'managed-host.out'
        print(f'control_case=managed control_argv={argv!r}', flush=True)
        run_anchored_command(argv, source, env, output,
            min(deadline, time.monotonic()+20), closure_deadline=deadline)
        raise RuntimeError('Managed host ended before the exact live stream readiness stop')
    else:
        raise RuntimeError('unsupported control client mode')
    print(f'control_case={control_case} control_argv={argv!r}', flush=True)
    status, _data = run_anchored_command(argv, source, env, output,
        min(deadline, time.monotonic()+540), closure_deadline=deadline)
    raise RuntimeError(f'{control_case} control workload ended before its controller stop status={status}')


def _parse_cargo_executable(output, runtime, target_name, target_kind, target_dir):
    runtime = Path(runtime).resolve()
    expected_root = (runtime/'target'/target_dir).resolve()
    matches = []
    for raw in bytes(output).splitlines():
        if not raw:
            continue
        try:
            record = json.loads(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError('Cargo artifact stream contains malformed JSON') from exc
        if record.get('reason') != 'compiler-artifact':
            continue
        target = record.get('target')
        executable = record.get('executable')
        if (type(target) is dict and target.get('name') == target_name
                and target_kind in target.get('kind', []) and type(executable) is str):
            path = Path(executable)
            if not path.is_absolute() or path.is_symlink():
                raise ValueError('Cargo artifact path is not an absolute regular file')
            resolved = path.resolve(strict=True)
            if expected_root not in resolved.parents or not resolved.is_file():
                raise ValueError('Cargo artifact escapes the private target directory')
            matches.append(resolved)
    if len(matches) != 1:
        raise ValueError(f'expected exactly one {target_name} executable artifact')
    return matches[0]


def parse_managed_fixture_executable(output, runtime):
    return _parse_cargo_executable(output, runtime, 'sys_process', 'test', 'debug/deps')


def parse_managed_companion_executable(output, runtime):
    return _parse_cargo_executable(output, runtime, 'macos-managed-capture-companion',
                                    'example', 'debug/examples')

def cargo_build_argv(operation, *arguments):
    """Build a Cargo command that must honor the frozen private lockfile."""
    if operation not in ('test', 'build'):
        raise ValueError('unsupported Cargo operation')
    return [str(CARGO), operation, '--locked', *arguments]

def cargo_source_graph_argv(source):
    """Ask stable Cargo for the locked, target-filtered package dependency tree."""
    return [str(CARGO), 'tree', '--locked', '--manifest-path',
            str(Path(source)/'Cargo.toml'), '--target', 'aarch64-apple-darwin',
            '--package', 'rhai', '--features', 'testing-environ,sys',
            '--edges', 'normal,build,dev', '--no-dedupe', '--prefix', 'none']

def cargo_metadata_graph_argv(source):
    """Read stable package target metadata; this is a target/feature superset."""
    return [str(CARGO), 'metadata', '--format-version', '1', '--locked',
            '--manifest-path', str(Path(source)/'Cargo.toml'),
            '--filter-platform', 'aarch64-apple-darwin',
            '--features', 'testing-environ,sys']

def _graph_text(value, label):
    if isinstance(value, bytes):
        try: value=value.decode('utf-8')
        except UnicodeDecodeError as exc: raise RuntimeError(f'{label} is not UTF-8') from exc
    if type(value) is not str or not value:
        raise RuntimeError(f'{label} is empty or invalid')
    return value

def validate_cargo_source_graph(tree_output, metadata_output):
    """Join Cargo's stable package tree to target metadata and the reviewed source superset.

    Cargo documents `cargo tree` as a close package/feature overview, not an
    exact compilation-unit graph. This check requests every package dependency
    kind (normal, build, and dev) while excluding feature-only display rows,
    then checks the complete reviewed build/proc-macro candidate set as a
    conservative source audit boundary. It never reports exact unit selection.
    """
    tree_text=_graph_text(tree_output, 'Cargo tree output')
    metadata_text=_graph_text(metadata_output, 'Cargo metadata output')
    packages=[]
    for line in tree_text.splitlines():
        if not line: raise RuntimeError('malformed Cargo tree package row')
        match=re.fullmatch(r'([A-Za-z0-9_-]+) v([^\s]+)((?: \([^()\n]*\))*)',line)
        if match is None: raise RuntimeError('malformed Cargo tree package row')
        packages.append((match.group(1),match.group(2)))
    selected=set(packages)
    if not selected or ('rhai','1.26.1') not in selected:
        raise RuntimeError('Cargo tree omitted the frozen Rhai package')
    try: metadata=json.loads(metadata_text)
    except (TypeError,ValueError) as exc: raise RuntimeError('Cargo metadata is invalid JSON') from exc
    package_rows=metadata.get('packages') if isinstance(metadata,dict) else None
    resolve=metadata.get('resolve') if isinstance(metadata,dict) else None
    nodes=resolve.get('nodes') if isinstance(resolve,dict) else None
    if not isinstance(package_rows,list) or not isinstance(nodes,list):
        raise RuntimeError('Cargo metadata omitted packages or resolved nodes')
    node_ids={node.get('id') for node in nodes if isinstance(node,dict)}
    if len(node_ids)!=len(nodes) or not all(type(item) is str for item in node_ids):
        raise RuntimeError('Cargo metadata has malformed resolved nodes')
    resolved_by_id={}
    for package in package_rows:
        if not isinstance(package,dict) or type(package.get('id')) is not str:
            raise RuntimeError('Cargo metadata has malformed package rows')
        if package['id'] in node_ids:
            if package['id'] in resolved_by_id:
                raise RuntimeError('Cargo metadata has duplicate resolved package identity')
            resolved_by_id[package['id']]=package
    if set(resolved_by_id)!=node_ids:
        raise RuntimeError('Cargo metadata resolution refers to missing packages')

    def candidate_kind(package):
        name,version=package.get('name'),package.get('version')
        targets=package.get('targets')
        if type(name) is not str or type(version) is not str or not isinstance(targets,list):
            raise RuntimeError('Cargo target metadata is missing or malformed')
        kinds=set()
        for target in targets:
            if not isinstance(target,dict): raise RuntimeError(f'malformed Cargo target: {name} {version}')
            target_kinds=target.get('kind')
            crate_types=target.get('crate_types')
            if not isinstance(target_kinds,list) or not all(type(kind) is str for kind in target_kinds):
                raise RuntimeError(f'malformed Cargo target kinds: {name} {version}')
            if not isinstance(crate_types,list) or not all(type(kind) is str for kind in crate_types):
                raise RuntimeError(f'malformed Cargo target crate types: {name} {version}')
            if 'custom-build' in target_kinds: kinds.add('custom-build')
            if 'proc-macro' in target_kinds or 'proc-macro' in crate_types: kinds.add('proc-macro')
        return kinds

    reviewed_superset=[]
    for package in resolved_by_id.values():
        kinds=candidate_kind(package)
        if kinds:
            key=(package['name'],package['version'])
            if key not in REVIEWED_BUILD_CANDIDATES:
                raise RuntimeError(f'unreviewed build/proc-macro candidate in metadata superset: {key[0]} {key[1]}')
            reviewed_superset.append(f'{key[0]} v{key[1]}')
    candidates=[]
    for name,version in sorted(selected):
        matching=[row for row in package_rows if isinstance(row,dict)
                  and row.get('name')==name and row.get('version')==version]
        if len(matching)!=1:
            raise RuntimeError(f'Cargo tree package is missing or ambiguous in metadata: {name} {version}')
        package=matching[0]
        if type(package.get('id')) is not str or package['id'] not in node_ids:
            raise RuntimeError(f'Cargo tree package is absent from Cargo metadata resolution: {name} {version}')
        if candidate_kind(package): candidates.append(f'{name} v{version}')
    return {'graph_kind':'stable-cargo-tree-package-superset',
            'exact_compilation_units':False,
            'target':'aarch64-apple-darwin','features':['testing-environ','sys'],
            'selected_package_count':len(selected),
            'selected_build_or_proc_macro_packages':candidates,
            'metadata_candidate_superset':sorted(reviewed_superset)}

def run_source_graph_preflight(source, env, deadline):
    """Reject package graphs outside the reviewed source candidate boundary before compile."""
    global SOURCE_GRAPH_PREFLIGHT
    commands=(('tree',cargo_source_graph_argv(source)),
              ('metadata',cargo_metadata_graph_argv(source)))
    outputs={}
    for label,argv in commands:
        if deadline-time.monotonic()<=0:
            raise TimeoutError('work deadline expired before Cargo graph preflight')
        stdout=RUNTIME/f'cargo-{label}-source-graph.out'
        stderr=RUNTIME/f'cargo-{label}-source-graph.stderr'
        status,data=run_anchored_command(argv,source,env,stdout,
            min(deadline,time.monotonic()+45),stderr_path=stderr,
            closure_deadline=deadline,monitor_resources=True,include_stderr=False)
        if status:
            diagnostic=stderr.read_text(errors='replace') if stderr.exists() else ''
            raise RuntimeError(f'Cargo {label} graph preflight failed status={status}: {diagnostic}')
        outputs[label]=data
    SOURCE_GRAPH_PREFLIGHT=validate_cargo_source_graph(outputs['tree'],outputs['metadata'])
    SOURCE_GRAPH_PREFLIGHT.update({
        'reviewed_source_baseline':'eedba0fc1ff632dce64f9fad0b1616bcf433c178',
        'reviewed_candidate_package_count':len(REVIEWED_BUILD_CANDIDATES),
        'cargo_tree_sha256':hashlib.sha256(outputs['tree']).hexdigest(),
        'cargo_metadata_sha256':hashlib.sha256(outputs['metadata']).hexdigest(),
        'limitation':'Cargo tree is an approximate package graph, not an exact compilation-unit graph; this records candidate-source coverage only.'})
    print('source_candidate_graph_preflight='+json.dumps(SOURCE_GRAPH_PREFLIGHT,sort_keys=True),flush=True)
    return SOURCE_GRAPH_PREFLIGHT

def measurement_cargo_argv():
    return cargo_build_argv(
        'test', '--features', 'testing-environ,sys', '--test', 'sys_process',
        'process_scope_overhead_measurement', '--', '--exact', '--ignored',
        '--nocapture', '--test-threads=1')

def main():
    # The gate is deliberately first: no runtime, evidence directory, version
    # query, Git/archive, Cargo, or fixture process may start before root review.
    require_launch_readiness()
    global _RPC
    sock_path=os.environ.get('RHAI_CUSTODY_SOCKET')
    if not sock_path: raise RuntimeError('missing scoped custodian RPC socket path')
    _RPC=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    _RPC.settimeout(5)
    _RPC.connect(sock_path)
    _RPC.settimeout(None)
    # Setup commands below are external children too. Any interrupted setup is
    # deliberately incomplete so the adapter retains the runtime for review.
    package_deadline=min(float(os.environ['RHAI_CUSTODY_WORK_DEADLINE']),time.monotonic()+560)
    control_case=os.environ.get('RHAI_CONTROL_CASE')
    if control_case not in (None, 'setup', 'build', 'managed'):
        raise RuntimeError('invalid or unsupported control client mode')
    if RUNTIME.is_symlink() or not RUNTIME.is_dir(): raise RuntimeError('unowned runtime path')
    if BASE.parent!=EVIDENCE or BASE.is_symlink(): raise RuntimeError('log base outside evidence directory')
    env=build_environment(RUNTIME)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    if control_case == 'setup':
        run_control_only(control_case, env, package_deadline, REPO)
        return
    verify_toolchain_identity(env, package_deadline)
    for name,p in [('cargo',CARGO),('rustc',RUSTC),('rustdoc',RUSTDOC)]:
        output=RUNTIME/f'{name}-version.out'
        args=[str(p),'--version','--verbose'] if name=='rustc' else [str(p),'--version']
        status,data=run_anchored_command(args,REPO,env,output,min(package_deadline,time.monotonic()+10),closure_deadline=package_deadline)
        if status: raise RuntimeError(f'{name} version command failed status={status}')
        v=data.decode(errors='replace').strip().replace('\n',' | ')
        print(f'{name}_path={p} {name}_version={v}',flush=True)
    hashes={}
    for name in OVERLAYS:
        output=RUNTIME/'git-show.out'
        status,data=run_anchored_command(['/usr/bin/git','-C',str(REPO),'show',f'{SOURCE_REF}:{name}'],REPO,env,output,min(package_deadline,time.monotonic()+10),closure_deadline=package_deadline)
        if status: raise RuntimeError(f'git show failed for {name} status={status}')
        hashes[name]=hashlib.sha256(data).hexdigest()
    head_out=RUNTIME/'git-head.out'
    status,data=run_anchored_command(['/usr/bin/git','-C',str(REPO),'rev-parse',SOURCE_REF],REPO,env,head_out,min(package_deadline,time.monotonic()+10),closure_deadline=package_deadline)
    if status: raise RuntimeError('git rev-parse failed')
    print('repo_head='+data.decode(errors='replace').strip(),flush=True)
    print('original_overlay_hashes='+repr(hashes),flush=True)
    wrapper=Path(__file__).with_name('run-macos-process-overhead.sh')
    adapter=Path(__file__).with_name('run-macos-process-overhead-scoped.py')
    scoped=Path('/Users/hoppworks/projects/agent-skills/tools/run_scoped.py')
    print(f'harness_sha256={sha(Path(__file__))}',flush=True)
    print(f'wrapper_sha256={sha(wrapper)}',flush=True)
    print(f'custody_adapter_sha256={sha(adapter)}',flush=True)
    print(f'shared_runner_reference_sha256={sha(scoped)}',flush=True)
    source=RUNTIME/'source'; source.mkdir()
    archive=RUNTIME/'baseline.tar'
    archive_err=RUNTIME/'git-archive.stderr'
    d=min(package_deadline,time.monotonic()+90)
    archive_status,_=run_anchored_command(['/usr/bin/git','-C',str(REPO),'archive',SOURCE_REF],REPO,env,archive,d,stderr_path=archive_err,closure_deadline=package_deadline)
    if archive_status: raise RuntimeError(f'git archive status={archive_status}: {archive_err.read_text(errors="replace")}')
    if sha(archive)!=ARCHIVE_SHA: raise RuntimeError('immutable archive hash mismatch')
    print(f'archive_sha256={sha(archive)} source_ref={SOURCE_REF}',flush=True)
    tar_out=RUNTIME/'tar-extract.out'
    tar_status,_=run_anchored_command(['/usr/bin/tar','-xf',str(archive),'-C',str(source)],source,env,tar_out,min(package_deadline,time.monotonic()+90),closure_deadline=package_deadline)
    if tar_status: raise RuntimeError('archive extraction failed')
    archive.unlink()
    private={n:sha(source/n) for n in OVERLAYS}
    if private!=hashes: raise RuntimeError('private source manifest differs from frozen source')
    print('private_overlay_hashes='+repr(private),flush=True)
    lock=REPO/'.scratch/managed-unix-scope-close/Cargo.lock.baseline'
    if sha(lock)!=LOCK_SHA: raise RuntimeError('accepted lock hash mismatch')
    plock=source/'Cargo.lock'; shutil.copy2(lock,plock); txt=plock.read_text()
    marker='name = "rhai"\nversion = "1.26.1"\ndependencies = [\n'
    if txt.count(marker)!=1: raise RuntimeError('unexpected accepted lock entry')
    a=txt.index(marker); b=txt.index('\n]',a); section=txt[a:b]
    if ' "libc",\n' not in section:
        i=section.index(' "libm",\n'); section=section[:i]+' "libc",\n'+section[i:]; plock.write_text(txt[:a]+section+txt[b:])
    if sha(plock)!='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425': raise RuntimeError('private edge-only lock hash mismatch')
    print(f'accepted_lock_sha256={sha(lock)} private_lock_sha256={sha(plock)}',flush=True)
    run_source_graph_preflight(source, env, package_deadline)
    if control_case in ('build', 'managed'):
        run_control_only(control_case, env, package_deadline, source)
        return
    print('phase=process_scope_overhead_measurement',flush=True)
    print('scope=immutable_POSIX_overhead_development_not_release',flush=True)
    print(f'runtime_path={RUNTIME}',flush=True)
    print(f'python={sys.version.replace(chr(10)," ")} platform={platform.platform()}',flush=True)
    print(f'harness_pid={os.getpid()} supervisor_pid={os.getppid()} inherited_pgid={os.getpgid(0)}',flush=True)
    measurement_dir=BASE.with_name(BASE.name+'.samples')
    parser_path=REPO/'.scratch/managed-unix-scope-close/measure-process-overhead.py'
    spec=importlib.util.spec_from_file_location('frozen_overhead_parser',parser_path)
    parser=importlib.util.module_from_spec(spec); spec.loader.exec_module(parser)
    measurement_log=BASE.with_name(BASE.name+'.cargo-output.log')
    cmd=measurement_cargo_argv()
    measurement_start=time.monotonic()
    status,out=run(cmd,measurement_log,package_deadline,env,source)
    out,samples,summary=export_measurement_output(measurement_dir,status,out,parser)
    if status!=0: raise RuntimeError('direct Cargo measurement failed; no retry')
    import json, csv, platform as _platform
    if summary['samples_total']!=120 or summary['warmups']!=0: raise RuntimeError('unexpected measurement count')
    parser.write_samples(measurement_dir/'raw-samples.csv',samples)
    rustc_out=RUNTIME/'rustc-version-final.out'
    rustc_status,rustc_bytes=run_anchored_command([str(RUSTC),'--version','--verbose'],REPO,env,rustc_out,min(package_deadline,time.monotonic()+5),closure_deadline=package_deadline)
    cargo_out=RUNTIME/'cargo-version-final.out'
    cargo_status,cargo_bytes=run_anchored_command([str(CARGO),'--version'],REPO,env,cargo_out,min(package_deadline,time.monotonic()+5),closure_deadline=package_deadline)
    if rustc_status or cargo_status: raise RuntimeError('toolchain metadata command failed')
    rustc=rustc_bytes.decode(errors='replace')
    cargo=cargo_bytes.decode(errors='replace').strip()
    metadata={**summary,'source_candidate_graph':SOURCE_GRAPH_PREFLIGHT,'os':_platform.platform(),'machine':_platform.machine(),'cargo':cargo,'rustc':rustc,'source_revision':SOURCE_REF,'source_archive_sha256':ARCHIVE_SHA,'command':cmd,'elapsed_package_seconds':time.monotonic()-measurement_start,'resource_policy':{'outer_seconds':600,'run_scoped_seconds':585,'driver_seconds':580,'cargo_seconds':540,'jobs':2,'descendants':16,'memory_policy_bytes':2*1024*1024*1024,'sampled_storage_stop_kib':LIMIT,'storage_sampling_seconds':1},'interpretation':'API-evaluation entry to completed Rhai report; excludes Engine construction and AST parsing. Spawn-to-first-byte is not exposed by this API.'}
    (measurement_dir/'summary.json').write_text(json.dumps(metadata,indent=2)+'\n')
    final={n:sha(source/n) for n in OVERLAYS}
    if final!=hashes: raise RuntimeError('final source manifest differs from frozen inputs')
    if sha(plock)!='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425': raise RuntimeError('private lock changed')
    print('final_private_overlay_hashes='+repr(final),flush=True)
    print(f'measurement_evidence={measurement_dir} samples=120 warmups=0',flush=True)
    print('measurement_check_status=passed',flush=True)
if __name__ == '__main__':
    main()
