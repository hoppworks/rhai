"""Check attempt03's original bounded failure receipt without treating it as PASS."""
from pathlib import Path
import hashlib
import json
import sys
import zlib

root = Path(sys.argv[1]).resolve()
journals = list((root / 'original-export' / 'run').glob('.scoped-run-*.journal'))
assert len(journals) == 1
raw = journals[0].read_bytes()
states = []
payloads = []
for line in raw.splitlines():
    length, crc, payload = line.split(b':', 2)
    assert int(length, 16) == len(payload)
    assert int(crc, 16) == zlib.crc32(payload)
    states.append(payload.split(b'|', 1)[0].decode('ascii'))
    payloads.append(payload)
assert states == ['INTENT', 'IDENTITY', 'STAGED', 'LIFECYCLE', 'EVIDENCE',
                  'OUTCOME', 'REMOVE_INTENT', 'REMOVED']
assert b'exit=00000055' in payloads[4]
assert b'payload=00000055' in payloads[5]
assert b'cleanup=CONFIRMED' in payloads[5]
record = {'journal': journals[0].relative_to(root).as_posix(),
          'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
          'states': states, 'crc32_and_length_valid': True,
          'terminal_removed': True, 'payload_exit_hex': '00000055',
          'product_acceptance': False}
(root / 'journal-readback.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
