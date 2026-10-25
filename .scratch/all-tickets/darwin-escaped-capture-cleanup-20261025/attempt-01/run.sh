#!/usr/bin/env bash
set -euo pipefail

repo=/Users/hoppworks/.codex/worktrees/darwin-capture-cleanup/rhai
evidence="$repo/.scratch/all-tickets/darwin-escaped-capture-cleanup-20261025/attempt-01"
source_dir="$AGENT_RUNTIME_DIR/source"
lock_source=/Users/hoppworks/projects/rhai/.scratch/all-tickets/darwin-drop-false-unchecked-20261009/attempt-06/Cargo.lock
expected_lock=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425

mkdir -p "$source_dir"
git -C "$repo" archive HEAD | tar -x -C "$source_dir"
cp "$lock_source" "$source_dir/Cargo.lock"
test "$(shasum -a 256 "$source_dir/Cargo.lock" | awk '{print $1}')" = "$expected_lock"
git -C "$repo" diff --binary HEAD -- tests/sys_process.rs | git -C "$source_dir" apply

export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=2
export PYTHONDONTWRITEBYTECODE=1

cd "$source_dir"
{
    printf 'candidate=%s\n' "$(git -C "$repo" rev-parse HEAD)"
    printf 'features=testing-environ,sys\n'
    printf 'cargo_build_jobs=%s\n' "$CARGO_BUILD_JOBS"
    printf 'lock_source=%s\n' "$lock_source"
    shasum -a 256 Cargo.lock Cargo.toml src/packages/sys/process/unix.rs tests/sys_process.rs
    uname -a
    sw_vers
    rustc +1.77.2 -Vv
    cargo +1.77.2 -V
} > "$evidence/source-bindings.txt"

run_case() {
    local name="$1"
    cargo +1.77.2 test --locked --features testing-environ,sys --test sys_process "$name" -- --exact --nocapture > "$evidence/$name.log" 2>&1 || {
        local status=$?
        printf '%s\n' "$status" > "$evidence/$name.status"
        tail -100 "$evidence/$name.log"
        return "$status"
    }
    printf '0\n' > "$evidence/$name.status"
    rg -Fq "test $name ... ok" "$evidence/$name.log"
}

run_case managed_escaped_fixture_cleanup_signals_only_exact_process_identity
run_case managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes
run_case managed_spawn_post_reap_cancel_bounds_escaped_capture

printf 'all targeted Darwin GREEN selectors passed; outer run_scoped status is recorded by the caller\n' > "$evidence/result.txt"
