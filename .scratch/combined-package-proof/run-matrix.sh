#!/usr/bin/env bash
set -euo pipefail
: "${AGENT_RUNTIME_DIR:?run via tools/run_scoped.py}"
repo=$(git rev-parse --show-toplevel)
revision=$(git rev-parse HEAD)
evidence="$repo/.scratch/combined-package-proof"
source="$AGENT_RUNTIME_DIR/source"
mkdir -p "$source" "$evidence/logs"
( while :; do printf "%s %s KiB\n" "$(date -u +%FT%TZ)" "$(du -sk "$AGENT_RUNTIME_DIR" 2>/dev/null | cut -f1)" >> "$evidence/logs/storage-samples.txt"; sleep 10; done ) &
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
{
  printf 'Source revision: %s + tests/combined_sys_net.rs from worktree\n' "$revision"
  uname -a
  sw_vers
  rustc --version
  cargo --version
  printf 'Scoped runtime: %s\n' "$AGENT_RUNTIME_DIR"
  printf '%s\n' 'Private CARGO_HOME and CARGO_TARGET_DIR; CARGO_BUILD_JOBS=2; serial test execution.'
} | tee "$evidence/logs/environment.txt"
base=testing-environ,sys,net
control_log="$evidence/logs/false-green-control.log"
control_status=0
printf 'Control command: RHAI_COMBINED_WRONG_EXPECTATION=1 cargo test --features %q --test combined_sys_net -- --exact sys_and_net_packages_coexist_in_one_engine_with_os_readback_and_typed_errors --test-threads=1 --nocapture\n' "$base" | tee "$control_log"
RHAI_COMBINED_WRONG_EXPECTATION=1 cargo test --features "$base" --test combined_sys_net -- --exact sys_and_net_packages_coexist_in_one_engine_with_os_readback_and_typed_errors --test-threads=1 --nocapture >> "$control_log" 2>&1 || control_status=$?
printf 'Control exit status: %s\n' "$control_status" | tee -a "$control_log"
cat "$control_log"
if [[ "$control_status" -eq 0 ]]; then
  printf 'false-green control unexpectedly passed\n' >&2
  exit 40
fi
if ! rg -q 'fresh host readback must match independent expected bytes' "$control_log"; then
  printf 'false-green control failed before its intended independent readback assertion\n' >&2
  exit 41
fi
printf '%s\n' 'Control accepted: the deliberately incorrect independent filesystem readback expectation failed.' | tee -a "$control_log"
features=(
  'testing-environ,sys,net'
  'testing-environ,sys,net,sync'
  'testing-environ,sys,net,no_index'
  'testing-environ,sys,net,metadata,serde'
  'testing-environ,sys,net,only_i32,no_float'
  'testing-environ,sys,net,unchecked'
  'testing-environ,sys,net,no_index,sync,metadata'
  'testing-environ,sys,net,f32_float'
)
targets=(combined_sys_net sys_env sys_fs sys_policy net_connect net_listen net_reads net_writes)
: > "$evidence/logs/matrix-status.txt"
for index in "${!features[@]}"; do
  label=$(printf 'row-%02d' "$((index + 1))")
  log="$evidence/logs/$label.log"
  feature_set=${features[$index]}
  command=(cargo test --features "$feature_set")
  for target in "${targets[@]}"; do command+=(--test "$target"); done
  command+=(-- --test-threads=1 --nocapture)
  printf '%s features=%s command=' "$label" "$feature_set" | tee -a "$evidence/logs/matrix-status.txt"
  printf '%q ' "${command[@]}" | tee -a "$evidence/logs/matrix-status.txt"
  printf '\n' | tee -a "$evidence/logs/matrix-status.txt"
  status=0
  "${command[@]}" > "$log" 2>&1 || status=$?
  printf 'exit_status=%s\n' "$status" | tee -a "$evidence/logs/matrix-status.txt"
  cat "$log"
done
