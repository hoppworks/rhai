"""Capture one completed COM1 suffix across a verified host log rotation."""
from pathlib import Path
import hashlib
import json
import os
import sys

stage = Path(sys.argv[1]).resolve()
assert stage.name == 'windows-rhai-native-1743a38908f34db6a42d6e092c2b6655'
pre = json.loads((stage / 'host-dispatch-preflight-final.json').read_text())
base = Path(pre['serial_path'])
previous = Path(str(base) + '.0')
def read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        data = os.read(fd, first.st_size)
        last = os.fstat(fd)
        assert first.st_ino == last.st_ino and first.st_size == last.st_size
        assert len(data) == first.st_size
        return first.st_ino, data
    finally:
        os.close(fd)
old_inode, old = read(previous)
new_inode, new = read(base)
assert old_inode == pre['serial_inode'] and new_inode != old_inode
assert len(old) == 2 * 1024 * 1024 and pre['serial_offset'] < len(old)
data = old[pre['serial_offset']:] + new
needle = b'RHAI_BOOTSTRAP rhai-native-1743a38908f34db6a42d6e092c2b6655 '
assert data.count(needle + b'0 BEGIN ') == 1
assert data.count(b' END ') == 1
out = stage / 'serial-original.bin'
assert not out.exists()
out.write_bytes(data)
record = {'serial_path': str(base), 'preflight_inode': old_inode,
          'rotated_inode': new_inode, 'offset_start': pre['serial_offset'],
          'old_segment_end': len(old), 'new_segment_end': len(new),
          'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
          'rotation_verified': True}
(stage / 'serial-capture-binding.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
