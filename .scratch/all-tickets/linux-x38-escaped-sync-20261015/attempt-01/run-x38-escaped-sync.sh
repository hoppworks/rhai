#!/usr/bin/env bash
set -Eeuo pipefail
repo=/var/home/Daniel/projects/rhai
pkg="$repo/.scratch/all-tickets/linux-x38-escaped-sync-20261015/attempt-01"
evidence="$pkg/evidence"
scope="${1:?owned session scope required}"
runtime="${AGENT_RUNTIME_DIR:?scoped runner required}"
lock="$repo/.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock"
toolchain=/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
cargo="$toolchain/cargo"
source_dir="$runtime/source"
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
  printf 'selectors=managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes;managed_spawn_post_reap_cancel_bounds_escaped_capture\nprofiles=testing-environ,sys,sync;testing-environ,sys,sync,unchecked\n'
  "$cargo" --version
  "$RUSTC" -Vv
  sha256sum Cargo.toml Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs
  printf 'scope=%s\nruntime=%s\ncargo_jobs=1\n' "$scope" "$runtime"
} > "$evidence/environment.txt"
: > "$evidence/statuses.txt"
mutate_assertion() {
python3 - "$1" <<'PYMUT'
from pathlib import Path
import sys
p=Path('tests/sys_process.rs'); s=p.read_text()
if sys.argv[1] == 'kill_capture':
    old='assert!(holder_live_after_wait && sentinel_live_after_wait && sentinel_pgid_matches, "fixture must prove the escaped holder remains operational in the unrelated sentinel group");'
    new='assert!(!(holder_live_after_wait && sentinel_live_after_wait && sentinel_pgid_matches), "RED_CONTROL: deliberately inverted escaped-holder liveness expectation");'
elif sys.argv[1] == 'post_reap':
    old='assert!(!result.is_unit(), "post-reap cancellation must return a report");'
    new='assert!(result.is_unit(), "RED_CONTROL: deliberately inverted post-reap report expectation");'
else:
    raise SystemExit('unknown selector '+sys.argv[1])
assert s.count(old)==1, (sys.argv[1],s.count(old))
p.write_text(s.replace(old,new,1))
PYMUT
}
run_test() {
 local label="$1" features="$2" test_name="$3" case="$4" expected="$5" rc start end
 start=$(date +%s%N)
 set +e
 timeout 300s "$cargo" test --locked --features "$features" --test sys_process "$test_name" -- --exact --nocapture --test-threads=1 > "$evidence/$label.log" 2>&1
 rc=$?
 set -e
 end=$(date +%s%N)
 printf '%s_status=%s\n%s_elapsed_ms=%s\n' "$label" "$rc" "$label" "$(((end-start)/1000000))" >> "$evidence/statuses.txt"
 if [[ "$expected" == RED ]]; then
   test "$rc" -eq 101
   grep -Fq 'RED_CONTROL: deliberately inverted' "$evidence/$label.log"
   grep -Fq 'test result: FAILED. 0 passed; 1 failed;' "$evidence/$label.log"
 else
   test "$rc" -eq 0
   grep -Fq 'test result: ok. 1 passed; 0 failed;' "$evidence/$label.log"
 fi
 if [[ "$case" == kill_capture ]]; then
   grep -Fq 'managed_escaped_pipe_wait' "$evidence/$label.log"
   grep -Fq 'managed_escaped_pipe_terminal' "$evidence/$label.log"
   for marker in 'leader_esrch=true' 'holder_live_after_wait=true' 'sentinel_live_after_wait=true' 'identity_ok=true' 'holder_esrch=true' 'sentinel_esrch=true' 'stdout_error=32' 'stderr_error=32'; do grep -Fq "$marker" "$evidence/$label.log"; done
 else
   grep -Fq 'managed_post_reap_cancel' "$evidence/$label.log"
   grep -Fq 'managed_escaped_pipe_terminal' "$evidence/$label.log"
   for marker in 'leader_esrch_before_kill=true' 'holder_live_after_cancel=true' 'leader_esrch=true' 'holder_esrch=true' 'sentinel_esrch=true' 'stdout_error=32' 'stderr_error=32'; do grep -Fq "$marker" "$evidence/$label.log"; done
 fi
}
for profile in checked_sync unchecked_sync; do
  if [[ "$profile" == checked_sync ]]; then features=testing-environ,sys,sync; else features=testing-environ,sys,sync,unchecked; fi
  for case in kill_capture post_reap; do
    if [[ "$case" == kill_capture ]]; then test_name=managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes; else test_name=managed_spawn_post_reap_cancel_bounds_escaped_capture; fi
    cp "$runtime/sys_process.rs.original" tests/sys_process.rs
    mutate_assertion "$case"
    sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/$profile-$case-red-source.sha256"
    run_test "$profile-$case-red" "$features" "$test_name" "$case" RED
    cp "$runtime/sys_process.rs.original" tests/sys_process.rs
    sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/$profile-$case-green-source.sha256"
    run_test "$profile-$case-green" "$features" "$test_name" "$case" GREEN
  done
done
cp "$runtime/sys_process.rs.original" tests/sys_process.rs
printf 'Both escaped-pipe selectors passed assertion RED=101 and restored GREEN=1/1 in checked and unchecked sync profiles; independent holder/leader/sentinel and EPIPE readbacks recorded.\n' > "$evidence/result.txt"
