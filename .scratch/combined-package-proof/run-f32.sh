#!/usr/bin/env bash
set -u
: "${AGENT_RUNTIME_DIR:?run via tools/run_scoped.py}"
repo=$(git rev-parse --show-toplevel)
revision=$(git rev-parse HEAD)
evidence="$repo/.scratch/combined-package-proof"
source="$AGENT_RUNTIME_DIR/source"
mkdir -p "$source" "$evidence/logs"
( while :; do printf "%s %s KiB\n" "$(date -u +%FT%TZ)" "$(du -sk "$AGENT_RUNTIME_DIR" 2>/dev/null | cut -f1)" >> "$evidence/logs/f32-storage-samples.txt"; sleep 5; done ) &
sampler=$!
trap 'kill "$sampler" 2>/dev/null || true; wait "$sampler" 2>/dev/null || true' EXIT
git archive "$revision" | tar -x -C "$source"
mkdir -p "$source/tests"
cp "$repo/tests/combined_sys_net.rs" "$source/tests/combined_sys_net.rs"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_BUILD_JOBS=2
export CARGO_PROFILE_DEV_DEBUG=0
cd "$source"
features=testing-environ,sys,net,f32_float
command=(cargo test --features "$features" --test combined_sys_net --test sys_env --test sys_fs --test sys_policy --test net_connect --test net_listen --test net_reads --test net_writes -- --test-threads=1 --nocapture)
printf 'Source revision: %s + tests/combined_sys_net.rs from worktree\n' "$revision" > "$evidence/logs/f32-environment.txt"
uname -a >> "$evidence/logs/f32-environment.txt"
sw_vers >> "$evidence/logs/f32-environment.txt"
rustc --version >> "$evidence/logs/f32-environment.txt"
cargo --version >> "$evidence/logs/f32-environment.txt"
printf 'Runtime: %s; private Cargo home/target; jobs=2\nFeatures: %s\nCommand: ' "$AGENT_RUNTIME_DIR" "$features" >> "$evidence/logs/f32-environment.txt"
printf '%q ' "${command[@]}" >> "$evidence/logs/f32-environment.txt"
printf '\n' >> "$evidence/logs/f32-environment.txt"
status=0
"${command[@]}" > "$evidence/logs/f32_float.log" 2>&1 || status=$?
printf 'exit_status=%s\n' "$status" >> "$evidence/logs/f32-environment.txt"
cat "$evidence/logs/f32_float.log"
exit "$status"
