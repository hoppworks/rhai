#!/bin/bash
set -Eeuo pipefail
scope=/home/workhorse/.local/share/agent-builds/rhai/api-metadata-20261007-workhorse-root1
source_dir="$AGENT_RUNTIME_DIR/source"
toolchain=/home/workhorse/.rustup/toolchains/1.93.0-x86_64-unknown-linux-gnu/bin
mkdir -p "$source_dir"
tar --warning=no-unknown-keyword -xzf "$scope/source.tar.gz" -C "$source_dir"
export PATH="$toolchain:$PATH"
export RUSTC="$toolchain/rustc"
export RUSTDOC="$toolchain/rustdoc"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_BUILD_JOBS=2
export CARGO_INCREMENTAL=0
cd "$source_dir"
cargo generate-lockfile > "$scope/resolve.log" 2>&1
cp Cargo.lock "$scope/Cargo.lock"
sha256sum Cargo.lock > "$scope/lock.sha256"
printf 'SOURCE_TAR_SHA256='; sha256sum "$scope/source.tar.gz" | cut -d' ' -f1
printf 'LOCK_SHA256='; cut -d' ' -f1 "$scope/lock.sha256"
printf 'RUSTC='; "$RUSTC" --version
set +e
cargo test --locked --features testing-environ,sys,net,metadata --test net_metadata --test sys_policy metadata -- --nocapture --test-threads=1 2>&1 | tee "$scope/native-red.log"
status=${PIPESTATUS[0]}
set -e
printf '%s\n' "$status" > "$scope/native-red.status"
printf 'CARGO_TEST_STATUS=%s\n' "$status"
if [ "$status" -eq 0 ]; then
  echo UNEXPECTED_GREEN
  exit 4
fi
if grep -Eq 'metadata comments are empty|metadata should explain|every .* metadata entry should mention' "$scope/native-red.log"; then
  echo EXPECTED_TDD_RED
  exit 0
fi
echo NON_ASSERTION_FAILURE
exit 5
