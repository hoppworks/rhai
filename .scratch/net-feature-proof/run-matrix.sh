#!/bin/bash
set -euo pipefail
ROOT=/Users/hoppworks/projects/rhai-net-feature-proof
OUT="$ROOT/.scratch/net-feature-proof"
mkdir -p "$OUT/logs"
cd "$AGENT_RUNTIME_DIR/source"
export CARGO_BUILD_JOBS=2
export CARGO_PROFILE_DEV_DEBUG=0
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
mkdir -p "$CARGO_HOME" "$CARGO_TARGET_DIR"
# Sample target-tree size once per second and stop this runner if its owned Cargo output exceeds 2 GiB.
watch_disk() {
  while :; do
    size=$(du -sk "$CARGO_TARGET_DIR" | awk '{print $1}')
    printf '%s %s\n' "$(date -u '+%H:%M:%S')" "$size" >> "$OUT/logs/target-size.tsv"
    if [ "$size" -gt 2097152 ]; then
      echo "private target exceeded 2 GiB: ${size} KiB" >&2
      kill -TERM -- -$$
      exit 97
    fi
    sleep 1
  done
}
watch_disk &
watch_pid=$!
trap 'kill "$watch_pid" 2>/dev/null || true; wait "$watch_pid" 2>/dev/null || true' EXIT
run_target_set() {
  label=$1
  features=$2
  shift 2
  echo "=== $label features=$features ==="
  cargo test --features "$features" "$@" 2>&1 | tee "$OUT/logs/$label.log"
}
run_target_set no-object 'net,no_object' --test net_connect --test net_listen --test net_reads --test net_writes
run_target_set only-i32 'net,only_i32,no_float' --test net_connect --test net_listen --test net_reads --test net_writes
run_target_set no-index-sync-metadata 'net,no_index,sync,metadata' --test net_connect --test net_listen --test net_reads --test net_writes
# Required false-green control on an independently observed byte assertion.
set +e
RHAI_NET_WRONG_WRITE_EXPECTATION=1 cargo test --features 'net,f32_float' --test net_writes script_write_blob_preserves_exact_bytes -- --exact --nocapture > "$OUT/logs/f32-wrong-byte-control.log" 2>&1
control_status=$?
set -e
cat "$OUT/logs/f32-wrong-byte-control.log"
printf '%s\n' "$control_status" > "$OUT/logs/f32-wrong-byte-control.status"
if [ "$control_status" -eq 0 ]; then
  echo 'wrong-byte control unexpectedly passed' >&2
  exit 98
fi
rg -q 'assertion `left == right` failed|assertion failed' "$OUT/logs/f32-wrong-byte-control.log"
run_target_set f32-float 'net,f32_float' --test net_connect --test net_listen --test net_reads --test net_writes
