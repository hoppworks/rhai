"""Independent saved-original readback for the finite native quota package."""
from pathlib import Path,PureWindowsPath
import json,hashlib,re,zlib,base64,sys
p=Path(sys.argv[1]).resolve();b=json.loads((p/'binding.json').read_text())
read=lambda f:json.loads(f.read_text())
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
results=[]
for c in b['controls']:
 root=p/(c['tag']+'-export');r=read(p/(c['tag']+'-export-readback.json'));o=read(root/'observer.json')
 assert r['begin']['id']==r['end']['id']==o['id']==c['id'] and r['begin']['accepted']==r['end']['accepted']==o['accepted']==True
 assert r['begin']['exit']==r['end']['exit']==o['exit']==0 and o['contract']==c['contract'] and o['phase']=='GREEN' and not o['failure']
 for name,item in r['files'].items():assert sha(root/name)==item['sha256'] and (root/name).stat().st_size==item['length'],name
 assert len(r['files'])<=64 and sum(x['length']for x in r['files'].values())<=16777216
 for key in ('fresh_host_record','driver_launched','exact_driver_exited','pipes_drained','process_disposed','owned_executables_stopped','runtime_absent_readback','runtime_absence_negative_control'):assert o[key],key
 for key in ('custody_pending','observer_kill_used','retained_driver_handles','parent_environment_changed','product_run'):assert not o[key],key
 assert len(o['channel_closure'])==2
 for channel in o['channel_closure']:assert all(channel[k]for k in ('reader_acquired','writer_acquired','reader_disposed','writer_disposed','eof')) and not channel['error'] and not channel['pending_task']
 assert PureWindowsPath(o['scope']).name==c['scope_leaf'] and PureWindowsPath(o['run'])==PureWindowsPath(o['scope'])/'run'
 manifests={}
 for component,original in (('build-readback',b['reused_public_build']),('fixture-build-readback',b)):
  bo=read(root/component/'build-observer.json');assert bo['accepted'] and bo['native_started'] and bo['exit']==0 and not bo['custody_indeterminate'] and not bo['driver_launched']
  assert bo['input_manifest_sha256']==original['input_manifest_sha256'] and bo['start_sha256']==original['start_sha256'] and bo['powershell_version'].startswith('5.1.') and bo['os_version']
  lines=(root/component/'build-manifest.txt').read_text().splitlines();assert lines[0]=='compiler_sha256='+b['reused_public_build']['compiler_sha256']
  manifests[component]={x[66:]:x[:64]for x in lines if re.match(r'^[0-9a-f]{64}  ',x)}
 for name,h in b['files'].items():
  assert sha(p/'input'/name)==h
  if name.endswith('.cs'):
   assert manifests['fixture-build-readback'][name]==h
   if '/fixtures/'not in name:assert manifests['build-readback'][name]==h
 for name in ('ScopedRunner.exe','MonitorAcceptanceDriver.exe'):assert sha(root/'bin'/name)==o['retained_binaries'][name]==manifests['build-readback']['build/'+name]==b['reused_public_build']['binaries'][name]
 assert sha(root/'input/fixture.exe')==o['fixture_sha256']==manifests['fixture-build-readback']['build/PayloadFixture.exe']
 assert sha(root/'fixture-build-readback/build-manifest.txt')==o['fixture_build_manifest_sha256']
 assert len(list((root/'fixture-build-readback/logs').glob('compile-*.stdout.txt')))==1
 owner_rows=[json.loads(x)for x in (root/'fixture-build-readback/logs/job-members.jsonl').read_text().splitlines()]
 assert [x['label']for x in owner_rows]==['before-compiler','after-exact-compiler-exit'] and all(x['assigned']==x['listed']==len(x['members'])==1 and x['members'][0]['id']==x['owner']for x in owner_rows)
 run=root/'run';journals=list(run.glob('.scoped-run-*.journal'));assert len(journals)==1;data=journals[0].read_bytes();rows=[]
 while data:
  assert re.fullmatch(rb'[0-9A-F]{4}:[0-9A-F]{8}:',data[:14]);length=int(data[:4],16);crc=int(data[5:13],16);body=data[14:14+length]
  assert len(body)==length and all(32<=x<=126 for x in body) and data[14+length:15+length]==b'\n' and zlib.crc32(body)==crc
  rows.append(body.decode('ascii').split('|'));data=data[15+length:]
 assert [x[0]for x in rows]==['INTENT','IDENTITY','STAGED','LIFECYCLE','EVIDENCE','OUTCOME','REMOVE_INTENT','REMOVED'] and len({x[1]for x in rows})==1
 identity=rows[1][2];assert re.fullmatch('[0-9A-F]{16}:[0-9a-f]{32}',identity) and all(x[2]==identity for x in rows[3:])
 fields=lambda row:dict(x.split('=',1)for x in row if '='in x)
 lifecycle=fields(rows[3]);ev=fields(rows[4]);out=fields(rows[5])
 assert lifecycle['operation']==lifecycle['cleanup']=='NONE' and lifecycle['cleanup_confirmed']=='1'
 assert ev['proof']=='EXACT' and ev['exit']==out['payload']=='00000000' and ev['supervision']==out['supervision']=='PayloadExited'
 assert out['cleanup']=='CONFIRMED' and out['host_exported']=='0' and out['runtime_removed']=='0' and ev['manifest']==out['evidence'] and ev['evidence_identity']==out['evidence_identity']
 assert PureWindowsPath(rows[0][2])==PureWindowsPath(o['allocated_runtime']) and PureWindowsPath(o['allocated_runtime']).parent==PureWindowsPath(o['run'])
 snaps=list(run.glob('.scoped-evidence-*'));assert len(snaps)==1;snap=snaps[0];runtime=snap/'runtime'
 for key,name in (('manifest','manifest.txt'),('stdout','stdout.log'),('stderr','stderr.log')):assert sha(snap/name).upper()==ev[key]
 assert sha(runtime/'fixture.exe')==o['fixture_sha256'];names=set()
 for line in (snap/'manifest.txt').read_text().splitlines():
  rel,kind,file_identity,size,creation,attributes,digest=line.split('|');assert not PureWindowsPath(rel).is_absolute() and '..'not in PureWindowsPath(rel).parts and re.fullmatch('[0-9A-F]{16}:[0-9a-f]{32}',file_identity)
  file=runtime.joinpath(*PureWindowsPath(rel).parts);assert rel not in names;names.add(rel)
  if kind=='F':assert file.is_file() and file.stat().st_size==int(size) and sha(file).upper()==digest
  else:assert kind=='D' and file.is_dir() and size=='0' and not digest
 assert ''in names and {str(PureWindowsPath(*f.relative_to(runtime).parts))for f in runtime.rglob('*')}==names-{''}
 assert (snap/'manifest.txt').read_text().splitlines()[0].split('|')[2]==identity
 actors=[];detail={}
 if c['contract']=='job-quota':
  for key in ('job_quota_green','job_quota_sensitivity','quota_protected_sensitivity','quota_actors_stopped'):assert o[key],key
  assert o['driver_elapsed_seconds']<110
  q=dict(x.split('=',1)for x in (runtime/'payload-job-quota.txt').read_bytes().decode().rstrip('\r\n').split(';'))
  assert q==o['job_quota_observed']['admission'] and q['active_limit']==q['payload_count']=='16' and q['spawned']=='15' and q['contract']=='PASS'
  assert q['excess_user_code']=='False' and q['protected_unchanged_at_denial']==q['countercase_user_code']=='True'
  before=list(map(int,q['members'].split(',')));after=list(map(int,q['members_after'].split(',')));recovered=list(map(int,q['recovered_members'].split(',')))
  assert before==after==sorted(set(before)) and 16<=len(before)<=32 and 15<=len(recovered)<=32 and recovered==sorted(set(recovered))
  def census(name):
   values=[]
   for row in (runtime/name).read_text().splitlines():
    m=re.fullmatch(r'pid=([1-9][0-9]*);creation=([1-9][0-9]*)',row);assert m;values.append({'pid':int(m[1]),'creation':int(m[2])})
   return values
  full=census('quota-members.txt');again=census('quota-recovered-members.txt');assert [x['pid']for x in full]==before and [x['pid']for x in again]==recovered
  fixture=[{'pid':int(q['pid']),'creation':int(q['creation'])}]
  for index in range(15):
   m=re.fullmatch(rb'pid=([1-9][0-9]*);creation=([1-9][0-9]*);job_member=True\r\n',(runtime/('quota-child-%02d.txt'%index)).read_bytes());assert m;fixture.append({'pid':int(m[1]),'creation':int(m[2])})
  assert len({x['pid']for x in fixture})==16 and all(x in full for x in fixture)
  admission=(runtime/'payload-job-quota.txt.admission').read_bytes().decode();assert admission=='create_returned='+q['api_create_returned']+';api_error='+q['api_error']+';pid='+q['excess_pid']+';creation='+q['excess_creation']+';wait_confirmed='+q['excess_wait_confirmed']+';exit='+q['excess_exit']+';before='+q['members']+'\r\n'
  if q['api_create_returned']=='False':assert int(q['api_error'])>0 and q['excess_pid']==q['excess_creation']=='0' and q['excess_exit']=='NONE' and q['excess_wait_confirmed']=='False'
  else:assert q['api_create_returned']=='True' and q['api_error']=='0' and int(q['excess_pid'])>0 and int(q['excess_creation'])>0 and q['excess_wait_confirmed']=='True' and re.fullmatch('[0-9A-F]{8}',q['excess_exit']) and q['excess_exit']!='00000000'
  assert (runtime/'quota-protected-after-denial.txt').read_bytes()==b'protected-before-quota\r\n' and (runtime/'quota-protected.txt').read_bytes()==b'protected-before-quota\r\nEXCESS_PROCESS_RAN\r\n'
  recovery={'pid':int(q['recovery_pid']),'creation':int(q['recovery_creation'])};assert recovery in again and (runtime/'quota-excess.txt').read_bytes()==('pid=%s;creation=%s;job_member=True\r\n'%(recovery['pid'],recovery['creation'])).encode()
  def images(name,values,known):
   rows=[]
   for line in (runtime/name).read_text().splitlines():
    m=re.fullmatch(r'pid=([1-9][0-9]*);creation=([1-9][0-9]*);image_b64=([A-Za-z0-9+/]+={0,2})',line);assert m
    actor={'pid':int(m[1]),'creation':int(m[2])};assert actor in values;image=PureWindowsPath(base64.b64decode(m[3],validate=True).decode());wanted=PureWindowsPath(o['allocated_runtime'])/'fixture.exe'if actor in known else PureWindowsPath('C:/Windows/System32/conhost.exe');assert image==wanted;rows.append(actor)
   assert rows==values;return len(values)-len(known)
  helpers=images('quota-member-images.txt',full,fixture);recovered_helpers=images('quota-recovered-images.txt',again,[fixture[0]]+fixture[3:]+[recovery])
  trace=(runtime/'quota-observation.log').read_text();assert len(trace.encode())<=262144 and 'phase=failure'not in trace
  for phase,key in (('before-admission','accounting_full'),('settled-denial','accounting_after'),('recovered-countercase','accounting_recovered')):
   found=re.findall(r'^accounting;phase='+phase+r';success=True;native_error=0;total=([0-9]+);active=([0-9]+);terminated=([0-9]+)$',trace,re.M);assert len(found)==1 and found[0][1]==q[key]
  actors=full+again;detail={'ordinary_payloads':16,'helpers_full':helpers,'helpers_recovered':recovered_helpers,'member_count_full':len(full),'member_count_recovered':len(again),'native_admission_error':int(q['api_error']),'accounting_full':int(q['accounting_full']),'accounting_after':int(q['accounting_after']),'accounting_recovered':int(q['accounting_recovered']),'physical16_actor_claim':False}
 elif c['contract']=='job-resources':
  assert o['job_resources_green'] and o['job_resources_sensitivity'] and o['job_actors_stopped']
  for role,suffix in (('root',''),('child','.child')):
   v=dict(x.split('=',1)for x in (runtime/('payload-job-resources.txt'+suffix)).read_text().splitlines());assert v==o['job_resources_observed'][role]
   assert all(v[k]==expected for k,expected in {'flags':'00002308','active_process_limit':'16','process_memory_bytes':'1073741824','job_memory_bytes':'2147483648','contract':'PASS'}.items());actors.append({'pid':int(v['pid']),'creation':int(v['creation'])})
  assert (runtime/'payload-job-resources.txt.work').read_bytes()==b'both-actors-resource-bounded\r\n'
 else:
  assert o['environment_contract_green'] and not o['environment_mismatches'];lines=(runtime/'payload-environment.txt').read_text().splitlines();assert len(lines)==7 and lines[-1]=='contract=PASS'
  cwd=PureWindowsPath(base64.b64decode(lines[0].split('=',1)[1]).decode());assert cwd==PureWindowsPath(o['allocated_runtime']);work=cwd/'work'
  wanted={'AGENT_RUNTIME_DIR':cwd,'TMP':work/'temp','TEMP':work/'temp','CARGO_HOME':work/'cargo-home','CARGO_TARGET_DIR':work/'target'}
  for line in lines[1:6]:
   key,data=line.split('=',1);assert PureWindowsPath(base64.b64decode(data).decode())==wanted[key] and PureWindowsPath(o['environment_observed'][key])==wanted[key]
 results.append({'id':c['id'],'tag':c['tag'],'contract':c['contract'],'scope':o['scope'],'runtime':o['allocated_runtime'],'actor_identities':actors,'files':r['files'],'frames':r['frames'],'crc_records':8,'driver_exit':0,'elapsed_seconds':o['driver_elapsed_seconds'],'fixture_sha256':o['fixture_sha256'],'detail':detail})
record={'accepted':True,'base':b['base'],'cases':results,'all_launched_attempts_accepted':False,'earlier_quota_attempts_unaccepted':3,'cumulative_compilers':6,'cumulative_drivers':6,'full_windows_gate':False,'native_cargo_started':False}
(p/'host-accepted-readback.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'accepted':True,'cases':[{k:x[k]for k in ('tag','frames','crc_records','elapsed_seconds','detail')}for x in results]}))
