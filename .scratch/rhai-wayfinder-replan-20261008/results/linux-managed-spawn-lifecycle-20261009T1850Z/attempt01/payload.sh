#!/usr/bin/env bash
set -euo pipefail
ATTEMPT="$(cd "$(dirname "$0")" && pwd)"
BASE="/var/roothome/rhai-evidence/linux-managed-drop-attempt02-20261009T1733Z-a7c3e1/linux-managed-drop-20261009T1518Z-6cf30d"
ARCHIVE="$BASE/source.tar.gz"
LOCK="$BASE/Cargo.lock.accepted"
TOOLCHAIN="/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu"
SOURCE="$AGENT_RUNTIME_DIR/source"
TEST_KILL="managed_spawn_kill_stops_leader_worker_leaf_and_preserves_sentinel"
TEST_DROP="managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not"
BASELINE="86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41"
test -n "$AGENT_RUNTIME_DIR"
test "$(sha256sum "$ARCHIVE" | cut -d' ' -f1)" = "68444772248d81587ee19d157c4d49d35a6ba12482233264bba0c622a113f644"
test "$(sha256sum "$LOCK" | cut -d' ' -f1)" = "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target" CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=2 CARGO_TERM_COLOR=never PYTHONDONTWRITEBYTECODE=1
export RUSTC="$TOOLCHAIN/bin/rustc" RUSTDOC="$TOOLCHAIN/bin/rustdoc" PATH="$TOOLCHAIN/bin:/usr/bin:/bin"
unset RUSTFLAGS CARGO_ENCODED_RUSTFLAGS RUSTC_WRAPPER RUSTDOCFLAGS
mkdir "$SOURCE"
tar -xzf "$ARCHIVE" -C "$SOURCE"
cp "$LOCK" "$SOURCE/Cargo.lock"
cd "$SOURCE"
test "$(sha256sum tests/sys_process.rs | cut -d' ' -f1)" = "$BASELINE"
cp tests/sys_process.rs "$AGENT_RUNTIME_DIR/sys_process.original.rs"
python3 - "$SOURCE/tests/sys_process.rs" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); text=p.read_text()
changes={
'assert!(members_gone, "managed spawned members must be gone after public kill");':
'assert!(!members_gone, "RED control: managed members unexpectedly gone after public kill");',
'assert!(all_gone, "dropping final Child clone did not terminate the managed group");':
'assert!(!all_gone, "RED control: final Child drop unexpectedly terminated the group");',
}
for old,new in changes.items():
    if text.count(old)!=1: raise SystemExit(f"expected exactly one assertion anchor; got {text.count(old)}: {old}")
    text=text.replace(old,new,1)
p.write_text(text)
PY
sha256sum tests/sys_process.rs > "$ATTEMPT/red-source.sha256"
test "$(cut -d' ' -f1 "$ATTEMPT/red-source.sha256")" != "$BASELINE"
"$TOOLCHAIN/bin/rustc" --version --verbose > "$ATTEMPT/rustc-version.txt"
"$TOOLCHAIN/bin/cargo" --version --verbose > "$ATTEMPT/cargo-version.txt"
uname -a > "$ATTEMPT/uname.txt"
set +e
"$TOOLCHAIN/bin/cargo" test --locked --features testing-environ,sys --test sys_process --no-run --message-format=json > "$ATTEMPT/red-build.stdout.jsonl" 2> "$ATTEMPT/red-build.stderr"
red_build=$?
set -e
printf '%s\n' "$red_build" > "$ATTEMPT/red-build.status"
test "$red_build" -eq 0
python3 - "$ATTEMPT/red-build.stdout.jsonl" "$ATTEMPT/red-executable.txt" <<'PY'
import json,sys
from pathlib import Path
xs=[]
for line in Path(sys.argv[1]).read_text().splitlines():
 try:x=json.loads(line)
 except json.JSONDecodeError:continue
 t=x.get('target',{})
 if x.get('reason')=='compiler-artifact' and t.get('name')=='sys_process' and 'test' in t.get('kind',[]) and x.get('executable'):xs.append(x['executable'])
