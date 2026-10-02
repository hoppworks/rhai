"""Replay the Linux preparation checks without launching the compiler package."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
RUNTIME = Path(os.environ['AGENT_RUNTIME_DIR'])
DESTINATION = HERE / 'linux-feature-source-evidence'
FILES = (
    'check-linux-current-feature-compilation.py',
    'test-linux-current-feature-export-interrupt.py',
    'stage-linux-current-feature-compilation.sh',
    'launch-linux-current-feature-compilation.sh',
    'linux-current-feature-compilation-contract.md',
)


def run(label, argv, expected=0):
    result = subprocess.run(argv, cwd=RUNTIME, capture_output=True, text=True,
                            timeout=10, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    (DESTINATION / (label + '.stdout')).write_text(result.stdout)
    (DESTINATION / (label + '.stderr')).write_text(result.stderr)
    (DESTINATION / (label + '.status')).write_text(str(result.returncode) + '\n')
    if result.returncode != expected:
        raise AssertionError(f'{label}: expected {expected}, got {result.returncode}')
    return result


def main():
    DESTINATION.mkdir()
    hashes = {}
    for name in FILES:
        contents = (HERE / name).read_bytes()
        hashes[name] = hashlib.sha256(contents).hexdigest()
        (RUNTIME / name).write_bytes(contents)
    helper = RUNTIME / FILES[0]
    original = helper.read_text()
    test = [sys.executable, str(RUNTIME / FILES[1])]
    for name in FILES[:2]:
        compile((RUNTIME / name).read_text(), name, 'exec')
    for name in FILES[2:4]:
        run(name + '-syntax', ['/bin/bash', '-n', str(RUNTIME / name)])
    blocks = (RUNTIME / FILES[3]).read_text().split("<<'PY'\n")[1:]
    assert len(blocks) == 3
    for index, block in enumerate(blocks):
        source, separator, _rest = block.partition('\nPY\n')
        assert separator
        compile(source, f'launcher-heredoc-{index}', 'exec')
    run('positive', test)
    needle = 'if INTERRUPTED is not None and not during_export:'
    assert original.count(needle) == 1
    helper.write_text(original.replace(needle, 'if INTERRUPTED is not None:'))
    red = run('interrupted-export-red', test, 1)
    assert 'InterruptedError' in red.stderr
    assert 'interrupted_compile_stopped=pass' in red.stdout
    helper.write_text(original)
    run('restored', test)
    for name, expected in hashes.items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected, name
    (DESTINATION / 'receipt.json').write_text(json.dumps({
        'status': 'source-only-passed', 'input_sha256': hashes,
        'runtime': str(RUNTIME), 'native_invocations': 0,
        'scope': 'Interruption export regression and shell syntax only; no compiler or native acceptance.',
    }, indent=2) + '\n')
    print('linux_feature_source_checks=pass')


if __name__ == '__main__':
    main()
