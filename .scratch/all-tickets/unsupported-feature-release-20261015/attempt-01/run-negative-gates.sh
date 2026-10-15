#!/usr/bin/env bash
set -u
repo=/var/home/Daniel/projects/rhai
attempt="$repo/.scratch/all-tickets/unsupported-feature-release-20261015/attempt-01"
evidence="$attempt/evidence"
runtime="$AGENT_RUNTIME_DIR"
toolchain=/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
mkdir -p "$runtime/source" "$runtime/cargo-home" "$runtime/target"
git -C "$repo" archive HEAD | tar -x -C "$runtime/source"
cp "$repo/.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock" "$runtime/source/Cargo.lock"
printf 'revision=%s\n' "$(git -C "$repo" rev-parse HEAD)" > "$evidence/source-revision.txt"
sha256sum "$runtime/source/Cargo.toml" "$runtime/source/Cargo.lock" "$runtime/source/src/packages/sys/mod.rs" "$runtime/source/src/packages/net/mod.rs" > "$evidence/source-hashes.txt"
test "$(sha256sum "$runtime/source/Cargo.toml" | cut -d' ' -f1)" = cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e
test "$(sha256sum "$runtime/source/Cargo.lock" | cut -d' ' -f1)" = 2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
export CARGO_HOME="$runtime/cargo-home"
export CARGO_TARGET_DIR="$runtime/target"
export CARGO_BUILD_JOBS=1
export CARGO_TERM_COLOR=never
export RUSTUP_HOME=/home/Daniel/.rustup
export RUSTC="$toolchain/rustc"
export RUSTDOC="$toolchain/rustdoc"
export PATH="$toolchain:/usr/bin:/bin"
{
  printf 'cargo='; "$toolchain/cargo" --version
  printf 'rustc='; "$RUSTC" --version
  printf 'target='; "$RUSTC" -vV | sed -n 's/^host: //p'
  printf 'jobs=%s\n' "$CARGO_BUILD_JOBS"
  printf 'runtime=%s\n' "$runtime"
} > "$evidence/toolchain-and-runtime.txt"
: > "$evidence/commands.txt"
: > "$evidence/statuses.csv"
printf 'check,exit,expected_diagnostic\n' > "$evidence/statuses.csv"
check_gate() {
  local name="$1" features="$2" diagnostic="$3" rc=0
  printf 'cargo check --locked --no-default-features --features %q\n' "$features" >> "$evidence/commands.txt"
  (cd "$runtime/source" && "$toolchain/cargo" check --locked --no-default-features --features "$features") > "$evidence/$name.log" 2>&1 || rc=$?
  printf '%s,%s,%s\n' "$name" "$rc" "$diagnostic" >> "$evidence/statuses.csv"
  if [ "$rc" -eq 0 ] || ! grep -Fq "$diagnostic" "$evidence/$name.log"; then
    printf 'required compiler diagnostic missing for %s (exit=%s)\n' "$name" "$rc" >&2
    return 1
  fi
  return 0
}
check_gate sys_no_std sys,no_std 'the `sys` feature requires `std`; it cannot be combined with `no_std`' || exit 11
check_gate net_no_std net,no_std 'the `net` feature requires `std`; it cannot be combined with `no_std`' || exit 12
check_gate sys_net_no_std sys,net,no_std 'the `sys` feature requires `std`; it cannot be combined with `no_std`' || exit 13
if ! grep -Fq 'the `net` feature requires `std`; it cannot be combined with `no_std`' "$evidence/sys_net_no_std.log"; then exit 14; fi
check_gate sys_no_object sys,no_object 'the `sys` feature requires object maps; it cannot be combined with `no_object`' || exit 15
cp "$runtime/source/src/packages/sys/mod.rs" "$runtime/sys-mod.rs.original"
python3 - "$runtime/source/src/packages/sys/mod.rs" <<'PYMUT'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
needle='#[cfg(feature = "no_object")]\ncompile_error!("the `sys` feature requires object maps; it cannot be combined with `no_object`");\n\n'
assert s.count(needle)==1
p.write_text(s.replace(needle,"",1))
PYMUT
control_rc=0
printf 'cargo check --locked --no-default-features --features sys,no_object (sys/no_object guard temporarily removed in private source)\n' >> "$evidence/commands.txt"
(cd "$runtime/source" && "$toolchain/cargo" check --locked --no-default-features --features sys,no_object) > "$evidence/guard-removed-control.log" 2>&1 || control_rc=$?
if grep -Fq 'the `sys` feature requires object maps; it cannot be combined with `no_object`' "$evidence/guard-removed-control.log"; then
  echo 'matcher incorrectly accepted missing sys/no_object guard' >&2
  exit 16
fi
printf 'guard_removed_control,%s,expected diagnostic absent; matcher rejects\n' "$control_rc" >> "$evidence/statuses.csv"
cp "$runtime/sys-mod.rs.original" "$runtime/source/src/packages/sys/mod.rs"
test "$(sha256sum "$runtime/source/src/packages/sys/mod.rs" | cut -d' ' -f1)" = "$(awk '$2 ~ /src\/packages\/sys\/mod.rs$/ {print $1}' "$evidence/source-hashes.txt")"
check_gate sys_no_object_restored sys,no_object 'the `sys` feature requires object maps; it cannot be combined with `no_object`' || exit 17
printf 'wasm_target=not installed for Rust 1.77.2; sys-only, net-only and combined sys+net WASM gates unverified without installation\n' > "$evidence/wasm-status.txt"
printf 'all present-target negative gates matched their intentional diagnostics; guard-removal control was rejected; private source restored\n' > "$evidence/result.txt"
