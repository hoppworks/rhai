#!/bin/sh
set -eu
prototype=/Users/hoppworks/projects/rhai-process-prototype/.scratch/process-prototype
cp -R "$prototype" "$AGENT_RUNTIME_DIR/source"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
mkdir -p "$CARGO_HOME"
rustc --version
cargo --version
uname -a
cargo build --manifest-path "$AGENT_RUNTIME_DIR/source/Cargo.toml"
bin="$CARGO_TARGET_DIR/debug/process-prototype"
"$bin" 2>&1 | tee "$prototype/evidence/native-macos.log"
if "$bin" --wrong-assertion > "$AGENT_RUNTIME_DIR/wrong.out" 2>&1; then
  echo 'wrong assertion unexpectedly passed' >&2
  exit 1
fi
cat "$AGENT_RUNTIME_DIR/wrong.out"
cp "$AGENT_RUNTIME_DIR/wrong.out" "$prototype/evidence/wrong-assertion.log"
