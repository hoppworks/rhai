"""Finite X23 example acceptance; commands and observations export before cleanup."""
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

evidence = Path(sys.argv[1]).resolve()
inputs = json.loads((evidence / 'inputs.json').read_text())
runtime = Path(os.environ['AGENT_RUNTIME_DIR']).resolve()
source = runtime / 'source'
result = {'rows': [], 'accepted': False, 'runtime': str(runtime)}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def command(tag, argv, env=None, timeout=1000):
    started = time.monotonic()
    with (evidence / (tag + '.stdout')).open('wb') as out, (evidence / (tag + '.stderr')).open('wb') as err:
        proc = subprocess.run(argv, cwd=source, env=env, stdout=out, stderr=err, timeout=timeout)
    record = {'argv': argv, 'cwd': str(source), 'exit': proc.returncode, 'seconds': time.monotonic() - started}
    (evidence / (tag + '.command.json')).write_text(json.dumps(record, indent=2) + '\n')
    print(tag, 'exit', proc.returncode, 'seconds', round(record['seconds'], 3), flush=True)
    size = int(subprocess.check_output(['du', '-sk', str(runtime)], text=True).split()[0]) * 1024
    if size > 8 * 1024**3:
        raise RuntimeError('owned runtime exceeds declared 8 GiB envelope')
    return proc.returncode

def example_phase(profile, executable, expected):
    tag = profile + ('-red' if expected == 8 else '-green')
    env = dict(os.environ, RHAI_SYS_PROCESS_EXAMPLE_EXPECTED_EXIT=str(expected))
    rc = command(tag, [str(executable)], env=env, timeout=30)
    out = (evidence / (tag + '.stdout')).read_text()
    err = (evidence / (tag + '.stderr')).read_text()
    if 'bounded cleanup did not observe a terminal child result' in err:
        raise RuntimeError(tag + ': example reported incomplete cleanup')
    required = [
        'Host read back run child record: "run child wrote its record\\n"',
        'Host read back spawned child record: "spawn child observed release\\n"',
        'Spawn wait was pending, then both cloned handles returned the same result.',
    ]
    if not all(marker in out for marker in required):
        raise RuntimeError(tag + ': missing independent host readback or pending/clone assertion')
    pids = re.findall(r'Host read back spawned child record: .*\(pid (\d+)\)', out)
    if len(pids) != 1:
        raise RuntimeError(tag + ': expected one observed spawn fixture PID')
    pid = int(pids[0])
    try:
        os.kill(pid, 0)
    except OSError as error:
        if error.errno != errno.ESRCH:
            raise
    else:
        raise RuntimeError(tag + ': spawned PID still present after terminal waits')
    if expected == 8:
        if rc != 101 or 'RED control changes only the expected exit' not in err or not re.search(r'left:\s*7\s+right:\s*8', err):
            raise RuntimeError(tag + ': not the intended wrong-exit assertion RED')
    elif rc != 0:
        raise RuntimeError(tag + ': restored expectation did not pass')
    row = {'profile': profile, 'expected_exit': expected, 'exit': rc, 'spawn_pid': pid,
           'spawn_post_exit_probe': 'ESRCH', 'binary_sha256': digest(executable),
           'example_sha256': digest(source / 'examples/sys_process.rs')}
    result['rows'].append(row)
    (evidence / 'result.json').write_text(json.dumps(result, indent=2) + '\n')

try:
    for name, expected in inputs['inputs'].items():
        if digest(evidence / name) != expected:
            raise RuntimeError('changed immutable input: ' + name)
    stat = runtime.stat()
    result['runtime_identity'] = {'device': stat.st_dev, 'inode': stat.st_ino}
    source.mkdir()
    subprocess.run(['tar', '-xf', str(evidence / 'source.tar'), '-C', str(source)], check=True)
    (source / 'Cargo.lock').write_bytes((evidence / 'Cargo.lock.accepted').read_bytes())
    subprocess.run(['git', 'apply', '--check', str(evidence / 'owned.patch')], cwd=source, check=True)
    subprocess.run(['git', 'apply', str(evidence / 'owned.patch')], cwd=source, check=True)
    if digest(source / 'examples/sys_process.rs') != inputs['working_files']['examples/sys_process.rs']:
        raise RuntimeError('staged example differs from reviewed owned patch')
    result['environment'] = {
        'os': subprocess.check_output(['sw_vers'], text=True),
        'architecture': subprocess.check_output(['uname', '-m'], text=True).strip(),
        'rustc': subprocess.check_output(['rustc', '+1.77.2', '--version'], text=True).strip(),
        'cargo': subprocess.check_output(['cargo', '+1.77.2', '--version'], text=True).strip(),
        'lock_sha256': digest(source / 'Cargo.lock'),
        'cargo_home': os.environ['CARGO_HOME'], 'target': os.environ['CARGO_TARGET_DIR'],
        'tmpdir': os.environ['TMPDIR'], 'cargo_jobs': os.environ['CARGO_BUILD_JOBS'],
        'build_environment': {key: os.environ.get(key) for key in
                              ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTUP_HOME',
                               'RUSTUP_TOOLCHAIN', 'CC', 'CFLAGS', 'MACOSX_DEPLOYMENT_TARGET']},
    }
    for profile, features in [('no-float', 'sys,no_float'), ('sync-no-float', 'sys,sync,no_float')]:
        rc = command(profile + '-build', ['cargo', '+1.77.2', 'build', '--locked', '--features', features,
                                         '--example', 'sys_process', '--message-format=json'])
        if rc != 0:
            raise RuntimeError(profile + ': build stopped before product acceptance')
        artifacts = []
        for line in (evidence / (profile + '-build.stdout')).read_text().splitlines():
            message = json.loads(line)
            if message.get('reason') == 'compiler-artifact' and message.get('target', {}).get('name') == 'sys_process' and 'example' in message.get('target', {}).get('kind', []) and message.get('executable'):
                artifacts.append(Path(message['executable']))
        if len(artifacts) != 1 or not artifacts[0].is_file():
            raise RuntimeError(profile + ': ambiguous or missing compiler artifact')
        example_phase(profile, artifacts[0], 8)
        example_phase(profile, artifacts[0], 7)
        if digest(source / 'Cargo.lock') != inputs['inputs']['Cargo.lock.accepted']:
            raise RuntimeError('locked dependency graph changed')
    result['accepted'] = True
except BaseException as error:
    result['failure'] = repr(error)
    raise
finally:
    (evidence / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
