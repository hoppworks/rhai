#!/bin/bash
set -euo pipefail

PROJECT=/Users/hoppworks/projects/rhai
EVIDENCE="$PROJECT/.scratch/all-tickets/darwin-drop-false-unchecked-20261009"
OUT="$EVIDENCE/attempt-06"
SOURCE="$AGENT_RUNTIME_DIR/source"
mkdir -p "$SOURCE"
git -C "$PROJECT" archive HEAD | tar -x -C "$SOURCE"
cp "$PROJECT/tests/sys_process.rs" "$SOURCE/tests/sys_process.rs"
cp "$OUT/Cargo.lock" "$SOURCE/Cargo.lock"
cp "$SOURCE/tests/sys_process.rs" "$OUT/current.sys_process.rs"
cd "$SOURCE"

TEST='direct_spawn_kill_on_drop_false_preserves_child_and_capture'
FEATURES='testing-environ,sys,unchecked'
COMMAND=(cargo +1.77.2 test --locked --features "$FEATURES" --test sys_process "$TEST" -- --exact --nocapture --test-threads=1)
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=2
mkdir -p "$CARGO_HOME" "$CARGO_TARGET_DIR"

cat > "$OUT/run-info.txt" <<EOF
base_revision=$(git -C "$PROJECT" rev-parse HEAD)
worktree_test_source_sha256=$(shasum -a 256 "$PROJECT/tests/sys_process.rs" | awk '{print $1}')
host=$(hostname)
os=$(sw_vers -productVersion) $(uname -a)
rustc=$(rustup run 1.77.2 rustc --version)
cargo=$(rustup run 1.77.2 cargo --version)
features=$FEATURES
test=$TEST
command=cargo +1.77.2 test --locked --features testing-environ,sys,unchecked --test sys_process $TEST -- --exact --nocapture --test-threads=1
runner_timeout_seconds=600
cargo_build_jobs=$CARGO_BUILD_JOBS
EOF

# Preserve the exact RED source: invert the result contract and suppress only the
# fixture release so the panic guard must terminate and observe this exact child.
python3 - "$SOURCE/tests/sys_process.rs" "$OUT/red-mutant.sys_process.rs" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
old_assert = 'assert!(alive_after_drop && ack_matches, "kill_on_drop(false) must preserve the child after final handle drop");'
new_assert = 'assert!(!alive_after_drop && ack_matches, "kill_on_drop(false) must preserve the child after final handle drop");'
old_release = '        let _ = std::fs::write(self.path("release"), b"release\\n");'
if s.count(old_assert) != 1:
    raise SystemExit(f'unexpected assertion mutation anchor count: {s.count(old_assert)}')
s = s.replace(old_assert, new_assert)
start = s.index('impl DirectDropFixture {')
end = s.index('\n#[cfg(all(any(target_os = "linux", target_os = "macos"), not(feature = "no_index"), not(feature = "no_float")))]\nimpl Drop for DirectDropFixture', start)
fixture_impl = s[start:end]
if fixture_impl.count(old_release) != 1:
    raise SystemExit(f'unexpected DirectDropFixture release anchor count: {fixture_impl.count(old_release)}')
fixture_impl = fixture_impl.replace(old_release, '        // RED control: withhold release to exercise exact-child panic cleanup.')
s = s[:start] + fixture_impl + s[end:]
Path(sys.argv[2]).write_text(s)
p.write_text(s)
PY
cat >> "$OUT/run-info.txt" <<EOF
test_source_sha256=$(shasum -a 256 "$OUT/current.sys_process.rs" | awk '{print $1}')
red_mutant_source_sha256=$(shasum -a 256 "$OUT/red-mutant.sys_process.rs" | awk '{print $1}')
cargo_lock_sha256=$(shasum -a 256 "$OUT/Cargo.lock" | awk '{print $1}')
EOF

set +e
"${COMMAND[@]}" > "$OUT/red.log" 2>&1
RED=$?
set -e
printf '%s\n' "$RED" > "$OUT/red.status"
if [ "$RED" -ne 101 ]; then
  tail -100 "$OUT/red.log" >&2
  echo "expected assertion RED status 101, got $RED" >&2
  exit 1
fi
grep -F 'direct_drop_after_final_client_drop' "$OUT/red.log" | grep -F 'alive=true challenge_ack=true' >/dev/null
grep -F 'kill_on_drop(false) must preserve the child after final handle drop' "$OUT/red.log" >/dev/null
grep -F 'signal=SIGKILL sent=true' "$OUT/red.log" >/dev/null
grep -F 'after=SIGKILL' "$OUT/red.log" | grep -F 'esrch=true' >/dev/null

cp "$OUT/current.sys_process.rs" "$SOURCE/tests/sys_process.rs"
set +e
"${COMMAND[@]}" > "$OUT/green.log" 2>&1
GREEN=$?
set -e
printf '%s\n' "$GREEN" > "$OUT/green.status"
if [ "$GREEN" -ne 0 ]; then
  tail -100 "$OUT/green.log" >&2
  echo "expected restored GREEN status 0, got $GREEN" >&2
  exit 1
fi
grep -F 'test result: ok. 1 passed; 0 failed' "$OUT/green.log" >/dev/null
grep -F 'stdout_bytes=524288 stderr_bytes=524288 complete=true' "$OUT/green.log" >/dev/null
grep -E 'direct_drop_terminal .*esrch=true' "$OUT/green.log" >/dev/null
grep -E 'direct_drop_fixture_cleanup .*esrch=true' "$OUT/green.log" >/dev/null

echo 'red=101 intended inverted assertion; panic guard sent SIGKILL only after exact identity match and observed ESRCH' >> "$OUT/run-info.txt"
echo 'green=0; 1 passed; child remained live after final handle drop, both streams captured fully, then exact PID was reaped' >> "$OUT/run-info.txt"
shasum -a 256 "$OUT/run-info.txt" "$OUT/current.sys_process.rs" "$OUT/red-mutant.sys_process.rs" "$OUT/Cargo.lock" "$OUT/red.log" "$OUT/red.status" "$OUT/green.log" "$OUT/green.status" > "$OUT/SHA256SUMS"
