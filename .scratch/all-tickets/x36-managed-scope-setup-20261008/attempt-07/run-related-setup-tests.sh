#!/usr/bin/env bash
set -Eeuo pipefail
scope=$1
runtime=$AGENT_RUNTIME_DIR
test -n "$scope"
test -n "$runtime"
evidence="$scope/evidence"
source_root="$runtime/source"
archive="$scope/source-input.tar.gz"
manifest="$scope/inputs.json"
mkdir -p "$evidence" "$source_root"
finish() {
  rc=$?
  trap - EXIT
  echo "script_exit=$rc" > "$evidence/script-exit.txt"
  exit "$rc"
}
trap finish EXIT
archive_sha=$(sha256sum "$archive" | awk '{print $1}')
runner_sha=$(sha256sum /home/workhorse/projects/agent-skills/tools/run_scoped.py | awk '{print $1}')
python3 - "$manifest" "$archive_sha" "$runner_sha" <<'PYMAN'
import json, sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text())
assert m['archive_sha256']==sys.argv[2]
assert m['run_scoped_sha256']==sys.argv[3]
PYMAN
tar --no-same-owner -xzf "$archive" -C "$source_root"
python3 - "$manifest" "$source_root" <<'PYFILES'
import hashlib, json, sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text())
root=Path(sys.argv[2])
actual={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in m['files']}
assert actual==m['files'], (actual,m['files'])
PYFILES
export CARGO_HOME="$runtime/cargo-home"
export CARGO_TARGET_DIR="$runtime/target"
export CARGO_BUILD_JOBS=2
export CARGO_TERM_COLOR=never
export PYTHONPYCACHEPREFIX="$runtime/pycache"
mkdir -p "$CARGO_HOME" "$CARGO_TARGET_DIR" "$PYTHONPYCACHEPREFIX"
{
  date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
  uname -a
  cargo --version
  rustc --version
  echo "TMPDIR=$TMPDIR"
  echo "AGENT_RUNTIME_DIR=$runtime"
  echo "runner_sha256=$runner_sha"
  df -B1 "$runtime"
} > "$evidence/environment.txt"
cd "$source_root"
start_epoch=$(date +%s)
if cargo test --locked --features testing-environ,sys --lib managed_scope_ -- --nocapture --test-threads=1 2>&1 | tee "$evidence/related-tests.log"; then
  rc=0
else
  rc=$?
fi
end_epoch=$(date +%s)
echo "cargo_test_exit=$rc" > "$evidence/status.txt"
echo "elapsed_seconds=$((end_epoch-start_epoch))" >> "$evidence/status.txt"
test "$rc" -eq 0
grep -Fq 'test result: ok. 6 passed; 0 failed' "$evidence/related-tests.log"
python3 - "$evidence/related-tests.log" > "$evidence/independent-readback.txt" <<'PYREAD'
import os, re, sys
text=open(sys.argv[1],encoding='utf-8').read()
pat=re.compile(r'managed-scope-setup operation=(run|spawn) child_pid=([0-9]+) failure_point=(BeforeSetpgid|AfterSetpgid|Fchdir|KernelSetpgidDenial) pid=ESRCH group=ESRCH reservation=retired marker=absent')
rows=pat.findall(text)
expected={(op,point) for op in ('run','spawn') for point in ('BeforeSetpgid','AfterSetpgid','Fchdir','KernelSetpgidDenial')}
assert len(rows)==8 and {(op,point) for op,_,point in rows}==expected, rows
assert len({pid for _,pid,_ in rows})==8, rows
for op,raw,point in rows:
    pid=int(raw)
    for label,probe in [('pid',lambda:os.kill(pid,0)),('process_group',lambda:os.killpg(pid,0))]:
        try:
            probe()
        except ProcessLookupError:
            pass
        else:
            raise AssertionError(f'{op}/{point} {label} {pid} still exists')
    print(f'operation={op} failure_point={point} pid={pid} pid_absent=true group_absent=true')
PYREAD
echo 'six related managed_scope tests passed on the reviewed candidate' > "$evidence/result.txt"
echo 'eight run/spawn failure cases had absent exact child and process-group IDs' >> "$evidence/result.txt"
