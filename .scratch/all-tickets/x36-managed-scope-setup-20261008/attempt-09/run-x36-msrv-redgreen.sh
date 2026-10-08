#!/usr/bin/env bash
set -Eeuo pipefail
scope=$1
runtime=$AGENT_RUNTIME_DIR
evidence="$scope/evidence"
archive="$scope/source-input.tar.gz"
manifest="$scope/inputs.json"
runner=/home/workhorse/projects/agent-skills/tools/run_scoped.py
script_sha=$(sha256sum "$0" | awk '{print $1}')
runner_sha=$(sha256sum "$runner" | awk '{print $1}')
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
python3 - "$manifest" "$archive_sha" "$runner_sha" "$script_sha" "$scope" <<'PYMAN'
import json, sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text())
assert m['archive_sha256']==sys.argv[2]
assert m['run_scoped_sha256']==sys.argv[3]
assert m['runner_script_sha256']==sys.argv[4]
assert m['scope']==sys.argv[5]
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
  printf 'runtime=%s\n' "$runtime"
  printf 'tmpdir=%s\n' "$TMPDIR"
  printf 'archive_sha256=%s\n' "$archive_sha"
  printf 'runner_sha256=%s\n' "$runner_sha"
  printf 'runner_script_sha256=%s\n' "$script_sha"
  df -B1 "$runtime"
} > "$evidence/environment.txt"
rustup toolchain install 1.77.2 --profile minimal --no-self-update > "$evidence/toolchain-install.log" 2>&1
{
  printf 'cargo='; cargo +1.77.2 --version
  printf 'rustc='; rustc +1.77.2 --version
} >> "$evidence/environment.txt"
cd "$runtime/source"
unix="$runtime/source/src/packages/sys/process/unix.rs"
cp "$unix" "$runtime/unix.rs.original"
printf 'phase,exit\n' > "$evidence/statuses.csv"
run_test() {
  local phase=$1 rc
  if cargo +1.77.2 test --locked --features testing-environ,sys --lib managed_scope_kernel_setpgid_denial_cleans_created_group -- --nocapture --test-threads=1 2>&1 | tee "$evidence/$phase.log"; then
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
p=Path(sys.argv[1])
evidence=Path(sys.argv[2])
source=p.read_text()
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
(evidence/'mutation-source-sha256.txt').write_text(hashlib.sha256(mutated.encode()).hexdigest()+'\n')
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
restored_sha=$(sha256sum "$unix" | awk '{print $1}')
expected_sha=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["files"]["src/packages/sys/process/unix.rs"])' "$manifest")
test "$restored_sha" = "$expected_sha"
printf '%s\n' "$restored_sha" > "$evidence/restored-source-sha256.txt"
if run_test green; then
  :
else
  echo 'restored targeted test failed' >&2
  exit 22
fi
grep -Fq 'test result: ok. 1 passed; 0 failed' "$evidence/green.log"
python3 - "$evidence/green.log" > "$evidence/in-run-readback.txt" <<'PYREAD'
import os, re, sys
text=open(sys.argv[1],encoding='utf-8').read()
pat=re.compile(r'managed-scope-setup operation=(run|spawn) child_pid=([0-9]+) failure_point=KernelSetpgidDenial pid=ESRCH group=ESRCH reservation=retired marker=absent')
rows=pat.findall(text)
assert len(rows)==2 and {name for name,_ in rows}=={'run','spawn'}, rows
for op,raw in rows:
    pid=int(raw)
    for label,probe in [('pid',lambda:os.kill(pid,0)),('process_group',lambda:os.killpg(pid,0))]:
        try:
            probe()
        except ProcessLookupError:
            pass
        else:
            raise AssertionError(f'{op} {label} {pid} still exists')
    print(f'operation={op} pid={pid} pid_absent=true group_absent=true')
PYREAD
printf '%s\n' 'kernel-denial mutation RED passed on Rust/Cargo 1.77.2' 'restored targeted GREEN passed on Rust/Cargo 1.77.2' 'public run and spawn assertions and in-run PID/group readback passed' > "$evidence/result.txt"
printf 'script_exit=0\n'
