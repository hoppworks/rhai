"""Retire exact exported quota media/staging, preserving original CDs and guest build."""
from pathlib import Path
import json,subprocess,hashlib
p=Path(__file__).resolve().parent;read=lambda f:json.loads(f.read_text());sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
b=read(p/'binding.json');r=read(p/'guest-cleanup-receipt.json');m=read(p/'cleanup-host-manifest.json');staging=read(p/'host-staging-before.json')
assert r['all_scopes_absent']and r['retained_verified']and not r['foreign_resources_touched']and r['manifest_sha256']==sha(p/'cleanup-host-manifest.json')and sorted(r['retired'])==sorted(x['scope']for x in m['scopes'])
assert staging['root']==b['host_source_root']and staging['all_immutable_inputs_matched']and staging['metadata_binding_fields_matched']
assert sha(p/'host-staging-before.json')=='12b9e2c09da507a52ec89c08fec1906713e3f66159485ce8e50465076176b4a4','Reviewed host staging manifest changed'
media_allowlist={'/var/lib/libvirt/images/rhai-win11-quality/process-quota-e6ce6222dba147a8b43b2c79187d3184.iso': 'a3d5285d3e2c6b0a17025593c1e027716ca21ecac5725a59dbbb0cb60390f0d0', '/var/lib/libvirt/images/rhai-win11-quality/process-quota-c8d7629099fd47d1b6f10ef65649db5e.iso': '1f96c2bcea39f750b7e1be31bd9791875a28839005c9e57cb461a2cf4dc200f8', '/var/lib/libvirt/images/rhai-win11-quality/process-quota-61233f37b1ce4ddc847ba9b8ff2a14ed.iso': '80f7bd10fc4fdd74f644ced634c8543a3638237267e108538518abb92e88bd1e', '/var/lib/libvirt/images/rhai-win11-quality/process-quota-48d19d95797f4b4f84f6962bac3f955c.iso': '7e4f3e4fe406138b7b3d4aef17f0f324e1a1b64c9b2af70695831dacd02df0eb', '/var/lib/libvirt/images/rhai-win11-quality/quota-build-readback-48d19d95797f4b4f84f6962bac3f955c.iso': '773350adfbe72012ed00ca9077be2fb14922e5341c3f5a62f2e50d34c51e0691', '/var/lib/libvirt/images/rhai-win11-quality/quota-build-readback-61233f37b1ce4ddc847ba9b8ff2a14ed.iso': 'e248643c3177fbd952ab9c2b5fb8dba748767f1c33a3266344e76300f5df4cf6', '/var/lib/libvirt/images/rhai-win11-quality/quota-retirement-48d19d95797f4b4f84f6962bac3f955c.iso': 'ee08e70a7917c64b64bc8b5a48d72d99d5947ef479f88cc780e90f4f004bb464', '/var/lib/libvirt/images/rhai-win11-quality/quota-retirement02-48d19d95797f4b4f84f6962bac3f955c.iso': '54ef6e8a55de4752c08dc4d665d431a878fc8cdb8e6117dbcf5d31b2a61c8c76'}
owned=staging['media'];expected=staging['files']
assert len(owned)==8 and len({x['path']for x in owned})==8 and {x['path']:x['sha256']for x in owned}==media_allowlist
for item in owned:assert sha(p/item['exported'])==item['sha256']
original='/var/lib/libvirt/images/rhai-win11-quality/acceptance-20261008T125846Z-b7f83433/monitor-fixture02.iso'
code = r'''

from pathlib import Path
import subprocess,json,hashlib,shutil,os,stat
root=Path(ROOT);expected=EXPECTED;owned=OWNED;original=ORIGINAL
media_allowlist=MEDIA_PINS
assert len(owned)==8 and len({x['path']for x in owned})==8 and {x['path']:x['sha256']for x in owned}==media_allowlist
for item in owned:
 f=Path(item['path'])
 assert f.parent==Path('/var/lib/libvirt/images/rhai-win11-quality') and f.resolve(strict=True)==f and stat.S_ISREG(f.lstat().st_mode) and hashlib.sha256(f.read_bytes()).hexdigest()==media_allowlist[str(f)],'Unreviewed/noncanonical media; preserve all targets'

assert subprocess.check_output(['virsh','domuuid','rhai-win11-quality'],text=True).strip()=='dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19'
def read_blocks(inactive=False):
 result={}
 for line in subprocess.check_output(['virsh','domblklist','rhai-win11-quality','--details']+(['--inactive']if inactive else []),text=True).splitlines():
  fields=line.split(None,3)
  if len(fields)==4 and fields[0] in ('file','block','network'):
   assert fields[2] not in result;result[fields[2]]=fields[3]
 return result
original_d='/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso'
blocks=read_blocks()
assert blocks.get('sdb')==original_d and blocks.get('sdc')in(owned[-1]['path'],original),'Foreign current mount; preserve it'
if blocks['sdc']==owned[-1]['path']:subprocess.run(['virsh','change-media','rhai-win11-quality','sdc',original,'--update','--live'],check=True,stdout=subprocess.DEVNULL)
blocks=read_blocks();assert blocks.get('sdc')==original and blocks.get('sdb')==original_d
assert root.is_dir() and not root.is_symlink() and str(root)=='/var/roothome/projects/rhai-process-quota-20261025-475b06d7' and root.resolve()==root
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
owned_real={os.path.realpath(x['path'])for x in owned}
def uses_root(value):
 if not value.startswith('/'):return False
 resolved=os.path.realpath(value.removesuffix(' (deleted)'))
 return resolved==str(root)or resolved.startswith(str(root)+'/')or resolved in owned_real
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit()or int(proc.name)==os.getpid():continue
 try:
  cmd=(proc/'cmdline').read_bytes()
  assert all(marker.encode()not in cmd for marker in [str(root)]+[x['path']for x in owned]),'Active owned staging/media argv: '+proc.name
  try:cwd=os.readlink(proc/'cwd')
  except FileNotFoundError:cwd=''
  assert not uses_root(cwd),'Active staging cwd: '+proc.name
  for fd in (proc/'fd').iterdir():
   try:target=os.readlink(fd)
   except FileNotFoundError:continue
   assert not uses_root(target),'Open staging file: '+proc.name
 except (FileNotFoundError,ProcessLookupError):continue
 except PermissionError:raise RuntimeError('Cannot prove staging inactivity for process '+proc.name)
inactive=read_blocks(True)
for item in owned:
 f=Path(item['path']);assert not f.is_symlink() and str(f) not in blocks.values() and str(f) not in inactive.values() and hashlib.sha256(f.read_bytes()).hexdigest()==item['sha256']
for item in owned:Path(item['path']).unlink()
shutil.rmtree(root)
assert not root.exists() and all(not Path(x['path']).exists()for x in owned)
print(json.dumps({'retired_media':owned,'original_sdc_restored':original,'original_sdb_preserved':True,'host_staging':str(root),'host_staging_entries':len(entries),'host_staging_files':len(actual),'host_staging_absent':True,'all_exact_images_absent':True,'foreign_resources_touched':False}))
'''
code=code.replace('ROOT',repr(b['host_source_root'])).replace('EXPECTED',repr(expected)).replace('OWNED',repr(owned)).replace('ORIGINAL',repr(original)).replace('MEDIA_PINS',repr(media_allowlist))
r=subprocess.run(['ssh','workhorse','python3 -B -'],input=code,capture_output=True,text=True);(p/'host-retirement.stdout').write_text(r.stdout);(p/'host-retirement.stderr').write_text(r.stderr);r.check_returncode();(p/'host-retirement.json').write_text(r.stdout);print(r.stdout)
