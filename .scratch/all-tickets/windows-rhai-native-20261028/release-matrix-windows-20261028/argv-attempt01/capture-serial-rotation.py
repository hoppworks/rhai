"""Capture the preflight-bound serial suffix across one observed log rotation."""
from pathlib import Path
import hashlib,json,os,sys
stage=Path(sys.argv[1]).resolve()
assert stage.name=='windows-rhai-native-eebf1576031e4604bf85943c7b3b177a'
pre=json.loads((stage/'host-dispatch-preflight-final.json').read_text())
current=Path(pre['serial_path']);old=Path(str(current)+'.0')
def read_exact(path, offset, expected_inode=None):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  before=os.fstat(fd)
  if expected_inode is not None: assert before.st_ino==expected_inode
  assert 0<=offset<=before.st_size<=4*1024*1024
  os.lseek(fd,offset,os.SEEK_SET); parts=[];remaining=before.st_size-offset
  while remaining:
   data=os.read(fd,remaining);assert data
   parts.append(data);remaining-=len(data)
  after=os.fstat(fd);assert (before.st_ino,before.st_size)==(after.st_ino,after.st_size)
  return b''.join(parts),before
 finally: os.close(fd)
a,sa=read_exact(old,pre['serial_offset'],pre['serial_inode'])
b,sb=read_exact(current,0);assert sa.st_ino!=sb.st_ino
data=a+b
needle=b'RHAI_BOOTSTRAP rhai-native-eebf1576031e4604bf85943c7b3b177a '
assert data.count(needle+b'0 BEGIN ')==1
assert sum(line.startswith(needle) and b' END ' in line for line in data.splitlines())==1
assert a.endswith(b'\n') or not b.startswith(needle), 'recorded rotation split must remain byte-contiguous'
out=stage/'serial-original.bin';assert not out.exists();out.write_bytes(data)
record={'serial_path':str(current),'inode':sa.st_ino,'offset_start':pre['serial_offset'],'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'rotation':{'old_path':str(old),'old_inode':sa.st_ino,'old_end':sa.st_size,'old_suffix_bytes':len(a),'new_inode':sb.st_ino,'new_end':sb.st_size,'new_prefix_bytes':len(b)}}
(stage/'serial-capture-binding.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
