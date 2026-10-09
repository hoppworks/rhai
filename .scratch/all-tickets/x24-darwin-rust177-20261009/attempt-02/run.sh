set -euo pipefail
source_dir="$AGENT_RUNTIME_DIR/source"
mkdir -p "$source_dir"
git -C /Users/hoppworks/projects/rhai archive HEAD | tar -x -C "$source_dir"
cp /Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-drop-false-unchecked-20261009/attempt-06/Cargo.lock "$source_dir/Cargo.lock"
test "$(shasum -a 256 "$source_dir/Cargo.lock" | awk '{print $1}')" = "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=2
export PYTHONDONTWRITEBYTECODE=1
cd "$source_dir"
python3 - <<'PY'
from pathlib import Path
p=Path("tests/sys_process.rs")
s=p.read_text()
marker="fn direct_spawn_try_wait_returns_unit_until_child_exits() {"
start=s.index(marker)
end=s.index("\n}\n",start)+3
test=s[start:end]
old='assert_eq!(wait_code, 0, "wait returns the result cached by the earlier terminal try_wait");'
new='assert_eq!(wait_code, 7, "wait returns the result cached by the earlier terminal try_wait");'
assert test.count(old)==1
p.write_text(s[:start]+test.replace(old,new,1)+s[end:])
PY
shasum -a 256 Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > /Users/hoppworks/projects/rhai/.scratch/all-tickets/x24-darwin-rust177-20261009/attempt-02/source-sha256.txt
python3 - <<'PY'
from pathlib import Path
import hashlib
s=Path("tests/sys_process.rs").read_bytes()
Path("/Users/hoppworks/projects/rhai/.scratch/all-tickets/x24-darwin-rust177-20261009/attempt-02/red-mutant-source.sha256").write_text(hashlib.sha256(s).hexdigest()+"  tests/sys_process.rs (isolated owned-copy wrong cached-wait expectation)\n")
PY
set +e
cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process direct_spawn_try_wait_returns_unit_until_child_exits -- --exact --nocapture > /Users/hoppworks/projects/rhai/.scratch/all-tickets/x24-darwin-rust177-20261009/attempt-02/red.log 2>&1
red=$?
set -e
printf '%s\n' "$red" > /Users/hoppworks/projects/rhai/.scratch/all-tickets/x24-darwin-rust177-20261009/attempt-02/red.status
test "$red" -eq 101
rg -Fq 'wait returns the result cached by the earlier terminal try_wait' /Users/hoppworks/projects/rhai/.scratch/all-tickets/x24-darwin-rust177-20261009/attempt-02/red.log
rg -Fq 'left: 0' /Users/hoppworks/projects/rhai/.scratch/all-tickets/x24-darwin-rust177-20261009/attempt-02/red.log
rg -Fq 'right: 7' /Users/hoppworks/projects/rhai/.scratch/all-tickets/x24-darwin-rust177-20261009/attempt-02/red.log
rg -Fq 'test direct_spawn_try_wait_returns_unit_until_child_exits ... FAILED' /Users/hoppworks/projects/rhai/.scratch/all-tickets/x24-darwin-rust177-20261009/attempt-02/red.log
