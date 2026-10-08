#!/bin/bash
set -euo pipefail
repo=/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery
evidence="$RHAI_X20_EVIDENCE"
source="$AGENT_RUNTIME_DIR/source"
mkdir -p "$source"
printf '%s\n' "$AGENT_RUNTIME_DIR" > "$evidence/private-runtime.txt"
git -C "$repo" archive --format=tar HEAD | tar -xf - -C "$source"
cp "$repo/.scratch/all-tickets/process-io-contract-evidence/attempt-01/stage/Cargo.lock.accepted" "$source/Cargo.lock"
expected_lock=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
actual_lock=$(shasum -a 256 "$source/Cargo.lock" | awk '{print $1}')
test "$actual_lock" = "$expected_lock"
test_source_sha=$(cd "$source" && shasum -a 256 tests/sys_process.rs | awk '{print $1}')
test "$test_source_sha" = 7ddc87f6e4b57d61d077445a81f1c3ef2f2e54cb35ac8c90a7ed328245d14017
cp "$source/tests/sys_process.rs" "$evidence/sys_process.baseline.rs"
python3 - "$source/tests/sys_process.rs" "$evidence/sys_process.baseline.rs" "$evidence/sys_process.mutant.rs" <<'PY'
from pathlib import Path
import sys
source = Path(sys.argv[1])
text = source.read_text()
start = text.index('fn run_io_contract_empty_output() {')
end = text.index('\n}\n', start)
block = text[start:end]
needle = 'assert!(!result["timed_out"].as_bool().unwrap());'
if block.count(needle) != 1:
    raise SystemExit(f'expected one X14 timeout assertion, got {block.count(needle)}')
mutant = text[:start] + block.replace(needle, 'assert!(result["timed_out"].as_bool().unwrap());', 1) + text[end:]
source.write_text(mutant)
Path(sys.argv[3]).write_text(mutant)
PY
mutant_sha=$(shasum -a 256 "$source/tests/sys_process.rs" | awk '{print $1}')
base_sha=$(shasum -a 256 "$evidence/sys_process.baseline.rs" | awk '{print $1}')
{
  printf 'revision=%s\n' "$(git -C "$repo" rev-parse HEAD)"
  printf 'os=%s %s\n' "$(sw_vers -productName)" "$(sw_vers -productVersion)"
  printf 'arch=%s\n' "$(uname -m)"
  printf 'rustc=%s\n' "$(rustc +1.93.0 --version)"
  printf 'cargo=%s\n' "$(cargo +1.93.0 --version)"
  printf 'features=testing-environ,sys\nfilter=run_io_contract_empty_output\n'
  printf 'accepted_lock_sha256=%s\n' "$actual_lock"
  printf 'baseline_test_source_sha256=%s\nmutant_test_source_sha256=%s\n' "$base_sha" "$mutant_sha"
  printf 'command=cargo +1.93.0 test --locked --features testing-environ,sys --test sys_process run_io_contract_empty_output -- --exact --nocapture --test-threads=1\n'
  printf 'cargo_jobs=1\n'
  printf 'cargo_target_dir=%s/target\ncargo_home=%s/cargo-home\n' "$AGENT_RUNTIME_DIR" "$AGENT_RUNTIME_DIR"
} > "$evidence/run-metadata.txt"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=1
export PYTHONDONTWRITEBYTECODE=1
cd "$source"
set +e
cargo +1.93.0 test --locked --features testing-environ,sys --test sys_process run_io_contract_empty_output -- --exact --nocapture --test-threads=1 > "$evidence/red.log" 2>&1
red=$?
set -e
printf '%s\n' "$red" > "$evidence/red.status"
cp "$evidence/sys_process.baseline.rs" "$source/tests/sys_process.rs"
restored_sha=$(shasum -a 256 "$source/tests/sys_process.rs" | awk '{print $1}')
test "$restored_sha" = "$base_sha"
set +e
cargo +1.93.0 test --locked --features testing-environ,sys --test sys_process run_io_contract_empty_output -- --exact --nocapture --test-threads=1 > "$evidence/green.log" 2>&1
green=$?
set -e
printf '%s\n' "$green" > "$evidence/green.status"
red_ok=false
if [[ "$red" -eq 101 ]] && grep -F 'test run_io_contract_empty_output ... FAILED' "$evidence/red.log" >/dev/null && grep -F 'assertion failed: result["timed_out"].as_bool().unwrap()' "$evidence/red.log" >/dev/null; then red_ok=true; fi
green_ok=false
if [[ "$green" -eq 0 ]] && grep -F 'test run_io_contract_empty_output ... ok' "$evidence/green.log" >/dev/null && grep -F '1 passed; 0 failed' "$evidence/green.log" >/dev/null; then green_ok=true; fi
{
  classification=not_accepted
  if [[ "$red_ok" == true && "$green_ok" == true ]]; then classification=accepted; fi
  printf 'classification=%s\nred_status=%s\nred_sensitivity_verified=%s\ngreen_status=%s\ngreen_passed=%s\nbaseline_source_restored=%s\n' "$classification" "$red" "$red_ok" "$green" "$green_ok" "$([[ "$restored_sha" == "$base_sha" ]] && echo true || echo false)"
  printf 'runtime_cleanup=runner_owned\naccepted_lock_sha256=%s\n' "$actual_lock"
} > "$evidence/outcome.txt"
shasum -a 256 "$evidence"/{sys_process.baseline.rs,sys_process.mutant.rs,run-metadata.txt,red.log,red.status,green.log,green.status,outcome.txt} > "$evidence/evidence.sha256"
test "$green_ok" = true
