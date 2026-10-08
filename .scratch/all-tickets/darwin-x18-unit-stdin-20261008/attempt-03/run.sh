#!/bin/bash
set -euo pipefail
repo=/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery
lock="$repo/.scratch/all-tickets/process-io-contract-evidence/attempt-01/stage/Cargo.lock.accepted"
evidence="$RHAI_X18_EVIDENCE"
src="$AGENT_RUNTIME_DIR/source"
mkdir -p "$src"
printf '%s\n' "$AGENT_RUNTIME_DIR" > "$evidence/private-runtime.txt"
git -C "$repo" archive --format=tar HEAD | tar -xf - -C "$src"
cp "$lock" "$src/Cargo.lock"
expected_lock=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
actual_lock=$(shasum -a 256 "$src/Cargo.lock" | awk '{print $1}')
test "$actual_lock" = "$expected_lock"
test_source_sha=$(cd "$src" && shasum -a 256 tests/sys_process.rs | awk '{print $1}')
test "$test_source_sha" = 7ddc87f6e4b57d61d077445a81f1c3ef2f2e54cb35ac8c90a7ed328245d14017
cp "$src/tests/sys_process.rs" "$evidence/sys_process-baseline.rs"
(cd "$src" && shasum -a 256 Cargo.toml tests/sys_process.rs tests/fixtures/sys_process_shared_child_contract.rs Cargo.lock) > "$evidence/source-hashes.txt"
{
  printf 'revision='; git -C "$repo" rev-parse HEAD
  printf 'features=testing-environ,sys\nfilter=unit_stdin_means_immediate_eof\n'
  printf 'command=cargo +1.93.0 test --locked --features testing-environ,sys --test sys_process unit_stdin_means_immediate_eof -- --exact --nocapture --test-threads=1\n'
  printf 'lock_sha256=%s\n' "$actual_lock"
  sw_vers
  uname -m
  rustc +1.93.0 --version
  cargo +1.93.0 --version
} > "$evidence/run-metadata.txt"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=1
export PYTHONDONTWRITEBYTECODE=1
cd "$src"
set +e
cargo +1.93.0 test --locked --features testing-environ,sys --test sys_process unit_stdin_means_immediate_eof -- --exact --nocapture --test-threads=1 > "$evidence/green.log" 2>&1
green=$?
set -e
printf '%s\n' "$green" > "$evidence/green.status"
green_ok=false
if [[ "$green" -eq 0 ]] &&
   grep -F 'test unit_stdin_means_immediate_eof ... ok' "$evidence/green.log" >/dev/null &&
   grep -F '1 passed; 0 failed' "$evidence/green.log" >/dev/null; then
  green_ok=true
fi
{
  classification=green_failed
  if [[ "$green_ok" == true ]]; then classification=accepted; fi
  printf 'classification=%s\n' "$classification"
  printf 'green_status=%s\ngreen_passed=%s\n' "$green" "$green_ok"
  printf 'baseline_source_restored=true\n'
  printf 'red_evidence=.scratch/all-tickets/darwin-x18-unit-stdin-20261008/attempt-02/red.log\n'
  printf 'lock_sha256=%s\n' "$actual_lock"
} > "$evidence/outcome.txt"
test "$green_ok" = true
