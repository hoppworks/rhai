#!/usr/bin/env bash
set -Eeuo pipefail
repo=/var/home/Daniel/projects/rhai
attempt="$repo/.scratch/all-tickets/linux-x37-managed-drop-base-20261015/attempt-01"
evidence="$attempt/evidence"
scope="${1:?session scope required}"
runtime="${AGENT_RUNTIME_DIR:?runner must set AGENT_RUNTIME_DIR}"
lock="$repo/.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock"
runner=/var/home/Daniel/projects/agent-skills/tools/run_scoped.py
revision=d304d1ad325275873b04b096cb9f519634125e00
toolchain=/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
cargo="$toolchain/cargo"
test_name=managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not
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
  cat /etc/os-release
  printf 'revision=%s\n' "$revision"
  printf 'runtime=%s\n' "$runtime"
  printf 'tmpdir=%s\n' "$TMPDIR"
  printf 'scope=%s\n' "$scope"
  printf 'run_scoped_sha256='; sha256sum "$runner" | awk '{print $1}'
  printf 'lock_sha256='; sha256sum "$lock" | awk '{print $1}'
  printf 'cargo_jobs=1\n'
  printf 'features=testing-environ,sys\n'
  printf 'profile=default\n'
  df -B1 "$runtime"
  grep -E 'MemAvailable|MemTotal' /proc/meminfo
} > "$evidence/environment.txt"
git -C "$repo" archive "$revision" | tar --no-same-owner -xf - -C "$runtime/source"
cp "$lock" "$runtime/source/Cargo.lock"
cd "$runtime/source"
sha256sum Cargo.toml Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/source-hashes.txt"
grep -Fq 'cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e  Cargo.toml' "$evidence/source-hashes.txt"
grep -Fq '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425  Cargo.lock' "$evidence/source-hashes.txt"
grep -Fq '2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6  src/packages/sys/process/unix.rs' "$evidence/source-hashes.txt"
grep -Fq 'ddd5a6259b80647528fc1640f77f2c9f69acd913a20bf84b2a0942d3aec09cbf  tests/sys_process.rs' "$evidence/source-hashes.txt"
export CARGO_HOME="$runtime/cargo-home"
export CARGO_TARGET_DIR="$runtime/target"
export CARGO_BUILD_JOBS=1
export CARGO_TERM_COLOR=never
export PYTHONDONTWRITEBYTECODE=1
export RUSTC="$toolchain/rustc"
export RUSTDOC="$toolchain/rustdoc"
export RUSTUP_HOME=/home/Daniel/.rustup
export PATH="$toolchain:/usr/bin:/bin"
mkdir -p "$CARGO_HOME" "$CARGO_TARGET_DIR"
{
  printf 'cargo='; "$cargo" --version
  printf 'rustc='; "$RUSTC" --version
} >> "$evidence/environment.txt"
cp tests/sys_process.rs "$runtime/sys_process.rs.original"
python3 - "$runtime/source/tests/sys_process.rs" <<'PYMUT'
from pathlib import Path
import sys
p=Path(sys.argv[1])
source=p.read_text()
name='managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not'
start=source.index(f'fn {name}()')
end=source.find('\nfn ',start)
if end < 0:
    end=len(source)
body=source[start:end]
old='assert!(sentinel_live, "final Child drop terminated the unrelated sentinel");'
new='assert!(!sentinel_live, "final Child drop terminated the unrelated sentinel");'
assert body.count(old)==1, body.count(old)
p.write_text(source[:start]+body.replace(old,new,1)+source[end:])
PYMUT
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/red-source.sha256"
printf 'phase,exit\n' > "$evidence/statuses.csv"
run_test() {
  local phase=$1 rc
  if timeout 300s "$cargo" test --locked --features testing-environ,sys --test sys_process "$test_name" -- --exact --nocapture --test-threads=1 > "$evidence/$phase.log" 2>&1; then
    rc=0
  else
    rc=$?
  fi
  printf '%s,%s\n' "$phase" "$rc" >> "$evidence/statuses.csv"
  return "$rc"
}
if run_test red; then
  echo 'wrong sentinel assertion unexpectedly passed' >&2
  exit 21
else
  red_rc=$?
fi
test "$red_rc" -eq 101
grep -Fq 'test result: FAILED. 0 passed; 1 failed;' "$evidence/red.log"
grep -Fq 'final Child drop terminated the unrelated sentinel' "$evidence/red.log"
grep -Fq 'all_esrch=true' "$evidence/red.log"
grep -Fq 'sentinel_cleanup' "$evidence/red.log"
grep -Fq 'esrch=true' "$evidence/red.log"
printf 'expected_red=only_sentinel_live_assertion_inverted\nexit=%s\n' "$red_rc" > "$evidence/mutation-control.txt"
cp "$runtime/sys_process.rs.original" "$runtime/source/tests/sys_process.rs"
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/green-source.sha256"
if run_test green; then
  :
else
  echo 'restored X37 test failed' >&2
  exit 22
fi
grep -Fq 'managed_spawn_nonfinal_drop' "$evidence/green.log"
grep -Fq 'all_live=true' "$evidence/green.log"
grep -Fq 'managed_spawn_final_drop' "$evidence/green.log"
grep -Fq 'all_esrch=true' "$evidence/green.log"
grep -Fq 'sentinel_cleanup' "$evidence/green.log"
grep -Fq 'esrch=true' "$evidence/green.log"
grep -Fq 'test result: ok. 1 passed; 0 failed;' "$evidence/green.log"
python3 "$attempt/postrun-readback.py" "$evidence/green.log" > "$evidence/in-run-readback.txt"
printf 'expected sentinel assertion RED 101; restored X37 GREEN 1/1; independent observations passed\n' > "$evidence/result.txt"
