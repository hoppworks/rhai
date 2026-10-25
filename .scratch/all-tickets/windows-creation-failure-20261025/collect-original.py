"""Read only exact recorded serial identity, including one libvirt rotation."""
from pathlib import Path
import sys,subprocess,json,shlex,hashlib
p=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent;d=json.loads((p/'dispatch.json').read_text());b=json.loads((p/'binding.json').read_text())
code='''from pathlib import Path
import os,sys,json
base=Path('/var/log/libvirt/qemu/rhai-win11-quality-serial0.log');old=base.with_name(base.name+'.0');expected=INODE;offset=OFFSET
paths=[x for x in (old,base) if x.exists() and x.stat().st_ino==expected]
assert len(paths)==1,'Recorded serial inode unavailable; preserve state, do not rerun native work'
first=paths[0]
with first.open('rb') as f:
 assert os.fstat(f.fileno()).st_ino==expected;f.seek(offset);data=f.read()
if first==old:
 with base.open('rb') as f:
  current=os.fstat(f.fileno());data+=f.read();assert base.stat().st_ino==current.st_ino,'Serial rotated while reading'
assert len(data)<16*1024*1024
sys.stdout.buffer.write(data)
'''.replace('INODE',str(d['serial_inode'])).replace('OFFSET',str(d['serial_offset']))
r=subprocess.run(['ssh','workhorse','python3 -c '+shlex.quote(code)],capture_output=True,check=True)
raw=r.stdout
for c in b['controls']:
 needle=('RHAI_BOOTSTRAP '+c['id']+' ').encode();lines=[x for x in raw.splitlines()if x.startswith(needle)]
 assert len(lines)>1 and any(b' END ' in x for x in lines),c['profile']+' not yet fully exported; no native repeat'

(p/'serial-original.txt').write_bytes(raw)
(p/'serial-readback.json').write_text(json.dumps({'recorded_inode':d['serial_inode'],'offset':d['serial_offset'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'all_requested_original_end_frames_observed':True,'native_repeats':0},indent=2)+'\n')
print('Original native exports secured:',len(b['controls']),len(raw),'bytes')
