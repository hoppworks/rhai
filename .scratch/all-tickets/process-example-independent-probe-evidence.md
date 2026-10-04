# Process example independent local probe preservation

These are the sources actually executed during the affected reviews and recorded named-case results. They were not rerun during closeout. Temporary path references document the execution layout, which is now retired. Frozen collector/probe dependencies remain in Git; their bytes were not duplicated here. These are local consumer models, not Linux absence or cleanup proof. Real663 cleanup was reported by the root separately.

## e537 producer/receiver and parser probe

Collector freeze e537a830200519eb39e4477ae46bb3cb144b089b, SHA694d327c4a20f6c0c4c28cadbe0417e6865b3e4dfaf4a91a727b6f51e2bea8c9. Source SHA f484c9078f8248335d959514319f65f5ac029350377c52c07c1d88ad2a43a017.

Recorded results: actual final producer/receiver positive passed; truncated observations, wrong groups and live state rejected; raw inventory has no scope attribute query. Actual parser rejected producer-shaped repeated command labels and empty command argv as documented in the review.

```python
import ast,json,io,contextlib,copy
p='/private/tmp/process-example-collector-e537.py'; t=ast.parse(open(p).read())
constants={n.targets[0].id:ast.literal_eval(n.value) for n in t.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Constant)}
inv=ast.parse(constants['REMOTE_INVENTORY']); custody=ast.parse(constants['REMOTE_CUSTODY'])
assert not any(isinstance(n,ast.Attribute) and isinstance(n.value,ast.Name) and n.value.id=='scope' for n in ast.walk(inv))
ret=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='retire')
delcode=next(ast.literal_eval(n.value) for n in ret.body if isinstance(n,ast.Assign) and any(isinstance(a,ast.Name) and a.id=='deletion' for a in n.targets)); d=ast.parse(delcode)
class Absent:
 def exists(self): return False
 def is_symlink(self): return False
rows=[dict(label=l,pid=i,ppid=1,pgid=g,start_ticks=i+10,cmdline='owned') for l,i,g in [('helper',101,100),('scoped-supervisor',102,100),('launcher',201,200),('run-scoped',202,200)]]
obs=[dict(label=r['label'],pid=r['pid'],start_ticks=r['start_ticks'],pgid=r['pgid'],state='absent') for r in rows]
ns=dict(json=json,s=Absent(),scope=Absent(),r=Absent(),final_obs=obs,groups={200,100},census2=[],files={'a':'h'},dirs=['d'])
b=io.StringIO()
with contextlib.redirect_stdout(b): exec(compile(ast.Module(body=[d.body[-1]],type_ignores=[]),'<actual-final-producer>','exec'),ns)
receipt=json.loads(b.getvalue()); assert receipt['final_groups']==[100,200]
start=next(i for i,n in enumerate(ret.body) if isinstance(n,ast.Assign) and any(isinstance(a,ast.Name) and a.id=='expected_obs' for a in n.targets))
receiver=compile(ast.Module(body=ret.body[start:-1],type_ignores=[]),'<actual-receiver>','exec')
fresh=dict(process_identities=rows[:2],launcher_identities=rows[2:],groups=[100,200])
exec(receiver,dict(receipt=receipt,fresh_custody=fresh))
for change in ('truncate','group','live'):
 bad=copy.deepcopy(receipt)
 if change=='truncate': bad['final_pid_start_observations'].pop()
 if change=='group': bad['final_groups']=[100]
 if change=='live': bad['final_pid_start_observations'][0]['state']='live'
 try: exec(receiver,dict(receipt=bad,fresh_custody=fresh))
 except RuntimeError: pass
 else: raise AssertionError(change)
parser=next(n for n in custody.body if isinstance(n,ast.FunctionDef) and n.name=='parse')
class TSV:
 def is_file(self): return True
 def read_text(self,**kw): return 'label\tpid\tppid\tpgid\tstart_ticks\tcmdline\nhelper\t101\t102\t100\t111\trun-examples.py\nscoped-supervisor\t102\t202\t100\t112\trun_scoped.py\ncommand:du\t103\t101\t100\t113\tdu\ncommand:du\t104\t101\t100\t114\tdu\ncommand:ps\t105\t101\t100\t115\t\n'
errors=[]; pn=dict(errors=errors,HEADER='label\tpid\tppid\tpgid\tstart_ticks\tcmdline')
exec(compile(ast.Module(body=[parser],type_ignores=[]),'<actual-parser>','exec'),pn)
pn['parse'](TSV(),{'helper','scoped-supervisor'},{'helper','scoped-supervisor'})
assert any('duplicate identity label' in e for e in errors) and any('malformed identity row' in e for e in errors)
print('PASS actual final producer/receiver; truncated/group/live negatives; inventory has no scope attribute queries')
print('CONFIRMED producer-contract mismatch:',errors)
```

## c600 independent framing and integer probes

