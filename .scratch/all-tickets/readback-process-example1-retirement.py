"""Independent readback after exact failed-example stage retirement."""
import datetime
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent / "process-example1-originals"
OUTPUT = BASE.parent / "process-example1-retirement-independent.json"
INPUTS = [
    ("proof-evidence/process-identities.tsv", "f7949153ace6ecfc2b7a4b491308f6e1cd72d01b3c7d2fbab0a422a24a3a9aaf"),
    ("outer-evidence/launcher-identities.tsv", "a3ef24e9092e530e7e41dc7d147bea70fe216769a321bcf2d49abd339d60de81"),
]
REMOTE = r"""
import json,pathlib,subprocess,sys
expected=json.loads(sys.argv[1]); states={}
for name,path in expected['paths'].items():
 try: pathlib.Path(path).lstat()
 except FileNotFoundError: states[name]='absent'
 else: raise RuntimeError('owned path remains: '+name)
observations=[]
for row in expected['identities']:
 pid=row['pid']; target=pathlib.Path('/proc',str(pid),'stat')
 try:
  raw=target.read_text(); closing=raw.rfind(')')
  if not raw.startswith(str(pid)+' (') or closing<=len(str(pid))+1 or raw[closing+1:closing+2]!=' ':
   raise ValueError('malformed proc stat framing')
  fields=raw[closing+2:].split()
  if len(fields)<20 or len(fields[0])!=1:
   raise ValueError('malformed proc stat fields')
  numbers=[int(value) for value in fields[1:20]]
  if numbers[-1]<=0: raise ValueError('nonpositive proc start ticks')
  state='live' if numbers[-1]==row['start_ticks'] else 'pid-reused-original-absent'
 except FileNotFoundError: state='absent'
 if state=='live': raise RuntimeError('original identity still live: '+str(pid))
 observations.append(dict(row,state=state))
result=subprocess.run(['/bin/ps','-e','-o','pid=,pgid='],check=True,capture_output=True,text=True,timeout=5)
members=[]
for line in result.stdout.splitlines():
 fields=line.split()
 if len(fields)!=2 or not all(v.isdigit() for v in fields) or int(fields[0])<=0:
  raise ValueError('malformed group observation')
 if int(fields[1]) in expected['groups']: members.append([int(v) for v in fields])
if members: raise RuntimeError('owned groups occupied: '+repr(members))
print(json.dumps(dict(paths=states,pid_start_observations=observations,groups=expected['groups'],group_members=members),sort_keys=True))
"""

def main():
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    receipt=json.loads((BASE/"retirement-receipt.json").read_text())
    assert receipt["stage_absent"] is True and receipt["scope_absent"] is True
    assert receipt["runtime_absent"] is True and receipt["custody_rechecked"] is True
    assert receipt["removed_files"]==49 and receipt["removed_directories"]==6
    identities=[]
    for name,digest in INPUTS:
        raw=(BASE/"stage-originals"/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==digest
        lines=raw.decode().splitlines()
        assert lines[0]=="label\tpid\tppid\tpgid\tstart_ticks\tcmdline"
        for line in lines[1:]:
            fields=line.split("\t",5)
            assert len(fields)==6
            pid,ppid,pgid,start=map(int,fields[1:5])
            assert min(pid,ppid,pgid,start)>0
            identities.append(dict(label=fields[0],pid=pid,start_ticks=start,pgid=pgid))
    assert len(identities)==66 and len({r["pid"] for r in identities})==66
    groups=sorted({r["pgid"] for r in identities})
    assert groups==[3061340,3061410]
    assert receipt["final_groups"]==groups and receipt["final_group_census"]==[]
    expected_tuples={(r["label"],r["pid"],r["start_ticks"],r["pgid"]) for r in identities}
    final=receipt["final_pid_start_observations"]
    assert len(final)==66
    assert {(r["label"],r["pid"],r["start_ticks"],r["pgid"]) for r in final}==expected_tuples
    assert all(r["state"] in ("absent","pid-reused-original-absent") for r in final)
    scope="/root/.local/share/agent-builds/rhai/linux-sys-process-example-66379d30-20261004"
    payload=dict(identities=identities,groups=groups,paths=dict(
        logical_stage="/root/rhai-linux-sys-process-example-66379d30-20261004",
        physical_stage="/var/roothome/rhai-linux-sys-process-example-66379d30-20261004",
        scope=scope,runtime=scope+"/agent-build-rqtg34_b"))
    command="python3 -c "+shlex.quote(REMOTE)+" "+shlex.quote(json.dumps(payload))
    run=subprocess.run(["ssh","-o","BatchMode=yes","workhorse",command],check=True,capture_output=True,text=True,timeout=30)
    actual=json.loads(run.stdout)
    assert actual["paths"]=={k:"absent" for k in payload["paths"]}
    assert actual["groups"]==groups and actual["group_members"]==[]
    rows=actual["pid_start_observations"]
    assert len(rows)==66
    assert {(r["label"],r["pid"],r["start_ticks"],r["pgid"]) for r in rows}==expected_tuples
    assert all(r["state"] in ("absent","pid-reused-original-absent") for r in rows)
    actual.update(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  acceptance=False,closure="exact original stage retirement",
                  retirement_receipt_sha256=hashlib.sha256((BASE/"retirement-receipt.json").read_bytes()).hexdigest())
    with OUTPUT.open("x") as handle:
        json.dump(actual,handle,indent=2,sort_keys=True)
        handle.write("\n")
    print(json.dumps(dict(verified=True,identities=66,groups=groups,owned_paths_absent=4,acceptance=False)))

if __name__=="__main__":
    main()
