#!/usr/bin/env bash
set -Eeuo pipefail
repo=/var/home/Daniel/projects/rhai
attempt="$repo/.scratch/all-tickets/linux-x34-sync-unchecked-20261015/attempt-01"
evidence="$attempt/evidence"
scope="${1:?session scope required}"
runtime="${AGENT_RUNTIME_DIR:?scoped runner required}"
lock="$repo/.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock"
toolchain=/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
cargo="$toolchain/cargo"
source_dir="$runtime/source"
features=testing-environ,sys,sync,unchecked
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
name='managed_run_deadline_reaps_group_under_fixture_reaper'
start=s.index(f'fn {name}()'); end=s.find('\nfn ',start)
if end<0: end=len(s)
body=s[start:end]
old='assert!(api_is_timed_out, "managed public run did not return its deadline report after exact group closure: {api_result}");'
new='assert!(!api_is_timed_out, "RED_CONTROL: deliberately inverted managed deadline expectation");'
assert body.count(old)==1,body.count(old)
p.write_text(s[:start]+body.replace(old,new,1)+s[end:])
PYMUT
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/red-source.sha256"
run_test() {
  local phase="$1" name="$2" rc
  set +e
  timeout 300s "$cargo" test --locked --features "$features" --test sys_process "$name" -- --exact --nocapture --test-threads=1 > "$evidence/$phase.log" 2>&1
  rc=$?
  set -e
  printf '%s=%s\n' "$phase" "$rc" >> "$evidence/statuses.txt"
  return "$rc"
}
printf 'phase=exit\n' > "$evidence/statuses.txt"
if run_test red managed_run_deadline_reaps_group_under_fixture_reaper; then echo 'RED control unexpectedly passed' >&2; exit 21; else rc=$?; fi
test "$rc" -eq 101
grep -Fq 'RED_CONTROL: deliberately inverted managed deadline expectation' "$evidence/red.log"
grep -Fq 'managed_deadline_group_boundary' "$evidence/red.log"
cp "$runtime/sys_process.rs.original" tests/sys_process.rs
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/green-source.sha256"
run_test green_deadline managed_run_deadline_reaps_group_under_fixture_reaper
grep -Fq 'test result: ok. 1 passed; 0 failed;' "$evidence/green_deadline.log"
grep -Fq 'managed_deadline_group_boundary' "$evidence/green_deadline.log"
run_test green_output_limit managed_run_output_limit_reaps_group_under_fixture_reaper
grep -Fq 'test result: ok. 1 passed; 0 failed;' "$evidence/green_output_limit.log"
grep -Fq 'managed_output_limit_group_boundary' "$evidence/green_output_limit.log"
grep -Fq 'cleanup_exact=true' "$evidence/green_output_limit.log"
printf 'deadline RED=101 at deliberate assertion; restored deadline GREEN=1/1; output-limit GREEN=1/1\n' > "$evidence/result.txt"
