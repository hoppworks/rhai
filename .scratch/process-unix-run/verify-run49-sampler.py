import ast
import contextlib
import hashlib
import io
import re
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path('/Users/hoppworks/projects/rhai-process-unix-run')
RAW = ROOT / '.scratch/process-unix-run/evidence/shared-child-first-green.MU5GH7'
HARNESS = ROOT / '.scratch/process-unix-run/shared-child-first-green.py'
STOP_KIB = 1_572_864


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_sample_line(line):
    old = re.match(r"storage_sample_status=(\d+) stdout=(.*?) stderr=(.*)$", line)
    if old:
        return ('status', int(old.group(1)), ast.literal_eval(old.group(2)), ast.literal_eval(old.group(3)))
    new = re.match(r"storage_sample_attempt=(\d+) status=(timeout|\d+)(?: timeout_s=([0-9.]+))? stdout=(.*?) stderr=(.*)$", line)
    if new:
        status = new.group(2) if new.group(2) == 'timeout' else int(new.group(2))
        return ('attempt', int(new.group(1)), status, ast.literal_eval(new.group(4)), ast.literal_eval(new.group(5)))
    return None


raw_lines = RAW.read_text().splitlines()
samples = [parsed for line in raw_lines if (parsed := parse_sample_line(line)) is not None]
assert samples, 'run49 raw has no retained storage samples'
failed = next((sample for sample in samples if sample[0] == 'status' and sample[1] != 0), None)
assert failed is not None, 'run49 raw lacks the observed failed du sample'
assert 'No such file or directory' in failed[3]
valid_before = next(sample for sample in reversed(samples[:samples.index(failed)]) if sample[0] == 'status' and sample[1] == 0)

module = ast.parse(HARNESS.read_text(), filename=str(HARNESS))
sample_node = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == 'sample_storage')
namespace = {
    'RUNTIME': Path('/private/var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-5l9vdd8s'),
    'SAMPLED_STOP_KIB': STOP_KIB,
    'subprocess': SimpleNamespace(TimeoutExpired=subprocess.TimeoutExpired),
    'time': time,
}
exec(compile(ast.Module(body=[sample_node], type_ignores=[]), str(HARNESS), 'exec'), namespace)
calls = []


def replay_sequence(sequence):
    def replay(argv, **kwargs):
        calls.append((argv, kwargs))
        assert argv == ['du', '-sk', str(namespace['RUNTIME'])]
        assert kwargs['capture_output'] and kwargs['text']
        assert kwargs['timeout'] <= 5.0
        item = sequence[len(calls) - 1]
        if item == 'timeout':
            raise subprocess.TimeoutExpired(argv, kwargs['timeout'], output='partial-out', stderr='partial-err')
        return subprocess.CompletedProcess(argv, item[0], item[1], item[2])
    namespace['subprocess'].run = replay


replay_sequence([(failed[1], failed[2], failed[3]), (valid_before[1], valid_before[2], valid_before[3])])
captured = io.StringIO()
with contextlib.redirect_stdout(captured):
    recovered_kib = namespace['sample_storage'](time.monotonic() + 5)
assert recovered_kib == int(valid_before[2].split()[0])
assert len(calls) == 2, 'one transient nonzero must cause exactly one bounded retry'
assert 'storage_sample_attempt=1 status=1' in captured.getvalue()
assert 'storage_sample_attempt=2 status=0' in captured.getvalue()


def expect_failure(sequence, deadline=None, needle=''):
    calls.clear()
    replay_sequence(sequence)
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            namespace['sample_storage'](time.monotonic() + 5 if deadline is None else deadline)
    except (RuntimeError, TimeoutError) as error:
        if needle:
            assert needle in str(error), str(error)
    else:
        raise AssertionError('sampler accepted an invalid, failed, or over-cap result')
    return output.getvalue(), len(calls)


failure_item = (failed[1], failed[2], failed[3])
out, attempts = expect_failure([failure_item, failure_item], needle='failed twice')
assert attempts == 2 and out.count('status=1') == 2, 'two failed samples must be retained and fail closed'

out, attempts = expect_failure(['timeout', 'timeout'], needle='timed out twice')
assert attempts == 2 and 'status=timeout' in out and 'partial-err' in out

