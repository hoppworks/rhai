"""Capture the exact post-run COM1 recovery suffix without modifying the guest."""
from pathlib import Path
import hashlib, json, os, sys
stage = Path(sys.argv[1]).resolve()
assert stage.name == 'windows-rhai-native-9dd1f408c6904bbe87d8cb18510b9029'
pre = json.loads((stage/'recovery-serial-preflight.json').read_text())
serial=Path(pre['path'])
fd=os.open(serial,os.O_RDONLY|os.O_NOFOLLOW)
try:
 before=os.fstat(fd)
 assert before.st_ino==pre['inode'] and pre['offset_start']<before.st_size<=pre['offset_start']+5*1024*1024
 os.lseek(fd,pre['offset_start'],os.SEEK_SET)
 data=os.read(fd,before.st_size-pre['offset_start'])
 after=os.fstat(fd)
 assert len(data)==before.st_size-pre['offset_start'] and after.st_ino==before.st_ino and after.st_size==before.st_size
finally: os.close(fd)
for name in pre['files']:
 assert data.count(('RHAI_RECOVERY '+name+' ').encode())==1
 assert data.count(('RHAI_END '+name).encode())==1
assert not (stage/'recovery-serial-original.bin').exists()
(stage/'recovery-serial-original.bin').write_bytes(data)
rec={'inode':before.st_ino,'offset_start':pre['offset_start'],'offset_end':before.st_size,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
(stage/'recovery-serial-binding.json').write_text(json.dumps(rec,indent=2)+'\n')
print(json.dumps(rec,indent=2))
