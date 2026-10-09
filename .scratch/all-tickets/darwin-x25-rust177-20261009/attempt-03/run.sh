set -euo pipefail
source_dir="$AGENT_RUNTIME_DIR/source"
mkdir -p "$source_dir"
git -C /Users/hoppworks/projects/rhai archive HEAD | tar -x -C "$source_dir"
cp /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-drop-false-unchecked-20261009/attempt-06/Cargo.lock "$source_dir/Cargo.lock"
test "$(shasum -a 256 "$source_dir/Cargo.lock" | awk '{print $1}')" = "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export PYTHONDONTWRITEBYTECODE=1
cd "$source_dir"
shasum -a 256 Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x25-rust177-20261009/attempt-03/source-sha256.txt
cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel -- --exact --nocapture > /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x25-rust177-20261009/attempt-03/green.log 2>&1
printf '%s\n' "$?" > /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x25-rust177-20261009/attempt-03/green.status
rg -q 'test managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel \.\.\. ok' /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x25-rust177-20261009/attempt-03/green.log
rg -q 'all_esrch=true.*sentinel=[0-9]+ live=true wait_returned=true' /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x25-rust177-20261009/attempt-03/green.log
