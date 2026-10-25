"""Read the archived native child records and journals, without executing native tools."""
from pathlib import Path
import base64
import json
import ntpath
import re
import zlib

packet = Path(__file__).resolve().parent
keys = ['AGENT_RUNTIME_DIR', 'TMP', 'TEMP', 'CARGO_HOME', 'CARGO_TARGET_DIR']
types = ['INTENT', 'IDENTITY', 'STAGED', 'LIFECYCLE', 'EVIDENCE', 'OUTCOME', 'REMOVE_INTENT', 'REMOVED']
report = {}
for phase in ['RED', 'GREEN']:
    root = packet / 'readback' / ('environment-' + phase.lower() + '01')
    observer = json.loads((root / 'observer.json').read_text())
    assert observer['phase'] == phase and observer['accepted'] and observer['exit'] == 0
    assert observer['driver_launched'] and observer['exact_driver_exited'] and observer['pipes_drained']
    assert not observer['retained_driver_handles'] and not observer['parent_environment_changed']
    stdout = dict(line.split('=', 1) for line in (root / 'bootstrap.stdout').read_text().splitlines() if '=' in line)
    expected_exit = '0000002A' if phase == 'RED' else '00000000'
    assert stdout['PAYLOAD_EXIT'] == expected_exit and stdout['SUPERVISION'] == 'PayloadExited'
    assert stdout['CLEANUP_CONFIRMED'] == 'True' and stdout['RUNTIME_REMOVED'] == 'True'
    assert stdout['HOST_EXPORTED'] == 'False'  # Host export is proven separately by the original serial frames.
    allocated = stdout['RUNTIME']
    assert observer['allocated_runtime'] == allocated
    witness = next(root.rglob('payload-environment.txt'))
    lines = witness.read_text().splitlines()
    assert len(lines) == 7
    decoded = {}
    for line, key in zip(lines[:-1], ['cwd'] + keys):
        name, value = line.split('=', 1)
        assert name == key
        decoded[key] = base64.b64decode(value, validate=True).decode('utf-8')
    assert decoded['cwd'].casefold() == allocated.casefold()
    expected = dict(zip(keys, [allocated, ntpath.join(allocated, 'work', 'temp'),
                             ntpath.join(allocated, 'work', 'temp'),
                             ntpath.join(allocated, 'work', 'cargo-home'),
                             ntpath.join(allocated, 'work', 'target')]))
    mismatches = [key for key in keys if decoded[key].casefold() != expected[key].casefold()]
    assert mismatches == (keys if phase == 'RED' else [])
    assert observer['environment_mismatches'] == mismatches
    assert observer['environment_observed'] == {key: decoded[key] for key in keys}
    assert lines[-1] == ('contract=FAIL' if phase == 'RED' else 'contract=PASS')
    journal = next(root.rglob('*.journal')).read_bytes()
    assert 0 < len(journal) <= 64 * 1024
    records = []
    at = 0
    while at < len(journal):
        header = journal[at:at + 14]
        assert re.fullmatch(rb'[0-9A-F]{4}:[0-9A-F]{8}:', header)
        length, crc = int(header[:4], 16), int(header[5:13], 16)
        assert 0 < length <= 4096
        body = journal[at + 14:at + 14 + length]
        assert len(body) == length and all(0x20 <= value <= 0x7e for value in body)
        assert journal[at + 14 + length:at + 15 + length] == b'\n'
        assert zlib.crc32(body) == crc
        records.append(body.decode('ascii').split('|'))
        at += 15 + length
    assert at == len(journal) and len(records) == 8
    assert [record[0] for record in records] == types
    assert len({record[1] for record in records}) == 1
    assert records[0][2] == allocated
    assert ('payload=' + expected_exit) in records[5]
    assert 'supervision=PayloadExited' in records[5] and 'cleanup=CONFIRMED' in records[5]
    report[phase] = {'payload_exit': expected_exit, 'mismatch_keys': mismatches,
                     'child_cwd_matches_independent_allocated_runtime': True,
                     'crc_valid_ordered_journal_records': len(records),
                     'parent_preservation_checked_by_original_observer': True,
                     'native_reexecution': False}
(packet / 'semantic-readback.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
