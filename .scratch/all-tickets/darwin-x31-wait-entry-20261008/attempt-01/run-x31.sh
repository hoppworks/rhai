#!/usr/bin/env bash
set -euo pipefail

REPO=/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery
EVIDENCE="$REPO/.scratch/all-tickets/darwin-x31-wait-entry-20261008/attempt-01"
RUNTIME="${AGENT_RUNTIME_DIR:?run_scoped must provide private runtime}"
STAGE="$RUNTIME/source"
LOCK="$REPO/.scratch/all-tickets/api-metadata-evidence/native3-20261007/Cargo.lock"
SOURCE_COMMIT=05320c2c9bf3d4396956632e0cc1706e96c94b15
UNIX_SOURCE="$STAGE/src/packages/sys/process/unix.rs"
TEST=packages::sys::process::unix::tests::public_wait_is_cancelled_after_entering_condvar
BASE_UNIX_SHA=55dc5ad528ad2b4fd56d3fcdd42f92af0b30bf3f96db37c476ee31320dcba713
LOCK_SHA=4ff0a7de6f504510af64092d446d411b86d95228b23a188b396bd188da367627

mkdir -p "$STAGE" "$RUNTIME/cargo-home" "$RUNTIME/target"
git -C "$REPO" archive --format=tar "$SOURCE_COMMIT" | tar -xf - -C "$STAGE"
cp "$LOCK" "$STAGE/Cargo.lock"
cp "$UNIX_SOURCE" "$RUNTIME/unix.original.rs"

{
    printf 'source_commit=%s\n' "$SOURCE_COMMIT"
    printf 'explicit_cwd=%s\n' "$STAGE"
    printf 'cargo_lock_source=%s\n' "$LOCK"
    printf 'cargo_test_name=%s\n' "$TEST"
    printf 'cargo_command=cargo +1.93.0 test --locked --lib --features <features> %s -- --exact --nocapture --test-threads=1\n' "$TEST"
} > "$EVIDENCE/command.txt"

python3 - "$STAGE" "$LOCK_SHA" "$BASE_UNIX_SHA" > "$EVIDENCE/source-preflight.txt" <<'PY'
import hashlib
import pathlib
import sys

stage = pathlib.Path(sys.argv[1])
expected_lock, expected_unix = sys.argv[2:]
expected = {
    "Cargo.toml": "cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e",
    "src/packages/sys/process.rs": "090094476662417aa94e2ff519cb8038c1d3721e02be6ec166762502bfbff2e2",
    "src/packages/sys/process/unix.rs": expected_unix,
}
for rel, digest in expected.items():
    actual = hashlib.sha256((stage / rel).read_bytes()).hexdigest()
    if actual != digest:
        raise SystemExit(f"source hash mismatch {rel}: {actual} != {digest}")
    print(f"source_sha256 {rel}={actual}")
lock_hash = hashlib.sha256((stage / "Cargo.lock").read_bytes()).hexdigest()
if lock_hash != expected_lock:
    raise SystemExit(f"lock hash mismatch: {lock_hash} != {expected_lock}")
print(f"cargo_lock_sha256={lock_hash}")
PY

{
    date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
    sw_vers
    uname -a
    rustc +1.93.0 --version
    cargo +1.93.0 --version
} > "$EVIDENCE/environment.txt" 2>&1

export CARGO_HOME="$RUNTIME/cargo-home"
export CARGO_TARGET_DIR="$RUNTIME/target"
export CARGO_BUILD_JOBS=1
export CARGO_TERM_COLOR=never
export PYTHONDONTWRITEBYTECODE=1

cd "$STAGE"
if cargo +1.93.0 metadata --locked --format-version 1 > "$EVIDENCE/cargo-metadata.json" 2> "$EVIDENCE/cargo-metadata.stderr"; then
    echo 'cargo_metadata_status=0' > "$EVIDENCE/cargo-metadata.status"
else
    metadata_status=$?
    printf 'cargo_metadata_status=%s\n' "$metadata_status" > "$EVIDENCE/cargo-metadata.status"
    exit "$metadata_status"
