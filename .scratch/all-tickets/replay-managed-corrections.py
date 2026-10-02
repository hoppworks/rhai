import ast, hashlib, json, os, subprocess, sys, time
from pathlib import Path
root=Path(sys.argv[1]); evidence=Path(sys.argv[2]); runtime=Path(os.environ["AGENT_RUNTIME_DIR"])
revision="74943bb231f7f26e6951d946baa687465d72d3a8"
prior="3e17e3f5c90d8f50fdbe6c0e1b8772851941d864"
names=["darwin-process-reader.py","test-darwin-process-reader.py","macos-process-overhead.py","macos-process-overhead-control.py","run-macos-process-overhead-scoped.py","test-macos-process-overhead-source.py","run-macos-process-overhead.sh","runtime-path-parser.zsh","macos-managed-capture-companion.rs"]
paths=[".scratch/all-tickets/"+n for n in names]+[".scratch/managed-unix-scope-close/measure-process-overhead.py"]
def frozen(ref,path):
    return subprocess.check_output(["/usr/bin/git","show",ref+":"+path],cwd=root)
original={p:frozen(revision,p) for p in paths}
for path,data in original.items():
    target=runtime/path; target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
evidence.mkdir(exist_ok=False)
start=time.monotonic(); statuses={}
env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",TMPDIR=str(runtime))
suite=runtime/".scratch/all-tickets/test-macos-process-overhead-source.py"
def check(label,args,expected,needle=None):
    result=subprocess.run([sys.executable,*map(str,args)],cwd=suite.parent,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
    (evidence/(label+".log")).write_bytes(result.stdout)
    statuses[label]=result.returncode
    assert result.returncode==expected,(label,result.returncode,result.stdout[-1500:])
    if needle: assert needle.encode() in result.stdout,(label,result.stdout[-1500:])
check("corrected-reader",[runtime/".scratch/all-tickets/test-darwin-process-reader.py"],0,"Ran 23 tests")
check("corrected-adapter",[suite],0,"Ran 58 tests")
# New tests against unchanged prior implementation expose each material finding.
for name in ["macos-process-overhead.py","run-macos-process-overhead-scoped.py"]:
    p=".scratch/all-tickets/"+name;(runtime/p).write_bytes(frozen(prior,p))
base=["-m","unittest","test-macos-process-overhead-source.EnvironmentTests."]
for label,test,needle in [
    ("prior-wrong-fixture-group","test_managed_native_snapshot_requires_progress_for_both_real_capture_streams","AssertionError"),
    ("prior-premature-gate-reap","test_managed_host_signal_defers_gate_reap_until_anchored_group_signal","AssertionError"),
    ("prior-cargo-stream-mixing","test_managed_build_requests_keep_cargo_streams_separate","AssertionError")]:
    check(label,["-m","unittest","test-macos-process-overhead-source.EnvironmentTests."+test],1,needle)
for path,data in original.items(): (runtime/path).write_bytes(data)
check("restored-adapter",[suite],0,"Ran 58 tests")
for path,data in original.items():
    assert (runtime/path).read_bytes()==data
    if path.endswith(".py"): ast.parse(data,filename=path)
receipt={"revision":revision,"prior_revision":prior,"runtime":str(runtime),"statuses":statuses,"elapsed_seconds":time.monotonic()-start,"source_sha256":{p:hashlib.sha256(d).hexdigest() for p,d in original.items()},"native_process_launches":0,"cargo_launches":0,"coverage":"Pure regression checks only; native acceptance remains open."}
(evidence/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps({"statuses":statuses,"elapsed_seconds":receipt["elapsed_seconds"]}))
