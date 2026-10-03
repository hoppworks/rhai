#!/usr/bin/env python3
"""Collect run95 only after exact managed-zombie evidence and custody readback."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import sys
import tarfile
import tempfile

PREFIX = "linux-managed-zombie-20261003-257edf69"
STAGE = "/root/rhai-linux-managed-zombie-20261003-257edf69-95"
SCOPE = "/root/.local/share/agent-builds/rhai/linux-managed-zombie-20261003-257edf69-95"
PHYSICAL = "/var/roothome/rhai-linux-managed-zombie-20261003-257edf69-95"
EXPECTED = 0
REMOTE = r'''import hashlib,json,pathlib,re,subprocess,sys
stage=pathlib.Path(sys.argv[1]); scope=pathlib.Path(sys.argv[2]); physical=pathlib.Path(sys.argv[3])
if not stage.is_dir() or stage.is_symlink() or stage.resolve()!=physical: raise SystemExit("run95 stage missing, symlinked, or noncanonical")
if scope.exists() or scope.is_symlink(): raise SystemExit("run95 scope remains; refuse acceptance/cleanup")
subprocess.run(["sha256sum","--check","input-identities.sha256"],cwd=stage,check=True,stdout=subprocess.DEVNULL)
source=(stage/"source.sha256").read_text().split()
if len(source)!=2 or source[1]!="source.tar" or source[0]!="ea085b4d28ee5ce3c7b998044242a50c755d9e9252638dbcf28c036b3df7c922" or hashlib.sha256((stage/"source.tar").read_bytes()).hexdigest()!=source[0]: raise SystemExit("frozen source archive identity mismatch")
contract=(stage/"contract.md").read_text()
pins=(
 "source_revision=257edf695f953271adf17b12dcc70c4287ae76b5",
 "source_archive_sha256=ea085b4d28ee5ce3c7b998044242a50c755d9e9252638dbcf28c036b3df7c922",
 "lock_sha256=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425",
 "base_helper_sha256=59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06",
 "proof_helper_sha256=bc2650660bb1c3a576a6f33507f87b8254c74a9e17f7053e7e1f754238eb417d",
 "test_file_sha256=8ec4d456672338920249446618ce768bc2fa1d29798d571dca1e897db87a076b",
 "contract_sha256=f8c7520d931144f8e72e90b782455b1e6c32d4c3eb47c392ea7a74f8d3168ec7",
 "exact_tests=1","feature_rows=1","positive_exact_invocations=1","negative_controls=2",
 "test_exact_invocations=3","rust_toolchain=1.77.2-x86_64-unknown-linux-gnu",
 "outer_timeout_seconds=600","run_scoped_timeout_seconds=585","helper_deadline_seconds=540",
 "export_reserve_seconds=30","cargo_build_jobs=2","max_descendants=16",
 "storage_preemptive_stop_kib=1572864","storage_hard_stop_kib=2097152","rss_hard_stop_kib=2097152")
if any(pin not in contract for pin in pins): raise SystemExit("run95 contract pins mismatch")
e=stage/"outer-evidence"
status_names=("outer-status.txt","run-scoped.status","pid-readback.status","pid-readback-launcher.status")
statuses={n:int((e/n).read_text().strip()) for n in status_names}
if statuses["outer-status.txt"]!=0 or statuses["run-scoped.status"]!=0: raise SystemExit(f"run95 expected-success status mismatch: {statuses}")
if statuses["pid-readback.status"]!=0 or statuses["pid-readback-launcher.status"]!=0: raise SystemExit(f"run95 custody readback incomplete: {statuses}")
for n in ("runtime-cleanup.tsv","scope-cleanup.tsv"):
 if "cleanup_status=0" not in (e/n).read_text(): raise SystemExit(f"run95 exact cleanup not confirmed in {n}")
def read_owned(path,required):
 rows=path.read_text(errors="strict").splitlines(); seen=set(); groups=set(); records=[]
 for line in rows[1:]:
  f=line.split("\t",5)
  if len(f)!=6 or not f[1].isdigit() or not f[3].isdigit() or not f[4].isdigit(): raise SystemExit(f"malformed exact process custody row: {line!r}")
  label,pid,ppid,pgid,start,_cmd=f; pid=int(pid); pgid=int(pgid); seen.add(label)
  try:
   raw=pathlib.Path("/proc",str(pid),"stat").read_text(); fields=raw[raw.rfind(")")+2:].split(); alive=fields[19]==start
  except FileNotFoundError: alive=False
  except (PermissionError,OSError,IndexError,ValueError) as ex: raise SystemExit(f"exact custody PID readback unknown {label} {pid}: {ex}")
  if alive: raise SystemExit(f"run95 owned process remains: {label} {pid}/{start}")
  if label in ("helper","scoped-supervisor"): groups.add(pgid)
  records.append({"label":label,"pid":pid,"start_ticks":start,"ppid":int(ppid),"pgid":pgid,"matching_process_alive":False})
 if not required.issubset(seen): raise SystemExit(f"required exact custody identities absent: {required-seen}")
 return records,groups
owned,groups=read_owned(stage/"proof-evidence/process-identities.tsv",{"helper","scoped-supervisor"})
launchers,launcher_groups=read_owned(e/"launcher-identities.tsv",{"launcher","run-scoped"})
if not groups: raise SystemExit("run95 helper process groups were not recorded")
ps0=subprocess.check_output(["/bin/ps","-e","-o","pid=,pgid="],text=True,timeout=5)
left=[[int(x.split()[0]),int(x.split()[1])] for x in ps0.splitlines() if len(x.split())==2 and int(x.split()[1]) in groups]
if left: raise SystemExit(f"run95 helper process group remains populated: {left!r}")
proof=stage/"proof-evidence"
def streams(label):
 return ((proof/(label+".stdout")).read_text(errors="strict"),
         (proof/(label+".stderr")).read_text(errors="strict"))
def output(label):
 a,b=streams(label); return a+b
def outer_result(stdout,stderr,failed=False,assertion=None):
 name="managed_run_reports_while_fixture_reaper_holds_stopped_zombies"
 prefixes=re.findall(r"(?m)^test "+re.escape(name)+r" \.\.\..*$",stdout)
 if len(prefixes)!=1: raise SystemExit(f"outer libtest name prefix count mismatch: {len(prefixes)}")
 summaries=re.findall(r"(?m)^test result: .*?$",stdout)
 if not summaries: raise SystemExit("outer libtest summary missing from stdout")
 summary=summaries[-1]
 pat=(r"test result: FAILED\. 0 passed; 1 failed; 0 ignored; 0 measured; \d+ filtered out; finished in \d+(?:\.\d+)?s" if failed else r"test result: ok\. 1 passed; 0 failed; 0 ignored; 0 measured; \d+ filtered out; finished in \d+(?:\.\d+)?s")
 if not re.fullmatch(pat,summary): raise SystemExit(f"outer final libtest summary mismatch: {summary!r}")
 if failed:
  block=stdout.split("failures:",1)
  if len(block)!=2: raise SystemExit("outer failure list missing")
  names=[x.strip() for x in block[1].split("test result:",1)[0].splitlines() if x.strip() and x.strip()!="failures:"]
  if names!=[name]: raise SystemExit(f"outer failure list mismatch: {names!r}")
  if len(re.findall(r"(?m)^thread '"+re.escape(name)+r"' panicked at tests/sys_process\.rs:1676:5:$",stderr))!=1: raise SystemExit("named panic did not originate in the exact managed test")
  if not assertion or stderr.count(assertion)!=1: raise SystemExit(f"expected exact panic assertion missing/duplicated in stderr: {assertion!r}")
 return summary
def require(text,items,label):
 missing=[x for x in items if x not in text]
 if missing: raise SystemExit(f"{label} lacks required receipt(s): {missing!r}")
green=output("managed-zombie-green")
green_stdout,green_stderr=streams("managed-zombie-green")
outer_result(green_stdout,green_stderr)
require(green,["host_live_at_return=true","leader_reaped=true","worker_state=Z","leaf_state=Z","api_outcome=typed_process_io","cause_op=observe_process_group_closure","cause_op_matches=true","kind=TimedOut exit=Some(0)","stdout_complete=true stderr_complete=true diagnostic=true","managed_held_zombie_cleanup worker=","reaper_status=ExitStatus(unix_wait_status(0))"],"green boundary/cleanup")
pat=re.compile(r"managed_held_zombie_boundary host_live_at_return=true leader=(\d+) leader_start=(\d+) leader_reaped=true worker=(\d+) worker_start=(\d+) worker_state=Z worker_pgid=(\d+) leaf=(\d+) leaf_start=(\d+) leaf_state=Z leaf_pgid=(\d+) group=(\d+).*?capture_complete=true host=(\d+) host_start=(\d+) api_success=false api_outcome=typed_process_io cause_op=observe_process_group_closure cause_op_matches=true kind=TimedOut exit=Some\(0\) stdout_complete=true stderr_complete=true diagnostic=true cause_details=.*? cleanup_diagnostics=.*?\s+held=\"pid=(\d+) start=(\d+) host_status=(\d+) worker=Some\((\d+)\) worker_start=Some\((\d+)\) leaf=Some\((\d+)\) leaf_start=Some\((\d+)\) held_zombies=true\\n\" reaper_status=ExitStatus\(unix_wait_status\(0\)\)",re.S)
def parse_receipt(text,label):
 m=pat.search(text)
 if not m: raise SystemExit(f"{label} missing exact current held-reaper/boundary/status receipt")
 v=list(map(int,m.groups()))
 leader,ls,worker,ws,wpg,leaf,le,lpg,group,host,hs,reaper,rs,hstatus,hw,hws,hl,hls=v
 if len({leader,worker,leaf})!=3 or len({leader,group,wpg,lpg})!=1: raise SystemExit(f"{label} PID hierarchy/group mismatch")
 if hstatus!=0 or (hw,hws,hl,hls)!=(worker,ws,leaf,le): raise SystemExit(f"{label} held reaper receipt identity/status mismatch")
 cleanup=re.search(r"managed_held_zombie_cleanup worker=(\d+) reaped=true leaf=(\d+) reaped=true",text)
 if not cleanup or tuple(map(int,cleanup.groups()))!=(worker,leaf): raise SystemExit(f"{label} cleanup receipt does not match held worker/leaf")
 got=re.findall(r"managed_pidfd_acquired pid=(\d+) start=(\d+) ppid=(\d+) pgid=(\d+)",text)
 if len(got)!=3: raise SystemExit(f"{label} expected exactly three PIDFD identity receipts")
 pidfds={int(pid):(int(st),int(pp),int(pg)) for pid,st,pp,pg in got}
 exp={leader:(ls,host,group),worker:(ws,leader,wpg),leaf:(le,worker,lpg)}
 if pidfds!=exp: raise SystemExit(f"{label} acquired PIDFD identities/parents disagree with exact boundary")
 ids={"leader":(leader,ls),"worker":(worker,ws),"leaf":(leaf,le),"host":(host,hs),"fixture-reaper":(reaper,rs)}
 return ids,group,pidfds
expected_ids,group,pidfds=parse_receipt(green,"green")
cleanup=proof/"green-fixture-closure.json"
closure=json.loads(cleanup.read_text())
if closure.get("fixture_group")!=group or closure.get("fixture_group_members_after_cleanup")!=[]: raise SystemExit("green group cleanup receipt mismatch")
rows={(r.get("label"),int(r.get("pid",-1)),int(r.get("start_ticks",-1))):r for r in closure.get("fixture_pid_start_identities",[])}
for label,(pid,start) in expected_ids.items():
 row=rows.get((label,pid,start))
 if row is None or row.get("matching_identity_alive") is not False: raise SystemExit(f"missing exact post-cleanup identity receipt: {label} {pid}/{start}")
 try:
  raw=pathlib.Path("/proc",str(pid),"stat").read_text(); fields=raw[raw.rfind(")")+2:].split(); same=fields[19]==str(start)
 except FileNotFoundError: same=False
 except (PermissionError,OSError,IndexError,ValueError) as ex: raise SystemExit(f"fixture PID/start readback unknown {label} {pid}: {ex}")
 if same: raise SystemExit(f"fixture PID/start identity still alive: {label} {pid}/{start}")
ps=subprocess.check_output(["/bin/ps","-e","-o","pid=,pgid="],text=True,timeout=5)
live=[[int(x.split()[0]),int(x.split()[1])] for x in ps.splitlines() if len(x.split())==2 and int(x.split()[1])==group]
if live: raise SystemExit(f"fixture process group still has members: {live!r}")
controls={"require-success-while-held":"managed-zombie-control require-success assertion","require-exit-seven":"managed-zombie-control require-exit-seven assertion"}
for name,needle in controls.items():
 text=output(name); control_stdout,control_stderr=streams(name)
 if int((proof/(name+".status")).read_text().strip())!=101: raise SystemExit(f"{name} did not exit with expected assertion status 101")
 outer_result(control_stdout,control_stderr,failed=True,assertion=needle)
 require(text,["managed_held_zombie_boundary","kind=TimedOut exit=Some(0)","managed_held_zombie_cleanup worker=","reaper_status=ExitStatus(unix_wait_status(0))"],name)
 cm=pat.search(text)
 if not cm: raise SystemExit(f"{name} lacks exact typed boundary receipt")
 cids,c_group,c_pidfds=parse_receipt(text,name)
 cclosure=json.loads((proof/(name+"-fixture-closure.json")).read_text())
 if cclosure.get("fixture_group")!=c_group or cclosure.get("fixture_group_members_after_cleanup")!=[]: raise SystemExit(f"{name} missing exact empty-group cleanup receipt")
 crows={(r.get("label"),int(r.get("pid",-1)),int(r.get("start_ticks",-1))):r for r in cclosure.get("fixture_pid_start_identities",[])}
 for label,(pid,start) in cids.items():
  row=crows.get((label,pid,start))
  if row is None or row.get("matching_identity_alive") is not False: raise SystemExit(f"{name} missing cleanup identity {label} {pid}/{start}")
  try:
   raw=pathlib.Path("/proc",str(pid),"stat").read_text(); fields=raw[raw.rfind(")")+2:].split(); same=fields[19]==str(start)
  except FileNotFoundError: same=False
  except (PermissionError,OSError,IndexError,ValueError) as ex: raise SystemExit(f"{name} fixture identity unreadable {label}: {ex}")
  if same: raise SystemExit(f"{name} fixture identity remains live: {label} {pid}/{start}")
 cps=subprocess.check_output(["/bin/ps","-e","-o","pid=,pgid="],text=True,timeout=5)
 cmembers=[[int(x.split()[0]),int(x.split()[1])] for x in cps.splitlines() if len(x.split())==2 and int(x.split()[1])==c_group]
 if cmembers: raise SystemExit(f"{name} fixture group remains populated: {cmembers!r}")
restore=json.loads((proof/"source-restoration.json").read_text())
if restore.get("restored_test_matches_original") is not True or restore.get("original_test_sha256",{}).get("tests/sys_process.rs")!="8ec4d456672338920249446618ce768bc2fa1d29798d571dca1e897db87a076b": raise SystemExit("test source byte restoration was not verified")
# Confirm fresh identity absence for all unique exact identities from green and controls.
ids=[]
for label,(pid,start) in expected_ids.items(): ids.append({"label":label,"pid":pid,"start_ticks":start,"matching_identity_alive":False})
files={}; dirs=[]
for p in sorted(stage.rglob("*")):
 rel=p.relative_to(stage).as_posix()
 if p.is_symlink(): raise SystemExit(f"symlink in run95 stage: {rel}")
 if p.is_dir(): dirs.append(rel)
 elif p.is_file(): files[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
 else: raise SystemExit(f"unexpected stage entry: {rel}")
fixed={
 "Cargo.lock.accepted":"2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425",
 "check-linux-current-msrv-examples.py":"59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06",
 "linux-managed-zombie-proof.py":"bc2650660bb1c3a576a6f33507f87b8254c74a9e17f7053e7e1f754238eb417d",
 "contract-source.md":"f8c7520d931144f8e72e90b782455b1e6c32d4c3eb47c392ea7a74f8d3168ec7",
 "stage.sh":"33125b53871f658df8943b41fd8ddbdbf9ef9888f0221a7b292746ba11496805",
 "launch.sh":"687ac9ca540de8349547a580e1b3fb38237a272d00f7a9505cbfb59acc3f1eab",
 "runner/tools/run_scoped.py":"9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d",
 "runner/tools/agentskills/__init__.py":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
 "runner/tools/agentskills/pyguard.py":"a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f"}
for rel,digest in fixed.items():
 if files.get(rel)!=digest: raise SystemExit(f"run95 pinned input hash mismatch: {rel}")
selected=("proof-evidence","outer-evidence","source.sha256","contract.md","input-identities.sha256","Cargo.lock.accepted","source.tar","check-linux-current-msrv-examples.py","linux-managed-zombie-proof.py","contract-source.md","stage.sh","launch.sh","runner/tools/run_scoped.py","runner/tools/agentskills/__init__.py","runner/tools/agentskills/pyguard.py")
selected_files={}
for rel in selected:
 p=stage/rel
 if p.is_symlink() or not p.exists(): raise SystemExit(f"required run95 export input missing/symlinked: {rel}")
 if p.is_file(): selected_files[rel]=files[rel]
 elif p.is_dir():
  for child in p.rglob("*"):
   if child.is_symlink(): raise SystemExit(f"symlink in selected subtree: {child}")
   if child.is_file(): selected_files[child.relative_to(stage).as_posix()]=files[child.relative_to(stage).as_posix()]
print(json.dumps({"stage":str(stage),"scope":str(scope),"statuses":statuses,"owned_process_identities":owned,"launcher_process_identities":launchers,"owned_process_groups":sorted(groups),"fixture_pid_start_identities":ids,"managed_pidfd_acquired":{str(k):{"start_ticks":v[0],"ppid":v[1],"pgid":v[2]} for k,v in pidfds.items()},"fixture_group":group,"fixture_group_members_after_cleanup":live,"files":files,"directories":dirs,"selected_files":selected_files,"selected_paths":list(selected)},sort_keys=True))
'''


def ssh(remote_command: str, *, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["ssh", "workhorse", remote_command], input=stdin,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def validate_export(manifest: dict, destination: Path, archive: bytes) -> None:
    if manifest["statuses"]["outer-status.txt"] != EXPECTED:
        raise RuntimeError("run95 status policy mismatch")
    if destination.exists():
        raise FileExistsError(f"preserve existing evidence destination: {destination}")
    destination.mkdir(mode=0o700, parents=True)
    with tempfile.NamedTemporaryFile(prefix="managed-zombie-", suffix=".tar", delete=False) as f:
        f.write(archive)
        archive_path = Path(f.name)
    try:
        with tarfile.open(archive_path, "r:") as tf:
            for member in tf.getmembers():
                rel = PurePosixPath(member.name)
                if rel.is_absolute() or ".." in rel.parts or member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                    raise RuntimeError(f"unsafe run95 archive member: {member.name}")
            tf.extractall(destination, filter="data")
    finally:
        archive_path.unlink()
    actual = {}
    for path in sorted(destination.rglob("*")):
        rel = path.relative_to(destination).as_posix()
        if path.is_symlink():
            raise RuntimeError(f"run95 export symlink: {rel}")
        if path.is_file():
            actual[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != manifest["selected_files"]:
        raise RuntimeError("run95 exported hashes differ from independent remote readback")
    (destination / "independent-readback.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (destination / "export-manifest.json").write_text(json.dumps({
        "run": "95", "remote_stage": STAGE, "remote_scope": SCOPE,
        "classification": "successful one-test MSRV evidence; reviewer acceptance pending",
        "archive_sha256": hashlib.sha256(archive).hexdigest(), "exported_files": actual,
        "remote_readback_sha256": hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
    }, indent=2, sort_keys=True) + "\n")


def collect(destination: Path) -> None:
    remote = ssh("python3 -c " + shlex.quote(REMOTE) + " " + shlex.quote(STAGE) + " " + shlex.quote(SCOPE) + " " + shlex.quote(PHYSICAL))
    manifest = json.loads(remote.stdout)
    paths = " ".join(shlex.quote(p) for p in manifest["selected_paths"])
    archive = ssh("tar -C " + shlex.quote(STAGE) + " -cf - " + paths).stdout
    validate_export(manifest, destination, archive)


def cleanup(destination: Path) -> None:
    exported = json.loads((destination / "export-manifest.json").read_text())
    readback = json.loads((destination / "independent-readback.json").read_text())
    if exported.get("remote_stage") != STAGE or exported.get("remote_scope") != SCOPE or readback.get("stage") != STAGE or readback.get("scope") != SCOPE:
        raise RuntimeError("export does not identify exact run95 owned stage/scope")
    if exported.get("exported_files") != readback.get("selected_files"):
        raise RuntimeError("run95 local export differs from independent selected hashes")
    local = {}
    for path in sorted(destination.rglob("*")):
        rel = path.relative_to(destination).as_posix()
        if path.is_symlink():
            raise RuntimeError(f"run95 local export symlink: {rel}")
        if path.is_file() and rel not in {"independent-readback.json", "export-manifest.json"}:
            local[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    if local != readback["selected_files"]:
        raise RuntimeError("run95 local evidence changed since export")
    fresh = json.loads(ssh("python3 -c " + shlex.quote(REMOTE) + " " + shlex.quote(STAGE) + " " + shlex.quote(SCOPE) + " " + shlex.quote(PHYSICAL)).stdout)
    if fresh["files"] != readback["files"] or fresh["directories"] != readback["directories"]:
        raise RuntimeError("fresh run95 inventory differs; preserve remote stage")
    payload = json.dumps(fresh, sort_keys=True)
    remote_cleanup = r'''import hashlib,json,pathlib,sys
m=json.loads(sys.argv[1]); stage=pathlib.Path(m["stage"]); scope=pathlib.Path(m["scope"])
if not stage.is_dir() or stage.is_symlink() or scope.exists() or scope.is_symlink(): raise SystemExit("run95 stage/scope identity changed")
actual={}; dirs=[]
for p in sorted(stage.rglob("*")):
 rel=p.relative_to(stage).as_posix()
 if p.is_symlink(): raise SystemExit("run95 symlink appeared: "+rel)
 if p.is_dir(): dirs.append(rel)
 elif p.is_file(): actual[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
 else: raise SystemExit("run95 unexpected entry: "+rel)
if actual!=m["files"] or dirs!=m["directories"]: raise SystemExit("run95 stage changed after readback")
for rel in sorted(actual,reverse=True): (stage/rel).unlink()
for rel in sorted(dirs,key=lambda x:(x.count("/"),x),reverse=True): (stage/rel).rmdir()
stage.rmdir()
if stage.exists() or scope.exists(): raise SystemExit("run95 exact owned stage remains")
print("run95_exact_hash_matched_stage_removed=true")
'''
    ssh("python3 -c " + shlex.quote(remote_cleanup) + " " + shlex.quote(payload))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("collect", "cleanup"))
    parser.add_argument("run", choices=("95",))
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    if args.mode == "collect":
        collect(args.destination)
    else:
        cleanup(args.destination)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (subprocess.CalledProcessError, OSError, RuntimeError, ValueError, KeyError) as exc:
        print(f"run95 collection refused: {exc}", file=sys.stderr)
        raise SystemExit(1)
