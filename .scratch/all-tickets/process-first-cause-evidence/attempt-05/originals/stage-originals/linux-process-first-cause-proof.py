#!/usr/bin/env python3
"""Bounded six-command Linux proof, adapted from the accepted overlap producer."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
import signal
import shutil
import sys
import time
from pathlib import Path

STAGE_PATH = Path('/root/rhai-linux-process-first-cause-fc-20261007-ack05-7d11e2c4')
SCOPE_PATH = Path('/root/.local/share/agent-builds/rhai/fc-20261007-ack05-7d11e2c4')
SOURCE_REL = 'src/packages/sys/process/unix.rs'
TESTS = {
    'direct': 'packages::sys::process::unix::tests::committed_stdout_cause_survives_stderr_overflow_direct_child',
    'managed': 'packages::sys::process::unix::tests::committed_stdout_cause_survives_stderr_overflow_managed',
}
EXPECTED_ARGV = [
    '/usr/bin/python3',
    '-c',
    "exec(open(__import__('os').environ['RHAI_FIRST_SCRIPT']).read())",
]
ASSERTION = 'the first committed stdout overflow must remain the public cause'
PATCH = Path(__file__).with_name('preserve-primary-cause.patch')
BASE = None
CASE_LEDGER = []
FIXTURE_ROWS = []
REQUIRED_EXPORT_RECEIPTS = {
    'package-result.json', 'source-inputs.json', 'source-restoration.json',
    'commands.json', 'control-results.json', 'fixture-identities.tsv',
    'process-identities.tsv', 'early-runtime-identity.json', 'tool-versions.json',
    'sampled-maxima.json', 'resource-samples.jsonl', 'export-budget.json',
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_base(path: Path):
    spec = importlib.util.spec_from_file_location('first_cause_accepted_base', path)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load accepted scoped-runner base')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def apply_patch_bytes(original: bytes) -> bytes:
    """Apply the exact single source hunk in the separately pinned patch artifact."""
    patch = PATCH.read_text(encoding='utf-8').splitlines()
    if patch[:4] != [
        'diff --git a/src/packages/sys/process/unix.rs b/src/packages/sys/process/unix.rs',
        'index 81b7f171c..d240657cb 100644',
        '--- a/src/packages/sys/process/unix.rs',
        '+++ b/src/packages/sys/process/unix.rs',
    ]:
        raise RuntimeError('proposed patch file identity/path differs from reviewed artifact')
    hunks = [i for i, line in enumerate(patch) if line.startswith('@@ ')]
    if len(hunks) != 1:
        raise RuntimeError('proposed patch must contain exactly one source hunk')
    hunk = patch[hunks[0] + 1:]
    old_lines = [line[1:] for line in hunk if line.startswith((' ', '-'))]
    new_lines = [line[1:] for line in hunk if line.startswith((' ', '+'))]
    if not old_lines or not new_lines:
        raise RuntimeError('proposed patch source hunk is empty')
    old = ('\n'.join(old_lines) + '\n').encode()
    new = ('\n'.join(new_lines) + '\n').encode()
    if original.count(old) != 1:
        raise RuntimeError('proposed patch hunk does not uniquely match frozen source bytes')
    return original.replace(old, new, 1)


def overwrite_stderr_guard(source: Path) -> tuple[bytes, bytes]:
    original = source.read_bytes()
    text = original.decode('utf-8')
    start = text.index('if !owner.capture_closed && !state.stderr_complete')
    end = text.index('if !owner.capture_closed\n        && owner', start)
    block = text[start:end]
    old = '''                if state.error.is_none() {\n                    state.error = Some(ProcessCause::OutputLimit(format!(\n                        "stderr for `{}` exceeded max_output of {} bytes",\n                        state.program, state.limit\n                    )));\n                }\n'''
    new = '''                state.error = Some(ProcessCause::OutputLimit(format!(\n                    "stderr for `{}` exceeded max_output of {} bytes",\n                    state.program, state.limit\n                )));\n'''
    if block.count(old) != 1:
        raise RuntimeError('stderr Overflow guard anchor is missing or ambiguous')
    changed = text[:start] + block.replace(old, new, 1) + text[end:]
    return original, changed.encode('utf-8')


def verify_input_manifest(stage: Path) -> None:
    manifest = stage / 'input-identities.sha256'
    if not manifest.is_file() or manifest.is_symlink():
        raise RuntimeError('frozen package input identity manifest is absent')
    expected = {}
    for line in manifest.read_text(encoding='ascii').splitlines():
        digest, name = line.split(None, 1)
        if name in expected or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise RuntimeError('malformed/duplicate input identity line')
        expected[name] = digest
    required = {'source.tar', 'Cargo.lock.accepted', 'archive-build-source.py',
                'check-linux-current-msrv-examples.py', 'linux-process-first-cause-proof.py',
                'fixture-adapter.patch', 'preserve-primary-cause.patch', 'contract.md',
                'runner/tools/run_scoped.py', 'runner/tools/agentskills/__init__.py',
                'runner/tools/agentskills/pyguard.py'}
    if not required.issubset(expected):
        raise RuntimeError('input identity manifest omits a required producer/consumer input')
    for name, digest in expected.items():
        path = stage / name
        if path.is_symlink() or not path.is_file() or sha(path) != digest:
            raise RuntimeError(f'frozen input identity mismatch: {name}')


def parse_fixture_receipt(raw: str, mode: str, case: str) -> dict[str, str]:
    marker = f'first-cause mode={mode} '
    lines = [line for line in raw.splitlines() if marker in line]
    if len(lines) != 1 or sum(line.count(marker) for line in lines) != 1:
        raise RuntimeError(f'{case} requires exactly one raw child receipt')
    prefix = f'test {TESTS[mode]} ... {marker}'
    if not lines[0].startswith(prefix):
        raise RuntimeError(f'{case} child receipt is not attached to its exact selected test')
    receipt = marker + lines[0].split(marker, 1)[1]
    fields = dict(part.split('=', 1) for part in receipt.split()[1:])
    required = ('child_pid', 'child_start_ticks', 'child_pgid', 'expected_program',
                'expected_argv_count', 'child_cmdline_hex', 'identity_confirmed',
                'identity_gate_released', 'identity_wait', 'stdout_write',
                'stdout_committed', 'stderr_write', 'stderr_overflow', 'reap', 'group_closed')
    if any(key not in fields for key in required):
        raise RuntimeError(f'{case} child receipt is incomplete')
    if fields['expected_program'] != '/usr/bin/python3' or fields['expected_argv_count'] != '3':
        raise RuntimeError(f'{case} checked spawn command description changed')
    if (fields['identity_confirmed'], fields['identity_gate_released'], fields['identity_wait']) != (
            'true', 'true', 'acknowledged'):
        raise RuntimeError(f'{case} live child identity was not independently acknowledged')
    if not all(fields[key].isdecimal() and int(fields[key]) > 0
               for key in ('child_pid', 'child_start_ticks', 'child_pgid')):
        raise RuntimeError(f'{case} child identity values are malformed')
    try:
        observed = bytes.fromhex(fields['child_cmdline_hex']).split(b'\0')
    except ValueError as exc:
        raise RuntimeError(f'{case} observed child cmdline is not valid hexadecimal') from exc
    expected = [argument.encode() for argument in EXPECTED_ARGV] + [b'']
    if observed != expected:
        raise RuntimeError(f'{case} observed child argv differs from the exact checked spawn vector')
    if (fields['stdout_write'], fields['stdout_committed'], fields['stderr_write'],
            fields['stderr_overflow'], fields['reap']) != (
            'acknowledged', 'true', 'acknowledged', 'observed', 'ESRCH'):
        raise RuntimeError(f'{case} child lifecycle receipt is incomplete')
    if fields['group_closed'] != ('true' if mode == 'managed' else 'false'):
        raise RuntimeError(f'{case} group-closure receipt does not match ProcessScope')
    return fields


def selected_test_status(stdout: str, mode: str, expected: str) -> bool:
    prefix = f'test {TESTS[mode]} ... '
    lines = stdout.splitlines()
    matches = [(index, line[len(prefix):]) for index, line in enumerate(lines)
               if line.startswith(prefix)]
    if len(matches) != 1:
        return False
    index, suffix = matches[0]
    if suffix == expected:
        return True
    return (suffix.startswith(f'first-cause mode={mode} ')
            and index + 1 < len(lines) and lines[index + 1] == expected)


def write_fixture_ledger() -> None:
    header = ('case\tpid\tstart_ticks\tpgid\texpected_argv\tobserved_cmdline_hex\t'
              'identity_confirmed\tidentity_gate_released\tidentity_wait\t'
              'stdout_write\tstdout_committed\tstderr_write\tstderr_overflow\t'
              'reap\tgroup_closed\n')
    path = BASE.STAGE / 'fixture-identities.tsv'
    path.write_text(header + ''.join('\t'.join(row[key] for key in (
        'case', 'pid', 'start_ticks', 'pgid', 'expected_argv', 'observed_cmdline_hex',
        'identity_confirmed', 'identity_gate_released', 'identity_wait', 'stdout_write',
        'stdout_committed', 'stderr_write', 'stderr_overflow', 'reap', 'group_closed')) + '\n' for row in FIXTURE_ROWS), encoding='utf-8')


def preserve_partial_evidence(stage: Path, destination: Path, *, check_deadline,
                              destination_is_safe, final_item_name: str | None = None,
                              prepare_final_item=None) -> None:
    """Copy available evidence idempotently while preserving partial exports on failure."""
    if not destination_is_safe() or destination.is_symlink():
        raise RuntimeError('partial evidence destination identity is unsafe')
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    items = sorted(stage.rglob('*'))
    if final_item_name is not None:
        finals = [item for item in items if item.relative_to(stage).as_posix() == final_item_name]
        if len(finals) != 1 or not finals[0].is_file() or finals[0].is_symlink():
            raise RuntimeError('required final evidence item is absent, non-regular, or ambiguous')
        items = [item for item in items if item != finals[0]] + finals
    for item in items:
        check_deadline(during_export=True)
        if item.is_symlink():
            raise RuntimeError(f'refusing symlink in partial evidence: {item}')
        relative = item.relative_to(stage)
        target = destination / relative
        if item.is_dir():
            if target.is_symlink():
                raise RuntimeError(f'refusing destination symlink: {relative}')
            target.mkdir(mode=0o700, parents=True, exist_ok=True)
        elif item.is_file():
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            if target.is_symlink():
                raise RuntimeError(f'refusing destination symlink: {relative}')
            if final_item_name is not None and relative.as_posix() == final_item_name and prepare_final_item:
                prepare_final_item(item)
                check_deadline(during_export=True)
            if target.exists():
                if target.is_symlink() or target.read_bytes() != item.read_bytes():
                    raise RuntimeError(f'conflicting partial evidence file: {relative}')
            else:
                shutil.copy2(item, target)
            check_deadline(during_export=True)


def write_resource_evidence(base, stage: Path) -> None:
    """Write the accepted runner's resource samples into the first-cause receipt set."""
    base.write_json(stage / 'sampled-maxima.json', {
        'maxima': base.MAXIMA, 'sample_count': len(base.SAMPLES),
        'samples_are_periodic_not_continuous_peak': True,
        'storage_preemptive_stop_kib': base.PREEMPTIVE_STORAGE_KIB,
        'storage_hard_stop_kib': base.HARD_STORAGE_KIB,
        'rss_hard_stop_kib': base.HARD_RSS_KIB,
        'descendant_hard_stop': base.MAX_DESCENDANTS,
    })
    (stage / 'resource-samples.jsonl').write_text(
        ''.join(json.dumps(row, sort_keys=True) + '\n' for row in base.SAMPLES),
        encoding='utf-8')


