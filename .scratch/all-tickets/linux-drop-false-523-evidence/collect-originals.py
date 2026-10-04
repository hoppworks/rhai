#!/usr/bin/env python3
"""Preserve the exact remote run first; analyze custody separately; retire only by hash gate."""
from __future__ import annotations
import argparse, hashlib, json, shlex, subprocess, tarfile, tempfile
from pathlib import Path, PurePosixPath

STAGE='/root/rhai-linux-drop-false-523-20261004'
SCOPE='/root/.local/share/agent-builds/rhai/linux-drop-false-523-20261004'
PHYSICAL='/var/roothome/rhai-linux-drop-false-523-20261004'
DEST=Path(__file__).resolve().parent/'originals'

INVENTORY=r'''import hashlib,json,pathlib,sys
s=pathlib.Path(sys.argv[1])
if not s.exists(): raise SystemExit('stage unavailable for raw preservation')
f={}; d=[]
for p in sorted(s.rglob('*')):
 r=p.relative_to(s).as_posix()
 if p.is_symlink(): raise SystemExit('stage symlink '+r)
 if p.is_dir(): d.append(r)
 elif p.is_file(): f[r]=hashlib.sha256(p.read_bytes()).hexdigest()
 else: raise SystemExit('unexpected stage object '+r)
print(json.dumps({'stage':str(s),'scope':sys.argv[2],'files':f,'directories':d},sort_keys=True))'''

PACKAGE_VALIDATION=r'''def validate_package(proof):
 result=json.loads((proof/'package-result.json').read_text()); restoration=json.loads((proof/'source-restoration.json').read_text()); inputs=json.loads((proof/'source-inputs.json').read_text())
 if (result.get('source_revision')!='523608648dcae99bc0f6b46eaf2bb91fa4ecc752' or result.get('source_archive_sha256')!='998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b'
     or result.get('baseline_test_sha256')!='5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb'
     or result.get('compatible_lock_sha256')!='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
     or result.get('source_restored_to_baseline') is not True or result.get('acceptance_claim') is not False or result.get('status')!=0): raise SystemExit('source provenance/restoration/package status invalid')
 if restoration.get('restored') is not True or restoration.get('restored_to_baseline_revision') is not True or restoration.get('error') is not None: raise SystemExit('private source restoration failed')
 if restoration.get('original_sha256')!={'tests/sys_process.rs':'5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb'} or restoration.get('cargo_lock_sha256')!='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425': raise SystemExit('restored baseline test/lock binding mismatch')
 if (inputs.get('revision')!='523608648dcae99bc0f6b46eaf2bb91fa4ecc752'
     or inputs.get('archive_sha256')!='998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b'
     or inputs.get('baseline_test_sha256')!='5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb'
     or inputs.get('cargo_lock_sha256')!='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
     or inputs.get('observer_patch_sha256')!='78d7f123c570e5efb94563b77c737fd4ed97ac9a594090c4a7dba664b461e9dd'
     or not re.fullmatch(r'[0-9a-f]{64}',inputs.get('test_after_patch_sha256',''))
     or result.get('test_only_handshake_patch_sha256')!=inputs.get('observer_patch_sha256')
     or result.get('base_helper_sha256')!='c5422e7895f5afacf987be55df2297b63b0763618ccbdc2a8374116a1421edd9'
     or not isinstance(inputs.get('cargo_manifests_sha256'),dict) or not inputs['cargo_manifests_sha256']
     or restoration.get('manifest_sha256')!=inputs['cargo_manifests_sha256'] or result.get('cargo_manifests_sha256')!=inputs['cargo_manifests_sha256']): raise SystemExit('frozen source/archive/test/lock/patch/helper/manifest binding mismatch')
 controls=result.get('controls',[])
 if not isinstance(controls,list) or [(x.get('name'),x.get('status'),x.get('expected_status')) for x in controls] != [('direct-red',101,101),('managed-red',101,101),('direct-green',0,0),('managed-green',0,0)]: raise SystemExit('control/green outcomes are incomplete or misordered')
 commands=result.get('commands',[])
 names={'direct-red','managed-red','direct-green','managed-green'}
 if not isinstance(commands,list) or {x.get('name') for x in commands if isinstance(x,dict)} < names: raise SystemExit('named Cargo command records are incomplete')
 command_rows={x.get('name'):x for x in commands if isinstance(x,dict) and x.get('name') in names}
 if any(command_rows[n].get('status')!=status or command_rows[n].get('expected_status')!=status for n,status in (('direct-red',101),('managed-red',101),('direct-green',0),('managed-green',0))): raise SystemExit('Cargo command status/provenance mismatch')
 for label in ('direct-red','managed-red','direct-green','managed-green'):
  if (proof/(label+'.status')).read_text().strip() != ('101' if label.endswith('red') else '0'): raise SystemExit('wrong individual test status '+label)
 return result,restoration,command_rows
'''

