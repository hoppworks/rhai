#!/usr/bin/env bash
set -Eeuo pipefail
repo=/Users/hoppworks/.codex/worktrees/darwin-capture-cleanup/rhai
attempt="$repo/.scratch/all-tickets/darwin-pipeclosed-20261025/attempt-01"
evidence="$attempt/evidence"
revision=9527d655c715348da519e414f55a7fa3207550c2
source_dir="$AGENT_RUNTIME_DIR/source"
mkdir -p "$source_dir" "$evidence"
git -C "$repo" archive "$revision" | tar -x -C "$source_dir"
cp "$repo/.scratch/all-tickets/core-current-msrv-evidence-04/Cargo.lock" "$source_dir/Cargo.lock"
git -C "$source_dir" apply "$attempt/owned.patch"
cd "$source_dir"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home" CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_BUILD_JOBS=2 CARGO_TERM_COLOR=never PYTHONDONTWRITEBYTECODE=1
test "$(shasum -a 256 Cargo.lock | awk '{print $1}')" = 2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
{
  date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
  printf 'revision=%s\nruntime=%s\nTMPDIR=%s\nouter_timeout_seconds=600\ncargo_jobs=2\n' "$revision" "$AGENT_RUNTIME_DIR" "$TMPDIR"
  uname -a
  sw_vers
  rustc +1.77.2 -Vv
  cargo +1.77.2 -V
  shasum -a 256 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py
  sdk_path=$(/usr/bin/xcrun --show-sdk-path)
  shasum -a 256 "$sdk_path/usr/include/libproc.h" "$sdk_path/usr/include/sys/proc_info.h"
} > "$evidence/environment.txt"
shasum -a 256 Cargo.toml Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs "$attempt/owned.patch" > "$evidence/source-hashes.txt"
cp tests/sys_process.rs "$AGENT_RUNTIME_DIR/sys_process.correct.rs"
correct_sha=$(shasum -a 256 tests/sys_process.rs | awk '{print $1}')
python3 - <<'PY'
from pathlib import Path
p=Path('tests/sys_process.rs')
s=p.read_text()
old='fn darwin_managed_run_closes_pipe_closed_descendants_before_return() {\n    assert_darwin_pipe_closed_scope(ProcessScope::Managed, true);\n}'
assert s.count(old)==1
p.write_text(s.replace(old, old.replace('ProcessScope::Managed', 'ProcessScope::DirectChild')))
PY
shasum -a 256 tests/sys_process.rs > "$evidence/known-broken-source.sha256"
diff -u "$AGENT_RUNTIME_DIR/sys_process.correct.rs" tests/sys_process.rs > "$evidence/known-broken.patch" || test "$?" -eq 1
printf 'phase\tfeatures\tselector\texit\n' > "$evidence/statuses.tsv"
managed=darwin_managed_run_closes_pipe_closed_descendants_before_return
direct=darwin_direct_run_returns_with_pipe_closed_descendants_live
rc=0
cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process "$managed" -- --exact --nocapture --test-threads=1 > "$evidence/known-broken-red.log" 2>&1 || rc=$?
printf 'red\ttesting-environ,sys\t%s\t%s\n' "$managed" "$rc" >> "$evidence/statuses.tsv"
test "$rc" -eq 101
rg -Fq 'managed scope must close pipe-closed descendants before API return' "$evidence/known-broken-red.log"
rg -Fq 'test result: FAILED. 0 passed; 1 failed;' "$evidence/known-broken-red.log"
cp "$AGENT_RUNTIME_DIR/sys_process.correct.rs" tests/sys_process.rs
test "$(shasum -a 256 tests/sys_process.rs | awk '{print $1}')" = "$correct_sha"
shasum -a 256 tests/sys_process.rs > "$evidence/restored-source.sha256"
rc=0
cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process -- --nocapture --test-threads=1 > "$evidence/base-regression-green.log" 2>&1 || rc=$?
printf 'green\ttesting-environ,sys\tfull-sys_process-target\t%s\n' "$rc" >> "$evidence/statuses.tsv"
test "$rc" -eq 0
rg -Fq "$managed" "$evidence/base-regression-green.log"
rg -Fq "$direct" "$evidence/base-regression-green.log"
rg -Fq 'test result: ok.' "$evidence/base-regression-green.log"
for features in testing-environ,sys,sync testing-environ,sys,unchecked testing-environ,sys,sync,unchecked; do
  for name in "$managed" "$direct"; do
    log="$evidence/${features//,/_}-$name.log"
    rc=0
    cargo +1.77.2 test --locked --features "$features" --test sys_process "$name" -- --exact --nocapture --test-threads=1 > "$log" 2>&1 || rc=$?
    printf 'green\t%s\t%s\t%s\n' "$features" "$name" "$rc" >> "$evidence/statuses.tsv"
    test "$rc" -eq 0
    rg -Fq 'test result: ok. 1 passed; 0 failed;' "$log"
  done
done
printf 'known-broken DirectChild control failed at intended managed contract; restored full base target and both new tests in all four profiles passed\n' > "$evidence/result.txt"
