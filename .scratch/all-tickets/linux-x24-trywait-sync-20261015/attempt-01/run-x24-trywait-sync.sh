#!/usr/bin/env bash
set -Eeuo pipefail
repo=/var/home/Daniel/projects/rhai
pkg=$repo/.scratch/all-tickets/linux-x24-trywait-sync-20261015/attempt-01
evidence=$pkg/evidence
scope=$1
runtime=$AGENT_RUNTIME_DIR
lock=$repo/.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock
toolchain=/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
cargo=$toolchain/cargo
source_dir=$runtime/source
mkdir -p "$source_dir" "$evidence"
git -C "$repo" archive HEAD | tar --no-same-owner -xf - -C "$source_dir"
cp "$lock" "$source_dir/Cargo.lock"
cp "$source_dir/tests/sys_process.rs" "$runtime/sys_process.rs.original"
cd "$source_dir"
export CARGO_TARGET_DIR=$runtime/target CARGO_HOME=$runtime/cargo-home
export CARGO_BUILD_JOBS=1 CARGO_TERM_COLOR=never
export RUSTC=$toolchain/rustc RUSTDOC=$toolchain/rustdoc RUSTUP_HOME=/home/Daniel/.rustup
export PATH=$toolchain:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1
{
 printf 'revision='; git -C "$repo" rev-parse HEAD
 date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
 uname -a
 cat /etc/os-release
 printf 'selector=direct_spawn_try_wait_returns_unit_until_child_exits\nprofiles=testing-environ,sys,sync;testing-environ,sys,sync,unchecked\n'
 "$cargo" --version
 "$RUSTC" -Vv
 sha256sum Cargo.toml Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs
 printf 'scope=%s\nruntime=%s\ncargo_jobs=1\n' "$scope" "$runtime"
} > "$evidence/environment.txt"
: > "$evidence/statuses.txt"
mutate_expected_code() {
python3 - <<'PYMUT'
from pathlib import Path
p=Path('tests/sys_process.rs'); s=p.read_text()
old='    assert_eq!(terminal_code, 0, "try_wait directly observes the natural exit result");'
new='    assert_eq!(terminal_code, 1, "try_wait directly observes the natural exit result");'
assert s.count(old)==1, s.count(old)
p.write_text(s.replace(old,new,1))
PYMUT
}
run_test() {
 label=$1; features=$2; expected=$3
 start=$(date +%s%N)
 set +e
 timeout 300s "$cargo" test --locked --features "$features" --test sys_process direct_spawn_try_wait_returns_unit_until_child_exits -- --exact --nocapture --test-threads=1 > "$evidence/$label.log" 2>&1
 rc=$?
 set -e
 end=$(date +%s%N)
 printf '%s_status=%s\n%s_elapsed_ms=%s\n' "$label" "$rc" "$label" "$(((end-start)/1000000))" >> "$evidence/statuses.txt"
 if [ "$expected" = RED ]; then
  test "$rc" -eq 101
  grep -Fq 'try_wait directly observes the natural exit result' "$evidence/$label.log"
  grep -Fq 'test result: FAILED. 0 passed; 1 failed;' "$evidence/$label.log"
 else
  test "$rc" -eq 0
  grep -Fq 'test result: ok. 1 passed; 0 failed;' "$evidence/$label.log"
  grep -Fq 'x24_running' "$evidence/$label.log"
  grep -Fq 'x24_post_exit_try_wait' "$evidence/$label.log"
  grep -Fq 'x24_finished' "$evidence/$label.log"
  grep -Fq 'reaped_esrch=true' "$evidence/$label.log"
 fi
}
for profile in checked_sync unchecked_sync; do
 if [ "$profile" = checked_sync ]; then features=testing-environ,sys,sync; else features=testing-environ,sys,sync,unchecked; fi
 cp "$runtime/sys_process.rs.original" tests/sys_process.rs
 mutate_expected_code
 sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/$profile-red-source.sha256"
 run_test "$profile-red" "$features" RED
 cp "$runtime/sys_process.rs.original" tests/sys_process.rs
 sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/$profile-green-source.sha256"
 run_test "$profile-green" "$features" GREEN
done
cp "$runtime/sys_process.rs.original" tests/sys_process.rs
printf 'The public try_wait/cached-wait selector passed assertion RED=101 and restored GREEN=1/1 in checked and unchecked sync profiles, with real child readiness, terminal result and ESRCH readback.\n' > "$evidence/result.txt"
