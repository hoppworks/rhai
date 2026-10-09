#!/bin/bash
set -Eeuo pipefail
PROJECT='/Users/hoppworks/projects/rhai'
EVIDENCE_DIR='/Users/hoppworks/projects/rhai/.scratch/all-tickets/writezero-unit-20261009T2025Z/darwin-stdin-closure-20261009T204536Z'
RUN_LABEL="${RUN_LABEL:-baseline-green-run-03}"
RED_LOG="$EVIDENCE_DIR/$RUN_LABEL.red.log"
RED_STATUS_FILE="$EVIDENCE_DIR/$RUN_LABEL.red.status"
GREEN_LOG="$EVIDENCE_DIR/$RUN_LABEL.green.log"
GREEN_STATUS_FILE="$EVIDENCE_DIR/$RUN_LABEL.green.status"
RUN_INFO="$EVIDENCE_DIR/$RUN_LABEL.run-info.txt"
BASE_REV='d1170c2d51fbb0dec072182f5232a6132b26550d'
BASELINE_FIX_PARENT='b04b486d2f7a6d80729c90d276523bfcdd89e6b9'
ACCEPTED_LOCK_SHA='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
LOCK_SOURCE='/Users/hoppworks/projects/rhai/.scratch/all-tickets/linux-stdin-closure110-evidence/original-export/Cargo.lock.accepted'
SDK_HEADER="$(/usr/bin/xcrun --show-sdk-path)/usr/include/sys/pipe.h"
export PYTHONDONTWRITEBYTECODE=1
DISK_BEFORE="$(df -h "$PROJECT" | tail -1)"
CPU_COUNT="$(sysctl -n hw.ncpu)"
MEMORY_BYTES="$(sysctl -n hw.memsize)"

test "$(git -C "$PROJECT" rev-parse HEAD)" = "$BASE_REV"
test "$(shasum -a 256 "$LOCK_SOURCE" | awk '{print $1}')" = "$ACCEPTED_LOCK_SHA"
test "$(git -C "$PROJECT" rev-parse 'd52450aa8^')" = "$BASELINE_FIX_PARENT"

mkdir -p "$AGENT_RUNTIME_DIR/source"
git -C "$PROJECT" archive --format=tar "$BASE_REV" | tar -xf - -C "$AGENT_RUNTIME_DIR/source"
cp "$PROJECT/tests/sys_process.rs" "$AGENT_RUNTIME_DIR/source/tests/sys_process.rs"
cp "$LOCK_SOURCE" "$AGENT_RUNTIME_DIR/source/Cargo.lock"
cp "$AGENT_RUNTIME_DIR/source/src/packages/sys/process/unix.rs" "$EVIDENCE_DIR/unix-current.rs"
cp "$AGENT_RUNTIME_DIR/source/tests/sys_process.rs" "$EVIDENCE_DIR/sys_process.rs"
cp "$LOCK_SOURCE" "$EVIDENCE_DIR/Cargo.lock"
if [ -e "$EVIDENCE_DIR/sys-pipe.h" ]; then
    cmp -s "$SDK_HEADER" "$EVIDENCE_DIR/sys-pipe.h"
else
    cp "$SDK_HEADER" "$EVIDENCE_DIR/sys-pipe.h"
fi

python3 - "$AGENT_RUNTIME_DIR/source/src/packages/sys/process/unix.rs" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
source = path.read_text()
fixed = '''                Err(error) if error.kind() == io::ErrorKind::BrokenPipe => {
                    if state.error.is_none() {
                        state.error =
                            Some(process_io_cause("write child stdin", &state.program, error));
                    }
                    close_stdin = true;
                    state.kill_requested = true;
                    progressed = true;
                }'''
baseline = '''                Err(error) if error.kind() == io::ErrorKind::BrokenPipe => {
                    state.stdin_offset = state.stdin.len();
                    close_stdin = true;
                    progressed = true;
                }'''
if source.count(fixed) != 1:
    raise SystemExit(f'expected exactly one current BrokenPipe branch, found {source.count(fixed)}')
path.write_text(source.replace(fixed, baseline))
PY
cp "$AGENT_RUNTIME_DIR/source/src/packages/sys/process/unix.rs" "$EVIDENCE_DIR/unix-known-broken-baseline.rs"

cd "$AGENT_RUNTIME_DIR/source"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_BUILD_JOBS=2
TEST_NAME='spawn_retains_error_when_child_closes_stdin_with_unsent_input_darwin'
set +e
cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process "$TEST_NAME" -- --exact --nocapture > "$RED_LOG" 2>&1
RED_STATUS=$?
set -e
printf '%s\n' "$RED_STATUS" > "$RED_STATUS_FILE"
if [ "$RED_STATUS" -ne 101 ]; then
    printf 'expected known-broken RED exit 101, got %s\n' "$RED_STATUS" >&2
    exit 31
