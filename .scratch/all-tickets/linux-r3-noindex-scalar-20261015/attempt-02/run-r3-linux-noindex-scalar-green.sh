#!/usr/bin/env bash
set -Eeuo pipefail
repo=/var/home/Daniel/projects/rhai
attempt="$repo/.scratch/all-tickets/linux-r3-noindex-scalar-20261015/attempt-02"
evidence="$attempt/evidence"
scope="${1:?session scope required}"
runtime="${AGENT_RUNTIME_DIR:?scoped runner required}"
lock="$repo/.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock"
toolchain=/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
cargo="$toolchain/cargo"
source_dir="$runtime/source"
features=testing-environ,sys,no_index,sync,unchecked
mkdir -p "$source_dir"
git -C "$repo" archive HEAD | tar --no-same-owner -xf - -C "$source_dir"
cp "$lock" "$source_dir/Cargo.lock"
cd "$source_dir"
export CARGO_TARGET_DIR="$runtime/target"
export CARGO_HOME="$runtime/cargo-home"
export CARGO_BUILD_JOBS=1
export CARGO_TERM_COLOR=never
export RUSTC="$toolchain/rustc"
export RUSTDOC="$toolchain/rustdoc"
export RUSTUP_HOME=/home/Daniel/.rustup
export PATH="$toolchain:/usr/bin:/bin"
export PYTHONDONTWRITEBYTECODE=1
{
  printf 'revision='; git -C "$repo" rev-parse HEAD
  date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
  uname -a
  cat /etc/os-release
  printf 'features=%s\nprofile=default\n' "$features"
  "$cargo" --version
  "$RUSTC" -Vv
  sha256sum Cargo.toml Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs
  printf 'scope=%s\nruntime=%s\ncargo_jobs=1\n' "$scope" "$runtime"
} > "$evidence/environment.txt"
set +e
timeout 300s "$cargo" test --locked --features "$features" --test sys_process scalar_run_with_cwd_works_without_collections -- --exact --nocapture --test-threads=1 > "$evidence/green.log" 2>&1
rc=$?
set -e
printf 'green=%s\n' "$rc" > "$evidence/statuses.txt"
test "$rc" -eq 0
grep -Fq 'test result: ok. 1 passed; 0 failed;' "$evidence/green.log"
grep -Fq 'no-index scalar child_pid=' "$evidence/green.log"
grep -Fq 'reap=ESRCH' "$evidence/green.log"
printf 'restored GREEN=1/1; public scalar run reported cwd/captures/exit; independent child record and ESRCH readback; run_raw absent assertion passed\n' > "$evidence/result.txt"
