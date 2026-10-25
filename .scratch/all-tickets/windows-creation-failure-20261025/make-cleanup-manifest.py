"""Bind accepted results and failed originals to seven exact inactive scopes."""
from pathlib import Path,PureWindowsPath
import json,hashlib,re
p=Path(__file__).resolve().parent;read=lambda f:json.loads(f.read_text());sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
rootbind=read(p/'binding.json');scopes=[];successes=[];failed=[]
for part in (p,p/'diagnostic01',p/'green01'):
 b=read(part/'binding.json');first=b['controls'][0];root=part/(first['tag']+'-export');o=read(root/'observer.json');private=PureWindowsPath(o['scope']).parent
 run='run/monitor-source-'+b['nonce'];files={}
 for f in (root/'build-readback').rglob('*'):
  if f.is_file():
   rel=str(f.relative_to(root/'build-readback'));dest=rel if rel in ('build-observer.json','bootstrap.stdout','bootstrap.stderr')else run+'/'+rel;files[dest]=sha(f)
 for name,h in b['files'].items():
  assert sha(part/'input'/name)==h
  files['source-input/'+name]=h
  if name.endswith('.cs'):files[run+'/input/'+name]=h
 for line in (root/'build-readback/build-manifest.txt').read_text().splitlines():
  if re.match('^[0-9a-f]{64}  build/',line):files[run+'/'+line[66:]]=line[:64]
 bo=read(root/'build-readback/build-observer.json');assert bo['accepted'] and bo['exit']==0 and not bo['custody_indeterminate']
 scopes.append({'scope':str(private/b['build_scope_leaf']),'kind':'completed-build','files':files,'empty_dirs':[run+'/temp']})
 for c in b['controls']:
  r=read(part/(c['tag']+'-export-readback.json'));root=part/(c['tag']+'-export');o=read(root/'observer.json')
  for name,item in r['files'].items():assert sha(root/name)==item['sha256']
  assert o['id']==c['id'] and PureWindowsPath(o['scope']).name==c['scope_leaf'] and o['exact_driver_exited'] and o['pipes_drained'] and not o['custody_pending'] and not o['retained_log_resources'] and o['process_disposed'] and o['owned_executables_stopped']
  for key in ('job_empty','process_closed_or_absent','thread_closed_or_absent','job_closed'):assert o['native_trace'][key]=='True'
  runtime=PureWindowsPath(o['allocated_runtime']);rel='run/'+runtime.name
  assert runtime.parent==PureWindowsPath(o['run'])
  marker=root/rel/'must-not-run.txt';assert marker.read_bytes()==b'protected-before-failed-association\r\n'
  record={'scope':o['scope'],'kind':'creation-control'if o['accepted']else'failed-creation-control','id':c['id'],'profile':c['profile'],'runtime':o['allocated_runtime'],'trace':o['native_trace'],'original_accepted':o['accepted'],'files':{name:item['sha256']for name,item in r['files'].items()},'empty_dirs':[rel+'/work',rel+'/work/temp',rel+'/work/cargo-home',rel+'/work/target']}
  if o['accepted']:
   a=read(part/'host-accepted-readback.json');match=[x for x in a['cases']if x['id']==c['id']];assert len(match)==1 and match[0]['accepted']
   successes.append({'part':str(part.relative_to(p)),'id':c['id'],'profile':c['profile'],'host_readback_sha256':sha(part/'host-accepted-readback.json'),'source_manifest_sha256':b['input_manifest_sha256'],'journal_crcs':match[0]['journal_crcs']})
  else:failed.append({'part':str(part.relative_to(p)),'id':c['id'],'failure':o['failure'],'trace':o['native_trace'],'product_acceptance':False,'original_bytes_preserved':True})
  scopes.append(record)
assert len(scopes)==7 and len(successes)==2 and len(failed)==2
combined={'accepted_named_criteria':True,'criteria':successes,'failed_originals':failed,'native_profile_compilers':4,'native_public_drivers':4,'profile_build_allocations':3,'new_production_fix_count':1,'denial_repeats':0,'full_windows_gate':False,'full_af_package':False,'native_cargo_started':False,'retained_driver_payload':rootbind['retained']}
(p/'combined-acceptance.json').write_text(json.dumps(combined,indent=2)+'\n')
(p/'cleanup-host-manifest.json').write_text(json.dumps({'nonce':rootbind['nonce'],'accepted_for_cleanup':True,'host_receipt_sha256':sha(p/'combined-acceptance.json'),'scopes':scopes,'retain':rootbind['retained']},indent=2)+'\n')
print('Seven scope file counts',[len(x['files'])for x in scopes])
