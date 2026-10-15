#!/usr/bin/env bash
set -Eeuo pipefail
repo=/var/home/Daniel/projects/rhai
pkg="$repo/.scratch/all-tickets/linux-x34-sync-20261015/attempt-01"
evidence="$pkg/evidence"
scope="${1:?owned session scope required}"
runtime="${AGENT_RUNTIME_DIR:?scoped runner required}"
lock="$repo/.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock"
toolchain=/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
cargo="$toolchain/cargo"
source_dir="$runtime/source"
features=testing-environ,sys,sync
mkdir -p "$source_dir"
git -C "$repo" archive HEAD | tar --no-same-owner -xf - -C "$source_dir"
cp "$lock" "$source_dir/Cargo.lock"
cp "$source_dir/tests/sys_process.rs" "$runtime/sys_process.rs.original"
cd "$source_dir"
export CARGO_TARGET_DIR="$runtime/target"
export CARGO_HOME="$runtime/cargo-home"
export CARGO_BUILD_JOBS=1
export CARGO_TERM_COLOR=never
export RUSTC="$toolchain/rustc"
export RUSTDOC="$toolchain/rustdoc"
export RUSTUP_HOME=/home/Daniel/.rustup
export PATH="$toolchain:/usr/bin:/bin"
export PYTHONDONTWRITEBYTECODE=1
{
  printf 'revision='; git -C "$repo" rev-parse HEAD
  date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
  uname -a
  cat /etc/os-release
  printf 'features=%s\nprofile=default\n' "$features"
  "$cargo" --version
  "$RUSTC" -Vv
  sha256sum Cargo.toml Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs
  printf 'scope=%s\nruntime=%s\ncargo_jobs=1\n' "$scope" "$runtime"
} > "$evidence/environment.txt"
python3 - <<'PYMUT'
from pathlib import Path
p=Path('tests/sys_process.rs'); s=p.read_text()
mutations=[
 ('assert!(api_is_timed_out, "managed public run did not return its deadline report after exact group closure: {api_result}");', 'assert!(!api_is_timed_out, "RED_CONTROL: deliberately inverted managed deadline expectation");'),
 ('assert!(api_is_output_limit, "managed public run did not return an OutputLimit process result: {api_result}");', 'assert!(!api_is_output_limit, "RED_CONTROL: deliberately inverted managed OutputLimit expectation");'),
]
for old,new in mutations:
 assert s.count(old)==1, (old,s.count(old))
 s=s.replace(old,new,1)
p.write_text(s)
PYMUT
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/red-source.sha256"
: > "$evidence/statuses.txt"
run_test() {
  local phase="$1" name="$2" expected="$3" rc
  local start end
  start=$(date +%s%N)
  set +e
  timeout 300s "$cargo" test --locked --features "$features" --test sys_process "$name" -- --exact --nocapture --test-threads=1 > "$evidence/$phase.log" 2>&1
  rc=$?
  set -e
  end=$(date +%s%N)
  printf '%s_status=%s\n%s_elapsed_ms=%s\n' "$phase" "$rc" "$phase" "$(((end-start)/1000000))" >> "$evidence/statuses.txt"
  if [[ "$expected" == RED ]]; then
    test "$rc" -eq 101
    grep -Fq 'RED_CONTROL: deliberately inverted' "$evidence/$phase.log"
    grep -Fq 'test result: FAILED. 0 passed; 1 failed;' "$evidence/$phase.log"
  else
    test "$rc" -eq 0
    grep -Fq 'test result: ok. 1 passed; 0 failed;' "$evidence/$phase.log"
  fi
}
run_test red_deadline managed_run_deadline_reaps_group_under_fixture_reaper RED
grep -Fq 'managed_deadline_group_boundary' "$evidence/red_deadline.log"
grep -Fq 'group_errno=3' "$evidence/red_deadline.log"
run_test red_output_limit managed_run_output_limit_reaps_group_under_fixture_reaper RED
grep -Fq 'managed_output_limit_group_boundary' "$evidence/red_output_limit.log"
grep -Fq 'prefix_preserved=true' "$evidence/red_output_limit.log"
cp "$runtime/sys_process.rs.original" tests/sys_process.rs
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/green-source.sha256"
run_test green_deadline managed_run_deadline_reaps_group_under_fixture_reaper GREEN
grep -Fq 'managed_deadline_group_boundary' "$evidence/green_deadline.log"
grep -Fq 'group_errno=3' "$evidence/green_deadline.log"
grep -Fq 'cleanup_exact=true' "$evidence/green_deadline.log"
run_test green_output_limit managed_run_output_limit_reaps_group_under_fixture_reaper GREEN
grep -Fq 'managed_output_limit_group_boundary' "$evidence/green_output_limit.log"
grep -Fq 'prefix_preserved=true' "$evidence/green_output_limit.log"
grep -Fq 'cleanup_exact=true' "$evidence/green_output_limit.log"
printf 'Both standalone unchecked X34 controls: assertion RED=101; restored deadline and output-limit GREEN=1/1.\n' > "$evidence/result.txt"
