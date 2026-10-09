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
shasum -a 256 Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x25-rust177-20261009/attempt-01/source-sha256.txt
python3 - <<'PY'
from pathlib import Path
p = Path("tests/sys_process.rs")
s = p.read_text()
old = 'assert!(pid_is_absent(sentinel_pid), "fixture must reap its exact sentinel");'
new = 'assert!(!pid_is_absent(sentinel_pid), "fixture must reap its exact sentinel");'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PY
set +e
cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel -- --exact --nocapture > /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x25-rust177-20261009/attempt-01/red.log 2>&1
red=$?
set -e
printf '%s\n' "$red" > /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x25-rust177-20261009/attempt-01/red.status
test "$red" -eq 101
rg -q 'assertion failed: !pid_is_absent\(sentinel_pid\)' /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x25-rust177-20261009/attempt-01/red.log
rg -q 'test managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel \.\.\. FAILED' /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x25-rust177-20261009/attempt-01/red.log
python3 - <<'PY'
from pathlib import Path
p = Path("tests/sys_process.rs")
s = p.read_text()
old = 'assert!(!pid_is_absent(sentinel_pid), "fixture must reap its exact sentinel");'
new = 'assert!(pid_is_absent(sentinel_pid), "fixture must reap its exact sentinel");'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PY
set +e
cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel -- --exact --nocapture > /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x25-rust177-20261009/attempt-01/green.log 2>&1
green=$?
set -e
printf '%s\n' "$green" > /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x25-rust177-20261009/attempt-01/green.status
test "$green" -eq 0
rg -q 'test managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel \.\.\. ok' /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x25-rust177-20261009/attempt-01/green.log
rg -q 'all_esrch=true.*sentinel=[0-9]+ live=true wait_returned=true' /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x25-rust177-20261009/attempt-01/green.log
