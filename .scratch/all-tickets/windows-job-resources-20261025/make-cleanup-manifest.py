"""Retire RED build/three exported controls; keep useful GREEN build explicitly."""
from pathlib import Path,PureWindowsPath
import json,hashlib
p=Path(__file__).resolve().parent
read=lambda f:json.loads(f.read_text());sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
accepted=read(p/'host-accepted-readback.json');assert accepted['accepted']
b=read(p/'red/binding.json');root=p/'red'/(b['tag']+'-export');o=read(root/'observer.json');private=PureWindowsPath(o['scope']).parent
buildscope=str(private/b['build_scope_leaf']);run='run/monitor-source-'+b['nonce'];files={}
for f in(root/'build-readback').rglob('*'):
 if f.is_file():
  rel=str(f.relative_to(root/'build-readback'));dest=rel if rel in('bootstrap.stdout','bootstrap.stderr','build-observer.json')else run+'/'+rel;files[dest]=sha(f)
for name,h in b['files'].items():
 files['source-input/'+name]=h
 if name.endswith('.cs'):files[run+'/input/'+name]=h
for name,h in o['retained_binaries'].items():files[run+'/build/'+name]=h
scopes=[{'scope':buildscope,'kind':'completed-build','files':files,'empty_dirs':[run+'/temp']}]
for c in accepted['cases']:
 files={name:record['sha256']for name,record in c['files'].items()};files['input/fixture.exe']=c['fixture_sha256']
 scopes.append(dict(c,kind=c['contract']+'-control',files=files,empty_dirs=[]))
g=read(p/'green/binding.json');retained={'scope':str(private/g['build_scope_leaf']),'build':str(private/g['build_scope_leaf']/'run'/('monitor-source-'+g['nonce'])/'build'),'source_pins':g['files'],'binaries':read(p/'green'/(g['tag']+'-export/observer.json'))['retained_binaries'],'expires_utc':read(p/'execution-binding.json')['cache_expires_utc'],'purpose':'same-source compatible immediate custody followups; preserve one useful current build rather than duplicate/rebuild for Session boundary','retire_at':'earlier ended/cancelled reuse or expiry, after exact ownership/inactivity/proof checks'}
(p/'retained-green-build.json').write_text(json.dumps(retained,indent=2)+'\n')
(p/'cleanup-host-manifest.json').write_text(json.dumps({'nonce':b['nonce'],'accepted_for_cleanup':True,'host_receipt_sha256':sha(p/'host-accepted-readback.json'),'scopes':scopes,'retain':retained},indent=2)+'\n')
print('Retire scope file counts',[(x['kind'],len(x['files']))for x in scopes]);print('Retain',retained['build'])
