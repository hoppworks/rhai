#!/usr/bin/env bash
set -Eeuo pipefail
repo=/var/home/Daniel/projects/rhai
attempt="$repo/.scratch/all-tickets/x36-managed-scope-setup-20261008/attempt-12"
evidence="$attempt/evidence"
scope="${1:?session scope required}"
runtime="${AGENT_RUNTIME_DIR:?runner must set AGENT_RUNTIME_DIR}"
runner=/var/home/Daniel/projects/agent-skills/tools/run_scoped.py
lock_archive="$repo/.scratch/all-tickets/x36-managed-scope-setup-20261008/attempt-06/source-input.tar.gz"
revision=ffeab7c7958e69ebada7064aa9d0ca31f84edb13
toolchain=/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
cargo="$toolchain/cargo"
test_name=managed_scope_kernel_setpgid_denial_cleans_created_group
mkdir -p "$evidence" "$runtime/source"
finish() {
  rc=$?
  trap - EXIT
  printf 'script_exit=%s\n' "$rc" > "$evidence/script-exit.txt"
  exit "$rc"
}
trap finish EXIT
test -n "$scope"
test -n "$runtime"
test "$(git -C "$repo" rev-parse HEAD)" = "$revision"
{
  date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
  uname -a
  printf 'revision=%s\n' "$revision"
  printf 'runtime=%s\n' "$runtime"
  printf 'tmpdir=%s\n' "$TMPDIR"
  printf 'scope=%s\n' "$scope"
  printf 'run_scoped_sha256='; sha256sum "$runner" | awk '{print $1}'
  printf 'lock_archive_sha256='; sha256sum "$lock_archive" | awk '{print $1}'
  printf 'cargo_jobs=1\n'
  printf 'estimated_additional_peak_bytes=3221225472\n'
  df -B1 "$runtime"
  grep -E 'MemAvailable|MemTotal' /proc/meminfo
} > "$evidence/environment.txt"
git -C "$repo" archive "$revision" | tar --no-same-owner -xf - -C "$runtime/source"
cp "$repo/src/packages/sys/process/unix.rs" "$runtime/source/src/packages/sys/process/unix.rs"
tar --no-same-owner -xOzf "$lock_archive" Cargo.lock > "$runtime/source/Cargo.lock"
cd "$runtime/source"
sha256sum Cargo.toml Cargo.lock src/packages/sys/process/unix.rs > "$evidence/source-hashes.txt"
grep -Fq 'cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e  Cargo.toml' "$evidence/source-hashes.txt"
grep -Fq '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425  Cargo.lock' "$evidence/source-hashes.txt"
grep -Fq '2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6  src/packages/sys/process/unix.rs' "$evidence/source-hashes.txt"
export CARGO_HOME="$runtime/cargo-home"
export CARGO_TARGET_DIR="$runtime/target"
export CARGO_BUILD_JOBS=1
export CARGO_TERM_COLOR=never
export PYTHONPYCACHEPREFIX="$runtime/pycache"
export RUSTC="$toolchain/rustc"
export RUSTDOC="$toolchain/rustdoc"
export PATH="$toolchain:$PATH"
mkdir -p "$CARGO_HOME" "$CARGO_TARGET_DIR" "$PYTHONPYCACHEPREFIX"
{
  printf 'cargo='; "$cargo" --version
  printf 'rustc='; "$RUSTC" --version
  printf 'features=testing-environ,sys,unchecked\n'
  printf 'test=%s\n' "$test_name"
} >> "$evidence/environment.txt"
unix="$runtime/source/src/packages/sys/process/unix.rs"
cp "$unix" "$runtime/unix.rs.original"
printf 'phase,exit\n' > "$evidence/statuses.csv"
run_test() {
  local phase=$1 rc
  if timeout 300s "$cargo" test --locked --features testing-environ,sys,unchecked --lib "$test_name" -- --nocapture --test-threads=1 2>&1 | tee "$evidence/$phase.log"; then
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
expected_sha=$(awk '$2=="src/packages/sys/process/unix.rs" {print $1}' "$evidence/source-hashes.txt")
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
printf 'expected mutation RED 101; restored GREEN 0; public run/spawn and in-run PID/group readback passed\n' > "$evidence/result.txt"
