#!/usr/bin/env bash
set -Eeuo pipefail
repo=/Users/hoppworks/.codex/worktrees/darwin-capture-cleanup/rhai
attempt="$repo/.scratch/all-tickets/darwin-lifecycle-profiles-20261025/attempt-01"
evidence="$attempt/evidence"
revision=c0fc47e403f685624c611d94783aa5dffc609c64
runner=/Users/hoppworks/projects/agent-skills/tools/run_scoped.py
source_dir="$AGENT_RUNTIME_DIR/source"
mkdir -p "$source_dir"
git -C "$repo" archive "$revision" | tar -x -C "$source_dir"
cp "$repo/.scratch/all-tickets/core-current-msrv-evidence-04/Cargo.lock" "$source_dir/Cargo.lock"
cd "$source_dir"
test "$(shasum -a 256 Cargo.lock | awk '{print $1}')" = 2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
test "$(shasum -a 256 tests/sys_process.rs | awk '{print $1}')" = 3c22dd7428b0a3299905d384e661d845bf7510ba488d58c23d1aa83700124172
test "$(shasum -a 256 src/packages/sys/process/unix.rs | awk '{print $1}')" = 2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home" CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_BUILD_JOBS=2 CARGO_TERM_COLOR=never PYTHONDONTWRITEBYTECODE=1
{
  date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
  printf 'revision=%s\nruntime=%s\nTMPDIR=%s\n' "$revision" "$AGENT_RUNTIME_DIR" "$TMPDIR"
  printf 'cargo_jobs=2\nouter_timeout_seconds=600\n'
  shasum -a 256 "$runner"
  uname -a
  sw_vers
  rustc +1.77.2 -Vv
  cargo +1.77.2 -V
} > "$evidence/environment.txt"
shasum -a 256 Cargo.toml Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/source-hashes.txt"
printf 'features\tselector\texit\n' > "$evidence/statuses.tsv"
kill_selector=managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel
drop_selector=managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not
capture_selector=managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes
cancel_selector=managed_spawn_post_reap_cancel_bounds_escaped_capture
run_case() {
  local features="$1" name="$2" rc=0
  local log="$evidence/${features//,/_}-$name.log"
  cargo +1.77.2 test --locked --features "$features" --test sys_process "$name" -- --exact --nocapture --test-threads=1 > "$log" 2>&1 || rc=$?
  printf '%s\t%s\t%s\n' "$features" "$name" "$rc" >> "$evidence/statuses.tsv"
  test "$rc" -eq 0
  rg -Fq 'test result: ok. 1 passed; 0 failed;' "$log"
}
for features in testing-environ,sys,sync testing-environ,sys,unchecked testing-environ,sys,sync,unchecked; do
  # The base unchecked kill row is already accepted; no unchanged repeat.
  if test "$features" != testing-environ,sys,unchecked; then
    run_case "$features" "$kill_selector"
  fi
  run_case "$features" "$drop_selector"
  run_case "$features" "$capture_selector"
  run_case "$features" "$cancel_selector"
done
printf 'eleven previously uncovered native Darwin lifecycle/capture GREEN rows passed; original native RED/base receipts are reused\n' > "$evidence/result.txt"
