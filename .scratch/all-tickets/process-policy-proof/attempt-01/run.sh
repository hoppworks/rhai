#!/usr/bin/env bash
set -Eeuo pipefail
: "${AGENT_RUNTIME_DIR:?}"
: "${SESSION_SCOPE:?}"

SOURCE="$AGENT_RUNTIME_DIR/source"
mkdir -p "$SOURCE" "$AGENT_RUNTIME_DIR/cargo-home" "$AGENT_RUNTIME_DIR/target"
cp -a "$SESSION_SCOPE/source/." "$SOURCE/"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_BUILD_JOBS=2
export PYTHONDONTWRITEBYTECODE=1
cd "$SOURCE"

cp tests/sys_process.rs "$SESSION_SCOPE/sys_process.rs.accepted"
python3 - "$SOURCE/tests/sys_process.rs" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
source = path.read_text()
old = 'let default_engine = engine(SysConfig::default());'
new = 'let default_engine = engine(SysConfig::default().programs(ProgramPolicy::AllowList(vec![executable_value.clone()])));'
if source.count(old) != 1:
    raise SystemExit(f"expected exactly one mutation point, found {source.count(old)}")
path.write_text(source.replace(old, new, 1))
PY

printf '%s\n' 'cargo test --locked --features testing-environ,sys --test sys_process default_and_nonmatching_process_policies_deny_public_run_without_starting_child -- --exact --nocapture --test-threads=1' > "$SESSION_SCOPE/command.txt"
rustc --version > "$SESSION_SCOPE/rustc-version.txt"
cargo --version > "$SESSION_SCOPE/cargo-version.txt"
uname -a > "$SESSION_SCOPE/uname.txt"
cargo metadata --locked --offline --no-deps --format-version 1 > "$SESSION_SCOPE/metadata.json"

set +e
cargo test --locked --features testing-environ,sys --test sys_process default_and_nonmatching_process_policies_deny_public_run_without_starting_child -- --exact --nocapture --test-threads=1 > "$SESSION_SCOPE/red.stdout" 2> "$SESSION_SCOPE/red.stderr"
red_status=$?
set -e
printf '%s\n' "$red_status" > "$SESSION_SCOPE/red.exit"
if [[ "$red_status" -eq 0 ]]; then
    echo 'broken-policy control unexpectedly passed' >&2
    exit 20
fi
if ! (grep -Fq 'script should fail with a SysError' "$SESSION_SCOPE/red.stdout" || grep -Fq 'script should fail with a SysError' "$SESSION_SCOPE/red.stderr"); then
    echo 'broken-policy control failed before the expected policy assertion' >&2
    exit 21
fi

cp "$SESSION_SCOPE/sys_process.rs.accepted" tests/sys_process.rs
set +e
cargo test --locked --features testing-environ,sys --test sys_process default_and_nonmatching_process_policies_deny_public_run_without_starting_child -- --exact --nocapture --test-threads=1 > "$SESSION_SCOPE/green.stdout" 2> "$SESSION_SCOPE/green.stderr"
green_status=$?
set -e
printf '%s\n' "$green_status" > "$SESSION_SCOPE/green.exit"
if [[ "$green_status" -ne 0 ]]; then
    echo 'restored focused process-policy test failed' >&2
    exit 22
fi
if ! (grep -Fq 'test result: ok. 1 passed; 0 failed' "$SESSION_SCOPE/green.stdout" || grep -Fq 'test result: ok. 1 passed; 0 failed' "$SESSION_SCOPE/green.stderr"); then
    echo 'focused test did not report its expected one-test green result' >&2
    exit 23
fi

sha256sum Cargo.lock tests/sys_process.rs > "$SESSION_SCOPE/green-source.sha256"
printf '%s\n' 'broken-policy control: expected failure at sys_support::sys_err expect_err' > "$SESSION_SCOPE/result.txt"
printf '%s\n' 'restored test: passed; assertions verify both denied markers absent, exact allow-list child record read, and direct child reaped (ESRCH)' >> "$SESSION_SCOPE/result.txt"
