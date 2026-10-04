#!/usr/bin/env python3
"""Read fresh exact custody after retirement; never signal or remove resources."""
import csv,hashlib,json,pathlib,shlex,subprocess
root=pathlib.Path(__file__).resolve().parent/'linux-process-performance-evidence/originals'
stage=root/'stage-originals'
manifest=json.loads((root/'export-manifest.json').read_text())
assert json.loads((root/'retirement-readback.json').read_text())['exact_stage_removed'] is True
ids=set();groups=set();bound={}
for name in ['proof-evidence/process-identities.tsv','outer-evidence/launcher-identities.tsv']:
 p=stage/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['files'][name]
 bound[name]=manifest['files'][name]
 rows=list(csv.DictReader(p.open(),delimiter='\t'))
 for r in rows:
  pid,start,group=int(r['pid']),int(r['start_ticks']),int(r['pgid'])
  assert min(pid,start,group)>0
  ids.add((pid,start));groups.add(group)
for name in ['proof-evidence/measurements.stderr','proof-evidence/control-pass.stderr']:
 p=stage/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['files'][name]
 bound[name]=manifest['files'][name]
 for line in p.read_text().splitlines():
  if line.startswith(('PERF_START,','PERF_RESOURCE,','PERF_CONTROL,kind=resource-count,')):
   r=dict(x.split('=',1) for x in line.split(',')[1:]);pid,start=int(r['pid']),int(r['start_ticks'])
   assert min(pid,start)>0
   ids.add((pid,start))
   if r.get('mode')=='managed':
    group=int(r['pgid']);assert group==pid;groups.add(group)
p=stage/'outer-evidence/runtime-cleanup.tsv'
assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['files']['outer-evidence/runtime-cleanup.tsv']
runtime=p.read_text().strip().split(' runtime=',1)[1]
scope='/root/.local/share/agent-builds/rhai/linux-process-performance-8c0ee-20261004'
assert pathlib.PurePosixPath(runtime).parent==pathlib.PurePosixPath(scope)
paths=['/root/rhai-linux-process-performance-8c0ee-20261004',scope,runtime]
paths+=['/var/roothome'+p.removeprefix('/root') for p in paths]
request={'identities':sorted(ids),'owned_groups':sorted(groups),'paths':paths,'bound_originals':bound}
remote=r'''import datetime,json,pathlib,subprocess,sys
def parse_start(raw,pid):
 z=raw.rfind(')');prefix=str(pid)+' ('
 if not raw.startswith(prefix) or z<len(prefix) or raw[z+1:z+2]!=' ':raise ValueError('malformed proc stat')
 fields=raw[z+2:].split()
 if len(fields)<20 or not fields[19].isdigit() or int(fields[19])<=0:raise ValueError('malformed proc start ticks')
 return int(fields[19])
r=json.load(sys.stdin);absent=[]
for pid,start in r['identities']:
 p=pathlib.Path('/proc')/str(pid)/'stat'
 try: text=p.read_text()
 except FileNotFoundError: absent.append([pid,start,'absent']);continue
 actual=parse_start(text,pid)
 if actual==start:raise SystemExit('exact identity remains '+str(pid))
 absent.append([pid,start,'reused'])
missing=[]
for name in r['paths']:
 p=pathlib.Path(name)
 if p.exists() or p.is_symlink():raise SystemExit('owned path remains '+name)
 missing.append(name)
ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)
for line in ps.splitlines():
 fields=line.split()
 if len(fields)!=2 or not all(x.isdecimal() for x in fields):raise SystemExit('malformed fresh census')
 if int(fields[1]) in r['owned_groups']:raise SystemExit('owned group remains '+line)
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'identities':absent,'owned_groups_empty':r['owned_groups'],'paths_absent':missing,'bound_originals':r['bound_originals']},sort_keys=True))'''
result=subprocess.run(['ssh','-o','BatchMode=yes','workhorse','python3 -c '+shlex.quote(remote)],input=json.dumps(request),capture_output=True,text=True,timeout=30,check=True)
value=json.loads(result.stdout)
with (root/'root-fresh-closure.json').open('x') as out:json.dump(value,out,indent=2);out.write('\n')
print(json.dumps({'identities':len(value['identities']),'groups':len(value['owned_groups_empty']),'paths':len(value['paths_absent'])}))
