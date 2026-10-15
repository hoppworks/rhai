#!/usr/bin/env bash
set -euo pipefail
repo=/var/home/Daniel/projects/rhai
evidence="$repo/.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02"
source_dir="$AGENT_RUNTIME_DIR/source"
mkdir -p "$source_dir"
git -C "$repo" archive HEAD | tar -x -C "$source_dir"
cp "$repo/tests/sys_process.rs" "$source_dir/tests/sys_process.rs"
cp "$evidence/source-Cargo.lock" "$source_dir/Cargo.lock"
cp "$repo/tests/sys_process.rs" "$evidence/test-source-restored.rs"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=1
export PYTHONDONTWRITEBYTECODE=1
cd "$source_dir"
python3 - <<'PY'
from pathlib import Path
p = Path("tests/sys_process.rs")
s = p.read_text()
name = "direct_run_returns_with_pipe_closed_worker_live_control"
start = s.index(f"fn {name}()")
end = s.find("\nfn ", start)
if end < 0:
    end = len(s)
body = s[start:end]
old = "assert_managed_pidfds_live(&pidfds);"
new = "assert_managed_pidfds_exited(&pidfds);"
assert body.count(old) == 1
p.write_text(s[:start] + body.replace(old, new, 1) + s[end:])
PY
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/red-source.sha256"
set +e
cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process direct_run_returns_with_pipe_closed_worker_live_control -- --exact --nocapture --test-threads=1 > "$evidence/direct-red.log" 2>&1
red=$?
set -e
printf '%s\n' "$red" > "$evidence/direct-red.status"
test "$red" -eq 101
grep -Fq "remained live at API return" "$evidence/direct-red.log"
cp "$evidence/test-source-restored.rs" tests/sys_process.rs
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/green-source.sha256"
cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process direct_run_returns_with_pipe_closed_worker_live_control -- --exact --nocapture --test-threads=1 > "$evidence/direct-green.log" 2>&1
printf '0\n' > "$evidence/direct-green.status"
cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process managed_run_closes_pipe_closed_worker_before_return -- --exact --nocapture --test-threads=1 > "$evidence/managed-green.log" 2>&1
printf '0\n' > "$evidence/managed-green.status"
python3 - "$evidence" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
for name, selector, markers in [
    ("direct-green.log", "direct_run_returns_with_pipe_closed_worker_live_control", ["pidfd", "live"]),
    ("managed-green.log", "managed_run_closes_pipe_closed_worker_before_return", ["pidfd", "exited"]),
]:
    s = (root / name).read_text(errors="replace")
    assert selector in s
    assert "test result: ok. 1 passed; 0 failed" in s
    assert all(marker in s for marker in markers)
PY
printf 'HEAD=%s\n' "$(git -C "$repo" rev-parse HEAD)" > "$evidence/environment.txt"
uname -a >> "$evidence/environment.txt"
cat /etc/os-release >> "$evidence/environment.txt"
rustc +1.77.2 -Vv >> "$evidence/environment.txt"
cargo +1.77.2 -V >> "$evidence/environment.txt"
printf 'features=testing-environ,sys\nprofile=default\n' >> "$evidence/environment.txt"
sha256sum "$evidence"/*.log > "$evidence/logs.sha256"