# Run only after originals were copied and verified. Any status/custody failure preserves the stage.
CUSTODY=r'''import hashlib,json,math,pathlib,re,shlex,subprocess,sys
m=json.loads(sys.argv[4]); s=pathlib.Path(sys.argv[1]); scope=pathlib.Path(sys.argv[2]); physical=pathlib.Path(sys.argv[3])
stage_aliases={pathlib.Path('/root/rhai-linux-drop-false-523-20261004'),pathlib.Path('/var/roothome/rhai-linux-drop-false-523-20261004')}
scope_aliases={pathlib.Path('/root/.local/share/agent-builds/rhai/linux-drop-false-523-20261004'),pathlib.Path('/var/roothome/.local/share/agent-builds/rhai/linux-drop-false-523-20261004')}
physical_stage=pathlib.Path('/var/roothome/rhai-linux-drop-false-523-20261004')
if s not in stage_aliases or physical!=physical_stage or scope not in scope_aliases or not s.is_dir() or s.is_symlink() or s.resolve()!=physical: raise SystemExit('stage identity changed')
expected={'source.tar':'998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b','Cargo.lock.accepted':'2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425','check-linux-current-msrv-examples.py':'c5422e7895f5afacf987be55df2297b63b0763618ccbdc2a8374116a1421edd9','archive-build-source.py':'a75b4e807f03e8247ed821df871ceb35e776b7f699046d7a099dd0b85199fd8b','drop-false-observer-handshake.patch':'78d7f123c570e5efb94563b77c737fd4ed97ac9a594090c4a7dba664b461e9dd','drop-false-observer.py':'07d2ab6e1f2015a18b1ee83f59585b16b97852a00cc45dfb5778f836d78ad0d2','linux-drop-false-proof.py':'61d828673fa032db6160263b7ba3585e826099fa6baf38f05aa7a0115c972d53','contract.md':'5f26d4fd99bddda2fcd5f3a0ee863b361c930a69f915be4c9f8389bfadb072f5','launch.sh':'faa6a9a19cef84d84391e0d5c68fb8db10af059b1d432bae49ed5a66710dacba','runner/tools/run_scoped.py':'9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d','runner/tools/agentskills/__init__.py':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855','runner/tools/agentskills/pyguard.py':'a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f'}
if scope.exists() or scope.is_symlink(): raise SystemExit('private scope/runtime remains')
proof=s/'proof-evidence'; outer=s/'outer-evidence'
required={'package-result.json','source-restoration.json','source-inputs.json','process-identities.tsv','commands.json','control-results.json','early-runtime-identity.json','direct-observer-readback.json','managed-observer-readback.json','direct-red-terminal.json','managed-red-terminal.json'}
if not required.issubset({p.name for p in proof.iterdir()}): raise SystemExit('required original proof files are missing')
''' + PACKAGE_VALIDATION + r'''
result,restoration,command_rows=validate_package(proof)
early=json.loads((proof/'early-runtime-identity.json').read_text()); runtime=pathlib.Path(early.get('runtime',''))
def aliases(path):
 text=str(path)
 if text=='/root' or text.startswith('/root/'): return {path,pathlib.Path('/var/roothome'+text[len('/root'):])}
 if text=='/var/roothome' or text.startswith('/var/roothome/'): return {path,pathlib.Path('/root'+text[len('/var/roothome'):])}
 return {path}
if (not runtime.is_absolute() or not re.fullmatch(r'agent-build-[a-z0-9]+',runtime.name) or not (aliases(runtime.parent)&scope_aliases)
    or any(x.exists() or x.is_symlink() for x in aliases(runtime))): raise SystemExit('exact private runtime is not a direct absent scope child')
# The helper's periodic resource records are stdout from the pinned helper, captured
# in the launcher-owned log; this run used the custom exporter, so no JSONL sidecar
# exists. Require the exact runtime banner and an ordered, bounded nonempty stream.
outer_log=(outer/'outer.log').read_text(encoding='utf-8',errors='strict')
if m.get('files',{}).get('outer-evidence/outer.log')!=hashlib.sha256(outer_log.encode('utf-8')).hexdigest(): raise SystemExit('outer log differs from original readback inventory')
log_lines=outer_log.splitlines()
runtime_banner='PRIVATE_RUNTIME '+str(runtime)
if log_lines.count(runtime_banner)!=1: raise SystemExit('outer log runtime binding is missing or ambiguous')
status_positions=[i for i,line in enumerate(log_lines) if line=='outer_status=0']
if len(status_positions)!=1: raise SystemExit('outer log successful terminal status is missing or ambiguous')
status_pos=status_positions[0]; banner_pos=log_lines.index(runtime_banner)
samples=[]; previous=-1.0
for i,line in enumerate(log_lines):
 if 'sample=' not in line: continue
 if not line.startswith('sample=') or not (banner_pos<i<status_pos): raise SystemExit('resource sample is outside the bound helper log interval')
 try: row=json.loads(line[len('sample='):])
 except (ValueError,TypeError) as e: raise SystemExit('malformed outer resource sample '+str(e))
 if not isinstance(row,dict) or set(row)!={'monotonic_seconds','storage_kib','rss_kib','descendants'}: raise SystemExit('outer resource sample schema mismatch')
 t=row['monotonic_seconds']; storage=row['storage_kib']; rss=row['rss_kib']; descendants=row['descendants']
 if isinstance(t,bool) or not isinstance(t,(int,float)) or not math.isfinite(t) or t<0 or t<=previous or t>540: raise SystemExit('outer resource sample time is invalid or unordered')
 if any(type(v) is not int or v<0 for v in (storage,rss,descendants)): raise SystemExit('outer resource sample counters are invalid')
 if storage>=1572864 or rss>=2097152 or descendants>16: raise SystemExit('outer resource sample exceeded a recorded stop limit')
 previous=t; samples.append(row)
if not samples: raise SystemExit('outer log contains no resource samples')
for label in ('outer-status.txt','run-scoped.status','pid-readback.status','pid-readback-launcher.status'):
 if (outer/label).read_text().strip()!='0': raise SystemExit('outer custody status failed: '+label)
for label in ('runtime-cleanup.tsv','scope-cleanup.tsv'):
 if 'status=0' not in (outer/label).read_text(): raise SystemExit('outer cleanup incomplete: '+label)
# Exact process identities: parse conservatively; unknown, malformed, live exact IDs or unreadable proc is a refusal.
def identities(path,required):
 rows=path.read_text(errors='strict').splitlines(); seen=set(); seen_ids=set(); groups=set(); out=[]
 if not rows or rows[0]!='label\tpid\tppid\tpgid\tstart_ticks\tcmdline': raise SystemExit('custody header mismatch '+str(path))
 for line in rows[1:]:
  f=line.split('\t',5)
  if len(f)!=6 or not f[0] or not all(re.fullmatch(r'[0-9]+',f[i]) for i in (1,2,3,4)) or (f[0] in required and not f[5]): raise SystemExit('malformed custody row '+repr(line))
  label,pid,ppid,pgid,start,cmd=f; pid=int(pid);pgid=int(pgid);start=int(start)
  command=label.startswith('command:') and bool(label[8:])
  if label not in required and not command: raise SystemExit('unexpected owned identity label '+repr(label))
  if min(pid,pgid,start)<=0: raise SystemExit('nonpositive identity '+repr(line))
  if label in required and label in seen: raise SystemExit('duplicate owner identity '+repr(line))
  if (pid,start) in seen_ids and not label.startswith('command:'): raise SystemExit('duplicate owner PID/start '+repr(line))
  if (pid,start) in seen_ids: raise SystemExit('duplicate recorded PID/start '+repr(line))
  seen_ids.add((pid,start))
  try:
   raw=pathlib.Path('/proc',str(pid),'stat').read_text(encoding='ascii'); prefix=str(pid)+' ('; z=raw.rfind(')')
   if not raw.startswith(prefix) or z<len(prefix) or raw[z+1:z+2]!=' ': raise ValueError('malformed PID/comm framing')
   fields=raw[z+2:].split()
   if len(fields)<20 or len(fields[0])!=1 or fields[0] not in 'RSDZTtXxKWPI' or not all(re.fullmatch(r'-?\d+',x) for x in fields[1:20]) or int(fields[19])<=0: raise ValueError('malformed proc stat fields')
   current=int(fields[19])
  except (FileNotFoundError,ProcessLookupError): current=None
  except (PermissionError,OSError,IndexError,ValueError) as e: raise SystemExit('identity readback unknown '+repr(line)+': '+str(e))
  if current==start: raise SystemExit('owned process remains '+repr(line))
  if current is not None and current<=0: raise SystemExit('invalid current start tick '+repr(line))
  seen.add(label); out.append({'label':label,'pid':pid,'ppid':int(ppid),'pgid':pgid,'start_ticks':start,'cmdline':cmd,'pid_absent_or_reused':True})
  if label in required or command: groups.add(pgid)
 if not required.issubset(seen): raise SystemExit('required identity rows missing '+repr(required-seen))
 return out,groups
owned,groups=identities(proof/'process-identities.tsv',{'helper','scoped-supervisor'})
launchers,lgroups=identities(outer/'launcher-identities.tsv',{'launcher','run-scoped'})
owners={x['label']:x for x in owned+launchers if x['label'] in {'helper','scoped-supervisor','launcher','run-scoped'}}
if set(owners)!={'helper','scoped-supervisor','launcher','run-scoped'}: raise SystemExit('owned parent identities incomplete')
if (owners['helper']['ppid']!=owners['scoped-supervisor']['pid'] or owners['scoped-supervisor']['ppid']!=owners['run-scoped']['pid']
    or owners['run-scoped']['ppid']!=owners['launcher']['pid']): raise SystemExit('owned parent chain mismatch')
if any(x['ppid']!=owners['helper']['pid'] for x in owned if x['label'].startswith('command:')): raise SystemExit('Cargo/resource command parent mismatch')
for label,relative in (('helper','linux-drop-false-proof.py'),('scoped-supervisor','runner/tools/run_scoped.py'),('launcher','launch.sh'),('run-scoped','runner/tools/run_scoped.py')):
 argv=shlex.split(owners[label]['cmdline'])
 allowed={str(s/relative),str(physical/relative)}
 if not any(token in allowed for token in argv): raise SystemExit('owned command provenance mismatch '+label)
groups|=lgroups
# Revalidate green and intended-RED fixture snapshots, retaining every exact PID/start tuple.
fixture_identities=[]
for case,kind in (('direct','observer'),('managed','observer'),('direct','red'),('managed','red')):
 r=json.loads((proof/(case+('-observer-readback.json' if kind=='observer' else '-red-terminal.json'))).read_text())
 if r.get('case')!=case or r.get('fixture_root_absent') is not True: raise SystemExit('fixture closure receipt invalid '+case+'/'+kind)
 if kind=='observer':
  live=r.get('live_observation',{}); identities_live=live.get('identities',{})
  if live.get('complete') is not True: raise SystemExit('live observer receipt is incomplete '+case)
  request=live.get('request',{}); host=live.get('host',{}); cargo=live.get('cargo',{})
  if request.get('case')!=case or not isinstance(host,dict) or not isinstance(cargo,dict): raise SystemExit('fixture request/host/Cargo provenance invalid '+case)
  cargo_row=next((x for x in owned if x['label']=='command:'+case+'-green'),None)
  if not cargo_row or (int(cargo_row['pid']),int(cargo_row['start_ticks']))!=(int(cargo.get('pid',0)),int(cargo.get('start_ticks',0))): raise SystemExit('green Cargo identity does not match independent command row '+case)
  if int(host.get('pid',0))!=int(request.get('test_pid',0)) or int(host.get('start_ticks',0))!=int(request.get('test_start_ticks',0)) or int(host.get('ppid',0))!=int(cargo_row['pid']): raise SystemExit('green host ancestry/request binding invalid '+case)
  fixture_root=pathlib.Path(live.get('fixture_root',''))
  test_name='direct_spawn_kill_on_drop_false_preserves_child_and_capture' if case=='direct' else 'managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit'
  expected_root_name='rhai-sys-test-'+str(host['pid'])+'-'+test_name+'-0'
  expected_fixture_roots={alias/'tmp'/expected_root_name for alias in aliases(runtime)}
  if fixture_root not in expected_fixture_roots or fixture_root.is_symlink(): raise SystemExit('green fixture root escaped exact private runtime test path '+case)
  required_live={'child'} if case=='direct' else {'sentinel','leader','worker','leaf'}
  if set(identities_live)!=required_live or not live.get('host'): raise SystemExit('fixture live identity schema mismatch '+case)
  if case=='direct':
   child=identities_live['child']
   if int(child.get('ppid',0))!=int(host['pid']) or int(child.get('pgid',0))!=int(request.get('child_pgid',0)) or int(child.get('pid',0))!=int(request.get('child_pid',0)) or int(child.get('start_ticks',0))!=int(request.get('child_start_ticks',0)): raise SystemExit('direct child request/parent/group binding invalid')
  else:
   sentinel=identities_live['sentinel']; leader=identities_live['leader']; worker=identities_live['worker']; leaf=identities_live['leaf']
   if any(int(request.get(k,0))!=int(request.get('group',0)) for k in ('leader_pgid','worker_pgid','leaf_pgid')) or (int(sentinel.get('ppid',0))!=int(host['pid']) or int(sentinel.get('pid',0))!=int(request.get('sentinel_pid',0)) or int(sentinel.get('pgid',0))!=int(request.get('sentinel_pgid',0)) or int(leader.get('ppid',0))!=int(host['pid']) or int(worker.get('ppid',0))!=int(leader.get('pid',0)) or int(leaf.get('ppid',0))!=int(worker.get('pid',0)) or int(leader.get('pid',0))!=int(request.get('group',0)) or any(int(v.get('pgid',0))!=int(request.get('group',0)) for v in (leader,worker,leaf))): raise SystemExit('managed member request/parent/group binding invalid')
  terminal=r.get('terminal_identities',[])
  required_terminal={'host'}|required_live
  if {x.get('label') for x in terminal}!=required_terminal: raise SystemExit('fixture terminal identity schema mismatch '+case)
  if any(x.get('absent') is not True and x.get('pid_reused_with_different_start') is not True for x in terminal): raise SystemExit('fixture terminal absence invalid '+case)
  rows=[('host',live['host'])]+list(identities_live.items())
 else:
  rows=list(r.get('terminal_identities',{}).items())
  marker=r.get('marker',{}); fixture_root=pathlib.Path(marker.get('fixture_root',''))
  test_name='direct_spawn_kill_on_drop_false_preserves_child_and_capture' if case=='direct' else 'managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit'
  expected_root_name='rhai-sys-test-'+str(marker.get('host_pid'))+'-'+test_name+'-0'
  expected_fixture_roots={alias/'tmp'/expected_root_name for alias in aliases(runtime)}
  if fixture_root not in expected_fixture_roots or fixture_root.is_symlink(): raise SystemExit('RED fixture root escaped exact private runtime test path '+case)
  parent_key_by_name={'child':'child_ppid','sentinel':'sentinel_ppid','leader':'leader_ppid','worker':'worker_ppid','leaf':'leaf_ppid'}
  marker_name={'host':'host','child':'child','sentinel':'sentinel','leader':'leader','worker':'worker','leaf':'leaf'}
  for name, ident in rows:
   stem=marker_name[name]
   if int(marker.get(stem+'_pid',0))!=int(ident.get('pid',0)) or int(marker.get(stem+'_start_ticks',0))!=int(ident.get('start_ticks',0)): raise SystemExit('RED marker/terminal identity mismatch '+case+'/'+name)
   parent_key=parent_key_by_name.get(name)
   expected_parent=int(marker.get('host_pid' if name in ('child','sentinel','leader') else ('leader_pid' if name=='worker' else 'worker_pid'),0))
   if parent_key and int(marker.get(parent_key,0))!=expected_parent: raise SystemExit('RED fixture ancestry marker mismatch '+case+'/'+name)
  required={'host','child'} if case=='direct' else {'host','sentinel','leader','worker','leaf'}
  if {name for name,_ in rows}!=required: raise SystemExit('RED terminal identity schema mismatch '+case)
  if any(not (v.get('absent') is True or v.get('pid_reused_with_different_start') is True) for _,v in rows): raise SystemExit('RED terminal absence invalid '+case)
 for label,identity in rows:
  if not isinstance(identity,dict) or int(identity.get('pid',0))<=0 or int(identity.get('start_ticks',0))<=0: raise SystemExit('fixture identity receipt incomplete '+case+'/'+label)
  pid=int(identity['pid']);start=int(identity['start_ticks'])
  try:
   raw=pathlib.Path('/proc',str(pid),'stat').read_text(encoding='ascii');prefix=str(pid)+' (';z=raw.rfind(')')
   if not raw.startswith(prefix) or z<len(prefix) or raw[z+1:z+2]!=' ': raise ValueError('malformed PID/comm framing')
   fields=raw[z+2:].split()
   if len(fields)<20 or len(fields[0])!=1 or fields[0] not in 'RSDZTtXxKWPI' or not all(re.fullmatch(r'-?\d+',x) for x in fields[1:20]) or int(fields[19])<=0: raise ValueError('malformed proc stat fields')
   current=int(fields[19])
  except (FileNotFoundError,ProcessLookupError): current=None
  except (PermissionError,OSError,IndexError,ValueError) as e: raise SystemExit('fixture exact identity unreadable '+label+': '+str(e))
  if current==start: raise SystemExit('fixture PID/start remains live '+label)
  fixture_identities.append({'case':case,'kind':kind,'label':label,'pid':pid,'start_ticks':start})
 red_groups=r.get('groups_censused',[])
 expected_groups=[]
 if case=='managed':
  bound=request if kind=='observer' else marker
  expected_groups=sorted({int(bound.get('sentinel_pgid',0)),int(bound.get('group',0))})
  if int(bound.get('group',0))!=int(bound.get('leader_pid',0)): raise SystemExit('managed group is not owned by its leader '+kind)
  if kind=='red' and any(int(bound.get(name+'_pgid',0))!=int(bound.get('group',0)) for name in ('leader','worker','leaf')): raise SystemExit('RED member PGIDs differ from managed group')
 if red_groups!=expected_groups: raise SystemExit('fixture exact group census differs from bound request/marker '+case+'/'+kind)
 if case=='direct' and red_groups: raise SystemExit('direct inherited host group must not be censused')
 for group in r.get('groups_censused',[]):
  if type(group) is not int or group<=0: raise SystemExit('invalid fixture group')
  groups.add(group)
ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5); left=[]
for line in ps.splitlines():
 f=line.split()
 if len(f)!=2 or not all(x.isdecimal() for x in f): raise SystemExit('malformed process census '+repr(line))
 pid,pgid=map(int,f)
 if pgid in groups: left.append((pid,pgid))
if left: raise SystemExit('owned helper/launcher/fixture group remains '+repr(left))
# Recompute complete original stage inventory for current readback.
f={};d=[]
for p in sorted(s.rglob('*')):
 rel=p.relative_to(s).as_posix()
 if p.is_symlink(): raise SystemExit('stage symlink '+rel)
 if p.is_dir(): d.append(rel)
 elif p.is_file(): f[rel]=__import__('hashlib').sha256(p.read_bytes()).hexdigest()
 else: raise SystemExit('unexpected stage object '+rel)
if f!=m['files'] or d!=m['directories']: raise SystemExit('stage inventory changed since original collection')
for name,digest in expected.items():
 if m['files'].get(name)!=digest or f.get(name)!=digest: raise SystemExit('immutable staged input pin mismatch '+name)
manifest_text=(s/'input-identities.sha256').read_text(encoding='ascii')
manifest_map={}
for line in manifest_text.splitlines():
 parts=line.split('  ',1)
 if len(parts)!=2 or not re.fullmatch(r'[0-9a-f]{64}',parts[0]) or parts[1] in manifest_map: raise SystemExit('malformed/duplicate stage input manifest row '+repr(line))
 manifest_map[parts[1]]=parts[0]
if manifest_map!=expected: raise SystemExit('complete input manifest differs from pinned immutable inputs')
receipt={'inventory_sha256':hashlib.sha256(json.dumps(m,sort_keys=True).encode()).hexdigest(),'input_manifest_sha256':hashlib.sha256(manifest_text.encode()).hexdigest(),'owned_processes':owned,'launcher_processes':launchers,'fixture_identities':fixture_identities,'groups_absent':sorted(groups),'fixture_cases_closed':['direct-red','managed-red','direct-green','managed-green'],'runtime':str(runtime),'runtime_absent':True,'scope_absent':True,'stage_inventory_still_exact':True}
print(json.dumps(receipt,sort_keys=True))'''


