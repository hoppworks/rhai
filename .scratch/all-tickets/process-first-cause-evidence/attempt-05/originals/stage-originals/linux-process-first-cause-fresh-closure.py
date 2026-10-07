#!/usr/bin/env python3
"""Independent fresh closure readback after collector receipts; no signal or deletion."""
import csv,hashlib,json,pathlib,shlex,subprocess
ROOT=pathlib.Path(__file__).resolve().parent
ORIG=ROOT/'originals'
STAGE='/root/rhai-linux-process-first-cause-fc-20261007-ack05-7d11e2c4'
SCOPE='/root/.local/share/agent-builds/rhai/fc-20261007-ack05-7d11e2c4'
PHYSICAL='/var/roothome/rhai-linux-process-first-cause-fc-20261007-ack05-7d11e2c4'
EXPECTED_ARGV=['/usr/bin/python3','-c',"exec(open(__import__('os').environ['RHAI_FIRST_SCRIPT']).read())"]
EXPECTED_ARGV_JSON=json.dumps(EXPECTED_ARGV,separators=(',',':'))
TESTS={
    'direct':'packages::sys::process::unix::tests::committed_stdout_cause_survives_stderr_overflow_direct_child',
    'managed':'packages::sys::process::unix::tests::committed_stdout_cause_survives_stderr_overflow_managed'}

def fixture_receipt(raw,mode,case):
    marker=f'first-cause mode={mode} '
    lines=[line for line in raw.splitlines() if marker in line]
    if len(lines)!=1 or sum(line.count(marker) for line in lines)!=1:raise ValueError('raw fixture receipt missing/duplicated during closure '+case)
    if not lines[0].startswith(f'test {TESTS[mode]} ... {marker}'):raise ValueError('raw fixture receipt is attached to the wrong selected test during closure '+case)
    return marker+lines[0].split(marker,1)[1]

def selected_test_status(stdout,mode,expected):
    prefix=f'test {TESTS[mode]} ... '
    lines=stdout.splitlines();matches=[(i,line[len(prefix):]) for i,line in enumerate(lines) if line.startswith(prefix)]
    if len(matches)!=1:return False
    index,suffix=matches[0]
    if suffix==expected:return True
    return suffix.startswith(f'first-cause mode={mode} ') and index+1<len(lines) and lines[index+1]==expected

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
    if fixture_file.read_text().splitlines()[0]!='case\tpid\tstart_ticks\tpgid\texpected_argv\tobserved_cmdline_hex\tidentity_confirmed\tidentity_gate_released\tidentity_wait\tstdout_write\tstdout_committed\tstderr_write\tstderr_overflow\treap\tgroup_closed':raise ValueError('fixture ledger header changed after collection')
    fixture_rows=list(csv.DictReader(fixture_file.open(),delimiter='\t'))
    expected_cases=['baseline-red-direct','baseline-red-managed','overwrite-red-direct','overwrite-red-managed','restored-green-direct','restored-green-managed']
    if [row.get('case') for row in fixture_rows]!=expected_cases:raise ValueError('fixture mode/order changed after collection')
    for row in fixture_rows:
     name=row['case'];mode=name.rsplit('-',1)[1]
     stdout=bind('proof-evidence/'+name+'.stdout').read_text()
     stderr=bind('proof-evidence/'+name+'.stderr').read_text()
     raw=stdout+'\n'+stderr
     receipt=fixture_receipt(raw,mode,name)
     fields=dict(part.split('=',1) for part in receipt.split()[1:])
     expected_cmdline=b'\0'.join(value.encode() for value in EXPECTED_ARGV)+b'\0'
     try:observed_cmdline=bytes.fromhex(row['observed_cmdline_hex'])
     except ValueError as exc:raise ValueError('fixture argv hex is malformed during closure '+name) from exc
     if (row['pid'],row['start_ticks'],row['pgid'],row['observed_cmdline_hex'],row['identity_confirmed'],row['identity_gate_released'],row['identity_wait'],row['stdout_write'],row['stdout_committed'],row['stderr_write'],row['stderr_overflow'],row['reap'],row['group_closed'])!=(fields.get('child_pid'),fields.get('child_start_ticks'),fields.get('child_pgid'),fields.get('child_cmdline_hex'),fields.get('identity_confirmed'),fields.get('identity_gate_released'),fields.get('identity_wait'),fields.get('stdout_write'),fields.get('stdout_committed'),fields.get('stderr_write'),fields.get('stderr_overflow'),fields.get('reap'),fields.get('group_closed')) or row['expected_argv']!=EXPECTED_ARGV_JSON or observed_cmdline!=expected_cmdline or fields.get('expected_program')!='/usr/bin/python3' or fields.get('expected_argv_count')!='3':raise ValueError('fixture identity/readiness/cleanup/argv differs from raw command receipt '+name)
     if any(v not in receipt for v in ('identity_confirmed=true','identity_gate_released=true','identity_wait=acknowledged','stdout_write=acknowledged','stdout_committed=true','stderr_write=acknowledged','stderr_overflow=observed','reap=ESRCH')):raise ValueError('actual readiness/closure missing '+name)
     expected_outcome='ok' if name.startswith('restored-green-') else 'FAILED'
     if not selected_test_status(stdout,mode,expected_outcome):raise ValueError('selected test outcome missing during closure '+name)
    for r in fixture_rows:
     pid,start,pgid=int(r['pid']),int(r['start_ticks']),int(r['pgid'])
     if min(pid,start,pgid)<=0:raise ValueError('nonpositive fixture identity during closure')
     ids.add((pid,start))
     if r['case'].endswith('-managed'):
      assert pid==pgid;groups.add(pgid)
    runtime=json.loads(bind('proof-evidence/early-runtime-identity.json').read_text())['runtime']
    assert pathlib.PurePosixPath(runtime).parent==pathlib.PurePosixPath(SCOPE)
    paths=[STAGE,SCOPE,runtime,PHYSICAL,PHYSICAL.replace('/var/roothome','/root'),'/var/roothome/.local/share/agent-builds/rhai/fc-20261007-ack05-7d11e2c4']
    request={'identities':sorted(ids),'owned_groups':sorted(groups),'paths':paths,'bound_originals':bound}
    value=invoke_closure(request)
    path=ORIG/'root-fresh-closure.json'
    with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
    print(json.dumps({'identities':len(value['identities']),'owned_groups':len(value['owned_groups_empty']),'paths':len(value['paths_absent'])}))

if __name__ == "__main__":
    main()
