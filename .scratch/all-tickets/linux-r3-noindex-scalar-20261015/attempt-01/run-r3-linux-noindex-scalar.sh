#!/usr/bin/env bash
set -Eeuo pipefail
repo=/var/home/Daniel/projects/rhai
attempt="$repo/.scratch/all-tickets/linux-r3-noindex-scalar-20261015/attempt-01"
evidence="$attempt/evidence"
scope="${1:?session scope required}"
runtime="${AGENT_RUNTIME_DIR:?scoped runner required}"
lock="$repo/.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock"
toolchain=/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
cargo="$toolchain/cargo"
source_dir="$runtime/source"
features=testing-environ,sys,no_index,sync,unchecked
mkdir -p "$source_dir"
git -C "$repo" archive HEAD | tar --no-same-owner -xf - -C "$source_dir"
cp "$lock" "$source_dir/Cargo.lock"
cd "$source_dir"
cp tests/sys_process.rs "$runtime/sys_process.rs.original"
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
old='assert!(matches!(missing_raw_api.as_ref(), rhai::EvalAltResult::ErrorFunctionNotFound(name, _) if name.starts_with("run_raw")), "run_raw remains registered: {missing_raw_api:?}");'
new='assert!(!matches!(missing_raw_api.as_ref(), rhai::EvalAltResult::ErrorFunctionNotFound(name, _) if name.starts_with("run_raw")), "RED_CONTROL: deliberately inverted absent run_raw assertion");'
assert s.count(old)==1, s.count(old)
p.write_text(s.replace(old,new,1))
PYMUT
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/red-source.sha256"
run_test() {
  local phase="$1" rc
  set +e
  timeout 300s "$cargo" test --locked --features "$features" --test sys_process scalar_run_with_cwd_works_without_collections -- --exact --nocapture --test-threads=1 > "$evidence/$phase.log" 2>&1
  rc=$?
  set -e
  printf '%s=%s\n' "$phase" "$rc" >> "$evidence/statuses.txt"
  return "$rc"
}
printf 'phase=exit\n' > "$evidence/statuses.txt"
if run_test red; then echo 'RED control unexpectedly passed' >&2; exit 21; else rc=$?; fi
test "$rc" -eq 101
grep -Fq 'RED_CONTROL: deliberately inverted absent run_raw assertion' "$evidence/red.log"
grep -Fq 'child-pid=' "$evidence/red.log"
grep -Fq 'test result: FAILED. 0 passed; 1 failed;' "$evidence/red.log"
cp "$runtime/sys_process.rs.original" tests/sys_process.rs
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/green-source.sha256"
run_test green
grep -Fq 'test result: ok. 1 passed; 0 failed;' "$evidence/green.log"
grep -Fq 'no-index scalar child_pid=' "$evidence/green.log"
grep -Fq 'reap=ESRCH' "$evidence/green.log"
printf 'RED=101 at deliberate absent-run_raw assertion; restored GREEN=1/1 with child PID ESRCH readback\n' > "$evidence/result.txt"
