#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_BUILD_JOBS=2
TC=/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu
export RUSTC="$TC/bin/rustc"
export RUSTDOC="$TC/bin/rustdoc"
export RHAI_CARGO="$TC/bin/cargo"
export PATH="$TC/bin:$PATH"
unset RUSTFLAGS CARGO_ENCODED_RUSTFLAGS RUSTC_WRAPPER RUSTC_WORKSPACE_WRAPPER
/usr/bin/python3 "$1/verify-wait.py" "$1"
