#!/bin/bash
set -uo pipefail
REPO=/Users/hoppworks/projects/rhai
PROOF="$REPO/.scratch/all-tickets/darwin-child-drop-20261009"
LOCK_SOURCE="$REPO/.scratch/all-tickets/darwin-drop-false-unchecked-20261009/attempt-06/Cargo.lock"
SOURCE="$AGENT_RUNTIME_DIR/source"
mkdir -p "$SOURCE"
cd "$REPO"
git archive HEAD | tar -x -C "$SOURCE"
cp "$LOCK_SOURCE" "$SOURCE/Cargo.lock"
cd "$SOURCE"
{
  echo "base_revision=$(git -C "$REPO" rev-parse HEAD)"
  echo "test_source_sha256=$(shasum -a 256 tests/sys_process.rs | awk '{print $1}')"
  echo "fixture_source_sha256=$(shasum -a 256 tests/fixtures/sys_process_shared_child_contract.rs | awk '{print $1}')"
  echo "cargo_lock_sha256=$(shasum -a 256 Cargo.lock | awk '{print $1}')"
  echo "host=$(hostname)"
  echo "os=$(sw_vers -productVersion)"
  echo "arch=$(uname -m)"
  echo "rustc=$(rustc +1.77.2 --version)"
  echo "cargo=$(cargo +1.77.2 --version)"
  echo "features=testing-environ,sys"
  echo "tests=shared_child_contract::spawn_returns_while_large_stdin_is_blocked_and_wait_snapshots_are_stable; shared_child_contract::nonfinal_child_clone_drop_keeps_the_real_child_available"
  echo "runner_timeout_seconds=600"
  echo "cargo_build_jobs=2"
} > "$PROOF/run-info.txt"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=2
cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process shared_child_contract::spawn_returns_while_large_stdin_is_blocked_and_wait_snapshots_are_stable -- --exact --nocapture --test-threads=1 > "$PROOF/x26.log" 2>&1
rc26=$?
printf '%s\n' "$rc26" > "$PROOF/x26.status"
cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process shared_child_contract::nonfinal_child_clone_drop_keeps_the_real_child_available -- --exact --nocapture --test-threads=1 > "$PROOF/x27.log" 2>&1
rc27=$?
printf '%s\n' "$rc27" > "$PROOF/x27.status"
[ "$rc26" -eq 0 ] && [ "$rc27" -eq 0 ]
