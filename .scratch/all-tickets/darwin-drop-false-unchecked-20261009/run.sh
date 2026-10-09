#!/bin/bash
set -euo pipefail

PROJECT=/Users/hoppworks/projects/rhai
EVIDENCE="$PROJECT/.scratch/all-tickets/darwin-drop-false-unchecked-20261009"
ATTEMPT_DIR="$EVIDENCE/attempt-02"
SOURCE="$AGENT_RUNTIME_DIR/source"
mkdir -p "$SOURCE"
git -C "$PROJECT" archive HEAD | tar -x -C "$SOURCE"
cp "$ATTEMPT_DIR/Cargo.lock" "$SOURCE/Cargo.lock"
cp "$SOURCE/tests/sys_process.rs" "$ATTEMPT_DIR/current.sys_process.rs"
cd "$SOURCE"

TEST='direct_spawn_kill_on_drop_false_preserves_child_and_capture'
FEATURES='testing-environ,sys,unchecked'
COMMAND=(cargo +1.77.2 test --locked --features "$FEATURES" --test sys_process "$TEST" -- --exact --nocapture --test-threads=1)
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
mkdir -p "$CARGO_HOME" "$CARGO_TARGET_DIR"

cat > "$ATTEMPT_DIR/run-info.txt" <<EOF
base_revision=$(git -C "$PROJECT" rev-parse HEAD)
host=$(hostname)
os=$(sw_vers -productVersion) $(uname -a)
rustc=$(rustup run 1.77.2 rustc --version)
cargo=$(rustup run 1.77.2 cargo --version)
features=$FEATURES
test=$TEST
command=cargo +1.77.2 test --locked --features testing-environ,sys,unchecked --test sys_process $TEST -- --exact --nocapture --test-threads=1
runner_timeout_seconds=600
cargo_build_jobs=2
EOF
shasum -a 256 "$ATTEMPT_DIR/Cargo.lock" "$ATTEMPT_DIR/current.sys_process.rs" >> "$ATTEMPT_DIR/run-info.txt"

# Mutate only the acceptance expectation; the real fixture and readbacks stay intact.
python3 - "$SOURCE/tests/sys_process.rs" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
old = 'assert!(alive_after_drop && ack_matches, "kill_on_drop(false) must preserve the child after final handle drop");'
new = 'assert!(!alive_after_drop && ack_matches, "kill_on_drop(false) must preserve the child after final handle drop");'
if s.count(old) != 1:
    raise SystemExit(f'expected exactly one acceptance assertion, found {s.count(old)}')
p.write_text(s.replace(old, new))
PY
set +e
"${COMMAND[@]}" > "$ATTEMPT_DIR/red.log" 2>&1
RED=$?
set -e
printf '%s\n' "$RED" > "$ATTEMPT_DIR/red.status"
if [ "$RED" -ne 101 ]; then
  echo "expected assertion RED status 101, got $RED" >&2
  exit 1
fi
grep -F 'assertion failed: !alive_after_drop && ack_matches' "$ATTEMPT_DIR/red.log" >/dev/null
grep -E 'direct_drop_after_final_client_drop .*alive=true challenge_ack=true' "$ATTEMPT_DIR/red.log" >/dev/null

cp "$ATTEMPT_DIR/current.sys_process.rs" "$SOURCE/tests/sys_process.rs"
set +e
"${COMMAND[@]}" > "$ATTEMPT_DIR/green.log" 2>&1
GREEN=$?
set -e
printf '%s\n' "$GREEN" > "$ATTEMPT_DIR/green.status"
if [ "$GREEN" -ne 0 ]; then
  tail -100 "$ATTEMPT_DIR/green.log" >&2
  echo "expected restored GREEN status 0, got $GREEN" >&2
  exit 1
fi
grep -F "test $TEST ... ok" "$ATTEMPT_DIR/green.log" >/dev/null
grep -F 'stdout_bytes=524288 stderr_bytes=524288 complete=true' "$ATTEMPT_DIR/green.log" >/dev/null
grep -E 'direct_drop_terminal .*esrch=true' "$ATTEMPT_DIR/green.log" >/dev/null

echo 'red=101 intended assertion; child alive + challenge ACK observed; fixture cleanup completed' >> "$ATTEMPT_DIR/run-info.txt"
echo 'green=0; 1 passed; child captured 524288 stdout + 524288 stderr bytes; ESRCH reaping observed' >> "$ATTEMPT_DIR/run-info.txt"
shasum -a 256 "$ATTEMPT_DIR/run-info.txt" "$ATTEMPT_DIR/red.log" "$ATTEMPT_DIR/red.status" "$ATTEMPT_DIR/green.log" "$ATTEMPT_DIR/green.status" "$ATTEMPT_DIR/current.sys_process.rs" > "$ATTEMPT_DIR/SHA256SUMS"
