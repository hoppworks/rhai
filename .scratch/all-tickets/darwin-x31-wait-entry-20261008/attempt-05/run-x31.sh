#!/usr/bin/env bash
set -euo pipefail

REPO=/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery
EVIDENCE="$REPO/.scratch/all-tickets/darwin-x31-wait-entry-20261008/attempt-05"
RUNTIME="${AGENT_RUNTIME_DIR:?run_scoped must provide private runtime}"
STAGE="$RUNTIME/source"
LOCK="$REPO/.scratch/all-tickets/darwin-x31-wait-entry-20261008/attempt-05/Cargo.lock.accepted"
SOURCE_COMMIT=05320c2c9bf3d4396956632e0cc1706e96c94b15
UNIX_SOURCE="$STAGE/src/packages/sys/process/unix.rs"
TEST=packages::sys::process::unix::tests::public_wait_is_cancelled_after_entering_condvar
BASE_UNIX_SHA=55dc5ad528ad2b4fd56d3fcdd42f92af0b30bf3f96db37c476ee31320dcba713
LOCK_SHA=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425

mkdir -p "$STAGE" "$RUNTIME/cargo-home" "$RUNTIME/target"
git -C "$REPO" archive --format=tar "$SOURCE_COMMIT" | tar -xf - -C "$STAGE"
cp "$LOCK" "$STAGE/Cargo.lock"
cp "$UNIX_SOURCE" "$RUNTIME/unix.original.rs"

{
    printf 'source_commit=%s\n' "$SOURCE_COMMIT"
    printf 'staged_source=%s\n' "$STAGE"
    printf 'cargo_lock_source=%s\n' "$LOCK"
    printf 'cargo_test_name=%s\n' "$TEST"
    printf 'cargo_command=cargo +1.77.2 test --locked --lib --features <features> %s -- --exact --nocapture --test-threads=1\n' "$TEST"
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
    rustc +1.77.2 --version --verbose
    cargo +1.77.2 --version
    printf 'pre_stage_cwd=%s\n' "$PWD"
    printf 'CARGO_BUILD_TARGET=%s\n' "${CARGO_BUILD_TARGET-<unset>}"
    printf 'RUSTFLAGS=%s\n' "${RUSTFLAGS-<unset>}"
    printf 'CARGO_ENCODED_RUSTFLAGS=%s\n' "${CARGO_ENCODED_RUSTFLAGS-<unset>}"
    printf 'RUSTC_BOOTSTRAP=%s\n' "${RUSTC_BOOTSTRAP-<unset>}"
} > "$EVIDENCE/environment.txt" 2>&1
grep -F 'host: aarch64-apple-darwin' "$EVIDENCE/environment.txt" >/dev/null
[[ -z "${CARGO_BUILD_TARGET:-}" ]] || { echo 'foreign CARGO_BUILD_TARGET is set' >&2; exit 2; }
[[ -z "${RUSTFLAGS:-}" && -z "${CARGO_ENCODED_RUSTFLAGS:-}" && -z "${RUSTC_BOOTSTRAP:-}" ]] || {
    echo 'foreign target, flags, or bootstrap override is set' >&2
    exit 2
}
[[ -z "${RUSTC_WRAPPER:-}" && -z "${CARGO_BUILD_RUSTC_WRAPPER:-}" ]] || {
    echo 'external rustc wrapper is set' >&2
    exit 2
}
[[ ! -e "$STAGE/.cargo/config" && ! -e "$STAGE/.cargo/config.toml" ]] || {
    echo 'project Cargo config unexpectedly present in frozen archive' >&2
    exit 2
}

export CARGO_HOME="$RUNTIME/cargo-home"
export CARGO_TARGET_DIR="$RUNTIME/target"
export CARGO_BUILD_JOBS=1
export CARGO_TERM_COLOR=never
export PYTHONDONTWRITEBYTECODE=1

cd "$STAGE"
printf 'actual_cwd=%s\n' "$PWD" > "$EVIDENCE/working-directory.txt"
printf '%s\n' 'cargo_metadata_preflight=omitted_by_review' > "$EVIDENCE/cargo-metadata.status"

run_case() {
    local label="$1" features="$2" expected="$3" status=0
    SECONDS=0
    if cargo +1.77.2 test --locked --lib --features "$features" "$TEST" -- --exact --nocapture --test-threads=1 > "$EVIDENCE/$label.log" 2>&1; then
        status=0
    else
        status=$?
    fi
    printf '%s\n' "$status" > "$EVIDENCE/$label.status"
    printf '%s_seconds=%s\n' "$label" "$SECONDS" >> "$EVIDENCE/durations.txt"

    grep -F "$TEST" "$EVIDENCE/$label.log" >/dev/null || {
        printf '%s did not report test id %s\n' "$label" "$TEST" >&2
        return 1
    }
    if [[ "$expected" == RED ]]; then
        [[ "$status" == 101 ]] || { echo "$label expected Cargo 101, got $status" >&2; return 1; }
        grep -F 'test result: FAILED. 0 passed; 1 failed;' "$EVIDENCE/$label.log" >/dev/null || {
            echo "$label missing failed-test result summary" >&2
            return 1
        }
        grep -F 'X31 RED: wait-entry assertion sensitivity control' "$EVIDENCE/$label.log" >/dev/null || {
            echo "$label missing intended assertion marker" >&2
            return 1
        }
        grep -F 'wait-entry checkpoint pid=' "$EVIDENCE/$label.log" >/dev/null || return 1
        grep -F 'nonterminal=true' "$EVIDENCE/$label.log" >/dev/null || return 1
        grep -F 'wait-entry fixture cleanup pid=' "$EVIDENCE/$label.log" >/dev/null || return 1
        grep -F 'reap=ESRCH' "$EVIDENCE/$label.log" >/dev/null || return 1
    else
        [[ "$status" == 0 ]] || { echo "$label expected Cargo 0, got $status" >&2; return 1; }
        grep -F 'test result: ok. 1 passed; 0 failed;' "$EVIDENCE/$label.log" >/dev/null || return 1
        grep -F 'wait-entry checkpoint pid=' "$EVIDENCE/$label.log" >/dev/null || return 1
        grep -F 'nonterminal=true' "$EVIDENCE/$label.log" >/dev/null || return 1
        grep -F 'shared-child entered-wait pid=' "$EVIDENCE/$label.log" >/dev/null || return 1
        grep -F 'waiter_woke=true reap=ESRCH' "$EVIDENCE/$label.log" >/dev/null || return 1
    fi
}

mutate_red() {
    python3 - "$UNIX_SOURCE" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text()
old = "        assert!(\n            entered_waits > 0,\n            \"observer acquired snapshot mutex after Condvar wait entry\"\n        );"
new = "        assert!(\n            entered_waits == 0,\n            \"X31 RED: wait-entry assertion sensitivity control\"\n        );"
if text.count(old) != 1:
    raise SystemExit(f"expected one complete wait-entry assertion, found {text.count(old)}")
path.write_text(text.replace(old, new, 1))
PY
    shasum -a 256 "$UNIX_SOURCE" > "$EVIDENCE/red-mutated-source.sha256"
    if diff -u "$RUNTIME/unix.original.rs" "$UNIX_SOURCE" > "$EVIDENCE/red-mutation.diff"; then
        echo 'mutation unexpectedly made no source change' >&2
        return 1
    else
        diff_status=$?
        [[ "$diff_status" == 1 ]] || return "$diff_status"
    fi
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
printf 'all_rows=accepted\nsource_restored=true\n' > "$EVIDENCE/attempt-result.txt"
