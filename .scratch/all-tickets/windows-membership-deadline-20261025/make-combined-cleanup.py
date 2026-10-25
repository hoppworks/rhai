"""Exact owned-resource inventory from accepted/closed native originals."""
from pathlib import Path, PureWindowsPath
import json,hashlib,re,zlib
p=Path(__file__).resolve().parent;b=json.loads((p/'binding.json').read_text())
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
read=lambda f:json.loads(f.read_text())
semantic=p/'attempt03/semantic-results.json'
semantic_hash=sha(semantic) if semantic.is_file() else None
oldbase=Path('.scratch/all-tickets/windows-workhorse-retirement-20261025')
oldscope=b['old_build']['build_scope'];private=PureWindowsPath(oldscope).parent
oldrun=str(PureWindowsPath(b['old_build']['build_relative']).parent.relative_to(PureWindowsPath('.local/share/agent-builds/rhai')/PureWindowsPath(oldscope).name)).replace('\\','/')
files={}
for f in (oldbase/'environment-green01-export/build-readback').rglob('*'):
 if f.is_file():
  relative=str(f.relative_to(oldbase/'environment-green01-export/build-readback'))
  dest=relative if relative in ('build-observer.json','bootstrap.stdout','bootstrap.stderr')else oldrun+'/'+relative
  files[dest.replace('\\','/')]=sha(f)
for name,h in read(oldbase/'original-packet/input-manifest.json')['files'].items():files['source-input/'+name]=h
for name,h in b['old_build']['source_pins'].items():files[oldrun+'/input/'+name]=h
for name,h in b['old_build']['binaries'].items():files[oldrun+'/build/'+name]=h
scopes=[{'scope':oldscope,'kind':'old-accepted-immutable-build','files':files,'empty_dirs':[oldrun+'/temp']}]
for packet in (p,p/'attempt02',p/'attempt03'):
 bb=read(packet/'binding.json');bo=read(packet/(bb['build_tag']+'-export/build-observer.json'));assert bo['accepted'] and bo['exact_build_exited'] and bo['exit']==0
 br=read(packet/(bb['build_tag']+'-export-readback.json'));newscope=str(private/bb['build_session_leaf']);newrun='run/monitor-source-'+bb['nonce'];files={n:x['sha256']for n,x in br['files'].items()}
 for name,h in bb['new_source_pins'].items():
  files['source-input/'+name]=h
  if not name.endswith('.ps1'):files[newrun+'/input/'+name]=h
 scopes.append({'scope':newscope,'kind':'new-accepted-fixture-build','files':files,'empty_dirs':[newrun+'/temp']})
 cases=bb['cases']if packet.name=='attempt03'else bb['cases'][:1]
 for c in cases:
  if packet==p:tag='membership-readback01'
  elif packet.name=='attempt02':tag='membership-readback02'
  else:tag=c['tag']
  root=packet/(tag+'-export')
  if packet.name=='attempt03' and not list((root/'run').glob('.scoped-run-*.journal')):
   # A failed final criterion needs the same bounded read-only export as the
   # first two cases. Missing closure proof is preserved, never treated as green.
   tag=c['tag']+'-readback';root=packet/(tag+'-export')
  r=read(packet/(tag+'-export-readback.json'));o=read(root/'observer.json');assert o['exact_driver_exited'] and o['pipes_drained'] and not o['retained_driver_handles']
  rows=[];journals=list((root/'run').glob('.scoped-run-*.journal'));assert len(journals)==1
  for line in journals[0].read_bytes().splitlines():
   size,crc,body=line.split(b':',2);assert len(body)==int(size,16) and zlib.crc32(body)==int(crc,16);rows.append(body.decode().split('|'))
  assert [x[0]for x in rows]==['INTENT','IDENTITY','STAGED','LIFECYCLE','EVIDENCE','OUTCOME','REMOVE_INTENT','REMOVED']
  field=lambda row:dict(x.split('=',1)for x in row if '='in x)
  ev=field(rows[4]);out=field(rows[5]);assert ev['proof']=='EXACT' and out['cleanup']=='CONFIRMED'
  snapshot=list((root/'run').glob('.scoped-evidence-*'));assert len(snapshot)==1;snapshot=snapshot[0]
  for key,name in (('manifest','manifest.txt'),('stdout','stdout.log'),('stderr','stderr.log')):assert sha(snapshot/name).upper()==ev[key]
  identities=[]
  for name in ('pair.identity','pair.child.identity'):
   m=re.fullmatch(rb'pid=([0-9]+) creation=([0-9]+)\r\n',(snapshot/'runtime'/name).read_bytes());assert m
   identities.append({'pid':int(m[1]),'creation':int(m[2])})
  assert len({x['pid']for x in identities})==2
  assert sha(snapshot/'runtime/fixture.exe')==bo['fixture_sha256']
  files={n:x['sha256']for n,x in r['files'].items()};files['input/fixture.exe']=bo['fixture_sha256']
  kind='accepted-control'if o['accepted']else 'failed-control-with-closed-job'
  assert o['id']==c['id'] and PureWindowsPath(o['scope'])==private/c['scope_leaf']
  assert PureWindowsPath(rows[0][2]).parent==PureWindowsPath(o['run'])
  if not o['accepted']:assert r['begin']['readback_only'] and not r['begin']['native_reexecution'] and r['begin']['runtime_absent']
  scopes.append({'scope':o['scope'],'kind':kind,'id':c['id'],'files':files,'empty_dirs':[],'runtime':rows[0][2],'identities':identities,'closed_job_verified':True,'criterion_accepted':o['accepted']})
assert len(scopes)==8 and len({s['scope']for s in scopes})==8
(p/'cleanup-host-manifest.json').write_text(json.dumps({'nonce':b['nonce'],'accepted_for_cleanup':True,'semantic_results_sha256':semantic_hash,'semantic_acceptance_is_cleanup_prerequisite':False,'scopes':scopes},indent=2)+'\n')
print('Exact scope file counts',[(x['kind'],len(x['files']))for x in scopes])
