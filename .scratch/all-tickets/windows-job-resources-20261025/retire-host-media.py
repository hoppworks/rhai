"""Export/hash-check only this package's three exact media, restore original sdc."""
from pathlib import Path
import json,subprocess,hashlib,shlex
p=Path(__file__).resolve().parent;out=p/'media';out.mkdir()
refs=[('red',p/'red/media-readback.json'),('green',p/'green/media-readback.json'),('cleanup',p/'cleanup-medium-readback.json')]
owned=[]
for tag,ref in refs:
 m=json.loads(ref.read_text());target=out/(tag+'.iso')
 subprocess.run(['scp','-q','workhorse:'+m['medium'],str(target)],check=True)
 assert hashlib.sha256(target.read_bytes()).hexdigest()==m['sha256'];owned.append({'path':m['medium'],'sha256':m['sha256'],'exported':str(target.relative_to(p))})
original='/var/lib/libvirt/images/rhai-win11-quality/acceptance-20261008T125846Z-b7f83433/monitor-fixture02.iso'
subprocess.run(['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','workhorse','virsh change-media rhai-win11-quality sdc '+shlex.quote(original)+' --live --force'],check=True)
code='''from pathlib import Path
import hashlib,subprocess,json
owned=OWNED
blocks=subprocess.check_output(['virsh','domblklist','rhai-win11-quality','--details'],text=True)
assert ORIGINAL in blocks
assert '/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso' in blocks
for item in owned:
 f=Path(item['path']);assert str(f) not in blocks and hashlib.sha256(f.read_bytes()).hexdigest()==item['sha256']
for item in owned:Path(item['path']).unlink()
assert all(not Path(x['path']).exists()for x in owned)
print(json.dumps({'retired':owned,'original_sdc_restored':ORIGINAL,'original_sdb_preserved':True,'all_exact_images_absent':True}))
'''.replace('OWNED',repr(owned)).replace('ORIGINAL',repr(original))
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','workhorse','python3 -c '+shlex.quote(code)],capture_output=True,text=True,check=True)
(p/'media-retirement.json').write_text(r.stdout);print(r.stdout)
