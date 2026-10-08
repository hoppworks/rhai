#!/bin/bash
set -euo pipefail
repo='/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery'
out='/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery/.scratch/all-tickets/darwin-io-contracts-20261008/attempt-01'
lock='/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery/.scratch/all-tickets/process-io-contract-evidence/attempt-01/stage/Cargo.lock.accepted'
source="$AGENT_RUNTIME_DIR/source"
mkdir -p "$source"
(git -C "$repo" archive HEAD | tar -x -C "$source")
cp "$lock" "$source/Cargo.lock"
actual_lock=$(shasum -a 256 "$source/Cargo.lock" | awk '{print $1}')
test "$actual_lock" = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
{
  printf 'revision=%s\n' "$(git -C "$repo" rev-parse HEAD)"
  printf 'os=%s %s\n' "$(sw_vers -productName)" "$(sw_vers -productVersion)"
  printf 'arch=%s\n' "$(uname -m)"
  printf 'rustc=%s\n' "$(rustup run 1.93.0 rustc -V)"
  printf 'cargo=%s\n' "$(rustup run 1.93.0 cargo -V)"
  printf 'accepted_lock_sha256=%s\n' "$actual_lock"
  printf 'test_source_sha256=%s\n' "$(shasum -a 256 "$source/tests/sys_process.rs" | awk '{print $1}')"
  printf 'cargo_jobs=2\n'
  printf 'cargo_target_dir=%s/target\n' "$AGENT_RUNTIME_DIR"
  printf 'cargo_home=%s/cargo-home\n' "$AGENT_RUNTIME_DIR"
  printf 'test_command=cargo +1.93.0 test --locked --features testing-environ,sys --test sys_process run_io_contract_ -- --nocapture --test-threads=1\n'
} > "$out/run-metadata.txt"
set +e
(
  cd "$source"
  export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
  export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
  export CARGO_BUILD_JOBS=2
  cargo +1.93.0 test --locked --features testing-environ,sys --test sys_process run_io_contract_ -- --nocapture --test-threads=1
) > "$out/final-green.log" 2>&1
rc=$?
set -e
printf '%s\n' "$rc" > "$out/final-green.exit"
shasum -a 256 "$out/run-metadata.txt" "$out/final-green.log" "$out/final-green.exit" > "$out/evidence.sha256"
cat "$out/final-green.log"
printf 'cargo_exit=%s\n' "$rc"
exit "$rc"
