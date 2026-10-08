#!/usr/bin/env bash
set -euo pipefail
EVIDENCE=$1
: "${AGENT_RUNTIME_DIR:?owned runtime required}"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=2
export CARGO_TERM_COLOR=never
export PYTHONDONTWRITEBYTECODE=1
python3 "$EVIDENCE/verify-example.py" "$EVIDENCE"
