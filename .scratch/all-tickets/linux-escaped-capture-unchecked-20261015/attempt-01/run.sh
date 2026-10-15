#!/usr/bin/env bash
set -euo pipefail
repo=/var/home/Daniel/projects/rhai
evidence="$repo/.scratch/all-tickets/linux-escaped-capture-unchecked-20261015/attempt-01"
source_dir="$AGENT_RUNTIME_DIR/source"
mkdir -p "$source_dir"
git -C "$repo" archive HEAD | tar -x -C "$source_dir"
cp "$evidence/source-Cargo.lock" "$source_dir/Cargo.lock"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=1
export PYTHONDONTWRITEBYTECODE=1
cd "$source_dir"
python3 - <<'PY'
from pathlib import Path
p = Path('tests/sys_process.rs')
s = p.read_text()
mutations = {
    'managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes': (
        'assert!(holder_live_after_wait && sentinel_live_after_wait && sentinel_pgid_matches, "fixture must prove the escaped holder remains operational in the unrelated sentinel group");',
        'assert!(!(holder_live_after_wait && sentinel_live_after_wait && sentinel_pgid_matches), "fixture must prove the escaped holder remains operational in the unrelated sentinel group");',
    ),
    'managed_spawn_post_reap_cancel_bounds_escaped_capture': (
        'assert!(!result.is_unit(), "post-reap cancellation must return a report");',
        'assert!(result.is_unit(), "post-reap cancellation must return a report");',
    ),
}
for name, (old, new) in mutations.items():
    start = s.index(f'fn {name}()')
    end = s.find('\nfn ', start)
    if end < 0:
        end = len(s)
    body = s[start:end]
    assert body.count(old) == 1, f'{name}: expected exactly one mutation anchor'
    s = s[:start] + body.replace(old, new, 1) + s[end:]
p.write_text(s)
PY
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/red-source.sha256"
set +e
cargo +1.77.2 test --locked --features testing-environ,sys,unchecked --test sys_process managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes -- --exact --nocapture --test-threads=1 > "$evidence/x38-red.log" 2>&1
x38_red=$?
set -e
printf '%s\n' "$x38_red" > "$evidence/x38-red.status"
test "$x38_red" -eq 101
grep -Fq 'fixture must prove the escaped holder remains operational in the unrelated sentinel group' "$evidence/x38-red.log"
grep -Fq 'managed_escaped_pipe_terminal' "$evidence/x38-red.log"
grep -Fq 'holder_esrch=true' "$evidence/x38-red.log"
grep -Fq 'sentinel_esrch=true' "$evidence/x38-red.log"
set +e
cargo +1.77.2 test --locked --features testing-environ,sys,unchecked --test sys_process managed_spawn_post_reap_cancel_bounds_escaped_capture -- --exact --nocapture --test-threads=1 > "$evidence/post-reap-red.log" 2>&1
post_red=$?
set -e
printf '%s\n' "$post_red" > "$evidence/post-reap-red.status"
test "$post_red" -eq 101
grep -Fq 'post-reap cancellation must return a report' "$evidence/post-reap-red.log"
grep -Fq 'managed_post_reap_uncancelled_wait' "$evidence/post-reap-red.log"
grep -Fq 'managed_escaped_pipe_terminal' "$evidence/post-reap-red.log"
grep -Fq 'holder_esrch=true' "$evidence/post-reap-red.log"
grep -Fq 'sentinel_esrch=true' "$evidence/post-reap-red.log"
git -C "$repo" show HEAD:tests/sys_process.rs > tests/sys_process.rs
sha256sum Cargo.lock src/packages/sys/process/unix.rs tests/sys_process.rs > "$evidence/green-source.sha256"
cargo +1.77.2 test --locked --features testing-environ,sys,unchecked --test sys_process managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes -- --exact --nocapture --test-threads=1 > "$evidence/x38-green.log" 2>&1
printf '0\n' > "$evidence/x38-green.status"
grep -Fq 'managed_escaped_pipe_terminal' "$evidence/x38-green.log"
grep -Fq 'test managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes ... ok' "$evidence/x38-green.log"
cargo +1.77.2 test --locked --features testing-environ,sys,unchecked --test sys_process managed_spawn_post_reap_cancel_bounds_escaped_capture -- --exact --nocapture --test-threads=1 > "$evidence/post-reap-green.log" 2>&1
printf '0\n' > "$evidence/post-reap-green.status"
grep -Fq 'managed_post_reap_uncancelled_wait' "$evidence/post-reap-green.log"
grep -Fq 'managed_escaped_pipe_terminal' "$evidence/post-reap-green.log"
grep -Fq 'test managed_spawn_post_reap_cancel_bounds_escaped_capture ... ok' "$evidence/post-reap-green.log"
printf 'HEAD=%s\n' "$(git -C "$repo" rev-parse HEAD)" > "$evidence/environment.txt"
uname -a >> "$evidence/environment.txt"
cat /etc/os-release >> "$evidence/environment.txt"
rustc +1.77.2 -Vv >> "$evidence/environment.txt"
cargo +1.77.2 -V >> "$evidence/environment.txt"
printf 'features=testing-environ,sys,unchecked\nprofile=default\n' >> "$evidence/environment.txt"
sha256sum "$evidence"/*.log > "$evidence/logs.sha256"
