"""Independent assertions on saved real Windows exports; launches no native work."""
from pathlib import Path, PureWindowsPath
import base64, hashlib, json, re, zlib

P = Path(__file__).resolve().parent

def load(path):
    return json.loads(path.read_text())

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def journal(root):
    files = list((root / 'run').glob('.scoped-run-*.journal'))
    assert len(files) == 1
    records = []
    for line in files[0].read_bytes().splitlines():
        size, crc, body = line.split(b':', 2)
        assert len(body) == int(size, 16)
        assert zlib.crc32(body) == int(crc, 16)
        assert all(32 <= c <= 126 for c in body)
        records.append(body.decode('ascii').split('|'))
    assert [r[0] for r in records] == ['INTENT', 'IDENTITY', 'STAGED', 'LIFECYCLE', 'EVIDENCE', 'OUTCOME', 'REMOVE_INTENT', 'REMOVED']
    assert len({r[1] for r in records}) == 1
    return records

def fields(row):
    return dict(item.split('=', 1) for item in row if '=' in item)

def stdout(root):
    raw = (root / 'bootstrap.stdout').read_bytes()
    result = {}
    for line in raw.decode().splitlines():
        key, value = line.split('=', 1)
        assert key not in result
        result[key] = value
    assert not re.findall(rb'(?m)^RUNTIME=([^\r\n]+)$', raw)
    assert len(re.findall(rb'(?m)^RUNTIME=([^\r\n]+)\r?$', raw)) == 1
    assert result['CLEANUP_CONFIRMED'] == 'True'
    assert result['RUNTIME_REMOVED'] == 'True'
    assert result['SUPERVISION'] == 'MonitorStopped'
    return result

binding = load(P / 'binding.json')
results = []
host_cases = []
private = PureWindowsPath(binding['build_scope']).parent
for case in binding['cases']:
    root = P / (case['tag'] + '-export')
    receipt = load(P / (case['tag'] + '-export-readback.json'))
    observer = load(root / 'observer.json')
    assert receipt['begin'] == observer
    assert observer['id'] == case['id'] == receipt['end']['id']
    assert observer['accepted'] and receipt['end']['accepted'] and observer['exit'] == receipt['end']['exit'] == 0
    assert observer['exact_driver_exited'] and observer['pipes_drained'] and not observer['retained_driver_handles']
    for flag in ('fresh_host_record', 'wrong_expectation_red', 'payload_stopped_readback', 'runtime_absent_readback', 'runtime_absence_negative_control'):
        assert observer[flag], (case['mode'], flag)
    assert observer['retained_binaries'] == binding['binaries']
    assert PureWindowsPath(observer['scope']) == private / case['scope_leaf']
    output = stdout(root)
    assert output['CLIENT_EXIT'] == ('0x00000001' if case['mode'] == 'client-death' else '0x0000004E')
    assert output['PAYLOAD_EXIT'] == '0000007D'
    assert output['MODE'].startswith(case['mode'] + ';ACTION_CONFIRMED=True;POST_TRANSFER_CHALLENGES=')
    challenges = int(output['MODE'].rsplit('=', 1)[1])
    assert challenges >= 4
    runtime = PureWindowsPath(output['RUNTIME'])
    assert runtime == PureWindowsPath(observer['allocated_runtime'])
    assert runtime.parent == PureWindowsPath(observer['run'])
    assert re.fullmatch(r'scoped-[0-9a-f]{32}', runtime.name)
    records = journal(root)
    assert PureWindowsPath(records[0][2]) == runtime
    assert records[1][2] == records[4][2] == records[-1][2] == output['RUNTIME_IDENTITY']
    evidence = fields(records[4]); outcome = fields(records[5])
    assert evidence['proof'] == 'EXACT' and evidence['exit'] == '0000007D' and evidence['supervision'] == 'MonitorStopped'
    assert outcome['payload'] == '0000007D' and outcome['supervision'] == 'MonitorStopped' and outcome['cleanup'] == 'CONFIRMED'
    assert re.fullmatch(r'[0-9A-F]{16}:[0-9a-f]{32}', evidence['work_identity'])
    assert 3 <= int(evidence['work_entries']) <= 65536 and 0 <= int(evidence['work_bytes']) <= 8 * 1024**3
    snapshots = list((root / 'run').glob('.scoped-evidence-*'))
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    for key, name in [('manifest', 'manifest.txt'), ('stdout', 'stdout.log'), ('stderr', 'stderr.log')]:
        assert digest(snapshot / name).upper() == evidence[key]
    manifest = (snapshot / 'manifest.txt').read_text().splitlines()
    assert manifest[0].split('|')[2] == output['RUNTIME_IDENTITY']
    assert not any(part.lower() == 'work' for line in manifest for part in re.split(r'[\\/|]', line))
    assert digest(snapshot / 'runtime/fixture.exe') == binding['binaries']['PayloadFixture.exe']
    marker = (snapshot / 'runtime/payload-record.txt').read_bytes()
    assert marker == b'payload-started\r\n'
    assert marker != b'wrong-payload-expectation'
    identity = (snapshot / 'runtime/payload-record.txt.identity').read_bytes()
    match = re.fullmatch(rb'pid=([0-9]+) creation=([0-9]+)\r\n', identity)
    assert match and int(match[1]) == observer['payload_pid'] and int(match[2]) == observer['payload_creation']
    total_runtime_bytes = sum(f.stat().st_size for f in (snapshot / 'runtime').rglob('*') if f.is_file())
    assert total_runtime_bytes == int(evidence['runtime_bytes'])
    results.append({'mode': case['mode'], 'driver_exit': 0, 'payload_exit': 125, 'client_exit': output['CLIENT_EXIT'], 'post_transfer_challenges': challenges, 'crc_valid_records': len(records), 'exact_job_proof': True, 'snapshot_hashes_bound': True, 'independent_pid_start_stop': True, 'actual_runtime_absent': True, 'snapshot_negative_absence_control': True, 'marker_negative_control': True, 'work_entries': int(evidence['work_entries']), 'work_bytes': int(evidence['work_bytes']), 'frames': receipt['frames'], 'exported_files': len(receipt['files'])})
    host_cases.append({'id': case['id'], 'scope_leaf': case['scope_leaf'], 'observer_sha256': digest(root / 'observer.json'), 'files': receipt['files']})
summary = {'batch_id': binding['batch_id'], 'semantic_accepted': True, 'source_base': binding['base'], 'cases': results, 'native_compiler_launches': 0, 'public_driver_launches': len(results), 'parent_environment_legacy_placeholder_not_used_as_proof': True, 'remaining_full_custody': 'deadline, both-member membership before useful work, actual atomic-association failure and remaining failed export/cleanup outcomes'}
(P / 'semantic-results.json').write_text(json.dumps(summary, indent=2) + '\n')
(P / 'host-accepted-readback.json').write_text(json.dumps({'batch_id': binding['batch_id'], 'semantic_accepted': True, 'cases': host_cases}, indent=2) + '\n')
print(json.dumps(summary))
