"""Read a completed case from original serial bytes; never restarts native work."""
from pathlib import Path
import json,subprocess,shlex,sys,os,shutil,base64,hashlib
p=Path(__file__).resolve().parent;b=json.loads((p/'binding.json').read_text());mode=sys.argv[1];c=({'id':json.loads((p/'interrupted-readback/cleanup-host-manifest.json').read_text())['readback_id'],'tag':'interrupted01'}if mode=='interrupted'else next(x for x in b['controls']if x['mode']==mode));dispatch=p/(c['tag']+'-dispatch.json');d=json.loads((dispatch if dispatch.exists() else p/'dispatch.json').read_text())
code='''from pathlib import Path
import os,sys
base=Path('/var/log/libvirt/qemu/rhai-win11-quality-serial0.log');old=base.with_name(base.name+'.0');nodes=[x for x in (old,base)if x.exists() and x.stat().st_ino==INODE];assert len(nodes)==1,'Recorded serial node lost; inspect saved data before any repeat'
with nodes[0].open('rb')as f:
 assert os.fstat(f.fileno()).st_ino==INODE;f.seek(OFFSET);data=f.read()
if nodes[0]==old:
 with base.open('rb')as f:
  current=os.fstat(f.fileno());data+=f.read();assert base.stat().st_ino==current.st_ino
assert len(data)<64*1024*1024;sys.stdout.buffer.write(data)
'''.replace('INODE',str(d['serial_inode'])).replace('OFFSET',str(d['serial_offset']))
r=subprocess.run(['ssh','workhorse','python3 -c '+shlex.quote(code)],capture_output=True,check=True);prefix=('RHAI_BOOTSTRAP '+c['id']+' ').encode();selected=[];live=[]
for line in r.stdout.splitlines(keepends=True):
 if line.startswith(prefix):selected.append(line)
 elif line.startswith(b'RHAI_DEADLINE_LIVE '):
  item=json.loads(base64.b64decode(line.split(b' ',1)[1]));
  if item['id']==c['id']:live.append(line)
assert selected and b' END 'in selected[-1],mode+' still incomplete; preserve live handle, no restart'
raw=b''.join(selected+live);(p/(c['tag']+'-serial-original.txt')).write_bytes(raw)
repo=next(x for x in p.parents if (x/'tools/windows-scoped-runner').is_dir());stage=Path(os.environ['AGENT_RUNTIME_DIR'])/c['tag'];stage.mkdir()
shutil.copyfile(repo/'.scratch/rhai-wayfinder-replan-20261008/results/windows-custody-20261008T125846Z-b7f83433/collect_serial.py',stage/'collect_serial.py');shutil.copyfile(p/(c['tag']+'-serial-original.txt'),stage/(c['tag']+'-serial-original.txt'))
subprocess.run([sys.executable,'-B',str(stage/'collect_serial.py'),c['tag'],c['id']],check=True,stdout=subprocess.DEVNULL)
shutil.copytree(stage/(c['tag']+'-export'),p/(c['tag']+'-export'));shutil.copyfile(stage/(c['tag']+'-export-readback.json'),p/(c['tag']+'-export-readback.json'))
if mode=='interrupted':
 print(json.dumps({'readback_only':True,'product_accepted':False,'files':len(json.loads((p/(c['tag']+'-export-readback.json')).read_text())['files'])}));sys.exit(0)
o=json.loads((p/(c['tag']+'-export/observer.json')).read_text());print(json.dumps({'mode':mode,'exit':o['exit'],'accepted':o['accepted'],'failure':o['failure'],'elapsed':o['elapsed_seconds'],'monitor_trace':o['monitor_trace'],'last_pair_live':o['last_pair_live_seconds'],'captured_live_records':len(live)}))
