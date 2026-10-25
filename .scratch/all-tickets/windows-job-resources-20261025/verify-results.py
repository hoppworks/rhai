"""Validate saved real Windows RED/GREEN originals; never launch workloads."""
from pathlib import Path,PureWindowsPath
import json,hashlib,re,zlib,base64
p=Path(__file__).resolve().parent
read=lambda f:json.loads(f.read_text())
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
red=read(p/'red/binding.json');green=read(p/'green/binding.json')
results=[];host=[]
for packet,caseid,tag,contract,phase in ((p/'red',red['id'],red['tag'],'job-resources','RED'),(p/'green',green['id'],green['tag'],'job-resources','GREEN'),(p/'green',green['environment_id'],green['environment_tag'],'environment','GREEN')):
 b=read(packet/'binding.json');r=read(packet/(tag+'-export-readback.json'));root=packet/(tag+'-export');o=read(root/'observer.json')
 assert o==r['begin']and o['id']==caseid==r['end']['id']and o['accepted']and r['end']['accepted']and o['exit']==r['end']['exit']==0
 assert o['phase']==phase and o['contract']==contract and o['fresh_host_record']and o['exact_driver_exited']and o['pipes_drained']and not o['retained_driver_handles']and not o['parent_environment_changed']
 assert o['runtime_absent_readback']and o['runtime_absence_negative_control']
 scope=PureWindowsPath(o['scope']);assert scope.name in (b['control_scope_leaf'],b.get('environment_scope_leaf'))and PureWindowsPath(o['run'])==scope/'run'
 bo=read(root/'build-readback/build-observer.json');assert bo['accepted']and bo['native_started']and not bo['custody_indeterminate']and bo['exit']==0
 assert bo['input_manifest_sha256']==b['manifest_sha256']and bo['start_sha256']==b['start_sha256']
 manifest=(root/'build-readback/build-manifest.txt').read_text().splitlines();assert manifest[0]=='compiler_sha256=cf32cb7e8e5691b962e1b6f92b03d87409dd9e7afbed71c5bf77b8203cc56ee1'
 for name,h in b['files'].items():
  if name.endswith('.cs'):assert manifest.count(h+'  '+name)==1
 for name,h in o['retained_binaries'].items():assert manifest.count(h+'  build/'+name)==1
 assert o['fixture_sha256']==o['retained_binaries']['PayloadFixture.exe']
 js=list((root/'run').glob('.scoped-run-*.journal'));assert len(js)==1;rows=[]
 for raw in js[0].read_bytes().splitlines():
  size,crc,body=raw.split(b':',2);assert len(body)==int(size,16)and zlib.crc32(body)==int(crc,16);rows.append(body.decode('ascii').split('|'))
 assert [x[0]for x in rows]==['INTENT','IDENTITY','STAGED','LIFECYCLE','EVIDENCE','OUTCOME','REMOVE_INTENT','REMOVED']and len({x[1]for x in rows})==1
 fields=lambda row:dict(x.split('=',1)for x in row if '='in x)
 lc=fields(rows[3]);ev=fields(rows[4]);out=fields(rows[5]);rid=rows[1][2]
 assert all(rows[i][2]==rid for i in (3,4,5,6,7))and lc['operation']=='NONE'and lc['cleanup']=='NONE'and lc['cleanup_confirmed']=='1'
 expected='0000002A'if phase=='RED'else '00000000'
 assert ev['proof']=='EXACT'and ev['exit']==expected==out['payload']and ev['supervision']==out['supervision']=='PayloadExited'and out['cleanup']=='CONFIRMED'and out['host_exported']=='0'and out['runtime_removed']=='0'
 assert ev['manifest']==out['evidence']and ev['evidence_identity']==out['evidence_identity']
 assert PureWindowsPath(rows[0][2])==PureWindowsPath(o['allocated_runtime'])and PureWindowsPath(rows[0][2]).parent==PureWindowsPath(o['run'])
 snapshots=list((root/'run').glob('.scoped-evidence-*'));assert len(snapshots)==1;snap=snapshots[0]
 for key,name in (('manifest','manifest.txt'),('stdout','stdout.log'),('stderr','stderr.log')):assert sha(snap/name).upper()==ev[key]
 assert (snap/'manifest.txt').read_text().splitlines()[0].split('|')[2]==rid
 assert sha(snap/'runtime/fixture.exe')==o['fixture_sha256']
 identities=[]
 if contract=='job-resources':
  assert o['job_actors_stopped']
  for role,suffix in (('root',''),('child','.child'))if phase=='GREEN'else (('root',''),):
   text=(snap/('runtime/payload-job-resources.txt'+suffix)).read_bytes();lines=text.decode().splitlines();values=dict(line.split('=',1)for line in lines);assert len(lines)==7 and values==o['job_resources_observed'][role]
   assert all(re.fullmatch(r'[1-9][0-9]*',values[k])for k in ('pid','creation'))
   identities.append({'pid':int(values['pid']),'creation':int(values['creation'])})
   wanted={'flags':'00002308','active_process_limit':'16','process_memory_bytes':'1073741824','job_memory_bytes':'2147483648','contract':'PASS'}
   if phase=='GREEN':assert all(values[k]==v for k,v in wanted.items())
   else:assert values['flags']=='00002000'and all(values[k]=='0'for k in ('active_process_limit','process_memory_bytes','job_memory_bytes'))and values['contract']=='FAIL'
  if phase=='GREEN':assert len({x['pid']for x in identities})==2 and o['job_resources_green']and o['job_resources_sensitivity']and(snap/'runtime/payload-job-resources.txt.work').read_bytes()==b'both-actors-resource-bounded\r\n'
  else:assert o['job_resources_red']and b'FAIL native payload Job resource contract'in(snap/'stderr.log').read_bytes()
 else:
  assert o['environment_contract_green']and not o['environment_mismatches']
  lines=(snap/'runtime/payload-environment.txt').read_text().splitlines();assert len(lines)==7 and lines[-1]=='contract=PASS'
  cwd=PureWindowsPath(base64.b64decode(lines[0].split('=',1)[1]).decode());assert cwd==PureWindowsPath(o['allocated_runtime']);work=cwd/'work'
  wanted={'AGENT_RUNTIME_DIR':cwd,'TMP':work/'temp','TEMP':work/'temp','CARGO_HOME':work/'cargo-home','CARGO_TARGET_DIR':work/'target'}
  for line in lines[1:6]:
   key,data=line.split('=',1);assert PureWindowsPath(base64.b64decode(data).decode())==wanted[key]and PureWindowsPath(o['environment_observed'][key])==wanted[key]
 results.append({'tag':tag,'contract':contract,'phase':phase,'expected_contract_result':'FAIL'if phase=='RED'else 'PASS','driver_exit':0,'payload_exit':expected,'crc_records':len(rows),'frames':r['frames'],'files':len(r['files']),'actor_identities':identities,'source':b['files']['tools/windows-scoped-runner/MonitorPayloadJob.cs']})
 host.append({'id':caseid,'scope':o['scope'],'runtime':o['allocated_runtime'],'identities':identities,'files':r['files'],'fixture_sha256':o['fixture_sha256'],'phase':phase,'contract':contract})
(p/'semantic-results.json').write_text(json.dumps({'accepted':True,'cases':results,'native_build_allocations':2,'compiler_processes':8,'compiler_processes_detail':'six binary compiles plus two canonical deliberate missing-source controls','public_drivers':3,'quota_exhaustion_or_project_command_proof':False},indent=2)+'\n')
(p/'host-accepted-readback.json').write_text(json.dumps({'accepted':True,'cases':host},indent=2)+'\n')
print((p/'semantic-results.json').read_text())
