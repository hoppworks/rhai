"""Read original serial readbacks and independent bytes; never launch native work."""
from pathlib import Path,PureWindowsPath
import json,hashlib,re,zlib,sys
p=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent
b=json.loads((p/'binding.json').read_text());sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
results=[]
selected=b['controls'] if len(sys.argv)<3 else [c for c in b['controls']if c['profile']==sys.argv[2]]
assert selected
for c in selected:
 r=json.loads((p/(c['tag']+'-export-readback.json')).read_text());root=p/(c['tag']+'-export')
 assert r['end']['accepted'] and r['end']['exit']==2
 for name,item in r['files'].items():assert sha(root/name)==item['sha256'],name
 o=json.loads((root/'observer.json').read_text())
 assert o['accepted'] and not o['failure'] and o['exit']==2 and o['id']==c['id']
 assert PureWindowsPath(o['scope']).name==c['scope_leaf'] and o['profile']==c['profile']
 for field in ('driver_launched','exact_driver_exited','pipes_drained','protected_marker_sensitivity','owned_executables_stopped','runtime_retained'):assert o[field],field
 for field in ('custody_pending','retained_log_resources','retained_driver_handles','parent_environment_changed','automatic_removal_claimed','product_run'):assert not o[field],field
 assert o['process_disposed'] and len(o['channel_closure'])==2
 for channel in o['channel_closure']:
  assert channel['reader_acquired'] and channel['reader_disposed'] and channel['writer_acquired'] and channel['writer_disposed'] and channel['eof'] and not channel['error'] and not channel['pending_task']
 stderr=(root/'bootstrap.stderr').read_text();assert 'journal must contain the exact eight-record completion grammar' in stderr
 assert 'whole-driver deadline' not in stderr and 'cleanup failure' not in stderr and 'pipe cleanup' not in stderr
 run=root/'run';journals=list(run.glob('.scoped-run-*'));assert len(journals)==1
 data=journals[0].read_bytes();rows=[];crcs=0
 while data:
  assert re.fullmatch(rb'[0-9A-F]{4}:[0-9A-F]{8}:',data[:14]);length=int(data[:4],16);crc=int(data[5:13],16);body=data[14:14+length]
  assert len(body)==length and all(32<=x<=126 for x in body) and data[14+length:15+length]==b'\n' and zlib.crc32(body)==crc
  rows.append(body.decode().split('|'));crcs+=1;data=data[15+length:]
 assert [x[0]for x in rows]==['INTENT','IDENTITY','STAGED','LIFECYCLE']
 intent,identity,staged,lifecycle=rows
 assert len(intent)==6 and re.fullmatch('[0-9a-f]{32}',intent[1]) and all(x[1]==intent[1] for x in rows)
 assert intent[2]==o['allocated_runtime'] and intent[3]==o['journal'] and PureWindowsPath(intent[3]).name==journals[0].name
 assert PureWindowsPath(intent[2]).parent==PureWindowsPath(o['run']) and PureWindowsPath(intent[2]).name=='scoped-'+intent[1]
 assert len(identity)==5 and identity[3:]==intent[4:] and re.fullmatch('[0-9A-F]{16}:[0-9a-f]{32}',identity[2])
 assert len(staged)==7 and 0<int(staged[2])<=2048 and 0<int(staged[3])<=512*1024**2 and all(re.fullmatch('[0-9A-Fa-f]{64}',x)for x in staged[4:6])
 assert len(lifecycle)==7 and lifecycle[2]==identity[2] and lifecycle[3].startswith('deadline=') and int(lifecycle[3][9:])>0 and lifecycle[5:]==['cleanup=NONE','cleanup_confirmed=0']
 runtime=run/PureWindowsPath(intent[2]).name;trace={}
 for line in (runtime/'native-creation-control.txt').read_text().splitlines():
  k,v=line.split('=',1);assert k not in trace;trace[k]=v
 assert trace==o['native_trace']
 for key in ('create_called','job_empty','process_closed_or_absent','thread_closed_or_absent','job_closed'):assert trace[key]=='True'
 assert trace['transferred']==trace['cleanup_error']=='False'
 if c['profile']=='ASSOCIATION_DENIED':
  assert not o['actor_stopped'] and o['actor_disposition']=='no_handles_returned_job_empty'
  assert trace['profile']=='association-denied' and trace['create_succeeded']=='False' and trace['create_error']=='5'
  assert trace['process_returned']==trace['thread_returned']=='False' and trace['process_id']=='0' and trace['query_duplicate_closed']=='True'
  assert 'Win32Exception:CreateProcessW(CREATE_SUSPENDED, JOB_LIST), Win32Error=5' in lifecycle[4]
 else:
  assert o['actor_stopped'] and o['actor_disposition']=='exact_pid_start_stopped'
  assert trace['root_termination_failed']==trace['root_signaled_after_termination_failure']=='True' and int(trace['root_termination_error'])>0 and trace['cleanup_detail_base64']==''
  assert trace['profile']=='post-create-abort' and trace['create_succeeded']==trace['process_returned']==trace['thread_returned']=='True'
  assert trace['create_error']=='0' and int(trace['process_id'])>0 and int(trace['creation'])>0 and 'CONTROL_ABORT_AFTER_REAL_SUSPENDED_CREATE' in lifecycle[4]
 expected=b'protected-before-failed-association\r\n'
 assert (runtime/'must-not-run.txt').read_bytes()==expected and (root/'input/must-not-run.txt').read_bytes()==expected
 assert (runtime/'must-not-run.txt').read_bytes()!=b'payload-started\r\n'
 manifest=(root/'build-readback/build-manifest.txt').read_text().splitlines();pins={x[66:]:x[:64]for x in manifest if re.match('^[0-9a-f]{64}  ',x)}
 assert manifest[0]=='compiler_sha256=cf32cb7e8e5691b962e1b6f92b03d87409dd9e7afbed71c5bf77b8203cc56ee1'
 profiles=['POST_CREATE_ABORT']if b['count']['new_profile_compilers']==1 else ['ASSOCIATION_DENIED','POST_CREATE_ABORT']
 assert 'creation_control_defines='+(';'.join('SCOPED_RUNNER_TESTING,SCOPED_RUNNER_'+profile for profile in profiles)) in manifest
 expected_profiles=['POST_CREATE_ABORT']if b['count']['new_profile_compilers']==1 else ['ASSOCIATION_DENIED','POST_CREATE_ABORT']
 assert sorted(x for x in pins if x.startswith('build/'))==sorted('build/ScopedRunner-'+profile+'.exe'for profile in expected_profiles)
 for name,h in b['files'].items():
  if name.endswith('.cs'):assert pins[name]==h
 assert pins['build/ScopedRunner-'+c['profile']+'.exe']==sha(root/'bin/ScopedRunner.exe')==o['binaries']['runner']
 assert sha(root/'bin/MonitorAcceptanceDriver.exe')==o['binaries']['driver']==b['retained']['binaries']['MonitorAcceptanceDriver.exe']
 assert sha(root/'input/fixture.exe')==sha(runtime/'fixture.exe')==o['binaries']['fixture']==b['retained']['binaries']['PayloadFixture.exe']
 bo=json.loads((root/'build-readback/build-observer.json').read_text());assert bo['accepted'] and bo['exit']==0 and bo['native_started'] and not bo['custody_indeterminate'] and not bo['driver_launched'] and bo['input_manifest_sha256']==b['input_manifest_sha256']
 assert (root/'build-readback/run-result.txt').read_text().startswith('BUILD_ONLY_PASS:')
 results.append({'id':c['id'],'tag':c['tag'],'scope':o['scope'],'runtime':o['allocated_runtime'],'profile':c['profile'],'trace':trace,'frames':r['frames'],'files':r['files'],'journal_crcs':crcs,'native_observer_elapsed_seconds':o['elapsed_seconds'],'accepted':True})
record={'accepted':True,'cases':results,'base':b['base'],'source_manifest_sha256':b['input_manifest_sha256'],'no_native_repeats':True,'full_windows_gate':False,'selected_profiles':[c['profile']for c in selected],'all_cases_in_this_invocation_accepted':len(selected)==len(b['controls'])}
(p/'host-accepted-readback.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'accepted':True,'cases':len(results),'crcs':[x['journal_crcs']for x in results],'frames':[x['frames']for x in results]}))
