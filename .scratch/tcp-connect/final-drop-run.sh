set -eu
repo_root="$PWD"
export CARGO_BUILD_JOBS=2 CARGO_PROFILE_DEV_DEBUG=0
python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py -- bash -c '
set -u
runtime="$AGENT_RUNTIME_DIR"
export CARGO_HOME="$runtime/cargo-home" CARGO_TARGET_DIR="$runtime/target"
mkdir -p "$CARGO_HOME" "$CARGO_TARGET_DIR"
tar --exclude=.git --exclude=target --exclude=.scratch -cf - -C "$1" . | tar -xf - -C "$runtime"
cd "$runtime"
printf "source-copy=%s\\n" "$PWD"
printf "CARGO_HOME=%s\\nCARGO_TARGET_DIR=%s\\n" "$CARGO_HOME" "$CARGO_TARGET_DIR"
set +e
cargo test --features net --test net_connect -- --nocapture > "$1/.scratch/tcp-connect/final-drop-net.log" 2>&1
net_status=$?
cargo test --features "net,sync" --test net_connect -- --nocapture > "$1/.scratch/tcp-connect/final-drop-sync.log" 2>&1
sync_status=$?
RHAI_NET_WRONG_EXPECTATION=1 cargo test --features net --test net_connect authorized_connect_is_observed_and_clone_close_is_shared -- --nocapture > "$1/.scratch/tcp-connect/final-drop-control.log" 2>&1
control_status=$?
set -e
printf "net status=%s; sync status=%s; control status=%s\\n" "$net_status" "$sync_status" "$control_status"
test "$net_status" -eq 0
test "$sync_status" -eq 0
test "$control_status" -ne 0
grep -F "deliberately wrong peer EOF expectation" "$1/.scratch/tcp-connect/final-drop-control.log"
' scoped-tcp-connect "$repo_root"
