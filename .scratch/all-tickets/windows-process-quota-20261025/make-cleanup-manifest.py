"""Bind exactly completed own quota scopes; keep the compatible default build."""
from pathlib import Path,PureWindowsPath
import json,hashlib,re,zlib
p=Path(__file__).resolve().parent
read=lambda f:json.loads(f.read_text())
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
latest=read(p/'attempt04/binding.json');accepted=read(p/'attempt04/host-accepted-readback.json');assert accepted['accepted']
scopes=[]
for packet in (p,p/'attempt02',p/'attempt03',p/'attempt04'):
 b=read(packet/'binding.json');controls=b['controls']if packet.name=='attempt04'else b['controls'][:1]
 for c in controls:
  root=packet/(c['tag']+'-export');r=read(packet/(c['tag']+'-export-readback.json'));o=read(root/'observer.json')
  assert r['complete']and o['exact_driver_exited']and o['pipes_drained']and o['process_disposed']and o['owned_executables_stopped']and not o['custody_pending']and not o['retained_driver_handles']
  for name,x in r['files'].items():assert sha(root/name)==x['sha256']
  journals=list((root/'run').glob('.scoped-run-*.journal'));assert len(journals)==1;rows=[]
  for line in journals[0].read_bytes().splitlines():
   n,crc,body=line.split(b':',2);assert int(n,16)==len(body)and zlib.crc32(body)==int(crc,16);rows.append(body.decode().split('|'))
  assert [x[0]for x in rows]==['INTENT','IDENTITY','STAGED','LIFECYCLE','EVIDENCE','OUTCOME','REMOVE_INTENT','REMOVED']
  fields=lambda row:dict(x.split('=',1)for x in row if '='in x)
  assert fields(rows[4])['proof']=='EXACT'and fields(rows[5])['cleanup']=='CONFIRMED'
  runtime=rows[0][2];assert PureWindowsPath(runtime).parent==PureWindowsPath(o['run'])and re.fullmatch('scoped-[0-9a-f]{32}',PureWindowsPath(runtime).name)
  actors={(o['driver_pid'],o['driver_creation'])};empty=[]
  for snap in (root/'run').glob('.scoped-evidence-*'):
   for name in ('quota-members.txt','quota-recovered-members.txt','quota-excess.txt'):
    f=snap/'runtime'/name
    if f.exists():
     for line in f.read_text().splitlines():
      m=re.match('pid=([1-9][0-9]*);creation=([1-9][0-9]*)',line);assert m;actors.add((int(m[1]),int(m[2])))
   for line in (snap/'manifest.txt').read_text().splitlines():
    values=line.split('|')
    if values[1]=='D':empty.append(snap.relative_to(root).as_posix()+'/runtime'+('/'+values[0].replace('\\','/')if values[0]else''))
  if o.get('job_actors_stopped'):
   for actor in o['job_resources_observed'].values():actors.add((int(actor['pid']),int(actor['creation'])))
  scopes.append({'scope':o['scope'],'kind':'completed-control','id':o['id'],'contract':o['contract'],'expected_accepted':o['accepted'],'runtime':runtime,'actors':[{'pid':pid,'creation':creation}for pid,creation in sorted(actors)],'files':{name:x['sha256']for name,x in r['files'].items()},'empty_dirs':empty})
for tag in ('attempt02',):
 packet=p/tag;b=read(packet/'binding.json');root=packet/(b['controls'][0]['tag']+'-export')/'fixture-build-readback';bo=read(root/'build-observer.json');assert bo['accepted']and bo['exit']==0 and not bo['custody_indeterminate'];run='run/monitor-source-'+b['nonce'];files={}
 for f in root.rglob('*'):
  if f.is_file():
   rel=f.relative_to(root).as_posix();files[rel if rel in ('build-observer.json','bootstrap.stdout','bootstrap.stderr')else run+'/'+rel]=sha(f)
 for name,h in b['files'].items():
  assert sha(packet/'input'/name)==h;files['source-input/'+name]=h
  if name.endswith('.cs'):files[run+'/input/'+name]=h
 for line in (root/'build-manifest.txt').read_text().splitlines():
  if re.match('^[0-9a-f]{64}  build/',line):files[run+'/'+line[66:]]=line[:64]
 scopes.append({'scope':bo['session'],'kind':'completed-build','id':bo['id'],'files':files,'empty_dirs':[run+'/temp']})
for tag in ('build03-readback','build04-readback'):
 q=p/tag;export_tag='build03'if tag=='build03-readback'else'build04';r=read(q/(export_tag+'-export-readback.json'));root=q/(export_tag+'-export');assert r['complete']and r['begin']['readback_only']and r['begin']['build_accepted']and not r['begin']['native_reexecution']
 for name,x in r['files'].items():assert sha(root/name)==x['sha256']
 scopes.append({'scope':r['begin']['scope'],'kind':'completed-build','id':read(root/'build-observer.json')['id'],'files':{name:x['sha256']for name,x in r['files'].items()},'empty_dirs':r['begin']['directories']})
retained=read(p/'retained-default-build.json');assert retained['scope']not in [x['scope']for x in scopes]
assert len(scopes)==9 and len({x['scope']for x in scopes})==9
out={'nonce':latest['nonce'],'accepted_for_cleanup':True,'host_receipt_sha256':sha(p/'attempt04/host-accepted-readback.json'),'build_readback_sha256':sha(q/'build04-export-readback.json'),'scopes':scopes,'retained':retained,'retained_manifest_sha256':sha(p/'quota01-export/build-readback/build-manifest.txt'),'keep_other_resources':True}
(p/'cleanup-host-manifest.json').write_text(json.dumps(out,indent=2)+'\n');print('Exact9scope file counts',[len(x['files'])for x in scopes])
