#!/usr/bin/env bash
set -euo pipefail
: "${AGENT_RUNTIME_DIR:?}"
checkout=/Users/hoppworks/projects/rhai-tcp-docs-example
proof="$checkout/.scratch/tcp-docs-example"
mkdir -p "$AGENT_RUNTIME_DIR/source"
git -C "$checkout" archive HEAD | tar -x -C "$AGENT_RUNTIME_DIR/source"
for path in Cargo.toml examples/net.rs tests/net_metadata.rs src/packages/net/mod.rs; do
 cp "$checkout/$path" "$AGENT_RUNTIME_DIR/source/$path"
done
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home" CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target" CARGO_BUILD_JOBS=2 CARGO_PROFILE_DEV_DEBUG=0
cd "$AGENT_RUNTIME_DIR/source"
printf '%s\n' "$AGENT_RUNTIME_DIR" > "$proof/runtime.txt"
{ uname -a; rustc --version --verbose; cargo --version; } > "$proof/environment.log"
owner_pid=$$
(
 while kill -0 "$owner_pid" 2>/dev/null; do
  usage=$(du -sk "$AGENT_RUNTIME_DIR" | awk '{print $1}')
  printf '%s\n' "$usage" >> "$proof/storage-kib.txt"
  if [ "$usage" -gt 2097152 ]; then kill -TERM "$owner_pid"; exit 1; fi
  sleep 1
 done
) & sampler=$!
trap 'kill "$sampler" 2>/dev/null || true; wait "$sampler" 2>/dev/null || true' EXIT
run() {
 label=$1; shift
 printf '%q ' "$@" > "$proof/$label.command"; printf '\n' >> "$proof/$label.command"
 code=0; "$@" > "$proof/$label.log" 2>&1 || code=$?
 printf '%s\n' "$code" > "$proof/$label.status"
 printf '%s: %s\n' "$label" "$code"
 return "$code"
}
python3 - <<'MUTATE'
from pathlib import Path
p=Path("examples/net.rs");s=p.read_text();assert s.count('b"ping"') == 1;p.write_text(s.replace('b"ping"','b"pang"'))
MUTATE
code=0; run wrong-peer cargo run --example net --features net,metadata || code=$?
[ "$code" -eq 101 ]
rg -q 'independent peer received the script bytes' "$proof/wrong-peer.log"
rg -q '112, 105, 110, 103' "$proof/wrong-peer.log"
cp "$checkout/examples/net.rs" examples/net.rs
run correct-peer cargo run --example net --features net,metadata
run metadata cargo test --features net,metadata --test net_metadata -- --nocapture
run no-object-peer cargo run --example net --features net,no_object,metadata
run no-object-metadata cargo test --features net,no_object,metadata --test net_metadata -- --nocapture
