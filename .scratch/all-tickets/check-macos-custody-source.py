"""Replay frozen pure controls and known-broken source in a private runtime."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import time

REPO = Path('/Users/hoppworks/projects/rhai-all-tickets')
REV = 'fdb9cf207158cff0635b500f26664a89bc2af5ab'
PARENT = 'a7232f054d324779bab9afd43f5b6d52ca7c685e'
BASE = REPO / '.scratch/all-tickets'
EVIDENCE = BASE / 'macos-custody-source-root-evidence'
RUNTIME = Path(os.environ['AGENT_RUNTIME_DIR'])
STARTED = time.monotonic()
EVIDENCE.mkdir()  # Preserve original runs; no overwrite/retry.
subprocess.run(['/bin/cp', __file__, str(EVIDENCE / 'helper-used.py')], check=True, timeout=5)
names = ('macos-process-overhead.py', 'run-macos-process-overhead-scoped.py',
         'test-macos-process-overhead-source.py')
def original(revision, name):
    return subprocess.check_output(['/usr/bin/git', '-C', str(REPO), 'show',
                                    revision + ':.scratch/all-tickets/' + name],
                                   text=True, timeout=5)
for name in names:
    (RUNTIME / name).write_text(original(REV, name))
adapter = RUNTIME / names[1]
frozen = adapter.read_text()
statuses = {}
def check(name, test=None, expected=0):
    command = [sys.executable, '-B', str(RUNTIME / names[2])]
    if test:
        command.append('EnvironmentTests.' + test)
    with (EVIDENCE / (name + '.log')).open('w') as log:
        result = subprocess.run(command, cwd=RUNTIME, stdout=log,
                                stderr=subprocess.STDOUT, timeout=20)
    statuses[name] = result.returncode
    (EVIDENCE / (name + '.status')).write_text(str(result.returncode) + '\n')
    assert result.returncode == expected, (name, result.returncode)
    output = (EVIDENCE / (name + '.log')).read_text()
    if expected:
        assert 'FAIL:' in output and 'ERROR:' not in output, output
    else:
        assert '\nOK\n' in output, output
check('positive')
needle = "return [sys.executable, '-c', CLIENT_CODE, mask_arg, sys.executable, str(driver)]"
assert frozen.count(needle) == 1
adapter.write_text(frozen.replace(needle,
    "return [sys.executable, '-c', CLIENT_CODE, mask_arg, str(driver)]"))
check('wrong-client-vector', 'test_client_exec_vector_runs_python_driver_with_restored_signal_mask', 1)
adapter.write_text(frozen)
old = original(PARENT, names[1])
def function(source, name):
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(source, node)
current_function = function(frozen, 'record_sampled_descendants')
old_function = function(old, 'record_sampled_descendants')
assert frozen.count(current_function) == 1
adapter.write_text(frozen.replace(current_function, old_function))
check('known-broken-disappeared-sample', 'test_sampled_descendant_missing_from_identity_census_fails_closed', 1)
adapter.write_text(frozen)
check('restored')
for name in names:
    compile((RUNTIME / name).read_text(), name, 'exec')
assert adapter.read_text() == frozen
(EVIDENCE / 'receipt.json').write_text(json.dumps({
    'revision': REV, 'known_broken_identity_source': PARENT, 'statuses': statuses,
    'elapsed_seconds': time.monotonic() - STARTED,
    'acceptance': 'Pure source regressions only; no native architecture acceptance.',
    'no_build_fixture_native_measurement': True,
}, indent=2) + '\n')
print('pure_source_positive_negative_restored=passed', flush=True)
