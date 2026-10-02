"""Replay frozen injected task-info regressions without loading native libproc."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

REPO = Path('/Users/hoppworks/projects/rhai-all-tickets')
REV = 'b2db6448af7c4c29fe6d6529910d4648e264739a'
EVIDENCE = REPO / '.scratch/all-tickets/macos-native-sampling-root-evidence'
RUNTIME = Path(os.environ['AGENT_RUNTIME_DIR'])
STARTED = time.monotonic()
EVIDENCE.mkdir()
(EVIDENCE / 'helper-used.py').write_bytes(Path(__file__).read_bytes())
names = ('darwin-process-reader.py', 'macos-process-overhead.py',
         'run-macos-process-overhead-scoped.py', 'test-darwin-process-reader.py',
         'test-macos-process-overhead-source.py')
for name in names:
    data = subprocess.check_output(['/usr/bin/git', '-C', str(REPO), 'show',
                                    REV + ':.scratch/all-tickets/' + name], timeout=5)
    (RUNTIME / name).write_bytes(data)
reader = RUNTIME / names[0]
frozen = reader.read_text()
statuses = {}

def check(label, name, expected=0, test=None):
    command = [sys.executable, '-B', str(RUNTIME / name)]
    if test:
        command.append(test)
    with (EVIDENCE / (label + '.log')).open('w') as log:
        result = subprocess.run(command, cwd=RUNTIME, stdout=log,
                                stderr=subprocess.STDOUT, timeout=10)
    statuses[label] = result.returncode
    (EVIDENCE / (label + '.status')).write_text(str(result.returncode) + '\n')
    output = (EVIDENCE / (label + '.log')).read_text()
    assert result.returncode == expected, (label, result.returncode, output)
    assert ('FAIL:' in output and 'ERROR:' not in output) if expected else '\nOK\n' in output

check('reader-positive', names[3])
check('adapter-positive', names[4])
needle = 'return (total + 1023) // 1024'
assert frozen.count(needle) == 1
reader.write_text(frozen.replace(needle, 'return total // 1024'))
check('wrong-rss-rounding', names[3], 1,
      'ReaderTests.test_taskinfo_layout_and_resident_kib_conversion')
reader.write_text(frozen)
assert frozen.count('confirm.start_seconds, confirm.start_microseconds,') == 1
assert frozen.count('info.start_seconds, info.start_microseconds,') == 1
reader.write_text(frozen.replace('confirm.start_seconds, confirm.start_microseconds,',
                                'confirm.start_seconds,').replace(
                                'info.start_seconds, info.start_microseconds,', 'info.start_seconds,'))
check('wrong-identity-microseconds', names[3], 1,
      'ReaderTests.test_taskinfo_is_bracketed_by_full_identity_including_microseconds')
reader.write_text(frozen)
check('reader-restored', names[3])
check('adapter-restored', names[4])
for name in names:
    compile((RUNTIME / name).read_text(), name, 'exec')
assert reader.read_text() == frozen
(EVIDENCE / 'receipt.json').write_text(json.dumps({
    'revision': REV, 'statuses': statuses, 'elapsed_seconds': time.monotonic() - STARTED,
    'acceptance': 'Injected source regressions only; native ABI and custody remain unverified.',
    'build_fixture_native_control_measurement_launches': 0,
}, indent=2) + '\n')
print('native_sampling_injected_controls=passed', flush=True)
