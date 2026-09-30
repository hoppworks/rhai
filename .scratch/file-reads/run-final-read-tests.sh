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
(cd "$private_root" && cargo test --features testing-environ,sys,metadata --test sys_fs test_file_handle_read_blob_preserves_bytes_and_obeys_host_cap -- --exact --nocapture) > "$source_root/.scratch/file-reads/final-read-base.log" 2>&1
(cd "$private_root" && cargo test --features testing-environ,sys,metadata,sync,no_index --test sys_fs test_file_handle_blob_read_is_omitted_under_no_index -- --exact --nocapture) > "$source_root/.scratch/file-reads/final-read-no-index.log" 2>&1
(cd "$private_root" && cargo test --features testing-environ,sys,metadata,unchecked --test sys_fs test_file_handle_read_blob_preserves_bytes_and_obeys_host_cap -- --exact --nocapture) > "$source_root/.scratch/file-reads/final-read-unchecked.log" 2>&1
for log in final-read-base.log final-read-no-index.log final-read-unchecked.log; do
  echo "=== $log ==="
  tail -n 8 "$source_root/.scratch/file-reads/$log"
done
