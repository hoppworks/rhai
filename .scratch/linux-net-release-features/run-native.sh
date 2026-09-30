#!/usr/bin/env bash
set -euo pipefail

: "${AGENT_RUNTIME_DIR:?must run under run_scoped.py}"
: "${PROOF_STAGE:?exact fresh owned stage required}"
: "${SOURCE_REVISION:?source revision required}"

mkdir -p "$AGENT_RUNTIME_DIR/source" "$AGENT_RUNTIME_DIR/cargo-home" "$AGENT_RUNTIME_DIR/target" "$AGENT_RUNTIME_DIR/evidence"
mkdir -p "$PROOF_STAGE/evidence"
tar -xzf "$PROOF_STAGE/source.tar.gz" -C "$AGENT_RUNTIME_DIR/source"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_INCREMENTAL=0
export CARGO_PROFILE_DEV_DEBUG=0
export CARGO_PROFILE_TEST_DEBUG=0
export CARGO_BUILD_JOBS=2
export PROOF_LOG="$AGENT_RUNTIME_DIR/evidence/native-linux-net-release.log"
export PROOF_STATUS="$AGENT_RUNTIME_DIR/evidence/status.tsv"

python3 "$PROOF_STAGE/verify.py" "$AGENT_RUNTIME_DIR/source" "$AGENT_RUNTIME_DIR" "$SOURCE_REVISION" "$PROOF_STAGE"
cp "$PROOF_LOG" "$PROOF_STAGE/evidence/native-linux-net-release.log"
cp "$PROOF_STATUS" "$PROOF_STAGE/evidence/status.tsv"
