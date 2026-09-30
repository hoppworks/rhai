set -eu
OUT=/Users/hoppworks/projects/rhai-file-handle-docs/.scratch/file-handle-docs
SRC="$AGENT_RUNTIME_DIR/source"
mkdir -p "$OUT" "$SRC"
rsync -a --exclude=.git --exclude=target --exclude=.scratch ./ "$SRC/"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export TMPDIR="$AGENT_RUNTIME_DIR/tmp"
export CARGO_BUILD_JOBS=2
mkdir -p "$CARGO_HOME" "$TMPDIR"
printf '%s\n' \
  'cargo run --example sys --features sys' \
  'wrong host payload control (expected failure)' \
  'cargo run --example sys --features sys,no_index' > "$OUT/commands.txt"
cd "$SRC"
cargo run --example sys --features sys
cp examples/sys.rs "$AGENT_RUNTIME_DIR/sys.rs.correct"
sed -i.bak 's/Rhaiting data/wrong payload/' examples/sys.rs
set +e
cargo run --example sys --features sys
control_status=$?
set -e
mv "$AGENT_RUNTIME_DIR/sys.rs.correct" examples/sys.rs
rm -f examples/sys.rs.bak
if [ "$control_status" -eq 0 ]; then
  echo 'wrong-payload control unexpectedly passed' >&2
  exit 1
fi
printf 'wrong-payload control exited %s as expected\n' "$control_status"
cargo run --example sys --features sys,no_index
printf '\nScoped runtime: %s\n' "$AGENT_RUNTIME_DIR"
du -sk "$AGENT_RUNTIME_DIR/target"