def validate_export_receipt_set(stage: Path, *, require_complete: bool = True) -> None:
    if not require_complete:
        budget = stage / 'export-budget.json'
        if not budget.is_file() or budget.is_symlink():
            raise RuntimeError('partial first-cause export is missing its bounded export receipt')
        return
    missing = sorted(name for name in REQUIRED_EXPORT_RECEIPTS
                     if not (stage / name).is_file() or (stage / name).is_symlink())
    if missing:
        raise RuntimeError(f'first-cause export is missing required receipts: {missing!r}')


def export_package_evidence(*, require_complete: bool) -> None:
    """Export finalized receipts once, with the bounded export receipt copied last."""
    export_started = time.monotonic() - BASE.START
    write_resource_evidence(BASE, BASE.STAGE)
    BASE.write_json(BASE.STAGE / 'export.json', {
        'runtime': str(BASE.RUNTIME), 'expected_outer_scope': str(BASE.RUNTIME.parent),
        'evidence_destination': str(BASE.EVIDENCE),
        'elapsed_seconds_at_export': round(export_started, 3),
        'helper_deadline_seconds': 540, 'helper_work_deadline_seconds': 510,
        'export_deadline_checks_between_items': True,
        'individual_copy_operations_preemptible': False,
        'partial_evidence_may_remain_if_export_fails': True,
        'runtime_cleanup_owner': 'run_scoped.py; coordinator must independently read back',
    })
    BASE.write_json(BASE.STAGE / 'export-budget.json', {
        'elapsed_seconds_at_export_start': round(export_started, 3),
        'elapsed_seconds_before_budget_receipt_copy': None,
        'helper_deadline_seconds': 540, 'helper_work_deadline_seconds': 510,
        'deadline_checked_at_entry_between_items_and_after': True,
        'individual_copy_operations_preemptible': False,
        'deadline_checked_immediately_before_and_after_budget_receipt_copy': True,
    })
    validate_export_receipt_set(BASE.STAGE, require_complete=require_complete)

    def prepare_budget_receipt(_path: Path) -> None:
        BASE.write_json(BASE.STAGE / 'export-budget.json', {
            'elapsed_seconds_at_export_start': round(export_started, 3),
            'elapsed_seconds_before_budget_receipt_copy': round(time.monotonic() - BASE.START, 3),
            'helper_deadline_seconds': 540, 'helper_work_deadline_seconds': 510,
            'deadline_checked_at_entry_between_items_and_after': True,
            'individual_copy_operations_preemptible': False,
            'deadline_checked_immediately_before_and_after_budget_receipt_copy': True,
        })

    preserve_partial_evidence(
        BASE.STAGE, BASE.EVIDENCE,
        check_deadline=BASE.check_deadline,
        destination_is_safe=BASE.export_destination_is_safe,
        final_item_name='export-budget.json',
        prepare_final_item=prepare_budget_receipt,
    )


