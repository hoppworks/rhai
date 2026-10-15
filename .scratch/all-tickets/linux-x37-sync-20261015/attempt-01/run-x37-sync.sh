#!/usr/bin/env bash
set -Eeuo pipefail
repo=/var/home/Daniel/projects/rhai
pkg="$repo/.scratch/all-tickets/linux-x37-sync-20261015/attempt-01"
evidence="$pkg/evidence"
scope="${1:?owned session scope required}"
runtime="${AGENT_RUNTIME_DIR:?scoped runner required}"
lock="$repo/.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock"
toolchain=/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
cargo="$toolchain/cargo"
source_dir="$runtime/source"
features=testing-environ,sys,sync
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
  printf 'features=%s\nprofile=default\n' "$features"
  "$cargo" --version
  "$RUSTC" -Vv
  sha256sum Cargo.toml Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs
  printf 'scope=%s\nruntime=%s\ncargo_jobs=1\n' "$scope" "$runtime"
} > "$evidence/environment.txt"
python3 - <<'PYMUT'
from pathlib import Path
p=Path('tests/sys_process.rs'); s=p.read_text()
old='assert!(sentinel_live, "final Child drop terminated the unrelated sentinel");'
new='assert!(!sentinel_live, "RED_CONTROL: deliberately inverted sentinel-live expectation");'
assert s.count(old)==1, s.count(old)
p.write_text(s.replace(old,new,1))
PYMUT
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/red-source.sha256"
: > "$evidence/statuses.txt"
run_test() {
 local phase="$1" expected="$2" rc start end
 start=$(date +%s%N)
 set +e
 timeout 300s "$cargo" test --locked --features "$features" --test sys_process managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not -- --exact --nocapture --test-threads=1 > "$evidence/$phase.log" 2>&1
 rc=$?
 set -e
 end=$(date +%s%N)
 printf '%s_status=%s\n%s_elapsed_ms=%s\n' "$phase" "$rc" "$phase" "$(((end-start)/1000000))" >> "$evidence/statuses.txt"
 if [[ "$expected" == RED ]]; then
   test "$rc" -eq 101
   grep -Fq 'RED_CONTROL: deliberately inverted sentinel-live expectation' "$evidence/$phase.log"
   grep -Fq 'test result: FAILED. 0 passed; 1 failed;' "$evidence/$phase.log"
 else
   test "$rc" -eq 0
   grep -Fq 'test result: ok. 1 passed; 0 failed;' "$evidence/$phase.log"
 fi
}
run_test red RED
grep -Fq 'managed_spawn_nonfinal_drop' "$evidence/red.log"
grep -Fq 'all_live=true' "$evidence/red.log"
grep -Fq 'managed_spawn_final_drop' "$evidence/red.log"
grep -Fq 'all_esrch=true' "$evidence/red.log"
grep -Fq 'live=true' "$evidence/red.log"
cp "$runtime/sys_process.rs.original" tests/sys_process.rs
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/green-source.sha256"
run_test green GREEN
grep -Fq 'managed_spawn_nonfinal_drop' "$evidence/green.log"
grep -Fq 'all_live=true' "$evidence/green.log"
grep -Fq 'managed_spawn_final_drop' "$evidence/green.log"
grep -Fq 'all_esrch=true' "$evidence/green.log"
grep -Fq 'live=true' "$evidence/green.log"
printf 'Final clone drop: sentinel-live assertion RED=101; restored X37 sync GREEN=1/1 with exact managed-group and sentinel observations.\n' > "$evidence/result.txt"
