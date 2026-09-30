#!/usr/bin/env bash
set -euo pipefail

: "${AGENT_RUNTIME_DIR:?run via remote run_scoped.py}"
: "${PROOF_STAGE:?exact owned staging path required}"
: "${SOURCE_REVISION:?source revision required}"

evidence="$PROOF_STAGE/evidence"
log="$evidence/native-linux-tcp.log"
status="$evidence/status.tsv"
mkdir -p "$AGENT_RUNTIME_DIR/source" "$AGENT_RUNTIME_DIR/cargo-home" "$AGENT_RUNTIME_DIR/target" "$evidence"
tar -xzf "$PROOF_STAGE/source.tar.gz" -C "$AGENT_RUNTIME_DIR/source"
source="$AGENT_RUNTIME_DIR/source"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_INCREMENTAL=0

{
    printf 'Source revision: %s\n' "$SOURCE_REVISION"
    printf 'Source archive SHA256: '
    sha256sum "$PROOF_STAGE/source.tar.gz"
    printf 'Runtime directory: %s\n' "$AGENT_RUNTIME_DIR"
    printf 'Runtime owner launcher PID: %s\n' "$PPID"
    uname -a
    cat /etc/os-release
    rustc --version --verbose
    cargo --version --verbose
    printf '\nFile descriptor limit: '
    ulimit -n
    printf '\nDisk before extraction/build:\n'
    df -Pk "$PROOF_STAGE" "$AGENT_RUNTIME_DIR"
    printf '\nCommands use --jobs 2 and --test-threads=1. Targets run one at a time.\n'
} > "$log"
: > "$status"

cd "$source"
max_sockets=0
max_disk_bytes=0

run_measured() {
    local label="$1" output="$AGENT_RUNTIME_DIR/$1.out" metrics="$AGENT_RUNTIME_DIR/$1.metrics" command_status=0
    shift
    "$@" > "$output" 2>&1 &
    local command_pid=$!
    python3 "$PROOF_STAGE/sample-owned-resources.py" "$command_pid" "$AGENT_RUNTIME_DIR" "$metrics" &
    local monitor_pid=$!
    wait "$command_pid" || command_status=$?
    wait "$monitor_pid"
    cat "$output" >> "$log"
    cat "$metrics" >> "$log"
    local sampled_sockets sampled_disk
    sampled_sockets="$(awk -F= '/^sampled_socket_fd_max=/{print $2}' "$metrics")"
    sampled_disk="$(awk -F= '/^sampled_private_disk_max_bytes=/{print $2}' "$metrics")"
    [ "$sampled_sockets" -gt "$max_sockets" ] && max_sockets="$sampled_sockets" || true
    [ "$sampled_disk" -gt "$max_disk_bytes" ] && max_disk_bytes="$sampled_disk" || true
    return "$command_status"
}

run_measured lockfile cargo generate-lockfile
printf '\nGenerated Cargo.lock SHA256: ' >> "$log"
sha256sum Cargo.lock >> "$log"

record_case() {
    local features="$1" target="$2" status_code=0
    printf '\n===== features=%s target=%s =====\n' "$features" "$target" | tee -a "$log"
    printf 'Command: cargo test --locked --jobs 2 --features %q --test %q -- --test-threads=1 --nocapture\n' "$features" "$target" | tee -a "$log"
    run_measured "${features//,/_}-$target" cargo test --locked --jobs 2 --features "$features" --test "$target" -- --test-threads=1 --nocapture || status_code=$?
    printf 'EXIT features=%s target=%s status=%d\n' "$features" "$target" "$status_code" | tee -a "$log" "$status"
    printf 'Disk after %s/%s: ' "$features" "$target" >> "$log"
    df -Pk "$AGENT_RUNTIME_DIR" | tail -n 1 >> "$log"
    du -sk "$AGENT_RUNTIME_DIR" >> "$log"
}

targets=(net_connect net_listen net_reads net_writes)
for features in net net,sync net,no_index; do
    for target in "${targets[@]}"; do
        record_case "$features" "$target"
    done
done

control_status=0
printf '\n===== wrong independent peer-byte expectation =====\n' | tee -a "$log"
printf 'Command: RHAI_NET_WRONG_WRITE_EXPECTATION=1 cargo test --locked --jobs 2 --features net --test net_writes script_write_blob_preserves_exact_bytes -- --exact --test-threads=1 --nocapture\n' | tee -a "$log"
run_measured wrong-peer-byte-control env RHAI_NET_WRONG_WRITE_EXPECTATION=1 cargo test --locked --jobs 2 --features net --test net_writes script_write_blob_preserves_exact_bytes -- --exact --test-threads=1 --nocapture || control_status=$?
printf 'EXIT wrong_peer_byte_control=%d\n' "$control_status" | tee -a "$log" "$status"
if [ "$control_status" -ne 101 ] \
    || ! grep -Fq 'left: [0, 255, 65]' "$AGENT_RUNTIME_DIR/wrong-peer-byte-control.out" \
    || ! grep -Fq 'right: [0, 254, 65]' "$AGENT_RUNTIME_DIR/wrong-peer-byte-control.out" \
    || ! grep -Fq "thread 'script_write_blob_preserves_exact_bytes'" "$AGENT_RUNTIME_DIR/wrong-peer-byte-control.out" \
    || ! grep -Fxq 'FAILED' "$AGENT_RUNTIME_DIR/wrong-peer-byte-control.out"; then
    printf 'Wrong peer-byte control did not fail at the expected actual-peer assertion.\n' | tee -a "$log"
    exit 1
fi

restore_status=0
printf '\n===== restored correct independent peer-byte expectation =====\n' | tee -a "$log"
run_measured restored-peer-byte-assertion cargo test --locked --jobs 2 --features net --test net_writes script_write_blob_preserves_exact_bytes -- --exact --test-threads=1 --nocapture || restore_status=$?
printf 'EXIT restored_peer_byte_assertion=%d\n' "$restore_status" | tee -a "$log" "$status"

{
    printf '\nFinal Cargo.lock SHA256: '
    sha256sum Cargo.lock
    printf '\nSampled maxima across invocations: socket_fds=%s private_disk_bytes=%s\n' "$max_sockets" "$max_disk_bytes"
    printf '\nDisk at end:\n'
    df -Pk "$AGENT_RUNTIME_DIR"
    du -sk "$AGENT_RUNTIME_DIR"
    printf '\nFinal source snapshot:\n'
    git -C "$source" status --short 2>/dev/null || true
} >> "$log"
cat "$log"

if [ "$(grep -c '^EXIT features=.* status=0$' "$status")" -ne 12 ] \
    || ! grep -qx 'EXIT wrong_peer_byte_control=101' "$status" \
    || ! grep -qx 'EXIT restored_peer_byte_assertion=0' "$status" \
    || [ "$(wc -l < "$status")" -ne 14 ] \
    || [ "$control_status" -ne 101 ] || [ "$restore_status" -ne 0 ]; then
    printf 'Unexpected status inventory or peer-byte control result.\n' >> "$log"
    exit 1
fi
if [ "$max_sockets" -gt 16 ]; then
    printf 'Sampled descendant socket descriptors exceeded the 16-handle budget.\n' >> "$log"
    exit 1
fi
if [ "$max_disk_bytes" -gt 2147483648 ]; then
    printf 'Private runtime exceeded 2 GiB disk budget.\n' >> "$log"
    exit 1
fi
