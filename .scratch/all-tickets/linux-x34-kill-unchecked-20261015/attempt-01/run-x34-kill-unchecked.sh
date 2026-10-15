#!/usr/bin/env bash
set -Eeuo pipefail
repo=/var/home/Daniel/projects/rhai
pkg="$repo/.scratch/all-tickets/linux-x34-kill-unchecked-20261015/attempt-01"
evidence="$pkg/evidence"
scope="${1:?owned session scope required}"
runtime="${AGENT_RUNTIME_DIR:?scoped runner required}"
lock="$repo/.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock"
toolchain=/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
cargo="$toolchain/cargo"
source_dir="$runtime/source"
features=testing-environ,sys,unchecked
test_name=managed_child_kill_reports_group_closed_under_fixture_reaper
mkdir -p "$source_dir"
git -C "$repo" archive HEAD | tar --no-same-owner -xf - -C "$source_dir"
cp "$lock" "$source_dir/Cargo.lock"
cp "$source_dir/tests/sys_process.rs" "$runtime/sys_process.rs.original"
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
  printf 'features=%s\nprofile=default\ntest=%s\n' "$features" "$test_name"
  "$cargo" --version
  "$RUSTC" -Vv
  sha256sum Cargo.toml Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs
  printf 'scope=%s\nruntime=%s\ncargo_jobs=1\n' "$scope" "$runtime"
} > "$evidence/environment.txt"
python3 - <<'PYMUT'
from pathlib import Path
p=Path('tests/sys_process.rs'); s=p.read_text()
old='assert!(killed_report, "public Child.kill report must record the killed child as unsuccessful");'
new='assert!(!killed_report, "RED_CONTROL: deliberately inverted public kill-report expectation");'
assert s.count(old)==1, s.count(old)
p.write_text(s.replace(old,new,1))
PYMUT
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/red-source.sha256"
run_test() {
 local phase="$1" expected="$2" rc start end
 start=$(date +%s%N)
 set +e
 timeout 300s "$cargo" test --locked --features "$features" --test sys_process "$test_name" -- --exact --nocapture --test-threads=1 > "$evidence/$phase.log" 2>&1
 rc=$?
 set -e
 end=$(date +%s%N)
 printf '%s_status=%s\n%s_elapsed_ms=%s\n' "$phase" "$rc" "$phase" "$(((end-start)/1000000))" >> "$evidence/statuses.txt"
 if [[ "$expected" == RED ]]; then
   test "$rc" -eq 101
   grep -Fq 'RED_CONTROL: deliberately inverted public kill-report expectation' "$evidence/$phase.log"
   grep -Fq 'test result: FAILED. 0 passed; 1 failed;' "$evidence/$phase.log"
 else
   test "$rc" -eq 0
   grep -Fq 'test result: ok. 1 passed; 0 failed;' "$evidence/$phase.log"
 fi
}
: > "$evidence/statuses.txt"
run_test red RED
grep -Fq 'managed_child_kill_live' "$evidence/red.log"
grep -Fq 'managed_child_kill_boundary' "$evidence/red.log"
for marker in 'leader_absent=true' 'worker_absent=true' 'leaf_absent=true' 'exact_descendants_reaped=true' 'sentinel_live_at_return=true' 'sentinel_reaped_after_return=true' 'api_bound=true' 'report_returned=true' 'killed_report=true' 'capture_complete=true' 'pidfds_exited=true' 'reaper_ok=true' 'host_absent_after_cleanup=true' 'group_empty=true'; do grep -Fq "$marker" "$evidence/red.log"; done
cp "$runtime/sys_process.rs.original" tests/sys_process.rs
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/green-source.sha256"
run_test green GREEN
grep -Fq 'managed_child_kill_live' "$evidence/green.log"
grep -Fq 'managed_child_kill_boundary' "$evidence/green.log"
for marker in 'leader_absent=true' 'worker_absent=true' 'leaf_absent=true' 'exact_descendants_reaped=true' 'sentinel_live_at_return=true' 'sentinel_reaped_after_return=true' 'api_bound=true' 'report_returned=true' 'killed_report=true' 'capture_complete=true' 'pidfds_exited=true' 'reaper_ok=true' 'host_absent_after_cleanup=true' 'group_empty=true'; do grep -Fq "$marker" "$evidence/green.log"; done
printf 'Public Child.kill row: assertion RED=101; restored unchecked-profile GREEN=1/1; exact process/group and fixture readbacks recorded.\n' > "$evidence/result.txt"
