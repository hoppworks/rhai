#!/usr/bin/env bash
set -euo pipefail
repo=/var/home/Daniel/projects/rhai
evidence="$repo/.scratch/all-tickets/linux-x35-direct-managed-unchecked-20261015/attempt-02"
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
name = 'direct_run_returns_with_pipe_closed_worker_live_control'
start = s.index(f'fn {name}()')
end = s.find('\nfn ', start)
if end < 0:
    end = len(s)
body = s[start:end]
old = 'assert_managed_pidfds_live(&pidfds);'
new = 'assert_managed_pidfds_exited(&pidfds);'
assert body.count(old) == 1
p.write_text(s[:start] + body.replace(old, new, 1) + s[end:])
PY
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/red-source.sha256"
set +e
cargo test --locked --features testing-environ,sys,unchecked --test sys_process direct_run_returns_with_pipe_closed_worker_live_control -- --exact --nocapture --test-threads=1 > "$evidence/direct-red.log" 2>&1
red=$?
set -e
printf '%s\n' "$red" > "$evidence/direct-red.status"
test "$red" -eq 101
grep -Fq 'test result: FAILED. 0 passed; 1 failed;' "$evidence/direct-red.log"
grep -Fq 'remained live at API return' "$evidence/direct-red.log"
grep -Fq 'worker_esrch=true' "$evidence/direct-red.log"
grep -Fq 'leaf_esrch=true' "$evidence/direct-red.log"
grep -Fq 'leader_esrch=true' "$evidence/direct-red.log"
cp "$repo/tests/sys_process.rs" "$source_dir/tests/sys_process.rs"
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/green-source.sha256"
cargo test --locked --features testing-environ,sys,unchecked --test sys_process direct_run_returns_with_pipe_closed_worker_live_control -- --exact --nocapture --test-threads=1 > "$evidence/direct-green.log" 2>&1
printf '0\n' > "$evidence/direct-green.status"
cargo test --locked --features testing-environ,sys,unchecked --test sys_process managed_run_closes_pipe_closed_worker_before_return -- --exact --nocapture --test-threads=1 > "$evidence/managed-green.log" 2>&1
printf '0\n' > "$evidence/managed-green.status"
python3 - "$evidence" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
for name, selector in [
    ('direct-green.log', 'direct_run_returns_with_pipe_closed_worker_live_control'),
    ('managed-green.log', 'managed_run_closes_pipe_closed_worker_before_return'),
]:
    s = (root / name).read_text(errors='replace')
    assert f'test {selector} ...' in s
    assert 'test result: ok. 1 passed; 0 failed;' in s
    assert s.count('managed_pidfd_acquired pid=') == 3
    assert 'worker_esrch=true' in s and 'leaf_esrch=true' in s
    assert 'leader_esrch=true' in s
PY
sha256sum "$evidence"/*.log > "$evidence/logs.sha256"
