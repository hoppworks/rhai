#!/usr/bin/env bash
set -Eeuo pipefail
repo=/var/home/Daniel/projects/rhai
attempt=$repo/.scratch/all-tickets/linux-x36-setup-unchecked-20261025/attempt-01
evidence=$attempt/evidence
runtime=$AGENT_RUNTIME_DIR
runner=/var/home/Daniel/projects/agent-skills/tools/run_scoped.py
revision=2cb6b67a9b13c2b5f363e2d2767ac6ec40898038
toolchain=/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
cargo=$toolchain/cargo
mkdir -p "$runtime/source" "$runtime/cargo-home" "$runtime/target"
{
  date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
  uname -a
  printf 'revision=%s\nruntime=%s\nTMPDIR=%s\n' "$revision" "$runtime" "$TMPDIR"
  printf 'runner_sha256='; sha256sum "$runner" | awk '{print $1}'
  printf 'cargo_jobs=1\nmax_test_seconds=300\n'
  free -h
  df -h "$repo"
} > "$evidence/environment.txt"
git -C "$repo" archive "$revision" | tar --no-same-owner -xf - -C "$runtime/source"
cp "$repo/.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock" "$runtime/source/Cargo.lock"
cd "$runtime/source"
sha256sum Cargo.toml Cargo.lock src/packages/sys/process/unix.rs > "$evidence/source-hashes.txt"
test "$(sha256sum Cargo.lock | awk '{print $1}')" = 2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
test "$(sha256sum src/packages/sys/process/unix.rs | awk '{print $1}')" = 2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6
printf 'cargo=' > "$evidence/toolchain.txt"; "$cargo" --version >> "$evidence/toolchain.txt"
printf 'rustc=' >> "$evidence/toolchain.txt"; "$toolchain/rustc" --version >> "$evidence/toolchain.txt"
export CARGO_HOME="$runtime/cargo-home" CARGO_TARGET_DIR="$runtime/target" CARGO_BUILD_JOBS=1 CARGO_TERM_COLOR=never
export RUSTC="$toolchain/rustc" RUSTDOC="$toolchain/rustdoc" PATH="$toolchain:$PATH"
: > "$evidence/statuses.txt"
tests=(managed_scope_setup_failure_never_executes_unmanaged_child managed_scope_partial_setup_failure_cleans_created_group managed_scope_fchdir_failure_cleans_created_group )
for features in testing-environ,sys,unchecked; do
  for name in "${tests[@]}"; do
    selector="packages::sys::process::unix::tests::$name"
    log="$evidence/${features//,/_}-$name.log"
    if timeout 300s "$cargo" test --locked --features "$features" --lib "$selector" -- --exact --nocapture --test-threads=1 > "$log" 2>&1; then rc=0; else rc=$?; fi
    printf 'features=%s selector=%s status=%s\n' "$features" "$selector" "$rc" >> "$evidence/statuses.txt"
    test "$rc" = 0
    grep -Fq 'test result: ok. 1 passed; 0 failed' "$log"
  done
done
free -h > "$evidence/capacity-after.txt"
printf 'all three targeted base-unchecked X36 tests passed; prior expected RED controls are linked in the package proof\n' > "$evidence/result.txt"
