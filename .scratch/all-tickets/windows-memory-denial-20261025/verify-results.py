"""Independent readback of the saved native Windows committed-memory proof."""
from pathlib import Path, PureWindowsPath
import hashlib, json, re, sys, zlib

p = Path(sys.argv[1]).resolve()
b = json.loads((p / 'binding.json').read_text())
read = lambda f: json.loads(f.read_text())
sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
root = p / 'memory01-export'
export = read(p / 'memory01-export-readback.json')
observer = read(root / 'observer.json')
control = b['control_id']
assert export['begin']['id'] == export['end']['id'] == observer['id'] == control
assert export['begin']['accepted'] == export['end']['accepted'] == observer['accepted'] is True
assert export['begin']['exit'] == export['end']['exit'] == observer['exit'] == 0
assert export['end']['files'] == len(export['files']) <= 64 and export['frames'] == 567
assert sum(x['length'] for x in export['files'].values()) <= 16 * 1024**2
for name, item in export['files'].items():
    f = root / name
    assert f.is_file() and f.stat().st_size == item['length'] and sha(f) == item['sha256'], name
assert sha(p / 'Start.ps1') == b['start_sha256']
assert sha(p / 'input-manifest.json') == b['manifest_sha256']
assert read(p / 'input-manifest.json')['files'] == b['files']
for name, digest in b['files'].items():
    assert sha(p / 'input' / name) == digest, name
for key in ('fresh_host_record', 'driver_launched', 'exact_driver_exited', 'pipes_drained',
            'process_disposed', 'owned_executables_stopped', 'job_memory_green',
            'job_memory_sensitivity', 'memory_actors_stopped', 'runtime_absent_readback',
            'runtime_absence_negative_control'):
    assert observer[key] is True, key
for key in ('custody_pending', 'observer_kill_used', 'retained_driver_handles',
            'parent_environment_changed', 'product_run'):
    assert observer[key] is False, key
assert observer['contract'] == 'job-memory' and observer['phase'] == 'GREEN' and not observer['failure']
assert observer['driver_elapsed_seconds'] < 110 and len(observer['channel_closure']) == 2
for channel in observer['channel_closure']:
    assert all(channel[x] for x in ('reader_acquired','writer_acquired','reader_disposed','writer_disposed','eof'))
    assert not channel['error'] and not channel['pending_task']
assert PureWindowsPath(observer['scope']).name == b['control_scope_leaf']
assert PureWindowsPath(observer['run']) == PureWindowsPath(observer['scope']) / 'run'
public = read(p / '../../windows-process-quota-20261025/retained-default-build.json')
for component, wanted in (('build-readback', public), ('fixture-build-readback', b)):
    build = read(root / component / 'build-observer.json')
    assert build['accepted'] and build['native_started'] and build['exit'] == 0
    assert not build['custody_indeterminate'] and not build['driver_launched']
    assert build['input_manifest_sha256'] == (wanted['input_manifest_sha256'] if component == 'build-readback' else b['manifest_sha256'])
    assert build['start_sha256'] == (wanted['start_sha256'] if component == 'build-readback' else b['start_sha256'])
    lines = (root / component / 'build-manifest.txt').read_text().splitlines()
    assert lines[0] == 'compiler_sha256=' + public['compiler_sha256']
    pins = {line[66:]: line[:64] for line in lines if re.fullmatch(r'[0-9a-f]{64}  .+', line)}
    if component == 'fixture-build-readback':
        assert pins['tools/windows-scoped-runner/fixtures/PayloadFixture.cs'] == b['files']['tools/windows-scoped-runner/fixtures/PayloadFixture.cs']
        assert pins['build/PayloadFixture.exe'] == observer['fixture_sha256'] == sha(root/'input/fixture.exe')
        assert sha(root/component/'build-manifest.txt') == observer['fixture_build_manifest_sha256']
    else:
        for name in ('ScopedRunner.exe','MonitorAcceptanceDriver.exe'):
            assert pins['build/'+name] == public['binaries'][name] == observer['retained_binaries'][name] == sha(root/'bin'/name)
logs = list((root/'fixture-build-readback/logs').glob('compile-*.stdout.txt'))
assert len(logs) == 1 and logs[0].name == 'compile-PayloadFixture.stdout.txt'
owner = [json.loads(x) for x in (root/'fixture-build-readback/logs/job-members.jsonl').read_text().splitlines()]
assert [x['label'] for x in owner] == ['before-compiler','after-exact-compiler-exit']
assert all(x['assigned'] == x['listed'] == len(x['members']) == 1 and x['members'][0]['id'] == x['owner'] for x in owner)
run = root/'run'; journals = list(run.glob('.scoped-run-*.journal'))
assert len(journals) == 1
raw = journals[0].read_bytes(); rows = []
while raw:
    assert re.fullmatch(rb'[0-9A-F]{4}:[0-9A-F]{8}:', raw[:14])
    length = int(raw[:4],16); crc = int(raw[5:13],16); body = raw[14:14+length]
    assert len(body) == length and raw[14+length:15+length] == b'\n' and zlib.crc32(body) == crc
    rows.append(body.decode('ascii').split('|')); raw = raw[15+length:]
