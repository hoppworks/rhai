"""Independently replay the frozen correction batch without native libproc."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

REPO = Path('/Users/hoppworks/projects/rhai-all-tickets')
REV = '18d64de68e46f7e837d6874ac2faff1393f5bf03'
EVIDENCE = REPO / '.scratch/all-tickets/macos-correction-root-evidence'
RUNTIME = Path(os.environ['AGENT_RUNTIME_DIR'])
START = time.monotonic()
SOURCE = RUNTIME / '.scratch/all-tickets'
SOURCE.mkdir(parents=True)
EVIDENCE.mkdir()
(EVIDENCE / 'helper-used.py').write_bytes(Path(__file__).read_bytes())
paths = ['.scratch/all-tickets/' + name for name in (
    'darwin-process-reader.py', 'test-darwin-process-reader.py',
    'macos-process-overhead.py', 'run-macos-process-overhead-scoped.py',
    'test-macos-process-overhead-source.py', 'run-macos-process-overhead.sh',
    'runtime-path-parser.zsh')]
paths.append('.scratch/managed-unix-scope-close/measure-process-overhead.py')
frozen = {}
for path in paths:
    data = subprocess.check_output(['/usr/bin/git', '-C', str(REPO), 'show', REV + ':' + path], timeout=5)
    target = RUNTIME / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    frozen[path] = data
statuses = {}

def check(label, name, test=None, expected=0):
    command = [sys.executable, '-B', str(SOURCE / name)]
    if test:
        command.append('EnvironmentTests.' + test)
    with (EVIDENCE / (label + '.log')).open('w') as log:
        result = subprocess.run(command, cwd=RUNTIME, stdout=log, stderr=subprocess.STDOUT, timeout=10)
    statuses[label] = result.returncode
    (EVIDENCE / (label + '.status')).write_text(str(result.returncode) + '\n')
    output = (EVIDENCE / (label + '.log')).read_text()
    assert result.returncode == expected, (label, output)
    assert ('FAIL:' in output and 'ERROR:' not in output) if expected else '\nOK\n' in output

def mutation(label, filename, before, after, test):
    path = '.scratch/all-tickets/' + filename
    original = frozen[path].decode()
    assert original.count(before) == 1, (label, original.count(before))
    (RUNTIME / path).write_text(original.replace(before, after))
    try:
        check(label, 'test-macos-process-overhead-source.py', test, expected=1)
    finally:
        (RUNTIME / path).write_bytes(frozen[path])

check('reader-positive', 'test-darwin-process-reader.py')
check('adapter-positive', 'test-macos-process-overhead-source.py')
mutation('wrong-cleanup-acceptance', 'run-macos-process-overhead-scoped.py',
         "and r.get('cleanup_complete') is True", "and True",
         'test_final_acceptance_requires_cleanup_complete_even_after_eof')
mutation('wrong-startup-deadline', 'run-macos-process-overhead-scoped.py',
         'conn = wait_for_client_connection(server, proc, work_deadline)',
         'conn = wait_for_client_connection(server, proc, closure_deadline)',
         'test_client_connection_deadline_is_work_stop_with_closure_reserve')
mutation('wrong-export-summary-expectation', 'test-macos-process-overhead-source.py',
         'self.assertEqual(exported_summary["samples_total"], 120)',
         'self.assertEqual(exported_summary["samples_total"], 119)',
         'test_measurement_run_decodes_successful_bytes_before_parser_and_export')
mutation('wrong-wrapper-duplicate-rejection', 'runtime-path-parser.zsh',
         '(( ${#runtime_paths[@]} > 0 ))', '(( ${#runtime_paths[@]} == 1 ))',
         'test_wrapper_runtime_record_parser_accepts_only_identical_duplicates')
check('reader-restored', 'test-darwin-process-reader.py')
check('adapter-restored', 'test-macos-process-overhead-source.py')
for path, data in frozen.items():
    assert (RUNTIME / path).read_bytes() == data
    if path.endswith('.py'):
        compile(data, path, 'exec')
(EVIDENCE / 'receipt.json').write_text(json.dumps({
    'revision': REV, 'runtime': str(RUNTIME), 'statuses': statuses,
    'elapsed_seconds': time.monotonic() - START,
    'source_sha256': {path: hashlib.sha256(data).hexdigest() for path, data in frozen.items()},
    'acceptance': 'Pure source regressions only; native ABI and custody remain open.',
    'target_fixture_native_control_measurement_launches': 0,
}, indent=2) + '\n')
print('macos_correction_source_controls=passed', flush=True)
