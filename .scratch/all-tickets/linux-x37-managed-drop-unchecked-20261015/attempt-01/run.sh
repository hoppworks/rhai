#!/usr/bin/env bash
set -euo pipefail
repo=/var/home/Daniel/projects/rhai
evidence="$repo/.scratch/all-tickets/linux-x37-managed-drop-unchecked-20261015/attempt-01"
source_dir="$AGENT_RUNTIME_DIR/source"
toolchain=/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
export PATH="$toolchain:/usr/bin:/bin"
export RUSTC="$toolchain/rustc"
export RUSTUP_HOME=/home/Daniel/.rustup
mkdir -p "$source_dir"
git -C "$repo" archive HEAD | tar -x -C "$source_dir"
cp "$repo/tests/sys_process.rs" "$source_dir/tests/sys_process.rs"
cp "$repo/.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock" "$source_dir/Cargo.lock"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=1
export PYTHONDONTWRITEBYTECODE=1
cd "$source_dir"
{
  printf 'HEAD=%s\n' "$(git -C "$repo" rev-parse HEAD)"
  uname -a
  cat /etc/os-release
  rustc -Vv
  cargo -V
  printf 'features=testing-environ,sys,unchecked\nprofile=default\n'
  sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs
} > "$evidence/environment.txt"
python3 - <<'PY'
from pathlib import Path
p = Path('tests/sys_process.rs')
s = p.read_text()
name = 'managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not'
start = s.index(f'fn {name}()')
end = s.find('\nfn ', start)
if end < 0:
    end = len(s)
body = s[start:end]
old = 'assert!(sentinel_live, "final Child drop terminated the unrelated sentinel");'
new = 'assert!(!sentinel_live, "final Child drop terminated the unrelated sentinel");'
assert body.count(old) == 1
p.write_text(s[:start] + body.replace(old, new, 1) + s[end:])
PY
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/red-source.sha256"
set +e
cargo test --locked --features testing-environ,sys,unchecked --test sys_process managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not -- --exact --nocapture --test-threads=1 > "$evidence/red.log" 2>&1
red=$?
set -e
printf '%s\n' "$red" > "$evidence/red.status"
test "$red" -eq 101
grep -Fq 'test result: FAILED. 0 passed; 1 failed;' "$evidence/red.log"
grep -Fq 'final Child drop terminated the unrelated sentinel' "$evidence/red.log"
grep -Fq 'all_esrch=true' "$evidence/red.log"
grep -Fq 'sentinel_cleanup' "$evidence/red.log"
grep -Fq 'esrch=true' "$evidence/red.log"
cp "$repo/tests/sys_process.rs" tests/sys_process.rs
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/green-source.sha256"
cargo test --locked --features testing-environ,sys,unchecked --test sys_process managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not -- --exact --nocapture --test-threads=1 > "$evidence/green.log" 2>&1
printf '0\n' > "$evidence/green.status"
python3 - "$evidence" <<'PY'
from pathlib import Path
import sys
s = (Path(sys.argv[1]) / 'green.log').read_text(errors='replace')
assert 'test managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not ...' in s
assert 'managed_spawn_nonfinal_drop' in s and 'all_live=true' in s
assert 'managed_spawn_final_drop' in s and 'all_esrch=true' in s
assert 'sentinel_pgid=' in s and 'sentinel=' in s and 'live=true' in s
assert 'sentinel_cleanup' in s and 'esrch=true' in s
assert 'test result: ok. 1 passed; 0 failed;' in s
PY
sha256sum "$evidence"/*.log > "$evidence/logs.sha256"
