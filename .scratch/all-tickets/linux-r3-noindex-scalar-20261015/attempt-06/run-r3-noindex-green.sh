#!/usr/bin/env bash
set -Eeuo pipefail
repo=/var/home/Daniel/projects/rhai
package="$repo/.scratch/all-tickets/linux-r3-noindex-scalar-20261015"
attempt="$package/attempt-06"
evidence="$attempt/evidence"
scope="${1:?owned session scope required}"
runtime="${AGENT_RUNTIME_DIR:?must run through run_scoped.py}"
lock=/var/home/Daniel/projects/rhai/.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock
toolchain=/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
source_dir="$runtime/source"
features=testing-environ,sys,no_index
mkdir -p "$source_dir"
git -C "$repo" archive HEAD | tar --no-same-owner -xf - -C "$source_dir"
cp "$repo/tests/sys_process.rs" "$source_dir/tests/sys_process.rs"
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
  "$toolchain/cargo" --version
  "$RUSTC" -Vv
  sha256sum Cargo.toml Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs
  printf 'scope=%s\nruntime=%s\ncargo_jobs=1\n' "$scope" "$runtime"
} > "$evidence/environment.txt"
set +e
timeout 600s "$toolchain/cargo" test --locked --features "$features" --test sys_process run_without_arguments_works_and_array_overloads_are_absent -- --exact --nocapture --test-threads=1 > "$evidence/green.log" 2>&1
rc=$?
set -e
printf 'green=%s\n' "$rc" > "$evidence/statuses.txt"
test "$rc" -eq 0
grep -Fq 'test result: ok. 1 passed; 0 failed;' "$evidence/green.log"
grep -Fq 'no-index run no-args success=true code=0 stdout_complete=true stderr_complete=true' "$evidence/green.log"
grep -Fq 'no-index array-taking run overload absent=true' "$evidence/green.log"
cp Cargo.lock "$attempt/source-Cargo.lock"
sha256sum Cargo.toml Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/source-hashes.txt"
printf 'Restored GREEN passed 1/1 at the exact selector. Public Engine run(program) completed /bin/true with code 0 and complete stdout/stderr. A Rust-injected Array supplied through Scope produced ErrorFunctionNotFound for run(program, args); the array-taking overload is absent.\n' > "$evidence/result.txt"
printf 'The private runtime was removed by run_scoped.py; only the empty owned session scope will be retired by the caller.\n' > "$evidence/cleanup-readback.txt"
