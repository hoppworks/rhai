#!/bin/bash
set -euo pipefail

PROJECT=/Users/hoppworks/projects/rhai
EVIDENCE="$PROJECT/.scratch/all-tickets/darwin-drop-false-unchecked-20261009"
RED_DIR="$EVIDENCE/attempt-02"
OUT="$EVIDENCE/attempt-03"
SOURCE="$AGENT_RUNTIME_DIR/source"
mkdir -p "$SOURCE"

# Reuse the already-observed assertion RED only after validating its entire identity.
test "$(cat "$RED_DIR/red.status")" = 101
grep -F 'features=testing-environ,sys,unchecked' "$RED_DIR/run-info.txt" >/dev/null
grep -F 'test=direct_spawn_kill_on_drop_false_preserves_child_and_capture' "$RED_DIR/run-info.txt" >/dev/null
grep -F 'base_revision=d32f4563677c09631715fe1b76a646604e770e3d' "$RED_DIR/run-info.txt" >/dev/null
grep -E 'direct_drop_after_final_client_drop .*alive=true challenge_ack=true completion_exists=false' "$RED_DIR/red.log" >/dev/null
grep -F 'kill_on_drop(false) must preserve the child after final handle drop' "$RED_DIR/red.log" >/dev/null
grep -E 'direct_drop_fixture_cleanup .*esrch=true' "$RED_DIR/red.log" >/dev/null

git -C "$PROJECT" archive HEAD | tar -x -C "$SOURCE"
cp "$OUT/Cargo.lock" "$SOURCE/Cargo.lock"
cp "$SOURCE/tests/sys_process.rs" "$OUT/current.sys_process.rs"
cmp "$RED_DIR/current.sys_process.rs" "$OUT/current.sys_process.rs"
cd "$SOURCE"

export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
mkdir -p "$CARGO_HOME" "$CARGO_TARGET_DIR"

cat > "$OUT/run-info.txt" <<EOF
base_revision=$(git -C "$PROJECT" rev-parse HEAD)
host=$(hostname)
os=$(sw_vers -productVersion) $(uname -a)
rustc=$(rustup run 1.77.2 rustc --version)
cargo=$(rustup run 1.77.2 cargo --version)
features=testing-environ,sys,unchecked
test=direct_spawn_kill_on_drop_false_preserves_child_and_capture
command=cargo +1.77.2 test --locked --features testing-environ,sys,unchecked --test sys_process direct_spawn_kill_on_drop_false_preserves_child_and_capture -- --exact --nocapture --test-threads=1
reused_red=$RED_DIR (status 101, intended false-preservation assertion, same base source and lock)
runner_timeout_seconds=600
cargo_build_jobs=2
EOF
shasum -a 256 "$OUT/Cargo.lock" "$OUT/current.sys_process.rs" >> "$OUT/run-info.txt"

cargo +1.77.2 test --locked --features testing-environ,sys,unchecked --test sys_process direct_spawn_kill_on_drop_false_preserves_child_and_capture -- --exact --nocapture --test-threads=1 > "$OUT/green.log" 2>&1
printf '0\n' > "$OUT/green.status"
grep -F 'test direct_spawn_kill_on_drop_false_preserves_child_and_capture ... ok' "$OUT/green.log" >/dev/null
grep -F 'stdout_bytes=524288 stderr_bytes=524288 complete=true' "$OUT/green.log" >/dev/null
grep -E 'direct_drop_terminal .*esrch=true' "$OUT/green.log" >/dev/null
echo 'green=0; 1 passed; child remained live after final handle drop, both 512 KiB streams completed, then exact PID was reaped' >> "$OUT/run-info.txt"
shasum -a 256 "$OUT/run-info.txt" "$OUT/green.log" "$OUT/green.status" "$OUT/current.sys_process.rs" > "$OUT/SHA256SUMS"