fi
grep -Fq 'DARWIN_RETAINED_BROKEN_PIPE_ASSERTION: first bounded Child.wait omitted retained stdin BrokenPipe' "$RED_LOG"
grep -Fq 'darwin-stdin-close-readback' "$RED_LOG"
grep -Fq 'darwin-stdin-missing-error-red' "$RED_LOG"
grep -Fq 'child_reaped=true group_absent=true host_unchanged=true sentinel_unchanged=true' "$RED_LOG"

cp "$EVIDENCE_DIR/unix-current.rs" "$AGENT_RUNTIME_DIR/source/src/packages/sys/process/unix.rs"
set +e
cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process "$TEST_NAME" -- --exact --nocapture > "$GREEN_LOG" 2>&1
GREEN_STATUS=$?
set -e
printf '%s\n' "$GREEN_STATUS" > "$GREEN_STATUS_FILE"
if [ "$GREEN_STATUS" -ne 0 ]; then
    printf 'expected GREEN exit 0, got %s\n' "$GREEN_STATUS" >&2
    exit 32
fi
grep -Fq "test $TEST_NAME ... ok" "$GREEN_LOG"
grep -Fq 'darwin-stdin-close-readback' "$GREEN_LOG"
grep -Fq 'darwin-spawn-stdin-closure' "$GREEN_LOG"

{
    printf 'base_revision=%s\n' "$BASE_REV"
    printf 'baseline_product_revision=%s\n' "$BASELINE_FIX_PARENT"
    printf 'baseline_delta=d52450aa8 BrokenPipe-only revert in private source copy\n'
    printf 'host=%s\n' "$(hostname)"
    printf 'os=%s\n' "$(sw_vers -productVersion) $(uname -a)"
    rustc +1.77.2 --version --verbose
    cargo +1.77.2 --version
    printf 'features=testing-environ,sys\n'
    printf 'test=%s\n' "$TEST_NAME"
    printf 'command=cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process %s -- --exact --nocapture\n' "$TEST_NAME"
    printf 'cargo_build_jobs=%s\n' "$CARGO_BUILD_JOBS"
    printf 'runner_timeout_seconds=600\n'
    printf 'cpu_count=%s\n' "$CPU_COUNT"
    printf 'memory_bytes=%s\n' "$MEMORY_BYTES"
    printf 'disk_before=%s\n' "$DISK_BEFORE"
    printf 'expected_peak_kib=1048576\n'
    printf 'expected_peak_basis=previous comparable bounded Cargo run measured 733060 KiB; rounded-up planning estimate, not a hard limit\n'
    printf 'binding_disk_reserve=none specified by current project or user instructions\n'
    printf 'red_status=%s\ngreen_status=%s\n' "$RED_STATUS" "$GREEN_STATUS"
    printf 'lock_sha256=%s\n' "$(shasum -a 256 Cargo.lock | awk '{print $1}')"
    printf 'lock_reused_from=%s\n' "$LOCK_SOURCE"
    printf 'manifest_sha256=%s\n' "$(shasum -a 256 Cargo.toml | awk '{print $1}')"
    printf 'test_source_sha256=%s\n' "$(shasum -a 256 tests/sys_process.rs | awk '{print $1}')"
    printf 'current_unix_source_sha256=%s\n' "$(shasum -a 256 "$EVIDENCE_DIR/unix-current.rs" | awk '{print $1}')"
    printf 'baseline_unix_source_sha256=%s\n' "$(shasum -a 256 "$EVIDENCE_DIR/unix-known-broken-baseline.rs" | awk '{print $1}')"
    printf 'sdk_pipe_header=%s\n' "$SDK_HEADER"
    rg -n '^[[:space:]]*#define (PIPE_SIZE|BIG_PIPE_SIZE)' "$SDK_HEADER"
    printf 'sdk_pipe_header_sha256=%s\n' "$(shasum -a 256 "$SDK_HEADER" | awk '{print $1}')"
    printf 'disk_after=%s\n' "$(df -h "$PROJECT" | tail -1)"
} > "$RUN_INFO"
(cd "$EVIDENCE_DIR" && shasum -a 256 Cargo.lock sys_process.rs unix-current.rs unix-known-broken-baseline.rs sys-pipe.h "$RUN_LABEL.red.log" "$RUN_LABEL.red.status" "$RUN_LABEL.green.log" "$RUN_LABEL.green.status" "$RUN_LABEL.run-info.txt" run-darwin.sh preflight-attempt-01.md preflight-runner.status preflight-scope-cleanup.txt preflight-attempt-02.md preflight-copy-runner.status preflight-copy-scope-cleanup.txt compile-attempt-01.md compile-attempt-01.log compile-attempt-01.status compile-runner.status compile-scope-cleanup.txt baseline-control-attempt-01.md baseline-control-attempt-01.log baseline-control-attempt-01.status baseline-control-runner-01.status baseline-control-scope-01.txt baseline-green-run-02.md baseline-green-run-02.red.log baseline-green-run-02.red.status baseline-green-run-02.green.log baseline-green-run-02.green.status baseline-green-run-02.log baseline-green-run-02.runner-status baseline-green-run-02.scope-cleanup > "$RUN_LABEL.SHA256SUMS" && shasum -a 256 -c "$RUN_LABEL.SHA256SUMS")
