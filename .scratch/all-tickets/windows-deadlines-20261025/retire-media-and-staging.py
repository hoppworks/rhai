"""Export/retire three exact own media and hash-bound host staging; restore CDs."""
from pathlib import Path
import json,subprocess,hashlib,shlex
p=Path(__file__).resolve().parent;b=json.loads((p/'binding.json').read_text());receipt=json.loads((p/'guest-cleanup-receipt.json').read_text());manifest=json.loads((p/'cleanup-host-manifest.json').read_text());assert receipt['all_scopes_absent'] and not receipt['foreign_resources_touched'] and receipt['host_manifest_sha256']==hashlib.sha256((p/'cleanup-host-manifest.json').read_bytes()).hexdigest() and sorted(receipt['retired'])==sorted(x['scope']for x in manifest['scopes'])
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();out=p/'media';out.mkdir(exist_ok=True);owned=[]
refs=[('initial',p/'media-readback.json'),('interrupted',p/'interrupted-readback/media-readback.json'),('cleanup',p/'cleanup-medium-readback.json')]
for tag,ref in refs:
 m=json.loads(ref.read_text());target=out/(tag+'.iso');subprocess.run(['scp','-q','workhorse:'+m['medium'],str(target)],check=True);assert sha(target)==m['sha256'];owned.append({'path':m['medium'],'sha256':m['sha256'],'exported':str(target.relative_to(p))})
expected={}
for f in (p/'input').rglob('*'):
 if f.is_file():expected['input-medium/input/'+str(f.relative_to(p/'input'))]=sha(f)
for name in ('Start.ps1','input-manifest.json'):expected['input-medium/'+name]=sha(p/name)
for f in p.glob('*.bundle'):expected['input-medium/'+f.name]=sha(f)
expected['input-medium/media-readback.json']=sha(p/'media-readback.json')
for name in ('cleanup.ps1','cleanup-host-manifest.json'):expected['cleanup/'+name]=sha(p/name)
expected['cleanup/media-readback.json']=sha(p/'cleanup-medium-readback.json')
for name in ('cleanup.ps1','cleanup-host-manifest.json','media-readback.json'):expected['interrupted-readback/'+name]=sha(p/'interrupted-readback'/name)
expected['assemble-medium.py']=sha(p.parent/'windows-job-resources-20261025/assemble-medium.py')
expected['console-key-input.py']=sha(p.parent/'windows-workhorse-retirement-20261025/console-key-input.py')
original='/var/lib/libvirt/images/rhai-win11-quality/acceptance-20261008T125846Z-b7f83433/monitor-fixture02.iso'
code='''from pathlib import Path
import subprocess,json,hashlib,shutil,os,stat
root=Path(ROOT);expected=EXPECTED;owned=OWNED;original=ORIGINAL
assert subprocess.check_output(['virsh','domuuid','rhai-win11-quality'],text=True).strip()=='dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19'
def read_blocks():
 result={}
 for line in subprocess.check_output(['virsh','domblklist','rhai-win11-quality','--details'],text=True).splitlines():
  fields=line.split(None,3)
  if len(fields)==4 and fields[0] in ('file','block','network'):
   assert fields[2] not in result;result[fields[2]]=fields[3]
 return result
original_d='/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso'
blocks=read_blocks()
assert blocks.get('sdb')==original_d and blocks.get('sdc')in(owned[-1]['path'],original),'Foreign current mount; preserve it'
if blocks['sdc']==owned[-1]['path']:subprocess.run(['virsh','change-media','rhai-win11-quality','sdc',original,'--live','--force'],check=True,stdout=subprocess.DEVNULL)
blocks=read_blocks();assert blocks.get('sdc')==original and blocks.get('sdb')==original_d
assert root.is_dir() and not root.is_symlink() and str(root).startswith('/var/roothome/projects/rhai-deadlines-20261025-')
entries=list(root.rglob('*'));assert len(entries)<256
expected_dirs=set()
for name in expected:
 for parent in Path(name).parents:
  if str(parent)!='.':expected_dirs.add(str(parent))
actual={};actual_dirs=set()
for f in entries:
 mode=f.lstat().st_mode;relative=str(f.relative_to(root))
 if stat.S_ISDIR(mode):actual_dirs.add(relative)
 else:
  assert stat.S_ISREG(mode),'Unexpected symlink/special entry; preserve all staging'
  actual[relative]=hashlib.sha256(f.read_bytes()).hexdigest()
assert actual==expected and actual_dirs==expected_dirs,'Unexpected host file/directory inventory; preserve it'
def uses_root(value):
 if not value.startswith('/'):return False
 resolved=os.path.realpath(value.removesuffix(' (deleted)'))
 return resolved==str(root)or resolved.startswith(str(root)+'/')
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit()or int(proc.name)==os.getpid():continue
 try:
  cmd=(proc/'cmdline').read_bytes()
  assert str(root).encode()not in cmd,'Active staging argv: '+proc.name
  try:cwd=os.readlink(proc/'cwd')
  except FileNotFoundError:cwd=''
  assert not uses_root(cwd),'Active staging cwd: '+proc.name
  for fd in (proc/'fd').iterdir():
   try:target=os.readlink(fd)
   except FileNotFoundError:continue
   assert not uses_root(target),'Open staging file: '+proc.name
 except (FileNotFoundError,ProcessLookupError):continue
 except PermissionError:raise RuntimeError('Cannot prove staging inactivity for process '+proc.name)
for item in owned:
 f=Path(item['path']);assert str(f) not in blocks.values() and hashlib.sha256(f.read_bytes()).hexdigest()==item['sha256']
for item in owned:Path(item['path']).unlink()
shutil.rmtree(root)
assert not root.exists() and all(not Path(x['path']).exists()for x in owned)
print(json.dumps({'retired_media':owned,'original_sdc_restored':original,'original_sdb_preserved':True,'host_staging':str(root),'host_staging_entries':len(entries),'host_staging_files':len(actual),'host_staging_absent':True,'all_exact_images_absent':True,'foreign_resources_touched':False}))
'''.replace('ROOT',repr(b['host_source_root'])).replace('EXPECTED',repr(expected)).replace('OWNED',repr(owned)).replace('ORIGINAL',repr(original))
r=subprocess.run(['ssh','workhorse','python3 -B -'],input=code,capture_output=True,text=True);(p/'host-retirement.stdout').write_text(r.stdout);(p/'host-retirement.stderr').write_text(r.stderr);r.check_returncode();(p/'host-retirement.json').write_text(r.stdout);print(r.stdout)
