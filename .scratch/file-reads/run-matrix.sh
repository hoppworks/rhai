set -eu
source_root="$PWD"
private_root="$AGENT_RUNTIME_DIR/source"
mkdir -p "$private_root"
git -C "$source_root" archive HEAD | tar -x -C "$private_root"
for path in src/packages/sys/config.rs src/packages/sys/fs.rs tests/sys_fs.rs; do
  mkdir -p "$private_root/$(dirname "$path")"
  cp "$source_root/$path" "$private_root/$path"
done
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_BUILD_JOBS=2
mkdir -p "$CARGO_HOME" "$CARGO_TARGET_DIR"
set +e
(cd "$private_root" && RHAI_FILE_READ_WRONG_EXPECTATION=1 cargo test --features testing-environ,sys,metadata --test sys_fs test_file_handle_reads_obey_host_cap_and_reject_negative_lengths_without_moving -- --exact --nocapture) > "$source_root/.scratch/file-reads/false-green-control.log" 2>&1
status=$?
set -e
if [ "$status" -eq 0 ] || ! rg -q 'wrong expectation' "$source_root/.scratch/file-reads/false-green-control.log"; then
  cat "$source_root/.scratch/file-reads/false-green-control.log"
  echo "false-green control did not fail for the expected wrong assertion (status=$status)" >&2
  exit 1
fi
(cd "$private_root" && cargo test --features testing-environ,sys,metadata --test sys_fs -- --test-threads=1) > "$source_root/.scratch/file-reads/sys-fs-base.log" 2>&1
(cd "$private_root" && cargo test --features testing-environ,sys,metadata,sync,no_index --test sys_fs -- --test-threads=1) > "$source_root/.scratch/file-reads/sys-fs-sync-no-index.log" 2>&1
(cd "$private_root" && cargo test --features testing-environ,sys,metadata,unchecked --test sys_fs -- --test-threads=1) > "$source_root/.scratch/file-reads/sys-fs-unchecked.log" 2>&1
for log in false-green-control.log sys-fs-base.log sys-fs-sync-no-index.log sys-fs-unchecked.log; do
  echo "=== $log ==="
  tail -n 14 "$source_root/.scratch/file-reads/$log"
done
