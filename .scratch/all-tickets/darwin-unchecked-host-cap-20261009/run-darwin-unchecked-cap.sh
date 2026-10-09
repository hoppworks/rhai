#!/bin/bash
set -Eeuo pipefail
PROJECT='/Users/hoppworks/projects/rhai'
EVIDENCE_DIR='/Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-unchecked-host-cap-20261009'
RUN_LABEL="${RUN_LABEL:-attempt-02}"
RED_LOG="$EVIDENCE_DIR/$RUN_LABEL.red.log"
RED_STATUS_FILE="$EVIDENCE_DIR/$RUN_LABEL.red.status"
GREEN_LOG="$EVIDENCE_DIR/$RUN_LABEL.green.log"
GREEN_STATUS_FILE="$EVIDENCE_DIR/$RUN_LABEL.green.status"
RUN_INFO="$EVIDENCE_DIR/$RUN_LABEL.run-info.txt"
BASE_REV='1b7513339c13a781933d4492a3ede98955ceac2a'
LOCK_SOURCE='/Users/hoppworks/projects/rhai/.scratch/all-tickets/linux-stdin-closure110-evidence/original-export/Cargo.lock.accepted'
LOCK_SHA='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
TEST_NAME='process_script_output_option_cannot_raise_the_host_cap'
export PYTHONDONTWRITEBYTECODE=1

test "$(git -C "$PROJECT" rev-parse HEAD)" = "$BASE_REV"
test "$(shasum -a 256 "$LOCK_SOURCE" | awk '{print $1}')" = "$LOCK_SHA"
mkdir -p "$AGENT_RUNTIME_DIR/source"
git -C "$PROJECT" archive --format=tar "$BASE_REV" | tar -xf - -C "$AGENT_RUNTIME_DIR/source"
cp "$LOCK_SOURCE" "$AGENT_RUNTIME_DIR/source/Cargo.lock"
cp "$PROJECT/tests/sys_process.rs" "$AGENT_RUNTIME_DIR/source/tests/sys_process.rs"
cp "$AGENT_RUNTIME_DIR/source/tests/sys_process.rs" "$EVIDENCE_DIR/$(basename "$RUN_LABEL").sys_process.rs"
cp "$AGENT_RUNTIME_DIR/source/Cargo.toml" "$EVIDENCE_DIR/$RUN_LABEL.Cargo.toml"
cp "$AGENT_RUNTIME_DIR/source/Cargo.lock" "$EVIDENCE_DIR/$RUN_LABEL.Cargo.lock"
python3 - "$AGENT_RUNTIME_DIR/source/tests/sys_process.rs" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1])
source=path.read_text()
start=source.index('fn process_script_output_option_cannot_raise_the_host_cap() {')
end=source.index('\n#[test]', start)
function=source[start:end]
anchor='assert_output_limit_error(error, stream, &expected_prefix);'
if function.count(anchor) != 1:
    raise SystemExit(f'expected one host-cap assertion in selected function, got {function.count(anchor)}')
path.write_text(source[:start]+function.replace(anchor, 'assert_output_limit_error(error, stream, &[]);', 1)+source[end:])
PY
cd "$AGENT_RUNTIME_DIR/source"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_BUILD_JOBS=2
COMMAND=(cargo +1.77.2 test --locked --features testing-environ,sys,unchecked --test sys_process "$TEST_NAME" -- --exact --nocapture)
set +e
"${COMMAND[@]}" > "$RED_LOG" 2>&1
RED_STATUS=$?
set -e
printf '%s\n' "$RED_STATUS" > "$RED_STATUS_FILE"
if [ "$RED_STATUS" -ne 101 ]; then
  printf 'expected wrong-expectation control exit 101, got %s\n' "$RED_STATUS" >&2
  exit 31
fi
grep -Fq "test $TEST_NAME ... FAILED" "$RED_LOG"
grep -Fq 'assertion `left == right` failed' "$RED_LOG"
grep -Fq 'left: [' "$RED_LOG"
grep -Fq 'right: []' "$RED_LOG"
# Restore exact committed test source before the acceptance run.
cp "$EVIDENCE_DIR/$RUN_LABEL.sys_process.rs" tests/sys_process.rs
set +e
"${COMMAND[@]}" > "$GREEN_LOG" 2>&1
GREEN_STATUS=$?
set -e
printf '%s\n' "$GREEN_STATUS" > "$GREEN_STATUS_FILE"
if [ "$GREEN_STATUS" -ne 0 ]; then
  printf 'expected restored GREEN exit 0, got %s\n' "$GREEN_STATUS" >&2
  exit 32
fi
grep -Fq "test $TEST_NAME ... ok" "$GREEN_LOG"
grep -Fq 'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured;' "$GREEN_LOG"
{
  printf 'base_revision=%s\n' "$BASE_REV"
  printf 'host=%s\n' "$(hostname)"
  printf 'os=%s\n' "$(sw_vers -productVersion) $(uname -a)"
  rustc +1.77.2 --version --verbose
  cargo +1.77.2 --version
  printf 'features=testing-environ,sys,unchecked\n'
  printf 'test=%s\n' "$TEST_NAME"
  printf 'command=cargo +1.77.2 test --locked --features testing-environ,sys,unchecked --test sys_process %s -- --exact --nocapture\n' "$TEST_NAME"
  printf 'runner_timeout_seconds=600\ncargo_build_jobs=%s\n' "$CARGO_BUILD_JOBS"
  printf 'red_status=%s\ngreen_status=%s\n' "$RED_STATUS" "$GREEN_STATUS"
  printf 'cargo_lock_sha256=%s\n' "$(shasum -a 256 Cargo.lock | awk '{print $1}')"
  printf 'manifest_sha256=%s\n' "$(shasum -a 256 Cargo.toml | awk '{print $1}')"
  printf 'tested_test_source_sha256=%s\n' "$(shasum -a 256 "$EVIDENCE_DIR/$RUN_LABEL.sys_process.rs" | awk '{print $1}')"
  printf 'disk_after=%s\n' "$(df -h "$PROJECT" | tail -1)"
} > "$RUN_INFO"
(cd "$EVIDENCE_DIR" && shasum -a 256 run-darwin-unchecked-cap.sh attempt-01.md attempt-01.red.log attempt-01.red.status attempt-01.runner.log attempt-01.runner.status attempt-01.scope-cleanup.txt "$RUN_LABEL.Cargo.toml" "$RUN_LABEL.Cargo.lock" "$RUN_LABEL.sys_process.rs" "$RUN_LABEL.red.log" "$RUN_LABEL.red.status" "$RUN_LABEL.green.log" "$RUN_LABEL.green.status" "$RUN_LABEL.run-info.txt" > "$RUN_LABEL.SHA256SUMS" && shasum -a 256 -c "$RUN_LABEL.SHA256SUMS")
