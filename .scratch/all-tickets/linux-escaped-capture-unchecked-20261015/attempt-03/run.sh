#!/usr/bin/env bash
set -euo pipefail
repo=/var/home/Daniel/projects/rhai
evidence="$repo/.scratch/all-tickets/linux-escaped-capture-unchecked-20261015/attempt-03"
source_dir="$AGENT_RUNTIME_DIR/source"
mkdir -p "$source_dir"
git -C "$repo" archive HEAD | tar -x -C "$source_dir"
cp "$repo/tests/sys_process.rs" "$source_dir/tests/sys_process.rs"
cp "$repo/tests/sys_process.rs" "$evidence/test-source-restored.rs"
cp "$evidence/source-Cargo.lock" "$source_dir/Cargo.lock"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=1
export PYTHONDONTWRITEBYTECODE=1
cd "$source_dir"
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/source.sha256"
cargo +1.77.2 test --locked --features testing-environ,sys,unchecked --test sys_process managed_spawn_post_reap_cancel_bounds_escaped_capture -- --exact --nocapture --test-threads=1 > "$evidence/post-reap-green.log" 2>&1
printf '0\n' > "$evidence/post-reap-green.status"
grep -Fq 'test managed_spawn_post_reap_cancel_bounds_escaped_capture' "$evidence/post-reap-green.log"
grep -Fq 'test result: ok. 1 passed; 0 failed' "$evidence/post-reap-green.log"
grep -Fq 'managed_post_reap_uncancelled_wait' "$evidence/post-reap-green.log"
grep -Fq 'managed_escaped_pipe_terminal' "$evidence/post-reap-green.log"
grep -Fq 'holder_live_after_cancel=true' "$evidence/post-reap-green.log"
grep -Fq 'stdout_error=32 stderr_result=-1 stderr_error=32' "$evidence/post-reap-green.log"
printf 'HEAD=%s\n' "$(git -C "$repo" rev-parse HEAD)" > "$evidence/environment.txt"
uname -a >> "$evidence/environment.txt"
cat /etc/os-release >> "$evidence/environment.txt"
rustc +1.77.2 -Vv >> "$evidence/environment.txt"
cargo +1.77.2 -V >> "$evidence/environment.txt"
printf 'features=testing-environ,sys,unchecked\nprofile=default\n' >> "$evidence/environment.txt"
sha256sum "$evidence/post-reap-green.log" > "$evidence/logs.sha256"
