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
test "$(sha256sum "$ARCHIVE" | cut -d' ' -f1)" = "68444772248d81587ee19d157c4d49d35a6ba12482233264bba0c622a113f644"
test "$(sha256sum "$LOCK" | cut -d' ' -f1)" = "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=2 CARGO_TERM_COLOR=never PYTHONDONTWRITEBYTECODE=1
export RUSTC="$TOOLCHAIN/bin/rustc" RUSTDOC="$TOOLCHAIN/bin/rustdoc"
export PATH="$TOOLCHAIN/bin:/usr/bin:/bin"
unset RUSTFLAGS CARGO_ENCODED_RUSTFLAGS RUSTC_WRAPPER RUSTDOCFLAGS
mkdir "$SOURCE"
tar -xzf "$ARCHIVE" -C "$SOURCE"
cp "$LOCK" "$SOURCE/Cargo.lock"
cd "$SOURCE"
test "$(sha256sum tests/sys_process.rs | cut -d' ' -f1)" = "86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41"
cp tests/sys_process.rs "$AGENT_RUNTIME_DIR/sys_process.original.rs"
python3 - "$SOURCE/tests/sys_process.rs" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1])
source=path.read_text()
start=source.index("fn child_wait_preserves_decoded_expansion_reports_and_committed_primary_cause() {")
end=source.find("\n/// The scalar text API", start)
if end < 0:
    raise SystemExit("could not bound Child.wait test function")
segment=source[start:end]
needle="        if !primary_limit {\n            assert!(expected_raw.len() < engine_limit);\n        }"
replacement=needle+"\n        if !primary_limit { expected_raw[0] ^= 1; }"
if segment.count(needle)!=1:
    raise SystemExit(f"expected one anchored expected-raw assertion, got {segment.count(needle)}")
path.write_text(source[:start]+segment.replace(needle,replacement,1)+source[end:])
PY
sha256sum tests/sys_process.rs > "$ATTEMPT/red-source.sha256"
test "$(cut -d' ' -f1 "$ATTEMPT/red-source.sha256")" != "86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41"
"$TOOLCHAIN/bin/rustc" --version --verbose > "$ATTEMPT/rustc-version.txt"
"$TOOLCHAIN/bin/cargo" --version --verbose > "$ATTEMPT/cargo-version.txt"
uname -a > "$ATTEMPT/uname.txt"
set +e
"$TOOLCHAIN/bin/cargo" test --locked --features testing-environ,sys --test sys_process --no-run --message-format=json \
  > "$ATTEMPT/red-build.stdout.jsonl" 2> "$ATTEMPT/red-build.stderr"
build_status=$?
set -e
printf '%s\n' "$build_status" > "$ATTEMPT/red-build.status"
test "$build_status" -eq 0
python3 - "$ATTEMPT/red-build.stdout.jsonl" "$ATTEMPT/red-executable.txt" <<'PY'
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
    raise SystemExit(f"expected one sys_process executable, got {records!r}")
Path(sys.argv[2]).write_text(records[0]+"\n")
PY
EXE="$(cat "$ATTEMPT/red-executable.txt")"
"$EXE" --list > "$ATTEMPT/red-list.stdout" 2> "$ATTEMPT/red-list.stderr"
grep -Fx "$TEST: test" "$ATTEMPT/red-list.stdout" > /dev/null
printf '%s\n' "$EXE --exact $TEST --nocapture" > "$ATTEMPT/red-command.txt"
set +e
"$EXE" --exact "$TEST" --nocapture > "$ATTEMPT/red-test.log" 2>&1
test_status=$?
set -e
printf '%s\n' "$test_status" > "$ATTEMPT/red-test.status"
test "$test_status" -eq 101
grep -F "wait must retain exact raw bytes" "$ATTEMPT/red-test.log" > /dev/null
grep -F "test $TEST ... FAILED" "$ATTEMPT/red-test.log" > /dev/null
cp "$AGENT_RUNTIME_DIR/sys_process.original.rs" tests/sys_process.rs
sha256sum tests/sys_process.rs > "$ATTEMPT/restored-source.sha256"
test "$(cut -d' ' -f1 "$ATTEMPT/restored-source.sha256")" = "86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41"
{
 printf 'red_build=%s\n' "$build_status"
 printf 'red_test=%s\n' "$test_status"
 printf 'failure=wrong_expected_first_raw_byte\n'
 printf 'assertion=wait must retain exact raw bytes\n'
 printf 'restored_source_sha256=%s\n' "$(cut -d' ' -f1 "$ATTEMPT/restored-source.sha256")"
 printf 'green_reused_from=../attempt01/green-test.log\n'
} > "$ATTEMPT/result.txt"
