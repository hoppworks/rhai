#!/usr/bin/env bash
set -uo pipefail
mkdir -p "$AGENT_RUNTIME_DIR/source"
cp -R /Users/hoppworks/projects/rhai-net-feature-proof/. "$AGENT_RUNTIME_DIR/source/"
cd "$AGENT_RUNTIME_DIR/source"
export CARGO_BUILD_JOBS=2 CARGO_PROFILE_DEV_DEBUG=0 CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home" CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
logs=/Users/hoppworks/projects/rhai-net-feature-proof/.scratch/net-feature-proof/logs
sample="$logs/final-storage-kib.txt"
rm -f "$sample"
(
  while :; do
    du -sk "$AGENT_RUNTIME_DIR/source" "$CARGO_HOME" "$CARGO_TARGET_DIR" 2>/dev/null | awk '{n += $1} END {print n+0}' >> "$sample"
    sleep 1
  done
) & sampler=$!
run() { label=$1; shift; "$@" > "$logs/$label.log" 2>&1; rc=$?; printf '%s\n' "$rc" > "$logs/$label.status"; printf '%s=%s\n' "$label" "$rc"; }
run noobj-final-compile cargo test --features net,no_object --no-run --test net_connect --test net_listen --test net_reads --test net_writes
run noobj-final-green cargo test --features net,no_object --test net_no_object -- --test-threads=1
RHAI_NET_NO_OBJECT_WRONG_PEER_EXPECTATION=1 run noobj-peer-wrong cargo test --features net,no_object --test net_no_object registered_stream_functions_work_without_dot_syntax -- --exact --nocapture
run f32-wrong-byte env RHAI_NET_WRONG_WRITE_EXPECTATION=1 cargo test --features net,f32_float --test net_writes script_write_blob_preserves_exact_bytes -- --exact --nocapture
run f32-correct-byte cargo test --features net,f32_float --test net_writes script_write_blob_preserves_exact_bytes -- --exact --nocapture
run only_i32-no_float-final cargo test --features net,only_i32,no_float --test net_connect --test net_listen --test net_reads --test net_writes -- --test-threads=1
run no_index-sync-metadata-final cargo test --features net,no_index,sync,metadata --test net_connect --test net_listen --test net_reads --test net_writes -- --test-threads=1
run f32_float-final cargo test --features net,f32_float --test net_connect --test net_listen --test net_reads --test net_writes -- --test-threads=1
kill "$sampler" 2>/dev/null || true
wait "$sampler" 2>/dev/null || true
