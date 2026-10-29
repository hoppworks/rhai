"""Capture the original COM1 suffix bound by immediate preflight inode/offset."""
from pathlib import Path
import hashlib
import json
import os
import sys

stage = Path(sys.argv[1]).resolve()
assert stage.name == 'windows-rhai-native-8edc9965d4f64647b6e86849167df542'
pre = json.loads((stage / 'host-dispatch-preflight-final.json').read_text())
serial = Path(pre['serial_path'])
fd = os.open(serial, os.O_RDONLY | os.O_NOFOLLOW)
try:
    before = os.fstat(fd)
    assert before.st_ino == pre['serial_inode']
    os.lseek(fd, pre['serial_offset'], os.SEEK_SET)
    data = os.read(fd, before.st_size - pre['serial_offset'])
    assert len(data) == before.st_size - pre['serial_offset']
    after = os.fstat(fd)
    assert after.st_ino == before.st_ino and after.st_size == before.st_size
finally:
    os.close(fd)
needle = b'RHAI_BOOTSTRAP rhai-native-8edc9965d4f64647b6e86849167df542 '
assert data.count(needle + b'0 BEGIN ') == 1
assert data.count(b' END ') == 1
out = stage / 'serial-original.bin'
assert not out.exists()
out.write_bytes(data)
record = {'serial_path': str(serial), 'inode': before.st_ino,
          'offset_start': pre['serial_offset'], 'offset_end': before.st_size,
          'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
(stage / 'serial-capture-binding.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
