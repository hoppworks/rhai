#!/usr/bin/env bash
set -Eeuo pipefail

scope=${SESSION_SCOPE:?SESSION_SCOPE must be set}
runtime=${AGENT_RUNTIME_DIR:?run_scoped must set AGENT_RUNTIME_DIR}
source="$runtime/source"
mkdir -p "$source" "$scope/out"
tar -xzf "$scope/stage/source.tar.gz" -C "$source"
cp "$scope/stage/sys_process.rs" "$source/tests/sys_process.rs"
cp "$scope/stage/Cargo.lock.accepted" "$source/Cargo.lock"

expected_source_hash=dd121c760ace68c651b8c87e2354683cc075a459fcf32e41c83a86c7b32d11d1
expected_lock_hash=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
actual_source_hash=$(sha256sum "$source/tests/sys_process.rs" | cut -d' ' -f1)
actual_lock_hash=$(sha256sum "$source/Cargo.lock" | cut -d' ' -f1)
[[ "$actual_source_hash" == "$expected_source_hash" ]]
[[ "$actual_lock_hash" == "$expected_lock_hash" ]]

export RUSTUP_TOOLCHAIN=1.93.0
export PATH=/home/linuxbrew/.linuxbrew/opt/rustup/bin:/usr/bin:/bin
export CARGO_TARGET_DIR="$runtime/target"
export CARGO_HOME="$runtime/cargo-home"
export CARGO_BUILD_JOBS=2
mkdir -p "$CARGO_TARGET_DIR" "$CARGO_HOME"
cd "$source"

{
  printf 'scope=%s\nruntime=%s\n' "$scope" "$runtime"
  printf 'rustc=%s\n' "$(rustc --version)"
  printf 'cargo=%s\n' "$(cargo --version)"
  printf 'source_sha256=%s\nlock_sha256=%s\n' "$actual_source_hash" "$actual_lock_hash"
  printf 'runner_sha256=%s\n' "$(sha256sum /home/workhorse/projects/agent-skills/tools/run_scoped.py | cut -d' ' -f1)"
  printf 'test=tests/sys_process.rs::run_preserves_argv_boundaries_without_shell_interpolation\n'
  printf 'command=cargo test --locked --features testing-environ,sys --test sys_process run_preserves_argv_boundaries_without_shell_interpolation -- --exact --nocapture --test-threads=1\n'
  printf 'red_control=expected[0] XOR 1 in private runtime copy only\n'
  printf 'cargo_jobs=%s\n' "$CARGO_BUILD_JOBS"
} > "$scope/out/run-manifest.txt"

python3 - "$source/tests/sys_process.rs" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
source = path.read_text()
needle = '    assert_eq!(observed, expected, "child received different argv boundaries or bytes");'
replacement = '    expected[0] ^= 1;\n' + needle
if source.count(needle) != 1:
    raise SystemExit('RED mutation anchor is not unique')
path.write_text(source.replace(needle, replacement))
PY

command=(cargo test --locked --features testing-environ,sys --test sys_process run_preserves_argv_boundaries_without_shell_interpolation -- --exact --nocapture --test-threads=1)
start=$SECONDS
deadline=$((start + 540))
remaining() { printf '%s' "$((deadline - SECONDS))"; }

red_budget=$(remaining)
if (( red_budget <= 0 )); then exit 80; fi
set +e
timeout --foreground --signal=TERM --kill-after=10 "${red_budget}s" "${command[@]}" > "$scope/out/red.stdout" 2> "$scope/out/red.stderr"
red_status=$?
set -e
printf '%s\n' "$red_status" > "$scope/out/red.status"
if [[ "$red_status" -ne 101 ]] || ! grep -Fq 'child received different argv boundaries or bytes' "$scope/out/red.stderr"; then
  printf 'Expected an assertion-level RED with status 101; got %s\n' "$red_status" >&2
  exit 81
fi

cp "$scope/stage/sys_process.rs" "$source/tests/sys_process.rs"
[[ "$(sha256sum "$source/tests/sys_process.rs" | cut -d' ' -f1)" == "$expected_source_hash" ]]
green_budget=$(remaining)
if (( green_budget <= 0 )); then exit 82; fi
set +e
timeout --foreground --signal=TERM --kill-after=10 "${green_budget}s" "${command[@]}" > "$scope/out/green.stdout" 2> "$scope/out/green.stderr"
green_status=$?
set -e
printf '%s\n' "$green_status" > "$scope/out/green.status"
if [[ "$green_status" -ne 0 ]] || ! grep -Fq 'run_preserves_argv_boundaries_without_shell_interpolation ... ok' "$scope/out/green.stdout"; then
  printf 'Expected restored GREEN; got %s\n' "$green_status" >&2
  exit 83
fi

printf 'aggregate_cargo_seconds=%s\n' "$((SECONDS - start))" >> "$scope/out/run-manifest.txt"
sha256sum "$scope/out"/* > "$scope/out/SHA256SUMS"
printf 'RED assertion control and restored GREEN passed in the same scoped runtime.\n'