def run_selected(mode: str, phase: str, cargo: Path, env: dict[str, str], source: Path) -> None:
    label = f'{phase}-{mode}'
    test_name = TESTS[mode]
    argv = [str(cargo), 'test', '--locked', '--lib', '--features',
            'testing-environ,sys', test_name, '--', '--exact', '--nocapture',
            '--test-threads=1']
    expected = 0 if phase == 'restored-green' else 101
    status = BASE.run_command(label, argv, env, expected_status=expected)
    stdout = BASE.read_text(BASE.STAGE / f'{label}.stdout')
    stderr = BASE.read_text(BASE.STAGE / f'{label}.stderr')
    combined = stdout + '\n' + stderr
    receipt = f'first-cause mode={mode} '
    fields = parse_fixture_receipt(combined, mode, label)
    for fact in ('identity_confirmed=true', 'identity_gate_released=true',
                 'identity_wait=acknowledged', 'stdout_write=acknowledged',
                 'stdout_committed=true', 'stderr_write=acknowledged',
                 'stderr_overflow=observed', 'reap=ESRCH'):
        if fact not in combined:
            raise RuntimeError(f'{label} missing fixture lifecycle fact: {fact}')
    if mode == 'managed' and 'group_closed=true' not in combined:
        raise RuntimeError(f'{label} missing exact Managed group closure receipt')
    if phase == 'restored-green':
        if (not selected_test_status(stdout, mode, 'ok')
                or 'test result: ok. 1 passed; 0 failed;' not in stdout):
            raise RuntimeError(f'{label} did not pass exactly one selected regression')
        BASE.verify_pass(label, status, combined,
                         [receipt.strip(),
                          'test result: ok. 1 passed; 0 failed;'])
    else:
        if ASSERTION not in combined or f"thread '{test_name}' panicked" not in combined:
            raise RuntimeError(f'{label} did not fail at the intended public cause assertion')
        if (not selected_test_status(stdout, mode, 'FAILED')
                or 'test result: FAILED. 0 passed; 1 failed;' not in stdout):
            raise RuntimeError(f'{label} did not select and fail exactly one test')
        BASE.verify_control(label, status, expected, combined, [ASSERTION],
                            stdout=combined, required_output=[receipt.strip()])
    fixture = {'case': label, 'pid': fields['child_pid'],
               'start_ticks': fields['child_start_ticks'], 'pgid': fields['child_pgid'],
               'expected_argv': json.dumps(EXPECTED_ARGV, separators=(',', ':')),
               'observed_cmdline_hex': fields['child_cmdline_hex'],
               'identity_confirmed': fields['identity_confirmed'],
               'identity_gate_released': fields['identity_gate_released'],
               'identity_wait': fields['identity_wait'],
               'stdout_write': fields['stdout_write'], 'stdout_committed': fields['stdout_committed'],
               'stderr_write': fields['stderr_write'], 'stderr_overflow': fields['stderr_overflow'],
               'reap': fields['reap'], 'group_closed': fields['group_closed']}
    FIXTURE_ROWS.append(fixture)
    write_fixture_ledger()
    CASE_LEDGER.append({'case': label, 'selected_test': test_name,
                        'expected_status': expected, 'observed_status': status,
                        'fixture': fixture, 'result': 'verified'})