assert [x[0] for x in rows] == ['INTENT','IDENTITY','STAGED','LIFECYCLE','EVIDENCE','OUTCOME','REMOVE_INTENT','REMOVED']
assert len({x[1] for x in rows}) == 1
snapshot = list(run.glob('.scoped-evidence-*')); assert len(snapshot) == 1
snapshot = snapshot[0]; runtime = snapshot/'runtime'
assert sha(runtime/'fixture.exe') == observer['fixture_sha256']
names = set()
for line in (snapshot/'manifest.txt').read_text().splitlines():
    rel, kind, identity, size, creation, attrs, digest = line.split('|')
    assert re.fullmatch(r'[0-9A-F]{16}:[0-9a-f]{32}', identity)
    assert not PureWindowsPath(rel).is_absolute() and '..' not in PureWindowsPath(rel).parts
    file = runtime.joinpath(*PureWindowsPath(rel).parts); assert rel not in names; names.add(rel)
    if kind == 'F': assert file.is_file() and file.stat().st_size == int(size) and sha(file).upper() == digest
    else: assert kind == 'D' and file.is_dir() and size == '0' and not digest
assert '' in names and {str(PureWindowsPath(*f.relative_to(runtime).parts)) for f in runtime.rglob('*')} == names - {''}
text = lambda suffix: (runtime/('payload-job-memory.txt'+suffix)).read_bytes().decode('ascii')
parse = lambda suffix: dict(x.split('=',1) for x in text(suffix).strip().split(';'))
rec = parse(''); root_record = parse('.root'); process = parse('.process-denial'); job = parse('.job-denial')
leaf0 = parse('.leaf-0'); leaf1 = parse('.leaf-1'); observed = observer['job_memory_observed']
assert rec['contract'] == 'PASS' and rec['job_member'] == root_record['job_member'] == 'True'
assert root_record['flags'] == '00002308' and int(root_record['process_limit']) == 1073741824 and int(root_record['job_limit']) == 2147483648
assert int(root_record['global_available_commit']) >= 3221225472 and 0 < int(root_record['private_bytes']) < 536870912
assert process == {'bytes':'1073741824','returned':'False','native_error':'1455','protected_unchanged':'True'}
assert job['bytes'] == '536870912' and job['returned'] == 'False' and job['native_error'] == '1455' and job['protected_unchanged'] == 'True'
assert 0 < int(job['root_private_before']) < 536870912 and int(job['global_available_commit_before']) >= 1073741824
actors = [{'pid':int(x['pid']),'creation':int(x['creation'])} for x in (root_record,leaf0,leaf1)]
assert len({x['pid'] for x in actors}) == 3
for leaf in (leaf0,leaf1):
    assert leaf['job_member'] == 'True' and int(leaf['committed_bytes']) == 805306368 and int(leaf['private_bytes']) >= 805306368
assert (rec['pid'],rec['creation']) == (root_record['pid'],root_record['creation'])
assert (rec['released_leaf'],rec['retained_leaf']) == (leaf0['pid'],leaf1['pid'])
assert rec['process_error'] == process['native_error'] and rec['job_error'] == job['native_error'] and int(rec['retries']) >= 0
assert text('.protected') == 'same-allocation-succeeded-after-exact-leaf-exit\r\n'
assert 'memory child cleanup failed' not in (snapshot/'stderr.log').read_text().lower()
assert observed['root']['pid'] == actors[0]['pid'] and observed['released_leaf']['pid'] == actors[1]['pid'] and observed['retained_leaf']['pid'] == actors[2]['pid']
assert observed['process_native_error'] == observed['job_native_error'] == 1455
assert observed['global_available_commit_before_job_denial'] == int(job['global_available_commit_before'])
def expect_limits(proc, total):
    if int(root_record['process_limit']) != proc or int(root_record['job_limit']) != total: raise AssertionError('memory-limit mismatch')
try: expect_limits(1073741825,2147483648)
except AssertionError as error: assert str(error) == 'memory-limit mismatch'
else: raise AssertionError('wrong memory limit unexpectedly passed')
expect_limits(1073741824,2147483648)
try: assert text('.protected') == 'wrong effect\r\n'
except AssertionError: pass
else: raise AssertionError('wrong protected effect unexpectedly passed')
assert 'RUNTIME_REMOVED=True' in (root/'bootstrap.stdout').read_text()
result = {'accepted':True,'driver_exit':0,'driver_elapsed_seconds':observer['driver_elapsed_seconds'],
          'files':len(export['files']),'frames':export['frames'],'crc_records':len(rows),
          'actors':actors,'process_error':1455,'job_error':1455,
          'global_commit_before_process':int(root_record['global_available_commit']),
          'global_commit_before_job':int(job['global_available_commit_before']),
          'same_allocation_recovered':True,'fresh_census_at_cleanup':'pending'}
(p/'host-accepted-readback.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
