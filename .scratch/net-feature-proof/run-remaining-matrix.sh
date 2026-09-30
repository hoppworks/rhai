#!/usr/bin/env bash
set -uo pipefail
mkdir -p "$AGENT_RUNTIME_DIR/source"
cp -R /Users/hoppworks/projects/rhai-net-feature-proof/. "$AGENT_RUNTIME_DIR/source/"
cd "$AGENT_RUNTIME_DIR/source"
export CARGO_BUILD_JOBS=2 CARGO_PROFILE_DEV_DEBUG=0
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home" CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
log_root=/Users/hoppworks/projects/rhai-net-feature-proof/.scratch/net-feature-proof/logs
sample_file="$log_root/remaining-matrix-storage-kib.txt"
(
  while :; do
    total=$(du -sk "$AGENT_RUNTIME_DIR/source" "$CARGO_HOME" "$CARGO_TARGET_DIR" 2>/dev/null | awk '{n += $1} END {print n+0}')
    printf '%s\n' "$total" >> "$sample_file"
    sleep 1
  done
) &
sampler=$!
run_combo() {
  feature_set=$1
  label=$2
  cargo test --features "$feature_set" --test net_connect --test net_listen --test net_reads --test net_writes -- --test-threads=1 > "$log_root/$label.log" 2>&1
  result=$?
  printf '%s\n' "$result" > "$log_root/$label.status"
  printf '%s: %s\n' "$label" "$result"
}
run_combo 'net,only_i32,no_float' only_i32-no_float
run_combo 'net,no_index,sync,metadata' no_index-sync-metadata
run_combo 'net,f32_float' f32_float
kill "$sampler" 2>/dev/null || true
wait "$sampler" 2>/dev/null || true
