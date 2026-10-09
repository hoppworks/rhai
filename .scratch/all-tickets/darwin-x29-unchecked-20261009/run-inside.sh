#!/bin/bash
set -euo pipefail
REPO=/Users/hoppworks/projects/rhai
PROOF="$REPO/.scratch/all-tickets/darwin-x29-unchecked-20261009"
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
  echo "features=testing-environ,sys,unchecked"
  echo "test=shared_child_contract::script_throw_drops_and_reaps_a_live_child"
  echo "command=cargo +1.77.2 test --locked --features testing-environ,sys,unchecked --test sys_process shared_child_contract::script_throw_drops_and_reaps_a_live_child -- --exact --nocapture --test-threads=1"
  echo "runner_timeout_seconds=600"
  echo "cargo_build_jobs=2"
} > "$PROOF/run-info.txt"
set +e
CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target" CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home" CARGO_BUILD_JOBS=2 cargo +1.77.2 test --locked --features testing-environ,sys,unchecked --test sys_process shared_child_contract::script_throw_drops_and_reaps_a_live_child -- --exact --nocapture --test-threads=1 > "$PROOF/cargo.log" 2>&1
status=$?
set -e
printf '%s\n' "$status" > "$PROOF/cargo.status"
exit "$status"
