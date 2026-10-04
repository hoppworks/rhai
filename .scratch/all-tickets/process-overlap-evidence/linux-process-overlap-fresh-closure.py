#!/usr/bin/env python3
"""Independent fresh closure readback after collector receipts; no signal or deletion."""
import csv,hashlib,json,pathlib,shlex,subprocess
ROOT=pathlib.Path(__file__).resolve().parent
ORIG=ROOT/'originals'
STAGE='/root/rhai-linux-process-overlap-d79-20261004-1259'
SCOPE='/root/.local/share/agent-builds/rhai/linux-process-overlap-d79-20261004-1259'
PHYSICAL='/var/roothome/rhai-linux-process-overlap-d79-20261004-1259'
remote=r'''import datetime,json,pathlib,subprocess,sys
r=json.load(sys.stdin);absent=[]
def start(raw,pid):
 z=raw.rfind(')');prefix=str(pid)+' ('
 if not raw.startswith(prefix) or z<len(prefix) or raw[z+1:z+2]!=' ':raise ValueError('malformed proc stat framing')
 f=raw[z+2:].split()
 if len(f)<20 or len(f[0])!=1 or f[0] not in 'RSDZTtXxKWPI' or not f[19].isdigit() or int(f[19])<=0:raise ValueError('malformed proc stat/start ticks')
 return int(f[19])
for pid,tick in r['identities']:
 p=pathlib.Path('/proc')/str(pid)/'stat'
 try:raw=p.read_text()
 except FileNotFoundError:absent.append([pid,tick,'absent']);continue
 if start(raw,pid)==tick:raise SystemExit('exact process identity remains '+str(pid))
 absent.append([pid,tick,'reused'])
missing=[]
for name in r['paths']:
 p=pathlib.Path(name)
 if p.exists() or p.is_symlink():raise SystemExit('owned path remains '+name)
 missing.append(name)
ps=subprocess.check_output(['/bin/ps','-e','-o','pid=,pgid='],text=True,timeout=5)
for line in ps.splitlines():
 f=line.split()
 if len(f)!=2 or not all(x.isdecimal() for x in f):raise SystemExit('malformed fresh process census')
 if int(f[1]) in r['owned_groups']:raise SystemExit('owned process group remains '+line)
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'identities':absent,'owned_groups_empty':r['owned_groups'],'paths_absent':missing,'bound_originals':r['bound_originals']},sort_keys=True))'''

def invoke_closure(request_value, ssh_run=subprocess.run):
    completed=ssh_run(['ssh','-o','BatchMode=yes','workhorse','python3 -c '+shlex.quote(remote)],
                      input=json.dumps(request_value),capture_output=True,text=True,timeout=30,check=True)
    return json.loads(completed.stdout)


def main():
    manifest=json.loads((ORIG/'export-manifest.json').read_text()); tree=ORIG/'stage-originals'
    assert json.loads((ORIG/'retirement-readback.json').read_text())['exact_stage_removed'] is True
    ids=set();groups=set();bound={}
    def bind(rel):
     p=tree/rel;actual=hashlib.sha256(p.read_bytes()).hexdigest()
     assert actual==manifest['files'][rel], 'original hash mismatch '+rel
     bound[rel]=actual
     return p
    for rel in ('proof-evidence/process-identities.tsv','outer-evidence/launcher-identities.tsv'):
     identity_file=bind(rel)
     if identity_file.read_text().splitlines()[0]!='label\tpid\tppid\tpgid\tstart_ticks\tcmdline':raise ValueError('identity ledger header changed after collection '+rel)
     rows=list(csv.DictReader(identity_file.open(),delimiter='\t'))
     for r in rows:
      pid,start,pgid=int(r['pid']),int(r['start_ticks']),int(r['pgid'])
      if min(pid,start,pgid)<=0:raise ValueError('nonpositive fresh identity '+rel)
      ids.add((pid,start));groups.add(pgid)
    rel='proof-evidence/fixture-identities.tsv'
    fixture_file=bind(rel)
    if fixture_file.read_text().splitlines()[0]!='case\tpid\tstart_ticks\tpgid\twrite\tdeadline\tpoll\toverflow\treap\towner\texpected_command':raise ValueError('fixture ledger header changed after collection')
    fixture_rows=list(csv.DictReader(fixture_file.open(),delimiter='\t'))
    expected_cases=['timeout-first-direct','timeout-first-managed','restored-direct','restored-managed']
    if [row.get('case') for row in fixture_rows]!=expected_cases:raise ValueError('fixture mode/order changed after collection')
    for row in fixture_rows:
     name=row['case'];mode=name.rsplit('-',1)[1]
     raw=(bind('proof-evidence/'+name+'.stdout').read_text()+'\n'+bind('proof-evidence/'+name+'.stderr').read_text())
     lines=[line for line in raw.splitlines() if line.startswith(f'overlap-fixture mode={mode} ')]
     if len(lines)!=1:raise ValueError('raw fixture receipt missing/duplicated during closure '+name)
     fields=dict(part.split('=',1) for part in lines[0].split()[1:])
     if (row['pid'],row['start_ticks'],row['pgid'],row['write'],row['deadline'],row['poll'],row['overflow'],row['reap'],row['owner'])!=(fields.get('child_pid'),fields.get('child_start_ticks'),fields.get('child_pgid'),fields.get('child_write'),fields.get('deadline'),fields.get('poll'),fields.get('overflow_observed'),fields.get('reap'),fields.get('owner')) or row['expected_command']!='/bin/sleep 30':raise ValueError('fixture identity/readiness/cleanup differs from raw command receipt '+name)
     if any(v not in lines[0] for v in ('child_write=acknowledged','deadline=expired','poll=stdout-readable','reap=ESRCH','owner=closed')):raise ValueError('actual readiness/closure missing '+name)
    for r in fixture_rows:
     pid,start,pgid=int(r['pid']),int(r['start_ticks']),int(r['pgid'])
     if min(pid,start,pgid)<=0:raise ValueError('nonpositive fixture identity during closure')
     ids.add((pid,start))
     if r['case'].endswith('-managed'):
      assert pid==pgid;groups.add(pgid)
    runtime=json.loads(bind('proof-evidence/early-runtime-identity.json').read_text())['runtime']
    assert pathlib.PurePosixPath(runtime).parent==pathlib.PurePosixPath(SCOPE)
    paths=[STAGE,SCOPE,runtime,PHYSICAL,PHYSICAL.replace('/var/roothome','/root'),'/var/roothome/.local/share/agent-builds/rhai/linux-process-overlap-d79-20261004-1259']
    request={'identities':sorted(ids),'owned_groups':sorted(groups),'paths':paths,'bound_originals':bound}
    value=invoke_closure(request)
    path=ORIG/'root-fresh-closure.json'
    with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
    print(json.dumps({'identities':len(value['identities']),'owned_groups':len(value['owned_groups_empty']),'paths':len(value['paths_absent'])}))

if __name__ == "__main__":
    main()
