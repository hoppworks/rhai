#!/bin/bash
set -uo pipefail
REPO=/Users/hoppworks/projects/rhai
PROOF="$REPO/.scratch/all-tickets/darwin-process-lifecycle-base-20261009"
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
  echo "tests=direct_spawn_kill_on_drop_false_preserves_child_and_capture; shared_child_contract::script_throw_drops_and_reaps_a_live_child"
  echo "command1=cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process direct_spawn_kill_on_drop_false_preserves_child_and_capture -- --exact --nocapture --test-threads=1"
  echo "command2=cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process shared_child_contract::script_throw_drops_and_reaps_a_live_child -- --exact --nocapture --test-threads=1"
  echo "runner_timeout_seconds=600"
  echo "cargo_build_jobs=2"
} > "$PROOF/run-info.txt"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=2
cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process direct_spawn_kill_on_drop_false_preserves_child_and_capture -- --exact --nocapture --test-threads=1 > "$PROOF/x28.log" 2>&1
rc28=$?
printf '%s\n' "$rc28" > "$PROOF/x28.status"
cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process shared_child_contract::script_throw_drops_and_reaps_a_live_child -- --exact --nocapture --test-threads=1 > "$PROOF/x29.log" 2>&1
rc29=$?
printf '%s\n' "$rc29" > "$PROOF/x29.status"
[ "$rc28" -eq 0 ] && [ "$rc29" -eq 0 ]
