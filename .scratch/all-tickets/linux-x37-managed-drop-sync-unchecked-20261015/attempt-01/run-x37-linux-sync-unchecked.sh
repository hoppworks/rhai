#!/usr/bin/env bash
set -Eeuo pipefail
repo=/var/home/Daniel/projects/rhai
attempt="$repo/.scratch/all-tickets/linux-x37-managed-drop-sync-unchecked-20261015/attempt-01"
evidence="$attempt/evidence"
scope="${1:?session scope required}"
runtime="${AGENT_RUNTIME_DIR:?scoped runner required}"
lock="$repo/.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock"
toolchain=/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
cargo="$toolchain/cargo"
test_name=managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not
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
features=testing-environ,sys,sync,unchecked
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
p=Path('tests/sys_process.rs')
s=p.read_text()
name='managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not'
start=s.index(f'fn {name}()')
end=s.find('\nfn ',start)
if end<0: end=len(s)
body=s[start:end]
old='assert!(sentinel_live, "final Child drop terminated the unrelated sentinel");'
new='assert!(!sentinel_live, "final Child drop terminated the unrelated sentinel");'
assert body.count(old)==1
p.write_text(s[:start]+body.replace(old,new,1)+s[end:])
PYMUT
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/red-source.sha256"
set +e
timeout 300s "$cargo" test --locked --features "$features" --test sys_process "$test_name" -- --exact --nocapture --test-threads=1 > "$evidence/red.log" 2>&1
red=$?
set -e
printf '%s\n' "$red" > "$evidence/red.status"
test "$red" -eq 101
grep -Fq 'test result: FAILED. 0 passed; 1 failed;' "$evidence/red.log"
grep -Fq 'final Child drop terminated the unrelated sentinel' "$evidence/red.log"
grep -Fq 'all_esrch=true' "$evidence/red.log"
grep -Fq 'live=true' "$evidence/red.log"
cp "$runtime/sys_process.rs.original" tests/sys_process.rs
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/green-source.sha256"
timeout 300s "$cargo" test --locked --features "$features" --test sys_process "$test_name" -- --exact --nocapture --test-threads=1 > "$evidence/green.log" 2>&1
printf '0\n' > "$evidence/green.status"
grep -Fq 'managed_spawn_nonfinal_drop' "$evidence/green.log"
grep -Fq 'all_live=true' "$evidence/green.log"
grep -Fq 'managed_spawn_final_drop' "$evidence/green.log"
grep -Fq 'all_esrch=true' "$evidence/green.log"
grep -Fq 'sentinel_cleanup' "$evidence/green.log"
grep -Fq 'esrch=true' "$evidence/green.log"
grep -Fq 'test result: ok. 1 passed; 0 failed;' "$evidence/green.log"
python3 "$attempt/postrun-readback.py" "$evidence/green.log" > "$evidence/external-readback.txt"
printf 'RED 101 at inverted sentinel assertion; restored GREEN 1/1; exact process/group readback passed\n' > "$evidence/result.txt"
