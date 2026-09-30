#!/usr/bin/env bash
set -euo pipefail

: "${AGENT_RUNTIME_DIR:?run via run_scoped.py}"
: "${PROOF_STAGE:?exact owned staging path required}"
: "${SOURCE_REVISION:?source revision required}"

log="$PROOF_STAGE/evidence/sys-fs-policy.log"
mkdir -p "$AGENT_RUNTIME_DIR/source" "$AGENT_RUNTIME_DIR/cargo-home" "$AGENT_RUNTIME_DIR/target"
tar -xf "$PROOF_STAGE/source.tar" -C "$AGENT_RUNTIME_DIR/source"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
source="$AGENT_RUNTIME_DIR/source"

{
    printf 'Source revision: %s\n' "$SOURCE_REVISION"
    printf 'Source archive SHA256: '
    sha256sum "$PROOF_STAGE/source.tar"
    printf 'Runtime directory: %s\n' "$AGENT_RUNTIME_DIR"
    uname -a
    cat /etc/os-release
    rustc --version --verbose
    cargo --version --verbose
    printf '%s\n' 'Command: cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_fs -- --nocapture'
} > "$log"

cd "$source"
status=0
cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_fs -- --nocapture >> "$log" 2>&1 || status=$?
printf '\nSys filesystem/policy exit status: %s\n' "$status" >> "$log"
cat "$log"
exit "$status"