def main() -> int:
    global BASE
    stage = Path(os.environ['PROOF_STAGE'])
    runtime = Path(os.environ['AGENT_RUNTIME_DIR'])
    BASE = load_base(stage / 'check-linux-current-msrv-examples.py')
    BASE.INPUT_STAGE = stage
    BASE.EXPECTED_STAGE = Path(os.environ['EXPECTED_PROOF_STAGE'])
    BASE.PRESCRIBED_STAGE = STAGE_PATH
    BASE.PRESCRIBED_SCOPE = SCOPE_PATH
    BASE.RUNTIME = runtime
    BASE.STAGE = runtime / 'evidence'
    BASE.EVIDENCE = BASE.EXPECTED_STAGE / 'proof-evidence'
    BASE.CONTRACT = stage / 'contract.md'
    BASE.SOURCE_ARCHIVE = stage / 'source.tar'
    BASE.LOCK_SOURCE = stage / 'Cargo.lock.accepted'
    BASE.RUSTUP = Path(os.environ['RUSTUP_BIN'])
    BASE.REVISION = os.environ['FIRST_CAUSE_SOURCE_REV']
    BASE.HELPER_EXIT_STATUS = 1
    BASE.TOOLCHAIN = '1.77.2-x86_64-unknown-linux-gnu'
    BASE.FEATURES = 'testing-environ,sys'
    BASE.SOURCE = runtime / 'source'
    BASE.CARGO_HOME = runtime / 'cargo-home'
    BASE.RUSTUP_HOME = runtime / 'rustup-home'
    BASE.TARGET = runtime / 'target'
    BASE.PRIVATE_HOME = runtime / 'home'
    BASE.PRIVATE_TMP = runtime / 'tmp'
    BASE.SOURCE_ARCHIVE_SHA256 = os.environ['FIRST_CAUSE_ARCHIVE_SHA256']
    BASE.LOCK_SHA256 = os.environ['FIRST_CAUSE_LOCK_SHA256']
    BASE.START = time.monotonic()
    BASE.DEADLINE = BASE.START + 540
    BASE.WORK_DEADLINE = BASE.DEADLINE - 30
    signal.signal(signal.SIGTERM, BASE.on_signal)
    signal.signal(signal.SIGINT, BASE.on_signal)
    planned = [
        {'case': f'{phase}-{mode}', 'selected_test': TESTS[mode],
         'expected_status': 0 if phase == 'restored-green' else 101,
         'result': 'pending'}
        for phase in ('baseline-red', 'overwrite-red', 'restored-green')
        for mode in ('direct', 'managed')
    ]
    original = None
    source = None
    expected_source_hash = None
    phase_hashes = []
    package_error = None
    completed = False
    try:
        BASE.capture_runtime_proof()
        BASE.validate_stage_inputs()
        verify_input_manifest(stage)
        for path in (BASE.CARGO_HOME, BASE.RUSTUP_HOME, BASE.PRIVATE_HOME, BASE.PRIVATE_TMP):
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
        env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': str(BASE.PRIVATE_HOME),
               'TMPDIR': str(BASE.PRIVATE_TMP), 'TMP': str(BASE.PRIVATE_TMP),
               'TEMP': str(BASE.PRIVATE_TMP), 'CARGO_HOME': str(BASE.CARGO_HOME),
               'RUSTUP_HOME': str(BASE.RUSTUP_HOME), 'CARGO_TARGET_DIR': str(BASE.TARGET),
               'CARGO_BUILD_JOBS': '2', 'CARGO_INCREMENTAL': '0',
               'CARGO_PROFILE_DEV_DEBUG': '0', 'CARGO_TERM_COLOR': 'never', 'RUST_BACKTRACE': '0'}
        BASE.run_command('rustup-install', [str(BASE.RUSTUP), 'toolchain', 'install',
            BASE.TOOLCHAIN, '--profile', 'minimal', '--no-self-update'], env,
            expected_status=0, cwd=runtime)
        bindir = BASE.RUSTUP_HOME / 'toolchains' / BASE.TOOLCHAIN / 'bin'
        rustc, cargo = bindir / 'rustc', bindir / 'cargo'
        if not rustc.is_file() or not cargo.is_file():
            raise RuntimeError('private Rust 1.77.2 toolchain is incomplete')
        env.update(PATH=f'{bindir}:/usr/bin:/bin:/usr/sbin:/sbin', RUSTC=str(rustc))
        BASE.run_command('rustc-version', [str(rustc), '--version', '--verbose'], env,
                         expected_status=0, cwd=runtime)
        BASE.run_command('cargo-version', [str(cargo), '--version', '--verbose'], env,
                         expected_status=0, cwd=runtime)
        rustc_text = BASE.read_text(BASE.STAGE / 'rustc-version.stdout')
        cargo_text = BASE.read_text(BASE.STAGE / 'cargo-version.stdout')
        if (not rustc_text.startswith('rustc 1.77.2 ')
                or 'host: x86_64-unknown-linux-gnu' not in rustc_text
                or not cargo_text.startswith('cargo 1.77.2 ')):
            raise RuntimeError('private toolchain version/host mismatch')
        source_archive = runtime / 'source-input.tar'
        import shutil
        shutil.copy2(BASE.SOURCE_ARCHIVE, source_archive)
        BASE.extract_archive(source_archive)
        source_archive.unlink()
        source = BASE.SOURCE / SOURCE_REL
        expected_source_hash = os.environ['FIRST_CAUSE_SOURCE_SHA256']
        if sha(source) != expected_source_hash:
            raise RuntimeError('frozen source hash mismatch')
        original = source.read_bytes()
        phase_hashes = [{'phase': 'baseline', 'sha256': sha(source), 'bytes': len(source.read_bytes())}]
        BASE.ORIGINAL_EXAMPLES[source] = original
        BASE.ORIGINAL_EXAMPLE_HASHES[SOURCE_REL] = expected_source_hash
        manifests = BASE.manifest_hashes()
        BASE.CARGO_MANIFESTS = manifests
        shutil.copy2(BASE.LOCK_SOURCE, BASE.SOURCE / 'Cargo.lock')
        if sha(BASE.SOURCE / 'Cargo.lock') != BASE.LOCK_SHA256:
            raise RuntimeError('accepted lock hash mismatch')
        BASE.write_json(BASE.STAGE / 'source-inputs.json',
                        {'source_revision': BASE.REVISION, 'source_sha256': expected_source_hash,
                         'archive_sha256': BASE.SOURCE_ARCHIVE_SHA256,
                         'lock_sha256': BASE.LOCK_SHA256, 'selected_tests': TESTS,
                         'phases': ['baseline-red', 'overwrite-red', 'restored-green']})
        for mode in ('direct', 'managed'):
            run_selected(mode, 'baseline-red', cargo, env, source)
        patched = apply_patch_bytes(original)
        source.write_bytes(patched)
        if source.read_bytes() != patched:
            raise RuntimeError('proposed patch byte check failed')
        phase_hashes.append({'phase': 'proposed-fix', 'sha256': sha(source), 'bytes': len(source.read_bytes())})
        _, overwritten = overwrite_stderr_guard(source)
        source.write_bytes(overwritten)
        if sha(source) != hashlib.sha256(overwritten).hexdigest():
            raise RuntimeError('stderr overwrite mutation byte check failed')
        phase_hashes.append({'phase': 'stderr-overwrite-mutant', 'sha256': sha(source), 'bytes': len(source.read_bytes())})
        BASE.write_json(BASE.STAGE / 'source-phase-hashes.json', phase_hashes)
        for mode in ('direct', 'managed'):
            run_selected(mode, 'overwrite-red', cargo, env, source)
        source.write_bytes(patched)
        if source.read_bytes() != patched:
            raise RuntimeError('patch restoration byte check failed')
        phase_hashes.append({'phase': 'restored-fix', 'sha256': sha(source), 'bytes': len(source.read_bytes())})
        for mode in ('direct', 'managed'):
            run_selected(mode, 'restored-green', cargo, env, source)
        if BASE.manifest_hashes() != manifests or sha(BASE.SOURCE / 'Cargo.lock') != BASE.LOCK_SHA256:
            raise RuntimeError('manifest or Cargo.lock changed during controls')
        BASE.write_json(BASE.STAGE / 'tool-versions.json',
                        {'rustc_stdout': rustc_text, 'cargo_stdout': cargo_text,
                         'toolchain': BASE.TOOLCHAIN})
        completed = len(BASE.CONTROL_RESULTS) == 6
    except BaseException as exc:
        package_error = f'{type(exc).__name__}: {exc}'
        if BASE.STAGE.is_dir():
            (BASE.STAGE / 'failure.txt').write_text(package_error + '\n', encoding='utf-8')
    finally:
        if source is not None and original is not None:
            try:
                phase_hashes.append({'phase': 'pre-restoration', 'sha256': sha(source)})
                source.write_bytes(original)
                final_hash = sha(source)
                phase_hashes.append({'phase': 'final-baseline-restored', 'sha256': final_hash, 'bytes': len(source.read_bytes())})
                if expected_source_hash and final_hash != expected_source_hash:
                    package_error = (package_error or '') + ' final source restoration hash mismatch'
            except BaseException as restore_error:
                package_error = (package_error or '') + f' source restoration failed: {restore_error!r}'
        if BASE.STAGE.is_dir():
            BASE.write_json(BASE.STAGE / 'source-phase-hashes.json', phase_hashes)
            case_by_name = {row['case']: row for row in planned}
            case_by_name.update({row['case']: row for row in CASE_LEDGER})
            BASE.write_json(BASE.STAGE / 'execution-ledger.json', {
                'ordered_cases': [case_by_name[row['case']] for row in planned],
                'commands': BASE.COMMANDS,
                'setup_commands': [row for row in BASE.COMMANDS if row.get('name') in ('rustup-install','rustc-version','cargo-version')],
                'case_order': [row['case'] for row in planned],
                'all_six_cases_verified': len(CASE_LEDGER) == 6,
        'fixture_rows': FIXTURE_ROWS,
            })
            result = {
                'acceptance_claim': False, 'source_revision': BASE.REVISION,
                'source_sha256': expected_source_hash,
                'source_restored': bool(source and expected_source_hash and sha(source) == expected_source_hash),
                'scope': 'six selected Child process first-cause tests; two each baseline RED, stderr-overwrite mutant RED, restored GREEN',
                'helper_exit_status': 0 if completed and package_error is None else 1,
                'package_status': 'complete' if completed and package_error is None else 'partial-or-failed',
                'error': package_error, 'selected_tests': TESTS,
                'ordered_cases': [case_by_name[row['case']] for row in planned],
                'commands': BASE.COMMANDS, 'controls': BASE.CONTROL_RESULTS,
                'archive_sha256': BASE.SOURCE_ARCHIVE_SHA256,
                'lock_sha256': BASE.LOCK_SHA256,
            }
            BASE.write_json(BASE.STAGE / 'package-result.json', result)
            BASE.write_json(BASE.STAGE / 'source-restoration.json', {
                'baseline_sha256': expected_source_hash,
                'phase_hashes': phase_hashes,
                'restored_baseline_matches': bool(source and expected_source_hash and sha(source) == expected_source_hash),
                'accepted_patch_sha256': sha(PATCH),
                'lock_sha256': BASE.LOCK_SHA256,
            })
            try:
                export_package_evidence(require_complete=(
                    completed and package_error is None and source is not None
                    and expected_source_hash and sha(source) == expected_source_hash
                ))
            except BaseException as partial_error:
                package_error = (package_error or '') + f' evidence export error: {partial_error!r}'
    return 0 if completed and package_error is None else 1

if __name__ == '__main__':
    raise SystemExit(main())
