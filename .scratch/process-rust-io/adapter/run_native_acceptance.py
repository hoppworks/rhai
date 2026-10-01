#!/usr/bin/env python3
"""Build private copies and run the fixed native Rust I/O acceptance package."""
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path
from process_identity import process_matches, process_start_identity

CASES = (
    'normal', 'cancel', 'missing-wake', 'term', 'kill',
    'stdout-4096-4096', 'stdout-4096-4097', 'stdout-0-0', 'stdout-0-1',
    'stderr-4096-4096', 'stderr-4096-4097', 'stderr-0-0', 'stderr-0-1',
)
TOPOLOGY_CASES = ('topology-cancel',)
INVOCATION_LIMIT = 600.0
BUILD_LIMIT = 300.0
CASE_LIMIT = 45.0
EXPORT_RESERVE = 10.0
MAX_PRIVATE_BYTES = 1024 * 1024 * 1024
SAMPLE_INTERVAL = 0.25


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def tree_bytes(path):
    for attempt in range(2):
        total = 0
        try:
            for item in path.rglob('*'):
                info = item.lstat()
                if stat.S_ISREG(info.st_mode):
                    total += info.st_size
            return total, bool(attempt)
        except FileNotFoundError:
            if attempt:
                raise
    raise RuntimeError('unreachable storage sampler retry state')


def args_control_uses_holder(control):
    return control in ('cancel', 'missing-wake', 'term', 'kill', 'topology-cancel') or control.endswith('-4097') or control.endswith('-0-1')


class ResourceSampler:
    """One-at-a-time ps and private-storage samples for the bounded invocation."""
    def __init__(self, runtime, export):
        self.runtime = runtime
        self.export = export
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.ps_lock = threading.Lock()
        self.samples = []
        self.children = []
        self.failure = None
        self.phase = 'source-copy'
        self.thread = threading.Thread(target=self._run, name='native-resource-sampler', daemon=True)

    def set_phase(self, phase):
        with self.lock:
            self.phase = phase

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=3)
        if self.thread.is_alive():
            raise RuntimeError('resource sampler did not stop within bounded cleanup')

    def _persist_children(self):
        path = self.export / 'sampler-children.json'
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(self.children, sort_keys=True, indent=2) + '\n')
        os.replace(temp, path)

    def _reap(self, process, child):
        """Bound shutdown and always collect the exit status from our Popen handle."""
        try:
            if process.poll() is None:
                child['terminate_requested'] = True
                process.terminate()
                try:
                    _, error = process.communicate(timeout=0.5)
                except subprocess.TimeoutExpired:
                    child['kill_requested'] = True
                    process.kill()
                    _, error = process.communicate(timeout=0.5)
            else:
                _, error = process.communicate(timeout=0.5)
            child.update({'terminal': process.poll() is not None, 'returncode': process.returncode,
                          'stderr': error[:200]})
        finally:
            self._persist_children()

    def _run(self):
        while not self.stop_event.is_set():
            started = time.monotonic()
            process = None
            ps_locked = False
            try:
                self.ps_lock.acquire()
                ps_locked = True
                process = subprocess.Popen(['/bin/ps', '-axo', 'pid=,ppid=,pgid=,lstart='],
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                child = {'pid': process.pid, 'terminal': False, 'terminate_requested': False,
                         'kill_requested': False}
                self.children.append(child)
                self._persist_children()
                output, error = process.communicate(timeout=2)
                child.update({'terminal': True, 'returncode': process.returncode,
                              'stderr': error[:200]})
                self._persist_children()
                self.ps_lock.release()
                ps_locked = False
                if process.returncode != 0:
                    raise RuntimeError('ps sampler failed: ' + error[:200])
                rows = []
                for line in output.splitlines():
                    fields = line.strip().split(None, 3)
                    if len(fields) == 4:
                        try:
                            rows.append({'pid': int(fields[0]), 'ppid': int(fields[1]),
                                         'pgid': int(fields[2]), 'lstart': fields[3]})
                        except ValueError:
                            raise RuntimeError('ps sampler returned malformed process identity')
                driver_pid = os.getpid()
                known = {row['pid']: row for row in rows}
                descendants = set()
                changed = True
                while changed:
                    changed = False
                    parents = descendants | {driver_pid}
                    for row in rows:
                        if row['ppid'] in parents and row['pid'] not in descendants:
                            descendants.add(row['pid'])
                            changed = True
                # ps may omit its own transient row; count its known live sampler slot once.
                owned_rows = [known[pid] for pid in sorted(descendants) if pid in known and pid != process.pid]
                with self.lock:
                    phase = self.phase
                controller_slot = 1 if phase.startswith('case:') else 0
                owned_count = controller_slot + len(owned_rows) + 1
                private_bytes, storage_retried = tree_bytes(self.runtime)
                sample = {'elapsed_seconds': round(time.monotonic() - started, 4),
                          'phase': phase, 'private_bytes': private_bytes,
                          'storage_retry_used': storage_retried,
                          'owned_processes_including_sampler': owned_count,
                          'process_limit': 8, 'sampler_pid': process.pid,
                          'owned_process_identities': owned_rows}
                with self.lock:
                    self.samples.append(sample)
                    if owned_count > 8 or private_bytes > MAX_PRIVATE_BYTES:
                        self.failure = 'sampled process or private-storage cap exceeded'
                        self.stop_event.set()
            except BaseException as exc:
                if process is not None:
                    try:
                        self._reap(process, child)
                    except BaseException as reap_exc:
                        child.update({'terminal': False, 'reap_error': repr(reap_exc)})
                        self._persist_children()
                if ps_locked:
                    self.ps_lock.release()
                with self.lock:
                    self.failure = 'resource sample unknown: ' + repr(exc)
                self.stop_event.set()
            self.stop_event.wait(max(0.0, SAMPLE_INTERVAL - (time.monotonic() - started)))

    def snapshot(self):
        with self.lock:
            return list(self.samples), self.failure

    def finalizer_ps(self):
        with self.ps_lock:
            return subprocess.run(['/bin/ps', '-axo', 'pid=,ppid=,pgid=,lstart='],
                                  capture_output=True, text=True, timeout=2, check=True).stdout


def copy_sources(repo, private):
    process_src = repo / '.scratch/process-rust-io'
    fixture_src = repo / '.scratch/process-prototype'
    rust = private / 'process-rust-io'
    fixture = private / 'process-prototype'
    shutil.copytree(process_src / 'src', rust / 'src')
    shutil.copy2(process_src / 'Cargo.toml', rust / 'Cargo.toml')
    shutil.copytree(process_src / 'adapter', rust / 'adapter',
                    ignore=shutil.ignore_patterns('runs', 'evidence', '__pycache__'))
    shutil.copytree(fixture_src / 'src', fixture / 'src')
    shutil.copy2(fixture_src / 'Cargo.toml', fixture / 'Cargo.toml')
    return rust, fixture


def record(ledger, export):
    path = export / 'run-ledger.json'
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(ledger, sort_keys=True, indent=2) + '\n')
    os.replace(temp, path)