fi

run_case() {
    local label="$1" features="$2" expected="$3" status=0
    SECONDS=0
    if cargo +1.93.0 test --locked --lib --features "$features" "$TEST" -- --exact --nocapture --test-threads=1 > "$EVIDENCE/$label.log" 2>&1; then
        status=0
    else
        status=$?
    fi
    printf '%s\n' "$status" > "$EVIDENCE/$label.status"
    printf '%s_seconds=%s\n' "$label" "$SECONDS" >> "$EVIDENCE/durations.txt"
    grep -F "$TEST" "$EVIDENCE/$label.log" >/dev/null || {
        printf '%s did not report exact test %s\n' "$label" "$TEST" >&2
        return 1
    }
    if [[ "$expected" == RED ]]; then
        [[ "$status" == 101 ]] || { echo "$label expected Cargo 101, got $status" >&2; return 1; }
        grep -F 'X31 RED: wait-entry assertion sensitivity control' "$EVIDENCE/$label.log" >/dev/null
        grep -F 'wait-entry checkpoint pid=' "$EVIDENCE/$label.log" >/dev/null
        grep -F 'nonterminal=true' "$EVIDENCE/$label.log" >/dev/null
        grep -F 'wait-entry fixture cleanup pid=' "$EVIDENCE/$label.log" >/dev/null
        grep -F 'reap=ESRCH' "$EVIDENCE/$label.log" >/dev/null
        grep -F 'test result: FAILED. 0 passed; 1 failed;' "$EVIDENCE/$label.log" >/dev/null
    else
        [[ "$status" == 0 ]] || { echo "$label expected Cargo 0, got $status" >&2; return 1; }
        grep -F 'test result: ok. 1 passed; 0 failed;' "$EVIDENCE/$label.log" >/dev/null
        grep -F 'wait-entry checkpoint pid=' "$EVIDENCE/$label.log" >/dev/null
        grep -F 'nonterminal=true' "$EVIDENCE/$label.log" >/dev/null
        grep -F 'shared-child entered-wait pid=' "$EVIDENCE/$label.log" >/dev/null
        grep -F 'waiter_woke=true reap=ESRCH' "$EVIDENCE/$label.log" >/dev/null
    fi
}

mutate_red() {
    python3 - "$UNIX_SOURCE" <<'PY'
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
text = path.read_text()
old = 'entered_waits > 0,'
new = 'entered_waits == 0,\n            "X31 RED: wait-entry assertion sensitivity control",'
if text.count(old) != 1:
    raise SystemExit(f"expected one wait-entry assertion, found {text.count(old)}")
path.write_text(text.replace(old, new, 1))
PY
    shasum -a 256 "$UNIX_SOURCE" > "$EVIDENCE/red-mutated-source.sha256"
}

restore_source() {
    cp "$RUNTIME/unix.original.rs" "$UNIX_SOURCE"
    local actual
    actual=$(shasum -a 256 "$UNIX_SOURCE" | awk '{print $1}')
    [[ "$actual" == "$BASE_UNIX_SHA" ]] || {
        printf 'restored source hash mismatch: %s\n' "$actual" >&2
        return 1
    }
    printf '%s  restored src/packages/sys/process/unix.rs\n' "$actual" >> "$EVIDENCE/source-restoration.txt"
}

for row in sync sync-no-float; do
    if [[ "$row" == sync ]]; then
        features=testing-environ,sys,sync
    else
        features=testing-environ,sys,sync,no_float
    fi
    printf '%s=%s\n' "$row" "$features" >> "$EVIDENCE/features.txt"
    mutate_red
    run_case "red-$row" "$features" RED
    restore_source
    run_case "green-$row" "$features" GREEN
done

du -sk "$RUNTIME/target" "$RUNTIME/cargo-home" > "$EVIDENCE/private-output-size-before-cleanup.txt"
printf 'runtime_removed_by_runner=true\n' > "$EVIDENCE/runner-cleanup-expected.txt"
printf 'all_rows=accepted\nsource_restored=true\n' > "$EVIDENCE/attempt-result.txt"
