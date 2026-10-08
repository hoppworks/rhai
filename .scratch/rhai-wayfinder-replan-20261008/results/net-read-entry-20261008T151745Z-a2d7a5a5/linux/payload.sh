#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_BUILD_JOBS=2
export RHAI_CARGO=/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin/cargo
export RUSTC=/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin/rustc
export RUSTDOC=/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin/rustdoc
unset RUSTFLAGS CARGO_ENCODED_RUSTFLAGS RUSTC_WRAPPER RUSTC_WORKSPACE_WRAPPER
python3 "$1/verify.py" "$1"