if len(xs)!=1:raise SystemExit(f'expected one sys_process executable, got {xs!r}')
Path(sys.argv[2]).write_text(xs[0]+'\n')
PY
EXE="$(cat "$ATTEMPT/red-executable.txt")"
"$EXE" --list > "$ATTEMPT/test-list.stdout" 2> "$ATTEMPT/test-list.stderr"
grep -Fx "$TEST_KILL: test" "$ATTEMPT/test-list.stdout" >/dev/null
grep -Fx "$TEST_DROP: test" "$ATTEMPT/test-list.stdout" >/dev/null
for spec in "$TEST_KILL|kill" "$TEST_DROP|final-drop"; do
 name=${spec%%|*}; label=${spec#*|}
 printf '%s --exact %s --nocapture\n' "$EXE" "$name" > "$ATTEMPT/red-$label.command.txt"
 set +e
 "$EXE" --exact "$name" --nocapture > "$ATTEMPT/red-$label.log" 2>&1
 st=$?
 set -e
 printf '%s\n' "$st" > "$ATTEMPT/red-$label.status"
 test "$st" -eq 101
 grep -F "RED control:" "$ATTEMPT/red-$label.log" >/dev/null
 grep -F "test $name ... FAILED" "$ATTEMPT/red-$label.log" >/dev/null
done
cp "$AGENT_RUNTIME_DIR/sys_process.original.rs" tests/sys_process.rs
sha256sum tests/sys_process.rs > "$ATTEMPT/restored-source.sha256"
test "$(cut -d' ' -f1 "$ATTEMPT/restored-source.sha256")" = "$BASELINE"
set +e
"$TOOLCHAIN/bin/cargo" test --locked --features testing-environ,sys --test sys_process --no-run --message-format=json > "$ATTEMPT/green-build.stdout.jsonl" 2> "$ATTEMPT/green-build.stderr"
green_build=$?
set -e
printf '%s\n' "$green_build" > "$ATTEMPT/green-build.status"
test "$green_build" -eq 0
python3 - "$ATTEMPT/green-build.stdout.jsonl" "$ATTEMPT/green-executable.txt" <<'PY'
import json,sys
from pathlib import Path
xs=[]
for line in Path(sys.argv[1]).read_text().splitlines():
 try:x=json.loads(line)
 except json.JSONDecodeError:continue
 t=x.get('target',{})
 if x.get('reason')=='compiler-artifact' and t.get('name')=='sys_process' and 'test' in t.get('kind',[]) and x.get('executable'):xs.append(x['executable'])
if len(xs)!=1:raise SystemExit(f'expected one sys_process executable, got {xs!r}')
Path(sys.argv[2]).write_text(xs[0]+'\n')
PY
GREEN_EXE="$(cat "$ATTEMPT/green-executable.txt")"
test "$GREEN_EXE" = "$EXE"
for spec in "$TEST_KILL|kill" "$TEST_DROP|final-drop"; do
 name=${spec%%|*}; label=${spec#*|}
 printf '%s --exact %s --nocapture\n' "$GREEN_EXE" "$name" > "$ATTEMPT/green-$label.command.txt"
 set +e
 "$GREEN_EXE" --exact "$name" --nocapture > "$ATTEMPT/green-$label.log" 2>&1
 st=$?
 set -e
 printf '%s\n' "$st" > "$ATTEMPT/green-$label.status"
 test "$st" -eq 0
 grep -F "test $name ... ok" "$ATTEMPT/green-$label.log" >/dev/null
done
cat > "$ATTEMPT/result.txt" <<EOF
source_archive_sha256=$(sha256sum "$ARCHIVE" | cut -d' ' -f1)
source_test_baseline_sha256=$(cut -d' ' -f1 "$ATTEMPT/restored-source.sha256")
lock_sha256=$(sha256sum "$LOCK" | cut -d' ' -f1)
features=testing-environ,sys plus defaults
red_build=$red_build
green_build=$green_build
red_kill=101 at deliberate wrong group-kill expectation
red_final_drop=101 at deliberate wrong final-drop expectation
green_kill=0 exact selector passed
green_final_drop=0 exact selector passed
scope_runtime=$AGENT_RUNTIME_DIR
EOF
