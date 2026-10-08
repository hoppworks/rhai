#!/usr/bin/env bash
set -Eeuo pipefail
scope=$1
runtime=$AGENT_RUNTIME_DIR
evidence="$scope/evidence"
archive="$scope/source-input.tar.gz"
manifest="$scope/inputs.json"
test -n "$scope"
test -n "$runtime"
mkdir -p "$evidence" "$runtime/source"
finish() {
  rc=$?
  trap - EXIT
  printf 'script_exit=%s\n' "$rc" > "$evidence/script-exit.txt"
  exit "$rc"
}
trap finish EXIT
archive_sha=$(sha256sum "$archive" | awk '{print $1}')
runner=/home/workhorse/projects/agent-skills/tools/run_scoped.py
runner_sha=$(sha256sum "$runner" | awk '{print $1}')
python3 - "$manifest" "$archive_sha" "$runner_sha" "$scope" <<'PYMAN'
import json, sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text())
assert m['archive_sha256']==sys.argv[2]
assert m['run_scoped_sha256']==sys.argv[3]
assert m['scope']==sys.argv[4]
assert m['session_id'] in m['scope']
PYMAN
tar --no-same-owner -xzf "$archive" -C "$runtime/source"
python3 - "$manifest" "$runtime/source" <<'PYFILES'
import hashlib, json, sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text())
root=Path(sys.argv[2])
actual={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in m['files']}
assert actual==m['files'], (actual,m['files'])
PYFILES
export RUSTUP_HOME="$runtime/rustup-home"
export CARGO_HOME="$runtime/cargo-home"
export CARGO_TARGET_DIR="$runtime/target"
export CARGO_BUILD_JOBS=2
export CARGO_TERM_COLOR=never
export PYTHONPYCACHEPREFIX="$runtime/pycache"
mkdir -p "$CARGO_HOME" "$CARGO_TARGET_DIR" "$PYTHONPYCACHEPREFIX"
{
  date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
  uname -a
  printf 'rustup='; rustup --version
  printf 'runtime=%s\n' "$runtime"
  printf 'tmpdir=%s\n' "$TMPDIR"
  printf 'archive_sha256=%s\n' "$archive_sha"
  printf 'runner_sha256=%s\n' "$runner_sha"
  df -B1 "$runtime"
} > "$evidence/environment.txt"
rustup toolchain install 1.77.2 --profile minimal --no-self-update > "$evidence/toolchain-install.log" 2>&1
{
  printf 'cargo='; cargo +1.77.2 --version
  printf 'rustc='; rustc +1.77.2 --version
} >> "$evidence/environment.txt"
cd "$runtime/source"
start_epoch=$(date +%s)
if cargo +1.77.2 test --locked --features testing-environ,sys --lib managed_scope_ -- --nocapture --test-threads=1 2>&1 | tee "$evidence/related-tests.log"; then
  rc=0
else
  rc=$?
fi
end_epoch=$(date +%s)
printf 'cargo_test_exit=%s\n' "$rc" > "$evidence/status.txt"
printf 'elapsed_seconds=%s\n' "$((end_epoch-start_epoch))" >> "$evidence/status.txt"
test "$rc" -eq 0
grep -Fq 'test result: ok. 6 passed; 0 failed' "$evidence/related-tests.log"
python3 - "$evidence/related-tests.log" > "$evidence/exact-cases.txt" <<'PYCASES'
import re, sys
text=open(sys.argv[1],encoding='utf-8').read()
pat=re.compile(r'managed-scope-setup operation=(run|spawn) child_pid=([0-9]+) failure_point=(BeforeSetpgid|AfterSetpgid|Fchdir|KernelSetpgidDenial) pid=ESRCH group=ESRCH reservation=retired marker=absent')
rows=pat.findall(text)
expected={(op,point) for op in ('run','spawn') for point in ('BeforeSetpgid','AfterSetpgid','Fchdir','KernelSetpgidDenial')}
assert len(rows)==8 and {(op,point) for op,_,point in rows}==expected, rows
assert len({pid for _,pid,_ in rows})==8, rows
for op,pid,point in rows:
    print(f'operation={op} failure_point={point} pid={pid}')
PYCASES
printf '%s\n' 'six related managed_scope tests passed on Rust/Cargo 1.77.2' > "$evidence/result.txt"
printf '%s\n' 'eight run/spawn failure cases had absent exact child and process-group IDs' >> "$evidence/result.txt"
