#!/usr/bin/env bash
set -euo pipefail
: "${AGENT_RUNTIME_DIR:?run via tools/run_scoped.py}"
repo=$(git rev-parse --show-toplevel)
revision=$(git rev-parse HEAD)
evidence="$repo/.scratch/all-tickets/combined-sys.log"
mkdir -p "$AGENT_RUNTIME_DIR/source"
git archive "$revision" | tar -x -C "$AGENT_RUNTIME_DIR/source"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
log="$AGENT_RUNTIME_DIR/combined-sys.log"
{
    printf 'Source revision: %s\n' "$revision"
    uname -a
    sw_vers
    rustc --version
    cargo --version
    printf '%s\n' 'Command: cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_env --test sys_fs -- --nocapture'
} > "$log"
cd "$AGENT_RUNTIME_DIR/source"
status=0
cargo test --features testing-environ,sys,metadata --test sys_policy --test sys_env --test sys_fs -- --nocapture >> "$log" 2>&1 || status=$?
printf '\nCargo exit status: %s\n' "$status" >> "$log"
cp "$log" "$evidence"
cat "$log"
exit "$status"