POST_RETIREMENT=r'''import json,pathlib,re,subprocess,sys
m=json.loads(sys.argv[4]);s=pathlib.Path(sys.argv[1]);scope=pathlib.Path(sys.argv[2]);physical=pathlib.Path(sys.argv[3]);runtime=pathlib.Path(m.get('runtime',''))
if s.exists() or s.is_symlink() or scope.exists() or scope.is_symlink() or runtime.exists() or runtime.is_symlink() or not runtime.is_absolute() or runtime.parent!=scope:raise SystemExit('fresh stage/scope/runtime absence failed')
identities=m.get('owned_processes',[])+m.get('launcher_processes',[])+m.get('fixture_identities',[])
for row in identities:
 pid=int(row['pid']);start=int(row['start_ticks'])
 try:
  raw=pathlib.Path('/proc',str(pid),'stat').read_text(encoding='ascii');prefix=str(pid)+' (';z=raw.rfind(')')
  if not raw.startswith(prefix) or z<len(prefix) or raw[z+1:z+2]!=' ':raise ValueError('malformed PID/comm framing')
  fields=raw[z+2:].split()
  if len(fields)<20 or len(fields[0])!=1 or fields[0] not in 'RSDZTtXxKWPI' or not all(re.fullmatch(r'-?\d+',x) for x in fields[1:20]) or int(fields[19])<=0:raise ValueError('malformed proc stat fields')
  current=int(fields[19])
 except (FileNotFoundError,ProcessLookupError):continue
 except (PermissionError,OSError,IndexError,ValueError) as e:raise SystemExit('fresh process identity unknown '+str(pid)+': '+str(e))
 if current==start:raise SystemExit('exact owned PID/start remains '+str(pid))
groups=m.get('groups_absent',[])
if physical.exists() or physical.is_symlink():raise SystemExit('physical stage remains after retirement')
if not groups or any(not isinstance(g,int) or g<=0 for g in groups):raise SystemExit('post-retirement group set missing/invalid')
ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5);left=[]
for line in ps.splitlines():
 f=line.split()
 if len(f)!=2 or not all(x.isdecimal() for x in f):raise SystemExit('malformed process census '+repr(line))
 pid,pgid=map(int,f)
 if pgid in groups:left.append([pid,pgid])
if left:raise SystemExit('post-retirement owned groups populated '+repr(left))
print(json.dumps({'stage_absent':True,'scope_absent':True,'runtime_absent':True,'physical_stage_absent':True,'identities_rechecked':len(identities),'groups_rechecked':groups,'groups_empty':True},sort_keys=True))'''

