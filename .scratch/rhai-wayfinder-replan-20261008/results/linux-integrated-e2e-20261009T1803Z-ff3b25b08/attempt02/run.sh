#!/usr/bin/env bash
set -Eeuo pipefail
scope=/root/.local/share/agent-builds/rhai/linux-e2e-20261009T1803Z-ff3b25b08-attempt02
runtime=${AGENT_RUNTIME_DIR:?runner must provide AGENT_RUNTIME_DIR}
evidence="$scope/evidence"
source_root="$runtime/source"
rustbin=/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
cargo="$rustbin/cargo"
mkdir -p "$evidence" "$source_root"
cat > "$evidence/run-command.txt" <<CMD
$cargo test --locked --jobs 2 --features testing-environ,sys,net,metadata --no-fail-fast --test sys_policy --test sys_env --test sys_fs --test sys_process --test sys_process_report --test combined_sys_net --test net_connect --test net_listen --test net_metadata --test net_reads --test net_writes -- --test-threads=2
CMD
{
  date -Is
  uname -a
  printf 'runtime=%s\nsource=%s\n' "$runtime" "$source_root"
  printf 'rustc='; "$rustbin/rustc" --version
  printf 'cargo='; "$cargo" --version
  printf 'runner=%s\n' /var/home/workhorse/projects/agent-skills/tools/run_scoped.py
  sha256sum "$scope/source.tar.gz" "$scope/Cargo.lock.accepted"
} > "$evidence/environment.txt"
tar -xzf "$scope/source.tar.gz" -C "$source_root"
cp "$scope/Cargo.lock.accepted" "$source_root/Cargo.lock"
printf '%s  %s\n' 2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425 "$source_root/Cargo.lock" | sha256sum -c - > "$evidence/lock-readback.txt"
export PATH="$rustbin:$PATH"
export RUSTC="$rustbin/rustc"
export CARGO_HOME="$runtime/cargo-home"
export CARGO_TARGET_DIR="$runtime/target"
cd "$source_root"
printf 'source_cwd=%s\n' "$PWD" >> "$evidence/environment.txt"
set +e
"$cargo" metadata --locked --no-deps --format-version 1 > "$evidence/cargo-metadata.json" 2> "$evidence/cargo-metadata.stderr"
metadata_status=$?
set -e
printf '%s\n' "$metadata_status" > "$evidence/cargo-metadata.status"
if test "$metadata_status" -ne 0; then exit "$metadata_status"; fi
set +e
"$cargo" test --locked --jobs 2 --features testing-environ,sys,net,metadata --no-fail-fast --test sys_policy --test sys_env --test sys_fs --test sys_process --test sys_process_report --test combined_sys_net --test net_connect --test net_listen --test net_metadata --test net_reads --test net_writes -- --test-threads=2 > "$evidence/cargo-test.stdout" 2> "$evidence/cargo-test.stderr"
status=$?
set -e
printf '%s\n' "$status" > "$evidence/cargo-test.status"
exit "$status"
