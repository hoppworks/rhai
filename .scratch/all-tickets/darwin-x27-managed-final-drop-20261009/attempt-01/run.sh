set -euo pipefail
source_dir="$AGENT_RUNTIME_DIR/source"
mkdir -p "$source_dir"
git -C /Users/hoppworks/projects/rhai archive HEAD | tar -x -C "$source_dir"
cp /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-drop-false-unchecked-20261009/attempt-06/Cargo.lock "$source_dir/Cargo.lock"
test "$(shasum -a 256 "$source_dir/Cargo.lock" | awk '{print $1}')" = '2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=2
export PYTHONDONTWRITEBYTECODE=1
cd "$source_dir"
python3 - <<'PY'
from pathlib import Path
p=Path('tests/sys_process.rs')
s=p.read_text()
marker='fn managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not() {'
start=s.index(marker)
end=s.index('\n}',start)+2
fn=s[start:end]
old='assert!(all_gone, "dropping final Child clone did not terminate the managed group");'
new='assert!(!all_gone, "dropping final Child clone did not terminate the managed group");'
assert fn.count(old)==1
p.write_text(s[:start]+fn.replace(old,new,1)+s[end:])
PY
shasum -a 256 Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/red-source-sha256.txt
set +e
cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not -- --exact --nocapture > /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/red.log 2>&1
red=$?
set -e
printf '%s\n' "$red" > /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/red.status
test "$red" -eq 101
rg -Fq 'all_esrch=true' /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/red.log
rg -Fq 'live=true' /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/red.log
rg -Fq 'dropping final Child clone did not terminate the managed group' /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/red.log
rg -Fq 'managed-scope sentinel_cleanup' /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/red.log
rg -Fq 'esrch=true' /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/red.log
git -C /Users/hoppworks/projects/rhai show HEAD:tests/sys_process.rs > tests/sys_process.rs
shasum -a 256 Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/green-source-sha256.txt
cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not -- --exact --nocapture > /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/green.log 2>&1
printf '0\n' > /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/green.status
rg -Fq 'all_live=true' /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/green.log
rg -Fq 'all_esrch=true' /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/green.log
rg -Fq 'test managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not ... ok' /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/green.log
rg -Fq 'managed-scope sentinel_cleanup' /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/green.log
rg -Fq 'esrch=true' /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/green.log
uname -a > /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/environment.txt
sw_vers >> /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/environment.txt
rustc +1.77.2 -Vv >> /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/environment.txt
cargo +1.77.2 -V >> /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/environment.txt
shasum -a 256 /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/red.log /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/green.log > /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-x27-managed-final-drop-20261009/attempt-01/logs.sha256
