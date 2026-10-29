"""Capture exact selected SDK hash readback from the native guest serial log."""
from pathlib import Path
import hashlib,json,os,sys
stage=Path(sys.argv[1]).resolve()
assert stage.name=='windows-rhai-native-9dd1f408c6904bbe87d8cb18510b9029'
pre=json.loads((stage/'sdk-hash-serial-preflight.json').read_text())
fd=os.open(pre['path'],os.O_RDONLY|os.O_NOFOLLOW)
try:
 before=os.fstat(fd)
 assert before.st_ino==pre['inode'] and pre['offset_start']<before.st_size<=pre['offset_start']+16384
 os.lseek(fd,pre['offset_start'],os.SEEK_SET);data=os.read(fd,before.st_size-pre['offset_start']);after=os.fstat(fd)
 assert len(data)==before.st_size-pre['offset_start'] and after.st_ino==before.st_ino and after.st_size==before.st_size
finally: os.close(fd)
lines=[x.strip() for x in data.decode('ascii').splitlines() if x.strip()]
assert len(lines)==8
names=[];pins={}
for line in lines:
 parts=line.split();assert len(parts)==4 and parts[0]=='RHAI_SDK_PIN'
 _,name,size,sha=parts;assert name not in pins and len(sha)==64 and int(size)>0
 names.append(name);pins[name]={'bytes':int(size),'sha256':sha.lower()}
assert names==pre['expected_names'],names
assert not (stage/'sdk-hash-serial-original.bin').exists()
(stage/'sdk-hash-serial-original.bin').write_bytes(data)
rec={'inode':before.st_ino,'offset_start':pre['offset_start'],'offset_end':before.st_size,'bytes':len(data),'serial_sha256':hashlib.sha256(data).hexdigest(),'pins':pins}
(stage/'sdk-hash-readback.json').write_text(json.dumps(rec,indent=2)+'\n')
print(json.dumps(rec,indent=2))
