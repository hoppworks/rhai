#!/usr/bin/env bash
set -euo pipefail
EVIDENCE=$1
: "${AGENT_RUNTIME_DIR:?runner must supply AGENT_RUNTIME_DIR}"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export PYTHONDONTWRITEBYTECODE=1
export CARGO_BUILD_JOBS=2
export CARGO_NET_GIT_FETCH_WITH_CLI=true
TOOLCHAIN=/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu
export RUSTC="$TOOLCHAIN/bin/rustc"
export RUSTDOC="$TOOLCHAIN/bin/rustdoc"
export PATH="$TOOLCHAIN/bin:$PATH"
mkdir "$AGENT_RUNTIME_DIR/source"
tar -xzf "$EVIDENCE/source.tar.gz" -C "$AGENT_RUNTIME_DIR/source"
cd "$AGENT_RUNTIME_DIR/source"
cp "$EVIDENCE/Cargo.lock.accepted" Cargo.lock
printf 'cwd=%s\nrustc=%s\ncargo=%s\n' "$PWD" "$("$RUSTC" --version)" "$(cargo --version)" > "$EVIDENCE/context.txt"
shasum -a 256 Cargo.lock >> "$EVIDENCE/context.txt"
git apply --check "$EVIDENCE/owned.patch"
git apply "$EVIDENCE/owned.patch"
cp tests/sys_process.rs "$EVIDENCE/test.correct.rs"
shasum -a 256 tests/sys_process.rs src/packages/sys/process/unix.rs > "$EVIDENCE/test.correct.sha256"
cargo metadata --locked --no-deps --format-version 1 > "$EVIDENCE/cargo-metadata.json" 2> "$EVIDENCE/cargo-metadata.stderr"
python3 - <<'PY'
from pathlib import Path
p=Path('tests/sys_process.rs'); text=p.read_text()
old='''    assert!(
        run_success && raw_success,
        "early child stdin closure must preserve successful results for run and run_raw"
    );'''
new='''    assert!(
        !(run_success && raw_success),
        "RED control: early child stdin closure must preserve successful results for run and run_raw"
    );'''
start=text.index('fn run_io_contract_run_and_run_raw_child_closing_stdin_early_still_return_result()')
end=text.index('\n#[test]',start)
section=text[start:end]
assert section.count(old)==1, section.count(old)
p.write_text(text[:start]+section.replace(old,new,1)+text[end:])
PY
TARGET=run_io_contract_run_and_run_raw_child_closing_stdin_early_still_return_result
shasum -a 256 tests/sys_process.rs > "$EVIDENCE/test.red.sha256"
set +e
cargo test --locked --jobs 2 --features testing-environ,sys --test sys_process "$TARGET" -- --exact --nocapture > "$EVIDENCE/red.log" 2>&1
RED_STATUS=$?
set -e
printf '%s\n' "$RED_STATUS" > "$EVIDENCE/red.status"
test "$RED_STATUS" -eq 101
grep -F 'RED control: early child stdin closure must preserve successful results for run and run_raw' "$EVIDENCE/red.log" >/dev/null
cp "$EVIDENCE/test.correct.rs" tests/sys_process.rs
cmp "$EVIDENCE/test.correct.rs" tests/sys_process.rs
shasum -a 256 tests/sys_process.rs > "$EVIDENCE/test.restored.sha256"
set +e
cargo test --locked --jobs 2 --features testing-environ,sys --test sys_process "$TARGET" -- --exact --nocapture > "$EVIDENCE/green.log" 2>&1
GREEN_STATUS=$?
set -e
printf '%s\n' "$GREEN_STATUS" > "$EVIDENCE/green.status"
test "$GREEN_STATUS" -eq 0
grep -F "test $TARGET ... ok" "$EVIDENCE/green.log" >/dev/null
grep -F 'api=run ' "$EVIDENCE/green.log" >/dev/null
grep -F 'api=run_raw ' "$EVIDENCE/green.log" >/dev/null
printf 'RED=101 after both child records and reaping readbacks; restored GREEN=0 for run and run_raw\n' > "$EVIDENCE/result.txt"
