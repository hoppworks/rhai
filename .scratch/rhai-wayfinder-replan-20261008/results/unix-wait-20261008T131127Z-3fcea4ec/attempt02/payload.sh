#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_BUILD_JOBS=2
python3 "$1/verify-wait.py" "$1"
