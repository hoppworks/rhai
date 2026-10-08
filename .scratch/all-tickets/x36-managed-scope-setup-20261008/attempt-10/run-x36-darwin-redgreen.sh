#!/usr/bin/env bash
set -Eeuo pipefail
scope=$1
archive=$2
manifest=$3
evidence=$4
runtime=${AGENT_RUNTIME_DIR:?runner must provide AGENT_RUNTIME_DIR}
mkdir -p "$evidence" "$runtime/source" "$runtime/cargo-home" "$runtime/target" "$runtime/pycache"
printf '%s\n' "$runtime" > "$evidence/runtime-path.txt"
shasum -a 256 "$archive" "$0" /Users/hoppworks/projects/agent-skills/tools/run_scoped.py > "$evidence/input-hashes.txt"
python3 - "$manifest" "$archive" "$0" /Users/hoppworks/projects/agent-skills/tools/run_scoped.py "$scope" <<'PYHASH'
import hashlib, json, sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(sys.argv[2]) == m['archive_sha256']
assert sha(sys.argv[3]) == m['script_sha256']
assert sha(sys.argv[4]) == m['run_scoped_sha256']
assert str(Path(sys.argv[5])) == m['scope']
PYHASH
python3 - "$archive" "$runtime/source" "$manifest" <<'PYEXTRACT'
import hashlib, json, sys, tarfile
from pathlib import Path
archive, root, manifest = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
m=json.loads(manifest.read_text())
with tarfile.open(archive, 'r:gz') as tf:
    for member in tf.getmembers():
        dest=(root/member.name).resolve()
        if root.resolve() not in dest.parents and dest != root.resolve():
            raise AssertionError(f'archive path escapes source root: {member.name}')
        if member.isdir():
            dest.mkdir(parents=True, exist_ok=True)
        elif member.isfile():
            dest.parent.mkdir(parents=True, exist_ok=True)
            src=tf.extractfile(member)
            if src is None: raise AssertionError(member.name)
            dest.write_bytes(src.read())
        else:
            raise AssertionError(f'unexpected archive entry type: {member.name}')
actual={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in m['files']}
assert actual==m['files'], (actual,m['files'])
PYEXTRACT
export CARGO_HOME="$runtime/cargo-home"
export CARGO_TARGET_DIR="$runtime/target"
export CARGO_BUILD_JOBS=1
export CARGO_TERM_COLOR=never
export CARGO_INCREMENTAL=0
export PYTHONPYCACHEPREFIX="$runtime/pycache"
{
  date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
  sw_vers
  uname -a
  printf 'scope=%s\nruntime=%s\ntmpdir=%s\n' "$scope" "$runtime" "$TMPDIR"
  printf 'cargo_jobs=%s\n' "$CARGO_BUILD_JOBS"
  rustc +1.93.0 --version
  cargo +1.93.0 --version
  df -h "$runtime" "$evidence"
  vm_stat
  memory_pressure
} > "$evidence/environment.txt" 2>&1
cd "$runtime/source"
unix="$runtime/source/src/packages/sys/process/unix.rs"
cp "$unix" "$runtime/unix.rs.original"
printf 'phase,exit\n' > "$evidence/statuses.csv"
run_test() {
  local phase=$1 rc
  if cargo +1.93.0 test --locked --features testing-environ,sys --lib managed_scope_kernel_setpgid_denial_cleans_created_group -- --nocapture --test-threads=1 2>&1 | tee "$evidence/$phase.log"; then
    rc=0
  else
    rc=$?
  fi
  printf '%s,%s\n' "$phase" "$rc" >> "$evidence/statuses.csv"
  return "$rc"
}
python3 - "$unix" "$evidence" <<'PYMUT'
from pathlib import Path
import hashlib, sys
p=Path(sys.argv[1]); out=Path(sys.argv[2]); source=p.read_text()
needle="""    #[cfg(test)]
    if let Some(fd) = kernel_setpgid_denial {
        create_kernel_managed_scope_setpgid_denial(fd)?;
    }
"""
assert source.count(needle)==1, source.count(needle)
mutated=source.replace(needle, """    #[cfg(test)]
    let _ = kernel_setpgid_denial;
""")
p.write_text(mutated)
(out/'mutation-source-sha256.txt').write_text(hashlib.sha256(mutated.encode()).hexdigest()+'\n')
PYMUT
if run_test red; then
  echo 'mutation unexpectedly passed' >&2
  exit 21
else
  red_rc=$?
fi
test "$red_rc" -eq 101
grep -Fq 'managed scope setup failure must not run the program' "$evidence/red.log"
grep -Fq 'test result: FAILED. 0 passed; 1 failed' "$evidence/red.log"
printf 'expected_red=assertion_failed_when_kernel_denial_seam_disabled\nexit=%s\n' "$red_rc" > "$evidence/mutation-control.txt"
cp "$runtime/unix.rs.original" "$unix"
restored_sha=$(shasum -a 256 "$unix" | awk '{print $1}')
expected_sha=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["files"]["src/packages/sys/process/unix.rs"])' "$manifest")
test "$restored_sha" = "$expected_sha"
printf '%s\n' "$restored_sha" > "$evidence/restored-source-sha256.txt"
if run_test green; then :; else echo 'restored targeted test failed' >&2; exit 22; fi
grep -Fq 'test result: ok. 1 passed; 0 failed' "$evidence/green.log"
python3 - "$evidence/green.log" > "$evidence/external-readback.txt" <<'PYREAD'
import os, re, sys
text=open(sys.argv[1], encoding='utf-8').read()
pat=re.compile(r'managed-scope-setup operation=(run|spawn) child_pid=([0-9]+) failure_point=KernelSetpgidDenial pid=ESRCH group=ESRCH reservation=retired marker=absent')
rows=pat.findall(text)
assert len(rows)==2 and {name for name,_ in rows}=={'run','spawn'}, rows
for op, raw in rows:
    pid=int(raw)
    for label, probe in [('pid', lambda: os.kill(pid,0)), ('process_group', lambda: os.killpg(pid,0))]:
        try: probe()
        except ProcessLookupError: pass
        else: raise AssertionError(f'{op} {label} {pid} still exists')
    print(f'operation={op} pid={pid} pid_absent=true group_absent=true')
PYREAD
printf 'expected mutation RED, restored GREEN, marker/reservation assertions, and independent Darwin PID/group readback passed\n' > "$evidence/result.txt"
cp "$unix" "$evidence/restored-unix.rs"
shasum -a 256 "$evidence"/* > "$evidence/evidence-export.sha256"