Collector freeze c600773798be9c4b7a134d33e8059622a330b67d, SHA45d7b8bd29ea6800aec8e0e8dd4a54fe68bbd3ebdf4f79c43dfca368667b7a85. Source SHA7a4917600a27f9aa238097938156851077e1f70015440d698386c15215c17e35. At execution, the imported supplied probe and collector were the frozen c600 versions; those temporary dependencies were subsequently replaced by ea7 for its recheck.

Recorded results: actual full custody accepted `missing-open)` and `wrong-pid (x)` as reuse; actual pre-deletion loop accepted malformed framing; actual final loop emitted66 reuse observations. Independent bool integer checks rejected boolean PID/start/PGID/PPID in both identity lists and observations. No deletion statement was executed.

```python
import runpy,ast,pathlib,copy,json
p=runpy.run_path('/private/tmp/c600-independent-review/probe-process-example-custody.py'); c=p['c']; base=p['base']; produce=p['produce']
old=pathlib.Path.read_text
for prefix in ('missing-open)', 'wrong-pid (x)'):
 def fake(path,*a,**kw):
  if str(path).startswith('/proc/') and str(path).endswith('/stat'): return prefix+' S '+' '.join(['1']*18+['999999999'])
  return old(path,*a,**kw)
 pathlib.Path.read_text=fake
 try: result=produce(stat='framing-edge')
 finally: pathlib.Path.read_text=old
 print('ACTUAL_FULL_CUSTODY',prefix,result['custody_ready'],result['pid_start_observations'][0]['state'])
 assert result['custody_ready'] and c.validate_custody_receipt(result)
t=ast.parse(pathlib.Path('/private/tmp/collector-c600.py').read_text()); retire=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='retire'); deletion=next(ast.literal_eval(n.value) for n in retire.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='deletion' for x in n.targets)); d=ast.parse(deletion)
loops=[n for n in d.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='row']
assert len(loops)==2
class FakePath:
 def __init__(self,*a): pass
 def read_text(self): return 'missing-open) S '+' '.join(['1']*18+['999999999'])
class FakeLib: Path=FakePath
for i,loop in enumerate(loops):
 ns=dict(pathlib=FakeLib,c=base,final_obs=[])
 exec(compile(ast.Module(body=[loop],type_ignores=[]),'<actual-retirement-proc-loop>','exec'),ns)
 print('ACTUAL_RETIREMENT_LOOP',i,'accepted malformed framing',len(ns['final_obs']))
# Actual validator rejects bools for every integer identity/observation field.
for section in ('process_identities','launcher_identities','pid_start_observations'):
 for field in ('pid','start_ticks','pgid')+ (() if section=='pid_start_observations' else ('ppid',)):
  bad=copy.deepcopy(base); bad[section][0][field]=True; assert not c.validate_custody_receipt(bad),(section,field)
print('PASS independent integer bool coverage; framing contract rejection missing in all3 loops')
```

## ea7 independently expanded framing checks

Frozen collector ea7ca8f6b30c0a680378f565530a3f616c22b4eb SHA f2864de1aad1b02a498152dfc0efece8fbc45a1e1eac6c062c8b874a094a7d01; frozen supplied probe SHA a0859f6943f1f223b6f87eaf8007835dec6b3e3ab6a7b203daa989e525287def.

Recorded results: supplied original-fixture probe passed e537 identity RED, c600 malformed-stat RED and ea7 rejected malformed framing in custody/both retirement loops; valid reuse with comm spaces/parentheses and signed fields passed. Original rows64+2, repeated du29/ps29, empty argv3, distinct PIDs66 retained. Independent expansion below passed all66 rows × both actual isolated retirement loops: valid reuse and NotFound accepted; missing opening, mismatched PID and matching zombie rejected. Measured command-local probe elapsed1.742seconds. No deletion statement was executed.

```python
import runpy,time,hashlib
start=time.monotonic()
p=runpy.run_path('/private/tmp/c600-independent-review/probe-process-example-custody.py')
loops=p['isolated_retirement_loop']; code=p['deletion_node'].value; shape=p['shaped_stat']
for row in p['base']['process_identities']+p['base']['launcher_identities']:
 rows={'process_identities':[row],'launcher_identities':[],'groups':[row['pgid']]}
 for i in (0,1):
  assert loops(code,i,shape(row,'S',row['start_ticks']+1),rows)
  assert loops(code,i,None,rows)
  for bad in (') S '+' '.join(['1']*18+['999999999']),str(row['pid']+1)+' (x) S '+' '.join(['1']*18+['999999999']),shape(row,'Z',row['start_ticks'])):
   assert not loops(code,i,bad,rows)
print('Independent expanded isolated-loop checks: all66 rows x both loops PASS; no deletion executed')
for name in ('collect-linux-sys-process-example.py','probe-process-example-custody.py'):
 print(name,hashlib.sha256(open('/private/tmp/c600-independent-review/'+name,'rb').read()).hexdigest())
print('Measured local probe elapsed seconds',round(time.monotonic()-start,3))
```

No review/native checks were rerun for this preservation. Unchanged applicable instruction revision: faba3db3bef6891ad2c0b20d434963bb8fe9572d.