def capture_lockfiles(rust, fixture, export, ledger):
    captured = []
    for name, origin in (('native-Cargo.lock', rust / 'Cargo.lock'),
                         ('fixture-Cargo.lock', fixture / 'Cargo.lock')):
        if origin.is_file():
            destination = export / name
            shutil.copy2(origin, destination)
            captured.append({'name': name, 'bytes': destination.stat().st_size,
                             'sha256': digest(destination)})
    ledger['resolved_lockfiles'] = captured
    record(ledger, export)


def bounded_process(command, cwd, env, operation_deadline, log_path, label,
                    ledger, sampler, ledger_key, phase, identity_required=True):
    _, sample_failure = sampler.snapshot()
    if sample_failure:
        raise RuntimeError(sample_failure)
    remaining = operation_deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('shared build budget exhausted before ' + label)
    started = time.monotonic()
    sampler.set_phase(phase + ':' + label)
    try:
        process = subprocess.Popen(command, env=env, cwd=cwd,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except BaseException as exc:
        output = repr(exc).encode()
        log_path.write_bytes(output)
        ledger.setdefault(ledger_key, []).append({'name': label, 'pid': None,
            'start_identity': None, 'launch_error': repr(exc), 'status': None,
            'output_complete': True, 'log': log_path.name, 'log_sha256': digest(log_path)})
        record(ledger, log_path.parent)
        raise
    try:
        identity = process_start_identity(process.pid) if identity_required else None
    except BaseException:
        try:
            output, _ = process.communicate(timeout=0.1)
            status = process.returncode
            complete = True
        except subprocess.TimeoutExpired as exc:
            output, status, complete = exc.output or b'', None, False
        log_path.write_bytes(output)
        ledger.setdefault(ledger_key, []).append({'name': label, 'pid': process.pid,
            'start_identity': None, 'identity_error': 'proc_pidinfo failed',
            'identity_scope': ('direct Popen handle + bounded communicate/reap'
                               if not identity_required else None),
            'status': status, 'output_complete': complete, 'log': log_path.name,
            'log_sha256': digest(log_path)})
        record(ledger, log_path.parent)
        raise
    stop_reason = None
    while True:
        try:
            output, _ = process.communicate(timeout=min(0.25, max(0.01, operation_deadline-time.monotonic())))
            break
        except subprocess.TimeoutExpired as exc:
            _, sample_failure = sampler.snapshot()
            if sample_failure:
                stop_reason = sample_failure
            elif time.monotonic() >= operation_deadline:
                stop_reason = f'private operation {label} exceeded shared build budget'
            if stop_reason:
                output = exc.output or b''
                break
    status = process.poll()
    elapsed = time.monotonic() - started
    log_path.write_bytes(output)
    ledger.setdefault(ledger_key, []).append({'name': label, 'pid': process.pid,
        'start_identity': identity, 'status': status if status is not None else 'scoped-owner-pending',
        'identity_scope': ('direct Popen handle + bounded communicate/reap'
                           if not identity_required else 'PID/start identity captured immediately'),
        'output_complete': status is not None, 'seconds': round(elapsed, 3),
        'timed_out': stop_reason is not None, 'stop_reason': stop_reason,
        'log': log_path.name, 'log_sha256': digest(log_path)})
    record(ledger, log_path.parent)
    if stop_reason:
        process.stdout.close()
        raise RuntimeError(stop_reason)
    if status is None or status != 0:
        raise RuntimeError(f'private operation {label} failed status={status} elapsed={elapsed:.3f}s')
    _, sample_failure = sampler.snapshot()
    if sample_failure:
        raise RuntimeError(sample_failure)
    return output


def build(manifest, env, build_deadline, export, label, ledger, sampler, cargo):
    return bounded_process([str(cargo), 'build', '--manifest-path', str(manifest)],
                           manifest.parent, env, build_deadline,
                           export / (label + '-build.log'), label, ledger, sampler,
                           'builds', 'build')


def export_failure(source, export):
    for name in ('evidence', 'runs'):
        origin = source / name
        if origin.exists():
            destination = export / ('incomplete-' + name)
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(origin, destination, symlinks=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--topology-only', action='store_true')
    args = parser.parse_args()
    cases = TOPOLOGY_CASES if args.topology_only else CASES
    repo = args.source_root.resolve(strict=True)
    runtime = Path(os.environ['AGENT_RUNTIME_DIR']).resolve(strict=True)
    started = time.monotonic()
    deadline = started + INVOCATION_LIMIT
    build_deadline = started + BUILD_LIMIT
    private = runtime / 'private-source'
    private.mkdir()
    export = repo / '.scratch/process-rust-io/evidence/native-linux-workload-topology-attempt3-20261001-0729UTC'
    export.mkdir(parents=True, exist_ok=False)
    parent_pid = os.getppid()
    supervisor_pid = parent_pid
    custody = {
        'runtime_path': str(runtime),
        'driver': {'pid': os.getpid(), 'start_identity': process_start_identity(os.getpid()),
                   'parent_pid': parent_pid, 'parent_start_identity': process_start_identity(parent_pid)},
        'supervisor': {'pid': supervisor_pid,
                       'start_identity': process_start_identity(supervisor_pid),
                       'pgid': os.getpgid(supervisor_pid)},
        'sampler_children': 'see sampler-children.json; PIDs captured from direct Popen handles and terminal outcomes recorded after communicate/reap'}
    custody_path = export / 'custody.json'
    custody_path.write_text(json.dumps(custody, sort_keys=True, indent=2) + '\n')
    (export / 'sampler-children.json').write_text('[]\n')
    (runtime / 'cargo-home').mkdir()
    (runtime / 'rustup-home').mkdir()
    (runtime / 'target').mkdir()
    rust, fixture = copy_sources(repo, private)
    env = dict(os.environ)
    env.update(CARGO_HOME=str(runtime / 'cargo-home'),
               RUSTUP_HOME=str(runtime / 'rustup-home'),
               CARGO_TARGET_DIR=str(runtime / 'target'),
               CARGO_BUILD_JOBS='2', CARGO_INCREMENTAL='0',
               CARGO_PROFILE_DEV_DEBUG='0')
    for inherited in ('RUSTC', 'RUSTDOC', 'RUSTC_WRAPPER',
                      'RUSTC_WORKSPACE_WRAPPER', 'CARGO_HOME_CONFIG',
                      'RUSTUP_TOOLCHAIN'):
        env.pop(inherited, None)
    ledger = {'cases': [], 'case_order': list(cases), 'limits': {
        'invocation_seconds': INVOCATION_LIMIT, 'build_seconds': BUILD_LIMIT,
        'case_seconds': CASE_LIMIT, 'export_reserve_seconds': EXPORT_RESERVE,
        'private_bytes': MAX_PRIVATE_BYTES, 'cargo_jobs': 2,
        'process_resources': 8, 'rust_workers': 3, 'rust_fds': 32,
        'stream_bytes': 2 * 1024 * 1024,
        'owned_fixture_process_scope': 'controller + custodian + runner + leader + anchor + sentinel + optional holder; driver/supervisor excluded',
        'owned_fixture_process_bound': 7, 'sampler_process_bound': 1,
        'owned_fixture_process_limit': 8,
        'sampler': 'one live ps/storage sampler at a time, every 250ms; fixture and sampler bound <=8',
        'process_peak_method': 'sampled owned PID/PPID/PGID/lstart graph; sampled maximum only, no continuous-peak claim',
        'rust_fd_method': 'RLIMIT_NOFILE=32 enforced in Rust; three worker handles checked at native_done'}}
    ledger['driver'] = {'pid': os.getpid(), 'start_identity': process_start_identity(os.getpid()),
                        'parent_pid': os.getppid(), 'parent_start_identity': process_start_identity(os.getppid())}
    sampler = ResourceSampler(runtime, export)
    controller_path = rust / 'adapter/controller.py'
    spec = importlib.util.spec_from_file_location('native_controller', controller_path)
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    try:
        ledger['storage_observations'] = []
        sampler.start()
        if sys.platform == 'darwin':
            rustup = Path('/Users/hoppworks/.cargo/bin/rustup')
            rust_target = '1.77.2-aarch64-apple-darwin'
        elif sys.platform.startswith('linux') and platform.machine() == 'x86_64':
            rustup = Path('/root/.cargo/bin/rustup')
            rust_target = '1.77.2-x86_64-unknown-linux-gnu'
        else:
            raise RuntimeError(f'unsupported native acceptance host: {sys.platform}/{platform.machine()}')
        bounded_process([str(rustup), 'toolchain', 'install', '1.77.2',
                         '--profile', 'minimal', '--no-self-update'],
                        repo, env, build_deadline, export / 'rustup-install.log',
                        'rustup-install-1.77.2', ledger, sampler, 'setup', 'toolchain-install')
        toolchain_bin = runtime / 'rustup-home' / 'toolchains' / rust_target / 'bin'
        rustc = toolchain_bin / 'rustc'
        cargo = toolchain_bin / 'cargo'
        rustdoc = toolchain_bin / 'rustdoc'
        for name, binary, expected in (('rustc', rustc, 'rustc 1.77.2'),
                                       ('cargo', cargo, 'cargo 1.77.2'),
                                       ('rustdoc', rustdoc, 'rustdoc 1.77.2')):
            version = bounded_process([str(binary), '--version'], repo, env,
                build_deadline, export / (name + '-version.log'), name + '-version',
                ledger, sampler, 'setup', 'toolchain-verify', identity_required=False)
            tokens = version.decode(errors='replace').strip().split()
            if tokens[:2] != expected.split():
                raise RuntimeError(f'private {name} version mismatch: {version!r}')
        env['RUSTC'] = str(rustc)
        env['RUSTDOC'] = str(rustdoc)
        env['PATH'] = str(toolchain_bin) + os.pathsep + env.get('PATH', '')
        ledger['toolchain'] = {'version': '1.77.2', 'rustc': str(rustc),
            'cargo': str(cargo), 'rustdoc': str(rustdoc),
            'verified_versions': {'rustc': '1.77.2', 'cargo': '1.77.2', 'rustdoc': '1.77.2'},
            'private_rustup_home': str(runtime / 'rustup-home'),
            'private_cargo_home': str(runtime / 'cargo-home')}
        record(ledger, export)
        build(rust / 'Cargo.toml', env, build_deadline, export, 'native-rust', ledger, sampler, cargo)
        capture_lockfiles(rust, fixture, export, ledger)
        native_storage, native_retry = tree_bytes(runtime)
        ledger['storage_observations'].append({'phase': 'after-native-build', 'bytes': native_storage,
                                               'retry_used': native_retry,
                                               'limit_bytes': MAX_PRIVATE_BYTES})
        if ledger['storage_observations'][-1]['bytes'] > MAX_PRIVATE_BYTES:
            raise RuntimeError('private build/runtime storage exceeded 1 GiB after native build')
        build(fixture / 'Cargo.toml', env, build_deadline, export, 'fixture', ledger, sampler, cargo)
        capture_lockfiles(rust, fixture, export, ledger)
        if len(ledger.get('resolved_lockfiles', [])) != 2:
            raise RuntimeError('both Cargo.lock files must be resolved and exported')
        fixture_storage, fixture_retry = tree_bytes(runtime)
        ledger['storage_observations'].append({'phase': 'after-fixture-build', 'bytes': fixture_storage,
                                               'retry_used': fixture_retry,
                                               'limit_bytes': MAX_PRIVATE_BYTES})
        if ledger['storage_observations'][-1]['bytes'] > MAX_PRIVATE_BYTES:
            raise RuntimeError('private build/runtime storage exceeded 1 GiB after fixture build')
        native_runner = runtime / 'target/debug/process-rust-io-acceptance'
        fixture_binary = runtime / 'target/debug/process-prototype'
        if not native_runner.is_file() or not fixture_binary.is_file():
            raise RuntimeError('expected private build outputs are missing')
        ledger['binaries'] = [
            {'manifest': 'process-rust-io/Cargo.toml', 'binary_sha256': digest(native_runner)},
            {'manifest': 'process-prototype/Cargo.toml', 'binary_sha256': digest(fixture_binary)}]
        for index, case in enumerate(cases):
            _, sample_failure = sampler.snapshot()
            if sample_failure:
                raise RuntimeError(sample_failure)
            remaining = deadline - time.monotonic()
            if remaining < CASE_LIMIT + EXPORT_RESERVE:
                raise TimeoutError(f'insufficient full case/export reserve before {case}: {remaining:.3f}s')
            storage_before, storage_retry = tree_bytes(runtime)
            ledger['storage_observations'].append({'phase': 'before-' + case, 'bytes': storage_before,
                                                   'retry_used': storage_retry,
                                                   'limit_bytes': MAX_PRIVATE_BYTES})
            if storage_before > MAX_PRIVATE_BYTES:
                raise RuntimeError('private build/runtime storage exceeded 1 GiB before case')
            sampler.set_phase('case:' + case)
            case_started = time.monotonic()
            status = controller.main(['--binary', str(fixture_binary),
                                      '--native-runner', str(native_runner), '--control', case])
            elapsed = time.monotonic() - case_started
            _, sample_failure = sampler.snapshot()
            if sample_failure:
                raise RuntimeError(sample_failure)
            if elapsed > CASE_LIMIT or status != 0:
                raise RuntimeError(f'case {case} failed status={status} elapsed={elapsed:.3f}s')
            evidence = rust / 'evidence'
            matches = sorted(evidence.glob(f'custodian-*-{case}.json'))
            if len(matches) != 1:
                raise RuntimeError(f'case {case} produced {len(matches)} completion receipts')
            out = export / matches[0].name
            shutil.copy2(matches[0], out)
            if digest(matches[0]) != digest(out):
                raise RuntimeError(f'case {case} export readback mismatch')
            receipt_data = json.loads(matches[0].read_text())
            if case == 'topology-cancel':
                topology_check_path = rust / 'adapter/test_workload_topology_receipt.py'
                topology_spec = importlib.util.spec_from_file_location(
                    'workload_topology_receipt_check', topology_check_path)
                topology_check = importlib.util.module_from_spec(topology_spec)
                topology_spec.loader.exec_module(topology_check)
                topology_check.assert_workload_topology(receipt_data)
                ledger.setdefault('receipt_assertions', {})[case] = 'workload-topology-v1 accepted'
            controller_identity = receipt_data.get('controller', {})
            if (controller_identity.get('pid') != ledger['driver']['pid']
                    or controller_identity.get('start_identity') != ledger['driver']['start_identity']
                    or not process_matches(controller_identity['pid'], controller_identity['start_identity'])):
                raise RuntimeError(f'controller/driver identity differs for {case}')
            identities = [{'role': 'controller-driver', 'pid': controller_identity['pid'],
                           'start_identity': controller_identity['start_identity'],
                           'still_same_process': True, 'expected_live': True}]
            required_roles = {'runner', 'leader', 'anchor', 'sentinel'}
            child_records = receipt_data.get('children', {})
            if args_control_uses_holder(case):
                required_roles.add('holder')
            for role in sorted(required_roles):
                if not isinstance(child_records.get(role), dict):
                    raise RuntimeError(f'post-terminal finalizer lacks required {role} receipt for {case}')
            for role, item in [('custodian', receipt_data.get('custodian', {})),
                                *[(role, v) for role, v in child_records.items() if isinstance(v, dict)]]:
                pid, start_id = item.get('pid'), item.get('start_identity')
                if not isinstance(pid, int) or not isinstance(start_id, list):
                    raise RuntimeError(f'post-terminal finalizer lacks {role} PID/start identity for {case}')
                identities.append({'role': role, 'pid': pid, 'start_identity': start_id,
                                   'still_same_process': process_matches(pid, start_id),
                                   'expected_live': False})
            if any(entry['still_same_process'] for entry in identities if not entry['expected_live']):
                raise RuntimeError(f'post-terminal exact-process finalizer found live original PID for {case}')
            ps = sampler.finalizer_ps()
            finalizer_path = export / ('finalizer-' + case + '.json')
            finalizer = {'case': case, 'terminal_receipt_sha256': digest(matches[0]),
                         'original_process_identities': identities,
                         'ps_snapshot': ps.splitlines(),
                         'sample_scope': 'single post-terminal system snapshot serialized with live sampler'}
            finalizer_path.write_text(json.dumps(finalizer, sort_keys=True, indent=2) + '\n')
            ledger['cases'].append({'index': index + 1, 'control': case,
                                    'seconds': round(elapsed, 3),
                                    'receipt': out.name, 'sha256': digest(out),
                                    'finalizer': finalizer_path.name,
                                    'finalizer_sha256': digest(finalizer_path)})
            case_storage, case_retry = tree_bytes(runtime)
            ledger['storage_observations'].append({'phase': 'after-' + case, 'bytes': case_storage,
                                                   'retry_used': case_retry,
                                                   'limit_bytes': MAX_PRIVATE_BYTES})
            if ledger['storage_observations'][-1]['bytes'] > MAX_PRIVATE_BYTES:
                raise RuntimeError(f'private build/runtime storage exceeded 1 GiB after {case}')
            record(ledger, export)
        if tuple(item['control'] for item in ledger['cases']) != cases:
            raise RuntimeError('fixed native case ledger order mismatch')
        sampler.stop()
        samples, sample_failure = sampler.snapshot()
        ledger['resource_samples'] = samples
        ledger['sampled_private_bytes_max'] = max((s['private_bytes'] for s in samples), default=0)
        ledger['sampled_process_max'] = max((s['owned_processes_including_sampler'] for s in samples), default=0)
        ledger['sampler_failure'] = sample_failure
        if sample_failure:
            raise RuntimeError(sample_failure)
        record(ledger, export)
        return 0
    except BaseException as exc:
        if sampler.thread.is_alive():
            sampler.stop()
        samples, sample_failure = sampler.snapshot()
        ledger['resource_samples'] = samples
        ledger['sampled_private_bytes_max'] = max((s['private_bytes'] for s in samples), default=0)
        ledger['sampled_process_max'] = max((s['owned_processes_including_sampler'] for s in samples), default=0)
        ledger['sampler_failure'] = sample_failure
        ledger['failure'] = repr(exc)
        ledger['elapsed_seconds'] = round(time.monotonic() - started, 3)
        capture_lockfiles(rust, fixture, export, ledger)
        export_failure(rust, export)
        path = export / 'run-ledger.json'
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(ledger, sort_keys=True, indent=2) + '\n')
        os.replace(temp, path)
        raise


if __name__ == '__main__':
    try:
        status = main()
    except BaseException as exc:
        print(f'native acceptance stopped: {exc!r}', file=sys.stderr)
        status = 1
    sys.exit(status)
