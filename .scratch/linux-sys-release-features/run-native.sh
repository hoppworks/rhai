#!/usr/bin/env bash
set -euo pipefail

: "${AGENT_RUNTIME_DIR:?run via the reviewed copied run_scoped.py}"
: "${PROOF_STAGE:?exact owned staging path required}"
: "${SOURCE_REVISION:?source revision required}"

evidence="$PROOF_STAGE/evidence"
log="$evidence/native-linux-sys-release.log"
status_file="$evidence/status.tsv"
mkdir -p "$AGENT_RUNTIME_DIR/source" "$AGENT_RUNTIME_DIR/cargo-home" "$AGENT_RUNTIME_DIR/target" "$evidence"
tar -xf "$PROOF_STAGE/source.tar" -C "$AGENT_RUNTIME_DIR/source"
source="$AGENT_RUNTIME_DIR/source"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_INCREMENTAL=0
export CARGO_PROFILE_DEV_DEBUG=0
export CARGO_PROFILE_TEST_DEBUG=0
: > "$status_file"

{
    printf 'Source revision: %s\n' "$SOURCE_REVISION"
    printf 'Source archive SHA256: '
    sha256sum "$PROOF_STAGE/source.tar"
    printf 'Runtime directory: %s\n' "$AGENT_RUNTIME_DIR"
    printf 'Runtime owner launcher PID: %s\n' "$PPID"
    uname -a
    cat /etc/os-release
    rustc --version --verbose
    cargo --version --verbose
    printf '\nCargo uses --jobs 2 and each test binary uses --test-threads=1.\n'
    printf 'Targets are run one at a time.\n'
    printf '\nDisk before extraction/build:\n'
    df -Pk "$PROOF_STAGE" "$AGENT_RUNTIME_DIR"
} > "$log"

cd "$source"
max_processes=0
max_disk_bytes=0

run_measured() {
    local label="$1" output="$AGENT_RUNTIME_DIR/$1.out" metrics="$AGENT_RUNTIME_DIR/$1.metrics" stop="$AGENT_RUNTIME_DIR/$1.stop" command_status=0
    shift
    rm -f "$stop"
    "$@" > "$output" 2>&1 &
    local command_pid=$!
    python3 "$PROOF_STAGE/sample-owned-resources.py" "$command_pid" "$AGENT_RUNTIME_DIR" "$metrics" "$stop" &
    local monitor_pid=$!
    wait "$command_pid" || command_status=$?
    wait "$monitor_pid"
    cat "$output" >> "$log"
    cat "$metrics" >> "$log"
    if [ -f "$stop" ]; then
        cat "$stop" >> "$log"
        printf 'PREEMPTED label=%s reason=sampled resource limit; scoped group cleanup owns remaining descendants\n' "$label" | tee -a "$log"
        return 125
    fi
    local sampled_processes sampled_disk
    sampled_processes="$(awk -F= '/^sampled_process_count_max=/{print $2}' "$metrics")"
    sampled_disk="$(awk -F= '/^sampled_private_disk_max_bytes=/{print $2}' "$metrics")"
    (( sampled_processes > max_processes )) && max_processes="$sampled_processes" || true
    (( sampled_disk > max_disk_bytes )) && max_disk_bytes="$sampled_disk" || true
    if [ "$sampled_processes" -gt 16 ]; then
        printf 'PREEMPTED label=%s reason=sampled owned process count exceeded 16\n' "$label" | tee -a "$log"
        return 125
    fi
    return "$command_status"
}

record_case() {
    local features="$1" target="$2" case_status=0 label
    label="${features//,/_}-$target"
    printf '\n===== features=%s target=%s =====\n' "$features" "$target" | tee -a "$log"
    printf 'Command: cargo test --locked --jobs 2 --features %q --test %q -- --test-threads=1 --nocapture\n' "$features" "$target" | tee -a "$log"
    run_measured "$label" cargo test --locked --jobs 2 --features "$features" --test "$target" -- --test-threads=1 --nocapture || case_status=$?
    printf 'EXIT features=%s target=%s status=%d\n' "$features" "$target" "$case_status" | tee -a "$log" "$status_file"
    printf 'Private runtime allocated storage after %s/%s: ' "$features" "$target" >> "$log"
    du -sB1 "$AGENT_RUNTIME_DIR" >> "$log"
    if [ "$case_status" -ne 0 ]; then
        return "$case_status"
    fi
}

