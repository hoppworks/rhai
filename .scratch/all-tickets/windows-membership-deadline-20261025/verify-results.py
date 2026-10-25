"""Offline acceptance from original native exports; no new Windows execution."""
import json,hashlib,re,zlib
from pathlib import Path, PureWindowsPath
p=Path(__file__).resolve().parent;b=json.loads((p/'binding.json').read_text())
def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
build=p/(b['build_tag']+'-export');br=read(p/(b['build_tag']+'-export-readback.json'));bo=read(build/'build-observer.json')
assert br['begin']['accepted'] and br['end']['accepted'] and br['end']['exit']==0 and bo['accepted'] and bo['exact_build_exited'] and bo['exit']==0
assert bo['source_pins']==b['new_source_pins']
assert sha(build/'run'/('monitor-source-'+b['nonce'])/'build/MonitorDeathFixture.exe')==bo['fixture_sha256']
results=[]
for c in b['cases']:
 root=p/(c['tag']+'-export');r=read(p/(c['tag']+'-export-readback.json'));o=read(root/'observer.json')
 assert r['begin']==o and r['end']['accepted'] and o['accepted'] and o['id']==c['id'] and o['mode']==c['mode']
 for flag in ('fresh_host_record','wrong_expectation_red','membership_negative_control','actors_stopped','runtime_absent_readback','runtime_absence_negative_control','exact_driver_exited','pipes_drained'):assert o[flag],flag
 assert not o['retained_driver_handles'] and o['fixture_sha256']==bo['fixture_sha256']
 actors=o['actors'];assert len(actors)==2 and actors[0]['pid']!=actors[1]['pid']
 run=root/'run';js=list(run.glob('.scoped-run-*.journal'));assert len(js)==1
 rows=[]
 for line in js[0].read_bytes().splitlines():
  size,crc,body=line.split(b':',2);assert len(body)==int(size,16) and zlib.crc32(body)==int(crc,16);rows.append(body.decode('ascii').split('|'))
 assert [x[0] for x in rows]==['INTENT','IDENTITY','STAGED','LIFECYCLE','EVIDENCE','OUTCOME','REMOVE_INTENT','REMOVED']
 fields=lambda row:dict(x.split('=',1) for x in row if '=' in x)
 evidence=fields(rows[4]);outcome=fields(rows[5]);assert evidence['proof']=='EXACT' and outcome['cleanup']=='CONFIRMED' and outcome['runtime_removed']=='0'
 snapshot=list(run.glob('.scoped-evidence-*'));assert len(snapshot)==1;snapshot=snapshot[0]
 for field,name in (('manifest','manifest.txt'),('stdout','stdout.log'),('stderr','stderr.log')):assert sha(snapshot/name).upper()==evidence[field]
 runtime=snapshot/'runtime';assert sha(runtime/'fixture.exe')==bo['fixture_sha256']
 members=','.join(str(x) for x in sorted(a['pid'] for a in actors))
 for i,name in enumerate(('pair','pair.child')):
  a=actors[i];peer=actors[1-i]
  identity=f"pid={a['pid']} creation={a['creation']}";peerid=f"pid={peer['pid']} creation={peer['creation']}"
  assert (runtime/(name+'.identity')).read_bytes()==(identity+'\r\n').encode()
  expected='self='+identity+';peer='+peerid+';members='+members+';assigned=2;returned=2\r\n'
  assert (runtime/(name+'.membership')).read_bytes()==expected.encode()
 assert (runtime/'pair.child.release').read_bytes()==b'both-members-confirmed\r\n'
 assert (runtime/'pair.child.work').read_bytes()==b'child-work-after-both-membership\r\n'
 assert (runtime/'pair.work').read_bytes()==b'parent-work-after-both-membership\r\n'
 assert (runtime/'pair.ready').read_bytes()==b'both-membership-and-work-confirmed\r\n'
 assert PureWindowsPath(o['allocated_runtime'])==PureWindowsPath(rows[0][2])
 assert PureWindowsPath(o['allocated_runtime']).parent==PureWindowsPath(o['run'])
 if c['mode']=='membership':assert o['exit']==0 and evidence['exit']=='00000000' and evidence['supervision']=='PayloadExited'
 else:
  assert o['pair_seen_live'] and 179<=o['elapsed_seconds']<=310
  assert o['exit']==124 or (o['exit']==2 and b'whole-driver deadline expired' in (root/'bootstrap.stderr').read_bytes())
  assert evidence['exit']=='0000007D' and evidence['supervision']=='MonitorStopped'
  assert [(a['pid'],a['creation']) for a in actors]==[(a['pid'],int(a['creation'])) for a in o['live_identities']]
 results.append({'mode':c['mode'],'accepted':True,'driver_exit':o['exit'],'payload_exit':evidence['exit'],'supervision':evidence['supervision'],'crc_records':len(rows),'frames':r['frames'],'files':len(r['files']),'actor_count':len(actors),'elapsed_seconds':o['elapsed_seconds']})
(p/'semantic-results.json').write_text(json.dumps({'accepted':True,'cases':results,'compiler_launches':1,'public_drivers':2,'monitor_absolute_30minute_deadline':'not proved'},indent=2)+'\n')
(p/'host-accepted-readback.json').write_text(json.dumps({'nonce':b['nonce'],'accepted':True,'build':br,'cases':[{'id':c['id'],'scope':read(p/(c['tag']+'-export/observer.json'))['scope'],'readback':read(p/(c['tag']+'-export-readback.json'))}for c in b['cases']]},indent=2)+'\n')
print((p/'semantic-results.json').read_text())