def ssh_json(code: str, readback: dict | None = None) -> dict:
    remote='python3 -c '+shlex.quote(code)+' '+shlex.quote(STAGE)+' '+shlex.quote(SCOPE)+' '+shlex.quote(PHYSICAL)
    if readback is not None:
        remote+=' '+shlex.quote(json.dumps(readback,sort_keys=True))
    run=subprocess.run(['ssh','workhorse',remote],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,text=True,timeout=20)
    rows=[line for line in run.stdout.splitlines() if line.strip()]
    if not rows: raise RuntimeError('remote command returned no JSON receipt')
    return json.loads(rows[-1])


def inventory() -> dict:
    return ssh_json(INVENTORY)


def collect(destination: Path) -> None:
    # Raw collection is deliberately before acceptance/custody analysis.
    if destination.exists() or destination.is_symlink(): raise FileExistsError(destination)
    destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    raw_tar=destination.with_name(destination.name+'.stage-originals.tar')
    if raw_tar.exists() or raw_tar.is_symlink(): raise FileExistsError(raw_tar)
    # Preserve the raw stage stream before inventory or custody diagnostics.
    with raw_tar.open('xb') as tmp:
        subprocess.run(['ssh','workhorse','tar','-C',STAGE,'-cf','-','.'],stdout=tmp,check=True,timeout=30)
        tmp.flush()
    remote=inventory()
    original_tree=destination/'stage-originals'
    with tarfile.open(raw_tar,'r:') as tf:
        for member in tf.getmembers():
            rel=PurePosixPath(member.name)
            if rel.is_absolute() or '..' in rel.parts or member.issym() or member.islnk() or not(member.isfile() or member.isdir()):
                raise RuntimeError('unsafe original tar member '+member.name)
        original_tree.mkdir(mode=0o700,parents=True)
        tf.extractall(original_tree,filter='data')
    files={};dirs=[]
    for path in sorted(original_tree.rglob('*')):
        rel=path.relative_to(original_tree).as_posix()
        if path.is_symlink(): raise RuntimeError('local original symlink '+rel)
        if path.is_dir(): dirs.append(rel)
        elif path.is_file(): files[rel]=hashlib.sha256(path.read_bytes()).hexdigest()
        else: raise RuntimeError('unexpected local original object '+rel)
    if files!=remote['files'] or dirs!=remote['directories']:
        raise RuntimeError('local originals do not match independent stage byte inventory; preserve both')
    (destination/'independent-readback.json').write_text(json.dumps(remote,indent=2,sort_keys=True)+'\n')
    tar_hash=hashlib.sha256()
    with raw_tar.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): tar_hash.update(block)
    export={'stage':STAGE,'scope':SCOPE,'files':remote['files'],'directories':remote['directories'],
            'readback_sha256':hashlib.sha256(json.dumps(remote,sort_keys=True).encode()).hexdigest(),
            'raw_tar_path':str(raw_tar),'raw_tar_sha256':tar_hash.hexdigest()}
    (destination/'export-manifest.json').write_text(json.dumps(export,indent=2,sort_keys=True)+'\n')
    # Custody analysis is separate and may fail without removing or rewriting originals.
    try:
        receipt=ssh_json(CUSTODY,remote)
    except Exception as exc:
        (destination/'custody-analysis-failed.txt').write_text(f'{type(exc).__name__}: {exc}\n')
        raise
    (destination/'fresh-custody-readback.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')


