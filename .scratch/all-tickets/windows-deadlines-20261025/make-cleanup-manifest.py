"""Bind completed deadline proofs plus interrupted originals to four exact roots."""
from pathlib import Path,PureWindowsPath
import json,hashlib,re
p=Path(__file__).resolve().parent;read=lambda f:json.loads(f.read_text());sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();b=read(p/'binding.json');accepted=read(p/'host-accepted-readback.json')
assert accepted['accepted'] and accepted['all_required_control_modes_accepted'] and len(accepted['cases'])==2
scopes=[];first=b['controls'][0];root=p/(first['tag']+'-export');bo=read(root/'build-readback/build-observer.json');assert bo['accepted'] and bo['exit']==0 and not bo['custody_indeterminate']
private=PureWindowsPath(bo['session']).parent;run='run/monitor-source-'+b['nonce'];files={}
for f in (root/'build-readback').rglob('*'):
 if f.is_file():
  rel=f.relative_to(root/'build-readback').as_posix();dest=rel if rel in ('build-observer.json','bootstrap.stdout','bootstrap.stderr')else run+'/'+rel;files[dest]=sha(f)
for name,h in b['files'].items():
 assert sha(p/'input'/name)==h
 files['source-input/'+name]=h
 if name.endswith('.cs'):files[run+'/input/'+name]=h
for line in (root/'build-readback/build-manifest.txt').read_text().splitlines():
 if re.match('^[0-9a-f]{64}  build/',line):files[run+'/'+line[66:]]=line[:64]
scopes.append({'scope':bo['session'],'kind':'completed-build','files':files,'empty_dirs':[run+'/temp']})
for c in b['controls']:
 root=p/(c['tag']+'-export');r=read(p/(c['tag']+'-export-readback.json'));o=read(root/'observer.json');match=[x for x in accepted['cases']if x['id']==c['id']];assert len(match)==1 and match[0]['accepted'] and match[0]['crc_records']==8
 for name,item in r['files'].items():assert sha(root/name)==item['sha256']
 assert o['accepted'] and o['exact_driver_exited'] and o['pipes_drained'] and o['process_disposed'] and o['owned_executables_stopped'] and o['actors_stopped'] and o['runtime_absent_readback'] and not o['custody_pending'] and not o['retained_driver_handles']
 empty=[]
 for m in (root/'run').glob('.scoped-evidence-*/manifest.txt'):
  snapshot=m.parent.relative_to(root).as_posix()+'/runtime'
  for line in m.read_text().splitlines():
   fields=line.split('|');assert len(fields)==7
   if fields[1]=='D':empty.append(snapshot+('/'+fields[0].replace('\\','/')if fields[0]else''))
 scopes.append({'scope':o['scope'],'kind':'accepted-control','id':c['id'],'mode':c['mode'],'actors':o['actors'],'files':{name:x['sha256']for name,x in r['files'].items()},'empty_dirs':empty})
old=read(p/'interrupted-readback/cleanup-host-manifest.json');r=read(p/'interrupted01-export-readback.json');root=p/'interrupted01-export';assert r['complete'] and not r['begin']['accepted'] and not r['end']['accepted'] and r['begin']['readback_only'] and not r['begin']['native_reexecution'] and not r['begin']['native_removal_claimed'] and r['begin']['id']==old['readback_id'] and r['begin']['scope']==old['scope'] and r['begin']['boot_filetime']>=old['minimum_new_boot_filetime']>old['old_driver_creation']
for name,item in r['files'].items():assert sha(root/name)==item['sha256']
scopes.append({'scope':old['scope'],'kind':'interrupted-control','id':old['original_case_id'],'old_driver_pid':old['old_driver_pid'],'old_driver_creation':old['old_driver_creation'],'boot_filetime':r['begin']['boot_filetime'],'files':{name:x['sha256']for name,x in r['files'].items()},'empty_dirs':r['begin']['directories'],'native_removal_claimed':False})
assert len(scopes)==4 and len({x['scope']for x in scopes})==4
out={'nonce':b['nonce'],'accepted_for_cleanup':True,'host_receipt_sha256':sha(p/'host-accepted-readback.json'),'interrupted_originals_sha256':sha(p/'interrupted01-export-readback.json'),'scopes':scopes,'keep_other_resources':True,'automatic_removal_of_interrupted_runtime_claimed':False}
(p/'cleanup-host-manifest.json').write_text(json.dumps(out,indent=2)+'\n');print('Four exact own roots/file counts:',[len(x['files'])for x in scopes])
