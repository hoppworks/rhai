"""Independent native deadline acceptance from immutable source and original bytes."""
from pathlib import Path,PureWindowsPath
import json,hashlib,re,zlib,sys
p=Path(__file__).resolve().parent;b=json.loads((p/'binding.json').read_text());sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();read=lambda f:json.loads(f.read_text())
selected=b['controls']if len(sys.argv)==1 else [c for c in b['controls']if c['mode']==sys.argv[1]]
assert selected
results=[]
for c in selected:
 root=p/(c['tag']+'-export');r=read(p/(c['tag']+'-export-readback.json'));o=read(root/'observer.json')
 assert r['begin']['id']==r['end']['id']==o['id']==c['id'] and r['begin']['accepted']==r['end']['accepted']==o['accepted']==True
 assert r['begin']['exit']==r['end']['exit']==o['exit'] and o['mode']==c['mode'] and not o['failure']
 assert PureWindowsPath(o['scope']).name==c['scope_leaf'] and PureWindowsPath(o['run'])==PureWindowsPath(o['scope'])/'run'
 for name,item in r['files'].items():assert sha(root/name)==item['sha256'],name
 for flag in ('driver_launched','exact_driver_exited','pipes_drained','process_disposed','runtime_absent_readback','runtime_absence_negative_control','actors_stopped','pair_seen_live','membership_negative_control','wrong_expectation_red','deadline_negative_control','owned_executables_stopped'):assert o[flag],flag
 for flag in ('observer_kill_used','custody_pending','retained_driver_handles','parent_environment_changed','product_run'):assert not o[flag],flag
 assert len(o['channel_closure'])==2
 for channel in o['channel_closure']:
  assert channel['reader_acquired'] and channel['writer_acquired'] and channel['reader_disposed'] and channel['writer_disposed'] and channel['eof'] and not channel['pending_task'] and not channel['error']
 bo=read(root/'build-readback/build-observer.json');assert bo['accepted'] and bo['exit']==0 and bo['native_started'] and not bo['custody_indeterminate'] and not bo['driver_launched'] and bo['input_manifest_sha256']==b['input_manifest_sha256'] and bo['start_sha256']==b['start_sha256']
 assert bo['os_version'] and bo['powershell_version'].startswith('5.1.') and bo['clr_version'] and bo['compiler_version']
 manifest=(root/'build-readback/build-manifest.txt').read_text().splitlines();pins={x[66:]:x[:64]for x in manifest if re.match('^[0-9a-f]{64}  ',x)}
 assert manifest[0]=='compiler_sha256=cf32cb7e8e5691b962e1b6f92b03d87409dd9e7afbed71c5bf77b8203cc56ee1'
 for name,h in b['files'].items():
  assert sha(p/'input'/name)==h
  if name.endswith('.cs'):assert pins[name]==h
 expected_bins=['MonitorABSOLUTEDriver.exe','MonitorDeadlineFixture.exe','MonitorWATCHDOGDriver.exe','ScopedRunnerDeadlineControl.exe']
 assert sorted(n for n in pins if n.startswith('build/'))==['build/'+n for n in expected_bins]
 assert 'deadline_runner_defines=SCOPED_RUNNER_TESTING,SCOPED_RUNNER_MONITOR_DEADLINE_CONTROL' in manifest
 assert 'deadline_absolute_driver_defines=SCOPED_RUNNER_TESTING,SCOPED_RUNNER_DRIVER_ABSOLUTE_CONTROL' in manifest
 assert 'deadline_watchdog_driver_defines=SCOPED_RUNNER_TESTING,SCOPED_RUNNER_DRIVER_WATCHDOG_CONTROL' in manifest and 'deadline_payload_defines=NONE' in manifest
 driver='Monitor'+c['mode'].upper()+'Driver.exe'
 for key,path,name in (('runner','bin/ScopedRunner.exe','ScopedRunnerDeadlineControl.exe'),('driver','bin/MonitorAcceptanceDriver.exe',driver),('fixture','input/fixture.exe','MonitorDeadlineFixture.exe')):assert sha(root/path)==o['binaries'][key]==pins['build/'+name]
 assert len(list((root/'build-readback/logs').glob('compile-*.stdout.txt')))==4
 run=root/'run';js=list(run.glob('.scoped-run-*.journal'));assert len(js)==1;data=js[0].read_bytes();rows=[]
 while data:
  assert re.fullmatch(rb'[0-9A-F]{4}:[0-9A-F]{8}:',data[:14]);length=int(data[:4],16);crc=int(data[5:13],16);body=data[14:14+length]
  assert len(body)==length and all(32<=x<=126 for x in body) and data[14+length:15+length]==b'\n' and zlib.crc32(body)==crc
  rows.append(body.decode('ascii').split('|'));data=data[15+length:]
 assert [x[0]for x in rows]==['INTENT','IDENTITY','STAGED','LIFECYCLE','EVIDENCE','OUTCOME','REMOVE_INTENT','REMOVED'] and len({x[1]for x in rows})==1
 identity=rows[1][2];assert re.fullmatch('[0-9A-F]{16}:[0-9a-f]{32}',identity) and all(x[2]==identity for x in rows[3:])
 fields=lambda row:dict(x.split('=',1)for x in row if '='in x)
 lifecycle=fields(rows[3]);assert lifecycle['operation']==lifecycle['cleanup']=='NONE' and lifecycle['cleanup_confirmed']=='1'
 evidence=fields(rows[4]);outcome=fields(rows[5]);assert evidence['proof']=='EXACT' and evidence['exit']=='0000007D' and evidence['supervision']=='MonitorStopped'
 assert outcome['payload']==evidence['exit'] and outcome['supervision']==evidence['supervision'] and outcome['cleanup']=='CONFIRMED' and outcome['host_exported']=='0' and outcome['runtime_removed']=='0' and outcome['evidence']==evidence['manifest'] and outcome['evidence_identity']==evidence['evidence_identity']
 snapshots=list(run.glob('.scoped-evidence-*'));assert len(snapshots)==1;snapshot=snapshots[0]
 for key,name in (('manifest','manifest.txt'),('stdout','stdout.log'),('stderr','stderr.log')):assert sha(snapshot/name).upper()==evidence[key]
 runtime=snapshot/'runtime';assert sha(runtime/'fixture.exe')==o['binaries']['fixture']
 snapshot_names=set()
 for line in (snapshot/'manifest.txt').read_text().splitlines():
  pieces=line.split('|');assert len(pieces)==7
  rel,kind,file_identity,size,creation,attributes,digest=pieces
  assert not PureWindowsPath(rel).is_absolute() and '..'not in PureWindowsPath(rel).parts and re.fullmatch('[0-9A-F]{16}:[0-9a-f]{32}',file_identity)
  file=runtime.joinpath(*PureWindowsPath(rel).parts)
  assert rel not in snapshot_names;snapshot_names.add(rel)
  if kind=='F':assert file.is_file() and file.stat().st_size==int(size) and sha(file).upper()==digest
  else:assert kind=='D' and file.is_dir() and size=='0' and not digest
 assert ''in snapshot_names
 assert {str(PureWindowsPath(*f.relative_to(runtime).parts))for f in runtime.rglob('*')}==snapshot_names-{''}
 assert (snapshot/'manifest.txt').read_text().splitlines()[0].split('|')[2]==identity
 actors=o['actors'];assert len(actors)==2 and actors[0]['pid']!=actors[1]['pid']
 for i,name in enumerate(('pair','pair.child')):
  actor=actors[i];peer=actors[1-i];ident=f"pid={actor['pid']} creation={actor['creation']}";peerid=f"pid={peer['pid']} creation={peer['creation']}"
  assert (runtime/(name+'.identity')).read_bytes()==(ident+'\r\n').encode()
  match=re.fullmatch(rb'self=([^;]+);peer=([^;]+);members=([0-9,]+);assigned=([0-9]+);returned=([0-9]+)\r\n',(runtime/(name+'.membership')).read_bytes())
  assert match and match[1].decode()==ident and match[2].decode()==peerid;members=[int(x)for x in match[3].split(b',')]
  assert 2<=len(members)<=16 and members==sorted(set(members)) and min(members)>0 and {actor['pid'],peer['pid']}.issubset(members) and len(members)==int(match[4])==int(match[5])
 for name,text in (('pair.child.release','both-members-confirmed'),('pair.child.work','child-work-after-both-membership'),('pair.work','parent-work-after-both-membership'),('pair.ready','both-membership-and-work-confirmed')):assert (runtime/name).read_bytes()==(text+'\r\n').encode()
 assert PureWindowsPath(o['allocated_runtime'])==PureWindowsPath(rows[0][2]) and PureWindowsPath(o['allocated_runtime']).parent==PureWindowsPath(o['run'])
 traces=list(run.glob('monitor-deadline-*.txt'));assert len(traces)==1
 trace=dict(line.split('=',1)for line in traces[0].read_text().splitlines());assert trace==o['monitor_trace'] and trace['absolute_ms']=='1800000' and int(trace['started'])>0
 if c['mode']=='watchdog':
  assert o['exit']==124 and 179<=o['elapsed_seconds']<=270 and o['last_pair_live_seconds']>=178
  assert trace['expiry']=='None' and trace['expired_at']==trace['lease_at_expiry']=='0' and int(trace['loop_stopped_at'])-int(trace['started'])>=179000
  assert b'WATCHDOG_CONTROL_MAIN_STALLED;BOUND_MS=180000' in (root/'bootstrap.stdout').read_bytes()
 else:
  assert o['exit']==0 and 1799<=o['elapsed_seconds']<=2020 and o['last_pair_live_seconds']>=1798
  assert trace['expiry']=='AbsoluteDeadline' and 1800000<=int(trace['expired_at'])-int(trace['started'])<=1830000 and int(trace['lease_at_expiry'])==int(trace['started'])+1800000 and trace['client_signaled']=='False'
  assert b'MODE=absolute-deadline;ACTION_CONFIRMED=True;'in(root/'bootstrap.stdout').read_bytes()
 results.append({'mode':c['mode'],'id':c['id'],'scope':o['scope'],'accepted':True,'frames':r['frames'],'files':r['files'],'crc_records':8,'driver_exit':o['exit'],'payload_exit':evidence['exit'],'monitor_trace':trace,'actors':actors,'elapsed_seconds':o['elapsed_seconds'],'last_pair_live_seconds':o['last_pair_live_seconds'],'binaries':o['binaries'],'runtime':o['allocated_runtime']})
record={'accepted':True,'base':b['base'],'source_manifest_sha256':b['input_manifest_sha256'],'cases':results,'all_required_control_modes_accepted':len(selected)==len(b['controls']),'all_launched_runs_accepted':len(selected)==len(b['controls'])and not b.get('interrupted_controls'),'interrupted_controls':b.get('interrupted_controls',[]),'launch_counts':b['count'],'full_windows_gate':False,'native_cargo_started':False}
(p/('host-accepted-readback.json'if len(selected)==len(b['controls'])else selected[0]['mode']+'-accepted-readback.json')).write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'accepted':True,'cases':[(x['mode'],x['driver_exit'],x['frames'],len(x['files']))for x in results]}))
