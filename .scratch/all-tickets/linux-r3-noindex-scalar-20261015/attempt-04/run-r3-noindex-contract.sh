#!/usr/bin/env bash
set -Eeuo pipefail
repo=/var/home/Daniel/projects/rhai
package="$repo/.scratch/all-tickets/linux-r3-noindex-scalar-20261015"
attempt="$package/attempt-04"
evidence="$attempt/evidence"
scope="${1:?owned session scope required}"
runtime="${AGENT_RUNTIME_DIR:?must run through run_scoped.py}"
lock="/var/home/Daniel/projects/rhai/.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock"
toolchain=/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
source_dir="$runtime/source"
features=testing-environ,sys,no_index
mkdir -p "$source_dir"
git -C "$repo" archive HEAD | tar --no-same-owner -xf - -C "$source_dir"
cp "$repo/tests/sys_process.rs" "$source_dir/tests/sys_process.rs"
cp "$lock" "$source_dir/Cargo.lock"
cp "$source_dir/tests/sys_process.rs" "$runtime/sys_process.green.rs"
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
python3 - "$source_dir/tests/sys_process.rs" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
start = s.index("fn run_without_arguments_works_and_array_overloads_are_absent() {")
end = s.index("\n}", start)
body = s[start:end]
old = 'assert!(result["success"].as_bool().unwrap());'
assert body.count(old) == 1
body = body.replace(old, 'assert!(!result["success"].as_bool().unwrap());', 1)
p.write_text(s[:start] + body + s[end:])
PY
set +e
timeout 600s "$toolchain/cargo" test --locked --features "$features" --test sys_process run_without_arguments_works_and_array_overloads_are_absent -- --exact --nocapture --test-threads=1 > "$evidence/red.log" 2>&1
red_rc=$?
set -e
printf 'red=%s\n' "$red_rc" > "$evidence/statuses.txt"
test "$red_rc" -eq 101
grep -Fq 'assertion failed: !result["success"].as_bool().unwrap()' "$evidence/red.log"
grep -Fq 'test result: FAILED. 0 passed; 1 failed;' "$evidence/red.log"
cp "$runtime/sys_process.green.rs" tests/sys_process.rs
set +e
timeout 600s "$toolchain/cargo" test --locked --features "$features" --test sys_process run_without_arguments_works_and_array_overloads_are_absent -- --exact --nocapture --test-threads=1 > "$evidence/green.log" 2>&1
green_rc=$?
set -e
printf 'green=%s\n' "$green_rc" >> "$evidence/statuses.txt"
test "$green_rc" -eq 0
grep -Fq 'test result: ok. 1 passed; 0 failed;' "$evidence/green.log"
grep -Fq 'no-index run no-args success=true code=0 stdout_complete=true stderr_complete=true' "$evidence/green.log"
grep -Fq 'no-index array-taking run overload absent=true' "$evidence/green.log"
cp Cargo.lock "$attempt/source-Cargo.lock"
sha256sum Cargo.toml Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/source-hashes.txt"
printf 'RED: deliberately inverted success expectation failed at the intended assertion (Cargo 101, 0 passed/1 failed).\nGREEN: restored test passed 1/1; public Engine run(program) completed /bin/true with exact status and complete captures; run(program, array) was rejected as missing overload.\n' > "$evidence/result.txt"
printf 'source and lock hashes exported; scoped runtime will be removed by run_scoped.py\n' > "$evidence/cleanup-readback.txt"
