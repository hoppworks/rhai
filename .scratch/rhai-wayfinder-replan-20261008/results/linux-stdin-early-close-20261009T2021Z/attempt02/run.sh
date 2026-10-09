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
printf 'cwd=%s\n' "$PWD" > "$EVIDENCE/context.txt"
printf 'rustc=%s\ncargo=%s\n' "$("$RUSTC" --version)" "$(cargo --version)" >> "$EVIDENCE/context.txt"
shasum -a 256 Cargo.lock >> "$EVIDENCE/context.txt"
git apply --check "$EVIDENCE/owned.patch"
git apply "$EVIDENCE/owned.patch"
shasum -a 256 tests/sys_process.rs > "$EVIDENCE/test.diagnostic.sha256"
cargo metadata --locked --no-deps --format-version 1 > "$EVIDENCE/cargo-metadata.json" 2> "$EVIDENCE/cargo-metadata.stderr"
TARGET=run_io_contract_child_closing_stdin_early_still_returns_child_result
set +e
cargo test --locked --jobs 2 --features testing-environ,sys --test sys_process "$TARGET" -- --exact --nocapture > "$EVIDENCE/diagnostic.log" 2>&1
STATUS=$?
set -e
printf '%s\n' "$STATUS" > "$EVIDENCE/diagnostic.status"
printf 'diagnostic run complete; inspect exact SysError detail in diagnostic.log\n' > "$EVIDENCE/result.txt"
