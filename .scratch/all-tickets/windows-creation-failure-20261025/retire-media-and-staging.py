"""Export/retire four exact own media and hash-bound host staging; restore CDs."""
from pathlib import Path
import json,subprocess,hashlib,shlex
p=Path(__file__).resolve().parent;b=json.loads((p/'binding.json').read_text());assert json.loads((p/'guest-cleanup-receipt.json').read_text())['all_scopes_absent']
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();out=p/'media';out.mkdir();owned=[]
refs=[('initial',p/'media-readback.json'),('diagnostic',p/'diagnostic01/media-readback.json'),('green',p/'green01/media-readback.json'),('cleanup',p/'cleanup-medium-readback.json')]
for tag,ref in refs:
 m=json.loads(ref.read_text());target=out/(tag+'.iso');subprocess.run(['scp','-q','workhorse:'+m['medium'],str(target)],check=True);assert sha(target)==m['sha256'];owned.append({'path':m['medium'],'sha256':m['sha256'],'exported':str(target.relative_to(p))})
expected={}
for part,prefix in ((p,''),(p/'diagnostic01','diagnostic01/'),(p/'green01','green01/')):
 for f in (part/'input').rglob('*'):
  if f.is_file():expected[prefix+'input/'+str(f.relative_to(part/'input'))]=sha(f)
 for name in ('Start.ps1','input-manifest.json'):
  expected[prefix+name]=sha(part/name)
 for f in part.glob('*.bundle'):expected[prefix+f.name]=sha(f)
 expected[prefix+'media-readback.json']=sha(part/'media-readback.json')
for name in ('cleanup.ps1','cleanup-host-manifest.json'):expected['cleanup/'+name]=sha(p/name)
expected['cleanup/media-readback.json']=sha(p/'cleanup-medium-readback.json')
expected['assemble-medium.py']=sha(p.parent/'windows-job-resources-20261025/assemble-medium.py')
original='/var/lib/libvirt/images/rhai-win11-quality/acceptance-20261008T125846Z-b7f83433/monitor-fixture02.iso'
subprocess.run(['ssh','workhorse','virsh change-media rhai-win11-quality sdc '+shlex.quote(original)+' --live --force'],check=True)
code='''from pathlib import Path
import subprocess,json,hashlib,shutil
root=Path(ROOT);expected=EXPECTED;owned=OWNED;original=ORIGINAL
blocks=subprocess.check_output(['virsh','domblklist','rhai-win11-quality','--details'],text=True)
assert original in blocks and '/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso' in blocks
assert root.is_dir() and not root.is_symlink() and str(root).startswith('/var/roothome/projects/rhai-creation-failure-20261025-')
entries=list(root.rglob('*'));assert len(entries)<256 and all(not f.is_symlink()for f in entries)
actual={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest()for f in entries if f.is_file()};assert actual==expected,'Unexpected host staging inventory; preserve it'
for item in owned:
 f=Path(item['path']);assert str(f) not in blocks and hashlib.sha256(f.read_bytes()).hexdigest()==item['sha256']
for item in owned:Path(item['path']).unlink()
shutil.rmtree(root)
assert not root.exists() and all(not Path(x['path']).exists()for x in owned)
print(json.dumps({'retired_media':owned,'original_sdc_restored':original,'original_sdb_preserved':True,'host_staging':str(root),'host_staging_entries':len(entries),'host_staging_files':len(actual),'host_staging_absent':True,'all_exact_images_absent':True,'foreign_resources_touched':False}))
'''.replace('ROOT',repr(b['host_source_root'])).replace('EXPECTED',repr(expected)).replace('OWNED',repr(owned)).replace('ORIGINAL',repr(original))
r=subprocess.run(['ssh','workhorse','python3 -c '+shlex.quote(code)],capture_output=True,text=True);(p/'host-retirement.stdout').write_text(r.stdout);(p/'host-retirement.stderr').write_text(r.stderr);r.check_returncode();(p/'host-retirement.json').write_text(r.stdout);print(r.stdout)
