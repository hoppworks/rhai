#!/usr/bin/env bash
set -u
: "${AGENT_RUNTIME_DIR:?run via tools/run_scoped.py}"
repo=$(git rev-parse --show-toplevel)
revision=$(git rev-parse HEAD)
evidence="$repo/.scratch/combined-package-proof/logs"
source="$AGENT_RUNTIME_DIR/source"
mkdir -p "$source" "$evidence"
git archive "$revision" | tar -x -C "$source"
mkdir -p "$source/tests"
cp "$repo/tests/combined_sys_net.rs" "$source/tests/combined_sys_net.rs"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_BUILD_JOBS=2
export CARGO_PROFILE_DEV_DEBUG=0
cd "$source"
features=testing-environ,sys,net
test_name=sys_and_net_packages_coexist_in_one_engine_with_os_readback_and_typed_errors
printf 'Source revision: %s + worktree integration test\n' "$revision" > "$evidence/targeted-environment.txt"
uname -a >> "$evidence/targeted-environment.txt"
sw_vers >> "$evidence/targeted-environment.txt"
rustc --version >> "$evidence/targeted-environment.txt"
cargo --version >> "$evidence/targeted-environment.txt"
printf 'Runtime: %s; private Cargo home/target; jobs=2\n' "$AGENT_RUNTIME_DIR" >> "$evidence/targeted-environment.txt"
control_status=0
RHAI_COMBINED_WRONG_EXPECTATION=1 cargo test --features "$features" --test combined_sys_net -- --exact "$test_name" --test-threads=1 --nocapture > "$evidence/false-green-control.log" 2>&1 || control_status=$?
printf 'Control exit status: %s\n' "$control_status" >> "$evidence/false-green-control.log"
cat "$evidence/false-green-control.log"
if [[ "$control_status" -eq 0 ]]; then echo 'false-green control unexpectedly passed' >&2; exit 40; fi
if ! rg -q 'fresh host readback must match independent expected bytes' "$evidence/false-green-control.log"; then echo 'false-green control failed before intended assertion' >&2; exit 41; fi
printf 'Control accepted: failed at deliberately incorrect independent host readback.\n' >> "$evidence/false-green-control.log"
green_status=0
cargo test --features "$features" --test combined_sys_net -- --exact "$test_name" --test-threads=1 --nocapture > "$evidence/targeted-green.log" 2>&1 || green_status=$?
printf 'Green exit status: %s\n' "$green_status" >> "$evidence/targeted-green.log"
cat "$evidence/targeted-green.log"
exit "$green_status"