out, attempts = expect_failure([], deadline=time.monotonic() - 1, needle='exceeded its enclosing deadline')
assert attempts == 0, 'expired enclosing deadline must prevent starting a sample'


def check_single_result(stdout, expected_error):
    out, attempts = expect_failure([(0, stdout, '')], needle=expected_error)
    assert attempts == 1, 'successful but malformed/path-mismatched output must fail without retry'


runtime = str(namespace['RUNTIME'])
check_single_result('250000\t/foreign/runtime\n', 'malformed output or path identity')
check_single_result(f'not-a-number\t{runtime}\n', 'malformed output or path identity')
check_single_result(f'{STOP_KIB}\t{runtime}\n', 'reached existing stop threshold')

source = HARNESS.read_text()

# Execute the exact output/export helpers against owned temporary files. This verifies
# their data paths without starting Cargo or an OS child.
with __import__('tempfile').TemporaryDirectory(prefix='run49-sampler-offline-') as temporary:
    temp_root = Path(temporary)
    log_path = temp_root / 'cargo.log'
    log_path.write_bytes(b'cargo completed with a retained diagnostic\n')
    emit_node = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == 'emit_log')
    emit_namespace = {'Path': Path, 'EVIDENCE_CAP': 256 * 1024}
    exec(compile(ast.Module(body=[emit_node], type_ignores=[]), str(HARNESS), 'exec'), emit_namespace)
    log_output = io.StringIO()
    with contextlib.redirect_stdout(log_output):
        emit_namespace['emit_log'](log_path, True)
    assert 'cargo completed with a retained diagnostic' in log_output.getvalue()
    assert 'cargo_output_begin complete=true' in log_output.getvalue()

    original = temp_root / 'original'
    source_copy = temp_root / 'source'
    original.mkdir()
    source_copy.mkdir()
    for name in ('Cargo.toml', 'src/packages/sys/process.rs'):
        for base in (original, source_copy):
            target = base / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(name)
    export_node = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == 'export_exit_manifests')
    export_namespace = {
        'source': source_copy,
        'REPO': original,
        'OVERLAYS': ['Cargo.toml', 'src/packages/sys/process.rs'],
        'sha': sha,
    }
    exec(compile(ast.Module(body=[export_node], type_ignores=[]), str(HARNESS), 'exec'), export_namespace)
    export_output = io.StringIO()
    with contextlib.redirect_stdout(export_output):
        export_namespace['export_exit_manifests']()
    assert 'exit_available_private_overlay_hashes=' in export_output.getvalue()
    assert 'exit_available_original_overlay_hashes=' in export_output.getvalue()

run_cargo = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == 'run_cargo')
run_cargo_source = ast.get_source_segment(source, run_cargo)
status_pos = run_cargo_source.index("print(f'cargo_status={status}'")
log_pos = run_cargo_source.index('emit_log(log_path, True)', status_pos)
final_sample_pos = run_cargo_source.index('sample_storage(deadline)', log_pos)
assert status_pos < log_pos < final_sample_pos
assert "emit_log(log_path, terminal_status is not None)" in run_cargo_source
assert 'atexit.register(export_exit_manifests)' in source

attempt_line = 'storage_sample_attempt=2 status=0 stdout=' + repr(valid_before[2]) + ' stderr=' + repr(valid_before[3])
parsed_attempt = parse_sample_line(attempt_line)
assert parsed_attempt and parsed_attempt[:3] == ('attempt', 2, 0)
assert parse_sample_line(raw_lines[raw_lines.index(next(line for line in raw_lines if line.startswith('storage_sample_status=1')))]) == failed

print(f'raw_sha256={sha(RAW)}')
print(f'harness_sha256={sha(HARNESS)}')
print(f'run49_failure_replayed={failed!r}')
print(f'bounded_retry_value_kib={recovered_kib} attempts=2')
print('offline_cases=nonzero_then_valid,two_nonzero,two_timeouts,deadline_exhausted,malformed,wrong_path,threshold')
print('emit_log_helper=executed_and_retained_terminal_diagnostic')
print('exit_manifest_export=executed_for_original_and_private_files')
print('run_cargo_terminal_order=source-reviewed; exception_output_retained=source-reviewed')
print('sample_parser=legacy_run49_and_new_attempt_status_formats')
print('classification=source_only_offline_sampler_verification; no_cargo_or_os_child_launched')
