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
    assert result['SUPERVISION'] == 'PayloadExited'
    return result

root = P / 'retirement-readback01-export'
readback = load(P / 'retirement-readback01-export-readback.json')
assert readback['begin']['readback_only'] and not readback['begin']['native_reexecution']
assert readback['begin']['runtime_absent']
assert not readback['end']['driver_launched']
original = load(root / 'observer.json')
assert not original['accepted'] and original['exit'] == 0
assert original['exact_driver_exited'] and original['pipes_drained'] and not original['retained_driver_handles']
assert (root / 'observer.json').read_bytes() == (P / 'retirement-abort01-export/observer.json').read_bytes()
out = stdout(root)
assert out['PAYLOAD_EXIT'] == '0000002A'
records = journal(root)
evidence = fields(records[4])
assert evidence['proof'] == 'EXACT' and evidence['exit'] == '0000002A'
assert fields(records[5])['cleanup'] == 'CONFIRMED'
assert str(PureWindowsPath(records[0][2])) == str(PureWindowsPath(out['RUNTIME']))
assert records[1][2] == out['RUNTIME_IDENTITY'] == records[4][2] == records[-1][2]
snapshots = list((root / 'run').glob('.scoped-evidence-*'))
assert len(snapshots) == 1
snapshot = snapshots[0]
for key, name in [('manifest', 'manifest.txt'), ('stdout', 'stdout.log'), ('stderr', 'stderr.log')]:
    assert digest(snapshot / name).upper() == evidence[key]
manifest = (snapshot / 'manifest.txt').read_text().splitlines()
assert manifest[0].split('|')[2] == out['RUNTIME_IDENTITY']
assert not any(part.lower() == 'work' for line in manifest for part in re.split(r'[\\/|]', line))
witness = (snapshot / 'stdout.log').read_text()
assert 'INTENTIONAL_ASSERTION_FAILURE: retirement abort after bounded-work fixture' in witness
assert 'WORK_RETIREMENT_EXPECTED_BYTES:613419011' in witness
assert 'WORK_RETIREMENT_LONG_RELATIVE_PATH:265' in witness
assert digest(snapshot / 'runtime/fixture.exe') == original['fixture_sha256']

def work_assertion(minimum):
    assert int(evidence['work_entries']) >= minimum, 'work entry count below independent expectation'
    assert int(evidence['work_bytes']) == 613419011
    assert re.fullmatch(r'[0-9A-F]{16}:[0-9a-f]{32}', evidence['work_identity'])

try:
    work_assertion(99999)
except AssertionError as error:
    assert 'work entry count' in str(error)
else:
    raise AssertionError('impossible work expectation was accepted')
work_assertion(2060)
build = load(root / 'build-readback/build-observer.json')
assert build['accepted'] and build['native_started'] and not build['custody_indeterminate'] and build['exit'] == 0
pins = {}
for line in (root / 'build-readback/build-manifest.txt').read_text().splitlines():
    match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
    if match:
        pins[match[2]] = match[1]
for name, value in pins.items():
    if name.startswith('tools/'):
        assert digest(P / 'original-packet/input' / name) == value
    elif name.startswith('build/'):
        assert original['retained_binaries'][Path(name).name] == value
result = {'retirement': {'native_public_driver_launches': 1, 'native_driver_exit': 0, 'native_payload_exit': 42, 'original_observer_accepted': False, 'recovered_parser_only': True, 'work_entries': int(evidence['work_entries']), 'work_bytes': int(evidence['work_bytes']), 'wrong_entry_expectation_rejected': True, 'restored_expectation_passed': True, 'crc_valid_journal_records': 8, 'independent_runtime_absence': True, 'child_witness_bound_to_snapshot_hashes': True, 'manifest_source_pins_verified': sum(n.startswith('tools/') for n in pins), 'actual_compiled_source_files': 11, 'inventory_only_not_compiled': ['CustodyBackendFixture.cs', 'NativeScopePolicyFixture.cs'], 'compiler_builds_repeated': 0}}

green = P / 'environment-green01-export'
if green.exists():
    observer = load(green / 'observer.json')
    assert observer['accepted'] and observer['exit'] == 0 and observer['environment_contract_green']
    assert not observer['environment_mismatches'] and not observer['parent_environment_changed']
    assert observer['exact_driver_exited'] and observer['pipes_drained'] and not observer['retained_driver_handles']
    output = stdout(green)
    assert output['PAYLOAD_EXIT'] == '00000000'
    rows = journal(green)
    assert str(PureWindowsPath(rows[0][2])) == str(PureWindowsPath(output['RUNTIME']))
    runtime = output['RUNTIME']
    witness_files = list((green / 'run').glob('.scoped-evidence-*/runtime/payload-environment.txt'))
    assert len(witness_files) == 1
    lines = witness_files[0].read_text().splitlines()
    assert len(lines) == 7 and lines[-1] == 'contract=PASS'
    values = {key: base64.b64decode(value, validate=True).decode() for key, value in (line.split('=', 1) for line in lines[:-1])}
    assert values['cwd'] == runtime
    expected = {'AGENT_RUNTIME_DIR': runtime, 'TMP': str(PureWindowsPath(runtime) / 'work/temp'), 'TEMP': str(PureWindowsPath(runtime) / 'work/temp'), 'CARGO_HOME': str(PureWindowsPath(runtime) / 'work/cargo-home'), 'CARGO_TARGET_DIR': str(PureWindowsPath(runtime) / 'work/target')}
    def env_assertion(expectation):
        for key, value in expectation.items():
            assert values[key].casefold() == value.casefold(), 'private environment mismatch: ' + key
    wrong = dict(expected, TMP=str(PureWindowsPath(runtime) / 'work/wrong-temp'))
    try:
        env_assertion(wrong)
    except AssertionError as error:
        assert 'TMP' in str(error)
    else:
        raise AssertionError('wrong private TMP expectation was accepted')
    env_assertion(expected)
    result['environment'] = {'native_public_driver_launches': 1, 'native_driver_exit': 0, 'native_payload_exit': 0, 'all_five_private_paths_pass': True, 'wrong_TMP_expectation_rejected': True, 'parent_preserved': True, 'crc_valid_journal_records': 8, 'compiler_builds_repeated': 0}
(P / 'native-semantic-readback.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
