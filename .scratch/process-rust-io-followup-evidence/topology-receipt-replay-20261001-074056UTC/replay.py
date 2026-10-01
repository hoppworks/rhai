import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

repo = Path('/Users/hoppworks/projects/rhai-process-rust-io')
source = repo / '.scratch/process-rust-io/adapter'
raw = repo / '.scratch/process-rust-io/evidence/native-linux-workload-topology-attempt3-20261001-073406UTC/driver-export/custodian-279616-topology-cancel.json'
runtime = Path(os.environ['AGENT_RUNTIME_DIR'])
work = runtime / 'topology-replay'
work.mkdir()
for name in ('test_workload_topology_receipt.py', 'process_identity.py', 'test_process_identity.py'):
    shutil.copy2(source / name, work / name)
shutil.copy2(raw, work / 'raw-attempt3.json')
marker = Path(os.environ['REPLAY_RUNTIME_MARKER'])
marker.write_text(str(runtime) + '\n')

actual = json.loads((work / 'raw-attempt3.json').read_text())
assert actual['native_io']['case'] == 'topology-cancel'

# Reconstruct the pre-fix duplicate-field assertion on a private copy.
fixed = (work / 'test_workload_topology_receipt.py').read_text()
new = '''    native_io = receipt["native_io"]
    assert native_io["case"] == "topology-cancel"
    assert type(native_io["workers_started"]) is int and native_io["workers_started"] == 3
    assert type(native_io["workers_joined"]) is int and native_io["workers_joined"] == 3
    assert type(native_io["wake_to_join_ms"]) is int
    assert 0 <= native_io["wake_to_join_ms"] <= 1000'''
assert new in fixed
legacy = fixed.replace(new, '    assert topology["worker_joins"] == 3')
(work / 'legacy_assertion.py').write_text(legacy)

def run(label, script, receipt):
    p = subprocess.run([sys.executable, str(script), str(receipt)], cwd=work,
                       text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(f'[{label}] exit={p.returncode}')
    print(p.stdout.rstrip())
    return p

old = run('expected-red-old-assertion', work / 'legacy_assertion.py', work / 'raw-attempt3.json')
assert old.returncode != 0 and "KeyError: 'worker_joins'" in old.stdout
fixed_result = run('fixed-actual-receipt', work / 'test_workload_topology_receipt.py', work / 'raw-attempt3.json')
assert fixed_result.returncode == 0

controls = (
    ('workers_joined=2', lambda d: d['native_io'].__setitem__('workers_joined', 2)),
    ('wake_to_join_ms=1001', lambda d: d['native_io'].__setitem__('wake_to_join_ms', 1001)),
    ('wrong-pre-escape-sid', lambda d: d['workload_topology']['escaped_grandchild_pre_escape'].__setitem__('sid', -1)),
)
for label, mutate in controls:
    candidate = json.loads(json.dumps(actual))
    mutate(candidate)
    path = work / (label.replace('=', '-') + '.json')
    path.write_text(json.dumps(candidate))
    result = run('expected-red-' + label, work / 'test_workload_topology_receipt.py', path)
    assert result.returncode != 0 and 'AssertionError' in result.stdout

suite = subprocess.run([sys.executable, '-m', 'unittest', '-v',
                        'test_workload_topology_receipt', 'test_process_identity'],
                       cwd=work, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                       text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
print('[focused-unit-and-process-identity] exit=' + str(suite.returncode))
print(suite.stdout.rstrip())
assert suite.returncode == 0

for path, label in ((source / 'test_workload_topology_receipt.py', 'source_assertion'),
                    (source / 'test_process_identity.py', 'source_process_identity_test'),
                    (source / 'process_identity.py', 'source_process_identity'),
                    (raw, 'raw_attempt3_receipt')):
    print(f'SHA256 {label} {hashlib.sha256(path.read_bytes()).hexdigest()} {path}')
print('REPLAY_ALL_EXPECTED_RESULTS=PASS')
