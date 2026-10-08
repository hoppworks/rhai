#!/bin/bash
set -euo pipefail
repo=/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery
lock="$repo/.scratch/all-tickets/process-io-contract-evidence/attempt-01/stage/Cargo.lock.accepted"
evidence="${RHAI_X18_EVIDENCE:?}"
src="$AGENT_RUNTIME_DIR/source"
mkdir -p "$src"
printf '%s\n' "$AGENT_RUNTIME_DIR" > "$evidence/private-runtime.txt"
git -C "$repo" archive --format=tar HEAD | tar -xf - -C "$src"
cp "$lock" "$src/Cargo.lock"
expected_lock=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
actual_lock=$(shasum -a 256 "$src/Cargo.lock" | awk '{print $1}')
test "$actual_lock" = "$expected_lock"
cp "$src/tests/sys_process.rs" "$evidence/sys_process-restored.rs"
shasum -a 256 "$src/Cargo.toml" "$src/tests/sys_process.rs" "$src/tests/fixtures/sys_process_shared_child_contract.rs" "$src/Cargo.lock" > "$evidence/source-hashes.txt"
{
  printf 'revision='; git -C "$repo" rev-parse HEAD
  printf 'features=testing-environ,sys\nfilter=unit_stdin_means_immediate_eof\n'
  printf 'command=cargo +1.93.0 test --locked --features testing-environ,sys --test sys_process unit_stdin_means_immediate_eof -- --exact --nocapture --test-threads=1\n'
  printf 'lock_sha256=%s\n' "$actual_lock"
  sw_vers
  uname -m
  rustc +1.93.0 --version
  cargo +1.93.0 --version
} > "$evidence/run-metadata.txt"
python3 - "$src/tests/sys_process.rs" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
b = p.read_bytes()
old = b'expected.extend_from_slice(b"stdin-eof");'
new = b'expected.extend_from_slice(b"stdin-not-eof");'
assert b.count(old) == 1, f'expected one exact X18 assertion, found {b.count(old)}'
p.write_bytes(b.replace(old, new, 1))
PY
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=1
export PYTHONDONTWRITEBYTECODE=1
set +e
cargo +1.93.0 test --locked --features testing-environ,sys --test sys_process unit_stdin_means_immediate_eof -- --exact --nocapture --test-threads=1 > "$evidence/red.log" 2>&1
red=$?
set -e
printf '%s\n' "$red" > "$evidence/red.status"
test "$red" -eq 101
grep -F 'test unit_stdin_means_immediate_eof ... FAILED' "$evidence/red.log" >/dev/null
grep -F 'assertion' "$evidence/red.log" >/dev/null
cp "$evidence/sys_process-restored.rs" "$src/tests/sys_process.rs"
cmp "$evidence/sys_process-restored.rs" "$src/tests/sys_process.rs"
shasum -a 256 "$src/tests/sys_process.rs" > "$evidence/restored-source-hash.txt"
set +e
cargo +1.93.0 test --locked --features testing-environ,sys --test sys_process unit_stdin_means_immediate_eof -- --exact --nocapture --test-threads=1 > "$evidence/green.log" 2>&1
green=$?
set -e
printf '%s\n' "$green" > "$evidence/green.status"
test "$green" -eq 0
grep -F 'test unit_stdin_means_immediate_eof ... ok' "$evidence/green.log" >/dev/null
grep -F '1 passed; 0 failed' "$evidence/green.log" >/dev/null
printf 'red=%s green=%s source_restored=true lock=%s\n' "$red" "$green" "$actual_lock" > "$evidence/result.txt"
