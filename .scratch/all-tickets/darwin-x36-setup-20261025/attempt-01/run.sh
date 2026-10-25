#!/usr/bin/env bash
set -Eeuo pipefail
repo=/Users/hoppworks/.codex/worktrees/darwin-capture-cleanup/rhai
attempt="$repo/.scratch/all-tickets/darwin-x36-setup-20261025/attempt-01"
evidence="$attempt/evidence"
revision=7638f2684ff2f06bb7587359eeb8c82e9c86a360
runner=/Users/hoppworks/projects/agent-skills/tools/run_scoped.py
source_dir="$AGENT_RUNTIME_DIR/source"
mkdir -p "$source_dir"
git -C "$repo" archive "$revision" | tar -x -C "$source_dir"
cp "$repo/.scratch/all-tickets/core-current-msrv-evidence-04/Cargo.lock" "$source_dir/Cargo.lock"
cd "$source_dir"
test "$(shasum -a 256 Cargo.lock | awk '{print $1}')" = 2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
test "$(shasum -a 256 src/packages/sys/process/unix.rs | awk '{print $1}')" = 2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_BUILD_JOBS=2 CARGO_TERM_COLOR=never PYTHONDONTWRITEBYTECODE=1
export X36_EVIDENCE="$evidence"
{
  date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
  printf 'revision=%s\nruntime=%s\nTMPDIR=%s\n' "$revision" "$AGENT_RUNTIME_DIR" "$TMPDIR"
  printf 'cargo_jobs=2\nouter_timeout_seconds=600\n'
  shasum -a 256 "$runner"
  uname -a
  sw_vers
  rustc +1.77.2 -Vv
  cargo +1.77.2 -V
} > "$evidence/environment.txt"
shasum -a 256 Cargo.toml Cargo.lock src/packages/sys/process/unix.rs > "$evidence/source-hashes.txt"
cp src/packages/sys/process/unix.rs "$AGENT_RUNTIME_DIR/unix.correct.rs"
python3 - <<'PY'
from pathlib import Path
import json, os
p = Path('src/packages/sys/process/unix.rs')
s = p.read_text()
names = [
    'managed_scope_setup_failure_never_executes_unmanaged_child',
    'managed_scope_partial_setup_failure_cleans_created_group',
    'managed_scope_fchdir_failure_cleans_created_group',
    'managed_scope_kernel_setpgid_denial_cleans_created_group',
]
for name in names:
    start = s.index('    fn ' + name + '()')
    end = s.index('\n    }', start) + len('\n    }')
    body = s[start:end]
    assert body.count('!marker.exists()') == 1, name
    s = s[:start] + body.replace('!marker.exists()', 'marker.exists()') + s[end:]
p.write_text(s)
Path(os.environ['X36_EVIDENCE'], 'mutation.json').write_text(json.dumps({
    'selectors': names,
    'change': 'Invert only the final marker-absence assertion in each named test after its public run setup failure and helper cleanup. Expect a marker that must be absent.',
    'production_code_changed': False,
}, indent=2) + '\n')
PY
shasum -a 256 src/packages/sys/process/unix.rs > "$evidence/mutated-source.sha256"
diff -u "$AGENT_RUNTIME_DIR/unix.correct.rs" src/packages/sys/process/unix.rs > "$evidence/mutation.patch" || test "$?" -eq 1
tests=(managed_scope_setup_failure_never_executes_unmanaged_child managed_scope_partial_setup_failure_cleans_created_group managed_scope_fchdir_failure_cleans_created_group managed_scope_kernel_setpgid_denial_cleans_created_group)
messages=('command executed after setup failure' 'command executed after partial setup failure' 'command executed after fchdir failure' 'command executed after kernel setpgid denial')
printf 'phase\tfeatures\tselector\texit\n' > "$evidence/statuses.tsv"
run_case() {
  local phase="$1" features="$2" name="$3" message="${4:-}"
  local selector="packages::sys::process::unix::tests::$name"
  local log="$evidence/${phase}_${features//,/_}-$name.log"
  local rc=0
  cargo +1.77.2 test --locked --features "$features" --lib "$selector" -- --exact --nocapture --test-threads=1 > "$log" 2>&1 || rc=$?
  printf '%s\t%s\t%s\t%s\n' "$phase" "$features" "$selector" "$rc" >> "$evidence/statuses.tsv"
  if test "$phase" = red; then
    test "$rc" -eq 101
    rg -Fq "$message" "$log"
    rg -Fq 'test result: FAILED. 0 passed; 1 failed;' "$log"
  else
    test "$rc" -eq 0
    rg -Fq 'test result: ok. 1 passed; 0 failed;' "$log"
  fi
}
for index in 0 1 2 3; do
  run_case red testing-environ,sys "${tests[$index]}" "${messages[$index]}"
done
cp "$AGENT_RUNTIME_DIR/unix.correct.rs" src/packages/sys/process/unix.rs
shasum -a 256 src/packages/sys/process/unix.rs > "$evidence/restored-source.sha256"
test "$(shasum -a 256 src/packages/sys/process/unix.rs | awk '{print $1}')" = 2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6
for features in testing-environ,sys testing-environ,sys,sync testing-environ,sys,unchecked testing-environ,sys,sync,unchecked; do
  for name in "${tests[@]}"; do
    run_case green "$features" "$name"
  done
done
printf 'four native expected assertion REDs and sixteen restored GREENs passed; source restoration verified\n' > "$evidence/result.txt"
