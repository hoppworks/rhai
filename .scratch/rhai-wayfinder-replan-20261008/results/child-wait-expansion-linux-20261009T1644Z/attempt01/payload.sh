#!/usr/bin/env bash
set -euo pipefail

ATTEMPT="$(cd "$(dirname "$0")" && pwd)"
BASE="/var/roothome/rhai-evidence/linux-managed-drop-attempt02-20261009T1733Z-a7c3e1/linux-managed-drop-20261009T1518Z-6cf30d"
ARCHIVE="$BASE/source.tar.gz"
LOCK="$BASE/Cargo.lock.accepted"
TOOLCHAIN="/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu"
SOURCE="$AGENT_RUNTIME_DIR/source"
TEST="child_wait_preserves_decoded_expansion_reports_and_committed_primary_cause"

test -n "$AGENT_RUNTIME_DIR"
test -x "$TOOLCHAIN/bin/cargo"
test -x "$TOOLCHAIN/bin/rustc"
test "$(sha256sum "$ARCHIVE" | cut -d' ' -f1)" = "68444772248d81587ee19d157c4d49d35a6ba12482233264bba0c622a113f644"
test "$(sha256sum "$LOCK" | cut -d' ' -f1)" = "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425"

export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=2
export CARGO_TERM_COLOR=never
export PYTHONDONTWRITEBYTECODE=1
export RUSTC="$TOOLCHAIN/bin/rustc"
export RUSTDOC="$TOOLCHAIN/bin/rustdoc"
export PATH="$TOOLCHAIN/bin:/usr/bin:/bin"
unset RUSTFLAGS CARGO_ENCODED_RUSTFLAGS RUSTC_WRAPPER RUSTDOCFLAGS

mkdir "$SOURCE"
tar -xzf "$ARCHIVE" -C "$SOURCE"
cp "$LOCK" "$SOURCE/Cargo.lock"
cd "$SOURCE"
printf '%s\n' "$PWD" > "$ATTEMPT/source-cwd.txt"
test "$(sha256sum tests/sys_process.rs | cut -d' ' -f1)" = "86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41"
test "$(sha256sum Cargo.lock | cut -d' ' -f1)" = "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425"
{
  uname -a
  "$RUSTC" --version --verbose
  "$TOOLCHAIN/bin/cargo" --version --verbose
  printf 'source_revision=34e0fa61a3d12fe6c41902c44618ff44e20d73d4\n'
  printf 'source_archive_sha256=%s\n' "$(sha256sum "$ARCHIVE" | cut -d' ' -f1)"
  printf 'test_source_sha256=%s\n' "$(sha256sum tests/sys_process.rs | cut -d' ' -f1)"
  printf 'lock_sha256=%s\n' "$(sha256sum Cargo.lock | cut -d' ' -f1)"
  printf 'features=testing-environ,sys\n'
  printf 'cargo_build_jobs=%s\n' "$CARGO_BUILD_JOBS"
} > "$ATTEMPT/environment.txt"
cp tests/sys_process.rs "$AGENT_RUNTIME_DIR/sys_process.original.rs"

build() {
  local phase="$1"
  set +e
  "$TOOLCHAIN/bin/cargo" test --locked --features testing-environ,sys --test sys_process --no-run --message-format=json \
    > "$ATTEMPT/$phase-build.stdout.jsonl" 2> "$ATTEMPT/$phase-build.stderr"
  local rc=$?
  set -e
  printf '%s\n' "$rc" > "$ATTEMPT/$phase-build.status"
  test "$rc" -eq 0
  python3 - "$ATTEMPT/$phase-build.stdout.jsonl" "$ATTEMPT/$phase-executable.txt" <<'PY'
import json,sys
from pathlib import Path
records=[]
for line in Path(sys.argv[1]).read_text().splitlines():
    try: item=json.loads(line)
    except json.JSONDecodeError: continue
    target=item.get("target",{})
    if item.get("reason")=="compiler-artifact" and target.get("name")=="sys_process" and "test" in target.get("kind",[]) and item.get("executable"):
        records.append(item["executable"])
if len(records)!=1:
    raise SystemExit(f"expected exactly one sys_process test executable, got {records!r}")
Path(sys.argv[2]).write_text(records[0]+"\n")
PY
}

run_exact() {
  local phase="$1"
  local executable
  executable="$(cat "$ATTEMPT/$phase-executable.txt")"
  "$executable" --list > "$ATTEMPT/$phase-list.stdout" 2> "$ATTEMPT/$phase-list.stderr"
  grep -Fx "$TEST: test" "$ATTEMPT/$phase-list.stdout" > /dev/null
  printf '%s\n' "$executable --exact $TEST --nocapture" > "$ATTEMPT/$phase-command.txt"
  set +e
  "$executable" --exact "$TEST" --nocapture > "$ATTEMPT/$phase-test.log" 2>&1
  local rc=$?
  set -e
  printf '%s\n' "$rc" > "$ATTEMPT/$phase-test.status"
}

python3 - "$SOURCE/tests/sys_process.rs" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1])
source=path.read_text()
needle='        assert_child_record(&record, 0);\n        eprintln!("child_wait_expansion primary_limit={primary_limit}'
replacement=('        assert_child_record(&record, 0);\n'
             '        eprintln!("RED control reached after independent child-record and ESRCH readback");\n'
             '        assert!(false, "RED control: deliberate wrong expectation after public Child.wait assertions");\n'
             '        eprintln!("child_wait_expansion primary_limit={primary_limit}')
if source.count(needle)!=1:
    raise SystemExit(f"expected one anchored Child.wait assertion insertion point, got {source.count(needle)}")
path.write_text(source.replace(needle,replacement,1))
PY
test "$(sha256sum tests/sys_process.rs | cut -d' ' -f1)" != "86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41"
sha256sum tests/sys_process.rs > "$ATTEMPT/red-source.sha256"
build red
run_exact red
test "$(cat "$ATTEMPT/red-test.status")" = 101
grep -F "RED control reached after independent child-record and ESRCH readback" "$ATTEMPT/red-test.log" > /dev/null
grep -F "RED control: deliberate wrong expectation after public Child.wait assertions" "$ATTEMPT/red-test.log" > /dev/null
grep -F "test $TEST ... FAILED" "$ATTEMPT/red-test.log" > /dev/null

cp "$AGENT_RUNTIME_DIR/sys_process.original.rs" tests/sys_process.rs
test "$(sha256sum tests/sys_process.rs | cut -d' ' -f1)" = "86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41"
sha256sum tests/sys_process.rs > "$ATTEMPT/green-source.sha256"
build green
run_exact green
test "$(cat "$ATTEMPT/green-test.status")" = 0
grep -F "child_wait_expansion primary_limit=false" "$ATTEMPT/green-test.log" > /dev/null
grep -F "child_wait_expansion primary_limit=true" "$ATTEMPT/green-test.log" > /dev/null
grep -F "test $TEST ... ok" "$ATTEMPT/green-test.log" > /dev/null
grep -E "1 passed; 0 failed" "$ATTEMPT/green-test.log" > /dev/null

{
  printf 'red_build=%s\n' "$(cat "$ATTEMPT/red-build.status")"
  printf 'red_test=%s\n' "$(cat "$ATTEMPT/red-test.status")"
  printf 'green_build=%s\n' "$(cat "$ATTEMPT/green-build.status")"
  printf 'green_test=%s\n' "$(cat "$ATTEMPT/green-test.status")"
  printf 'red_reached_after_host_record_and_esrch=true\n'
  printf 'green_verified_no_primary_and_preserved_primary=true\n'
} > "$ATTEMPT/result.txt"