def cleanup(destination: Path) -> None:
    readback=json.loads((destination/'independent-readback.json').read_text())
    exported=json.loads((destination/'export-manifest.json').read_text())
    collected=json.loads((destination/'fresh-custody-readback.json').read_text())
    expected_readback_hash=hashlib.sha256(json.dumps(readback,sort_keys=True).encode()).hexdigest()
    if collected.get('stage_inventory_still_exact') is not True or collected.get('inventory_sha256')!=expected_readback_hash: raise RuntimeError('original fresh custody receipt is missing or unbound')
    expected_tar=destination.with_name(destination.name+'.stage-originals.tar')
    if (exported.get('stage')!=STAGE or exported.get('scope')!=SCOPE or exported.get('files')!=readback.get('files') or exported.get('directories')!=readback.get('directories')
        or exported.get('readback_sha256')!=expected_readback_hash or exported.get('raw_tar_path')!=str(expected_tar)):
        raise RuntimeError('local original manifest binding mismatch; preserve stage')
    actual={};dirs=[]
    original_tree=destination/'stage-originals'
    for p in sorted(original_tree.rglob('*')):
        rel=p.relative_to(original_tree).as_posix()
        if p.is_symlink(): raise RuntimeError('local original symlink '+rel)
        if p.is_dir(): dirs.append(rel)
        elif p.is_file():
            actual[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    if actual!=readback['files'] or dirs!=readback['directories']:
        raise RuntimeError('local original bytes changed; preserve remote stage')
    raw_tar=expected_tar
    if not raw_tar.is_file() or raw_tar.is_symlink() or hashlib.sha256(raw_tar.read_bytes()).hexdigest()!=exported.get('raw_tar_sha256'):
        raise RuntimeError('preserved original raw tar changed; preserve remote stage')
    # Fresh inventory and independent custody checks must exactly match the preserved originals.
    fresh=inventory()
    if fresh!=readback: raise RuntimeError('fresh stage inventory differs from preserved original readback')
    custody=ssh_json(CUSTODY,readback)
    (destination/'fresh-custody-before-retirement.json').write_text(json.dumps(custody,indent=2,sort_keys=True)+'\n')
    payload=json.dumps(readback,sort_keys=True)
    code=r'''import hashlib,json,pathlib,sys
m=json.loads(sys.argv[4]);s=pathlib.Path(sys.argv[1]);scope=pathlib.Path(sys.argv[2]);physical=pathlib.Path(sys.argv[3])
if not s.is_dir() or s.is_symlink() or s.resolve()!=physical or scope.exists() or scope.is_symlink(): raise SystemExit('stage/scope identity changed')
f={};d=[]
for p in sorted(s.rglob('*')):
 r=p.relative_to(s).as_posix()
 if p.is_symlink(): raise SystemExit('stage symlink '+r)
 if p.is_dir():d.append(r)
 elif p.is_file():f[r]=hashlib.sha256(p.read_bytes()).hexdigest()
 else:raise SystemExit('unexpected stage entry '+r)
if f!=m['files'] or d!=m['directories']:raise SystemExit('exact original hash gate failed')
for r in sorted(f,reverse=True):(s/r).unlink()
for r in sorted(d,key=lambda x:(x.count('/'),x),reverse=True):(s/r).rmdir()
s.rmdir()
if s.exists() or scope.exists():raise SystemExit('stage/scope remains')
print(json.dumps({'stage_absent':True,'scope_absent':True,'removed_files':len(f),'removed_directories':len(d)}))'''
    # The same remote interpreter repeats all exact custody and inventory checks
    # immediately before unlinking anything; no host-side gap separates gate/deletion.
    deletion_code=CUSTODY+'\n'+code.replace("print(json.dumps({'stage_absent':True,'scope_absent':True,'removed_files':len(f),'removed_directories':len(d)}))", "print(json.dumps({'stage_absent':True,'scope_absent':True,'removed_files':len(f),'removed_directories':len(d),'predelete_custody':receipt},sort_keys=True))")
    removed=ssh_json(deletion_code,readback)
    if (removed.get('stage_absent') is not True or removed.get('scope_absent') is not True
        or removed.get('removed_files')!=len(readback['files'])
        or removed.get('removed_directories')!=len(readback['directories'])):
        raise RuntimeError('remote retirement receipt does not match the verified original inventory')
    (destination/'remote-retirement.json').write_text(json.dumps(removed,indent=2,sort_keys=True)+'\n')
    after=ssh_json(POST_RETIREMENT,custody)
    (destination/'remote-cleanup.json').write_text(json.dumps({'removed':removed,'fresh_absence':after},indent=2,sort_keys=True)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('collect','cleanup'));parser.add_argument('destination',type=Path,nargs='?',default=DEST);args=parser.parse_args()
    try:
        collect(args.destination) if args.mode=='collect' else cleanup(args.destination)
    except Exception as exc:
        raise SystemExit(f'preserve original stage; {type(exc).__name__}: {exc}')
