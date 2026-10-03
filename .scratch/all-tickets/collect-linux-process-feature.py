#!/usr/bin/env python3
"""Read back and export one exact Linux process-feature stage; cleanup is gated."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import sys
import tarfile
import tempfile

PREFIX = "linux-process-feature-20261003-6c451c5c"
REMOTE = r'''import hashlib,json,os,pathlib,subprocess,sys
stage=pathlib.Path(sys.argv[1]); scope=pathlib.Path(sys.argv[2]); expected=int(sys.argv[3]); physical=pathlib.Path(sys.argv[4])
if not stage.is_dir() or stage.is_symlink() or stage.resolve()!=physical: raise SystemExit("stage missing, symlinked, or noncanonical")
if scope.exists() or scope.is_symlink(): raise SystemExit("scope remains; refuse evidence acceptance/cleanup")
subprocess.run(["sha256sum","--check","input-identities.sha256"],cwd=stage,check=True,stdout=subprocess.DEVNULL)
e=stage/"outer-evidence"
status_names=("outer-status.txt","run-scoped.status","pid-readback.status","pid-readback-launcher.status")
statuses={n:int((e/n).read_text().strip()) for n in status_names}
if statuses["outer-status.txt"]!=expected: raise SystemExit(f"outer status mismatch: {statuses}")
if statuses["run-scoped.status"]!=expected: raise SystemExit(f"runner status mismatch: {statuses}")
if statuses["pid-readback.status"]!=0 or statuses["pid-readback-launcher.status"]!=0: raise SystemExit(f"PID readback incomplete: {statuses}")
for n in ("runtime-cleanup.tsv","scope-cleanup.tsv"):
 text=(e/n).read_text()
 if "cleanup_status=0" not in text: raise SystemExit(f"cleanup not confirmed in {n}: {text!r}")
ids=[]; groups=set()
for path,required in ((stage/"proof-evidence/process-identities.tsv",{"helper","scoped-supervisor"}), (e/"launcher-identities.tsv",{"launcher","run-scoped"})):
 rows=path.read_text(errors="strict").splitlines()
 seen=set()
 for line in rows[1:]:
  f=line.split("\t",5)
  if len(f)!=6 or not f[1].isdigit() or not f[4].isdigit(): raise SystemExit(f"malformed process identity row: {line!r}")
  label,pid,_,pgid,start,_=f; pid=int(pid); seen.add(label)
  if label in ("helper","scoped-supervisor"): groups.add(int(pgid))
  try:
   raw=pathlib.Path("/proc",str(pid),"stat").read_text(); fields=raw[raw.rfind(")")+2:].split()
   alive=fields[19]==start
  except FileNotFoundError: alive=False
  except (PermissionError,OSError,IndexError,ValueError) as ex: raise SystemExit(f"PID readback unknown for {label} {pid}: {ex}")
  if alive: raise SystemExit(f"owned process remains: {label} pid={pid} start={start}")
  ids.append({"label":label,"pid":pid,"start_ticks":start,"matching_process_alive":False})
 if not required.issubset(seen): raise SystemExit(f"required identity labels missing: {required-seen}")
ps=subprocess.check_output(["/bin/ps","-e","-o","pid=,pgid="],text=True,timeout=5)
live=[]
for row in ps.splitlines():
 f=row.split()
 if len(f)==2 and int(f[1]) in groups: live.append([int(f[0]),int(f[1])])
if not groups or live: raise SystemExit(f"scoped process groups remain or are unavailable: {live!r}")
fixture_pids=set()
for p in stage.rglob("*"):
 if p.is_file() and p.suffix in (".stdout",".stderr"):
  try: text=p.read_text(errors="replace")
  except OSError: continue
  for line in text.splitlines():
   if "reap=ESRCH pid=" in line:
    try: fixture_pids.add(int(line.rsplit("reap=ESRCH pid=",1)[1].split()[0]))
    except (ValueError,IndexError): raise SystemExit(f"malformed fixture reap receipt in {p}")
fixture=[]
for pid in sorted(fixture_pids):
 try: pathlib.Path("/proc",str(pid),"stat").read_text()
 except FileNotFoundError: fixture.append({"pid":pid,"reaped":"ESRCH"})
 except (PermissionError,OSError) as ex: raise SystemExit(f"fixture PID readback unknown {pid}: {ex}")
 else: raise SystemExit(f"fixture PID still exists: {pid}")
files={}; dirs=[]
for p in sorted(stage.rglob("*")):
 rel=p.relative_to(stage).as_posix()
 if p.is_symlink(): raise SystemExit(f"symlink in stage: {rel}")
 if p.is_dir(): dirs.append(rel)
 elif p.is_file(): files[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
 else: raise SystemExit(f"non-regular stage entry: {rel}")
selected=("proof-evidence","outer-evidence","source.sha256","contract.md","input-identities.sha256","process-feature.patch","linux-process-feature-proof.py","linux-process-options-control.py","linux-process-io-control.py","check-linux-current-msrv-examples.py")
if (stage/"apply-process-feature-patch.py").exists(): selected=selected+("apply-process-feature-patch.py",)
selected_files={}
for rel in selected:
 p=stage/rel
 if p.is_symlink() or not p.exists(): raise SystemExit(f"required export input missing or symlinked: {rel}")
 if p.is_file(): selected_files[rel]=files[rel]
 elif p.is_dir():
  for child in p.rglob("*"):
   if child.is_symlink(): raise SystemExit(f"symlink in export subtree: {child}")
   if child.is_file(): selected_files[child.relative_to(stage).as_posix()]=files[child.relative_to(stage).as_posix()]
print(json.dumps({"stage":str(stage),"scope":str(scope),"statuses":statuses,"processes":ids,"scoped_groups":sorted(groups),"live_group_processes":live,"fixture_pid_receipts":fixture,"fixture_receipt_count":len(fixture_pids),"files":files,"directories":dirs,"selected_files":selected_files,"selected_paths":list(selected)},sort_keys=True))
'''


def ssh(remote_command: str, *, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["ssh", "workhorse", remote_command], input=stdin,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def stage_for(run: str) -> tuple[str, int]:
    if run not in {"91", "92", "93"}:
        raise ValueError("run must be 91, 92, or 93")
    suffix = "" if run == "91" else f"-{run}"
    root = f"/root/rhai-{PREFIX}{suffix}"
    return root, (0 if run == "93" else 1)


def collect(run: str, destination: Path) -> None:
    stage, expected = stage_for(run)
    suffix = "" if run == "91" else f"-{run}"
    scope = f"/root/.local/share/agent-builds/rhai/{PREFIX}{suffix}"
    physical = f"/var/roothome/{Path(stage).name}"
    remote = ssh("python3 -c " + shlex.quote(REMOTE) + " " +
                 shlex.quote(stage) + " " + shlex.quote(scope) + " " + str(expected) + " " + shlex.quote(physical))
    manifest = json.loads(remote.stdout)
    if manifest["statuses"]["outer-status.txt"] != expected:
        raise RuntimeError("status policy mismatch")
    if destination.exists():
        raise FileExistsError(f"preserve existing evidence destination: {destination}")
    destination.mkdir(mode=0o700, parents=True)
    try:
        export_args = " ".join(shlex.quote(p) for p in manifest["selected_paths"])
        archive = ssh("tar -C " + shlex.quote(stage) + " -cf - " + export_args).stdout
        with tempfile.NamedTemporaryFile(prefix="process-feature-", suffix=".tar", delete=False) as f:
            f.write(archive)
            archive_path = Path(f.name)
        try:
            with tarfile.open(archive_path, "r:") as tf:
                members = tf.getmembers()
                for member in members:
                    relative = PurePosixPath(member.name)
                    if relative.is_absolute() or ".." in relative.parts or member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                        raise RuntimeError(f"unsafe stage archive member: {member.name}")
                tf.extractall(destination, filter="data")
        finally:
            archive_path.unlink()
        extracted = destination
        actual = {}
        for p in sorted(extracted.rglob("*")):
            rel = p.relative_to(extracted).as_posix()
            if p.is_symlink():
                raise RuntimeError(f"export contains symlink: {rel}")
            if p.is_file():
                actual[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
        if actual != manifest["selected_files"]:
            raise RuntimeError("exported selected-evidence hash inventory differs from remote readback")
        (destination / "independent-readback.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        export = {"run": run, "remote_stage": stage, "remote_scope": scope,
                  "classification": "successful proof run" if expected == 0 else "failed preflight/harness run; not product acceptance",
                  "archive_sha256": hashlib.sha256(archive).hexdigest(),
                  "exported_files": actual, "remote_readback_sha256": hashlib.sha256(
                      json.dumps(manifest, sort_keys=True).encode()).hexdigest()}
        (destination / "export-manifest.json").write_text(json.dumps(export, indent=2, sort_keys=True) + "\n")
    except BaseException:
        # Keep partial evidence for diagnosis; never remove an export on failure.
        raise


def cleanup(run: str, destination: Path) -> None:
    stage, expected = stage_for(run)
    suffix = "" if run == "91" else f"-{run}"
    scope = f"/root/.local/share/agent-builds/rhai/{PREFIX}{suffix}"
    exported = json.loads((destination / "export-manifest.json").read_text())
    readback = json.loads((destination / "independent-readback.json").read_text())
    if exported["remote_stage"] != stage or exported["remote_scope"] != scope:
        raise RuntimeError("export refers to a different owned stage/scope")
    if readback["statuses"]["outer-status.txt"] != expected or not readback["files"]:
        raise RuntimeError("export is incomplete or status policy does not match this run")
    if exported["exported_files"] != readback["selected_files"]:
        raise RuntimeError("export and remote inventory do not match")
    local_files = {}
    for p in sorted(destination.rglob("*")):
        rel = p.relative_to(destination).as_posix()
        if p.is_symlink():
            raise RuntimeError(f"export contains a symlink: {rel}")
        if p.is_file() and rel not in {"independent-readback.json", "export-manifest.json"}:
            local_files[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    if local_files != readback["selected_files"]:
        raise RuntimeError("local exported evidence changed since collection")
    # Exact-path, hash-gated deletion. The remote snippet fails on any new or
    # changed file, symlink, non-empty unexpected directory, or live scope.
    fresh = json.loads(ssh("python3 -c " + shlex.quote(REMOTE) + " " +
                           shlex.quote(stage) + " " + shlex.quote(scope) + " " + str(expected) + " " +
                           shlex.quote(f"/var/roothome/{Path(stage).name}")).stdout)
    if fresh["files"] != readback["files"] or fresh["directories"] != readback["directories"]:
        raise RuntimeError("fresh stage inventory differs from exported cleanup inventory")
    payload = json.dumps(fresh, sort_keys=True)
    remote_cleanup = r'''import hashlib,json,pathlib,sys
m=json.loads(sys.argv[1]); stage=pathlib.Path(m["stage"]); scope=pathlib.Path(m["scope"])
if not stage.is_dir() or stage.is_symlink() or scope.exists() or scope.is_symlink(): raise SystemExit("stage/scope identity changed")
actual={}; dirs=[]
for p in sorted(stage.rglob("*")):
 rel=p.relative_to(stage).as_posix()
 if p.is_symlink(): raise SystemExit("symlink appeared: "+rel)
 if p.is_dir(): dirs.append(rel)
 elif p.is_file(): actual[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
 else: raise SystemExit("unexpected entry: "+rel)
if actual!=m["files"] or dirs!=m["directories"]: raise SystemExit("stage changed since exported readback")
for rel in sorted(actual,reverse=True): (stage/rel).unlink()
for rel in sorted(dirs,key=lambda x:(x.count("/"),x),reverse=True): (stage/rel).rmdir()
stage.rmdir()
if stage.exists() or scope.exists(): raise SystemExit("owned stage/scope remains")
print("exact_hash_matched_stage_removed=true")
'''
    ssh("python3 -c " + shlex.quote(remote_cleanup) + " " + shlex.quote(payload))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("collect", "cleanup"))
    parser.add_argument("run", choices=("91", "92", "93"))
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    if args.mode == "collect":
        collect(args.run, args.destination)
    else:
        cleanup(args.run, args.destination)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (subprocess.CalledProcessError, OSError, RuntimeError, ValueError, KeyError) as exc:
        print(f"collection refused: {exc}", file=sys.stderr)
        raise SystemExit(1)