lock_status=0
printf '\n===== generate isolated lockfile =====\n' | tee -a "$log"
printf 'Command: cargo generate-lockfile\n' | tee -a "$log"
run_measured lockfile-resolution cargo generate-lockfile || lock_status=$?
printf 'EXIT lockfile_resolution=%d\n' "$lock_status" | tee -a "$log"
if [ "$lock_status" -ne 0 ] || [ ! -f Cargo.lock ]; then
    printf 'Private lockfile generation failed.\n' | tee -a "$log"
    exit 1
fi
cp Cargo.lock "$evidence/Cargo.lock.generated"
printf 'Generated Cargo.lock SHA256: ' | tee -a "$log"
sha256sum Cargo.lock | tee -a "$log"

targets=(sys_env sys_fs sys_policy)
profiles=(
    testing-environ,sys
    testing-environ,sys,sync
    testing-environ,sys,no_index
    testing-environ,sys,metadata,serde
    testing-environ,sys,only_i32,no_float
    testing-environ,sys,unchecked
    testing-environ,sys,no_index,sync,metadata
    testing-environ,sys,f32_float
)

for features in "${profiles[@]}"; do
    for target in "${targets[@]}"; do
        record_case "$features" "$target"
    done
done

control_status=0
printf '\n===== wrong actual file-read expectation control =====\n' | tee -a "$log"
printf 'Command: RHAI_FILE_READ_WRONG_EXPECTATION=1 cargo test --locked --jobs 2 --features testing-environ,sys --test sys_fs test_file_handle_reads_obey_host_cap_and_reject_negative_lengths_without_moving -- --exact --test-threads=1 --nocapture\n' | tee -a "$log"
run_measured wrong-file-read-expectation-control env RHAI_FILE_READ_WRONG_EXPECTATION=1 cargo test --locked --jobs 2 --features testing-environ,sys --test sys_fs test_file_handle_reads_obey_host_cap_and_reject_negative_lengths_without_moving -- --exact --test-threads=1 --nocapture || control_status=$?
printf 'EXIT wrong_file_read_expectation_control=%d\n' "$control_status" | tee -a "$log" "$status_file"
if [ "$control_status" -ne 101 ] \
    || ! grep -Fq 'left: "abc"' "$AGENT_RUNTIME_DIR/wrong-file-read-expectation-control.out" \
    || ! grep -Fq 'right: "wrong expectation"' "$AGENT_RUNTIME_DIR/wrong-file-read-expectation-control.out" \
    || ! grep -Fq "thread 'test_file_handle_reads_obey_host_cap_and_reject_negative_lengths_without_moving' panicked" "$AGENT_RUNTIME_DIR/wrong-file-read-expectation-control.out" \
    || ! grep -Fq 'test result: FAILED' "$AGENT_RUNTIME_DIR/wrong-file-read-expectation-control.out"; then
    printf 'Wrong file-read control did not fail at the expected actual-byte assertion.\n' | tee -a "$log"
    exit 1
fi

restore_status=0
printf '\n===== corrected actual file-read assertion =====\n' | tee -a "$log"
run_measured corrected-file-read-assertion cargo test --locked --jobs 2 --features testing-environ,sys --test sys_fs test_file_handle_reads_obey_host_cap_and_reject_negative_lengths_without_moving -- --exact --test-threads=1 --nocapture || restore_status=$?
printf 'EXIT corrected_file_read_assertion=%d\n' "$restore_status" | tee -a "$log" "$status_file"

{
    printf '\nSampled maxima across invocations: descendant_processes=%s private_disk_bytes=%s\n' "$max_processes" "$max_disk_bytes"
    printf 'Sampling interval: 1 second; maxima are sampled values.\n'
    printf '\nPrivate runtime allocated storage at end:\n'
    du -sB1 "$AGENT_RUNTIME_DIR"
    printf '\nFinal Cargo.lock SHA256: '
    sha256sum Cargo.lock
} >> "$log"
cat "$log"

expected_cases=$(( ${#profiles[@]} * ${#targets[@]} ))
if [ "$(grep -c '^EXIT features=.* status=0$' "$status_file")" -ne "$expected_cases" ] \
    || ! grep -qx 'EXIT wrong_file_read_expectation_control=101' "$status_file" \
    || ! grep -qx 'EXIT corrected_file_read_assertion=0' "$status_file" \
    || [ "$(wc -l < "$status_file" | tr -d ' ')" -ne $((expected_cases + 2)) ] \
    || [ "$control_status" -ne 101 ] || [ "$restore_status" -ne 0 ]; then
    printf 'Unexpected status inventory or file-read control result.\n' >> "$log"
    exit 1
fi
if [ "$max_processes" -gt 16 ] || [ "$max_disk_bytes" -gt 2147483648 ]; then
    printf 'Sampled resource maximum exceeded a fixed limit.\n' >> "$log"
    exit 1
fi
