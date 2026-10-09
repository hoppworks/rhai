#!/usr/bin/env bash
set -euo pipefail
ATTEMPT="$(cd "$(dirname "$0")" && pwd)"
BASE="/var/roothome/rhai-evidence/linux-managed-drop-attempt02-20261009T1733Z-a7c3e1/linux-managed-drop-20261009T1518Z-6cf30d"
ARCHIVE="$BASE/source.tar.gz"; LOCK="$BASE/Cargo.lock.accepted"
TOOLCHAIN="/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu"
SOURCE="$AGENT_RUNTIME_DIR/source"
TEST_SHA="86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41"
LOCK_SHA="2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425"
SELECTOR='direct_spawn_try_wait_returns_unit_until_child_exits'
PROFILES=(sync no_float sync-no-float)
FEATURES=(testing-environ,sys,sync testing-environ,sys,no_float testing-environ,sys,sync,no_float)
test -n "$AGENT_RUNTIME_DIR"
test "$(sha256sum "$ARCHIVE" | cut -d' ' -f1)" = "68444772248d81587ee19d157c4d49d35a6ba12482233264bba0c622a113f644"
test "$(sha256sum "$LOCK" | cut -d' ' -f1)" = "$LOCK_SHA"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target" CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=2 CARGO_TERM_COLOR=never PYTHONDONTWRITEBYTECODE=1
export RUSTC="$TOOLCHAIN/bin/rustc" RUSTDOC="$TOOLCHAIN/bin/rustdoc" PATH="$TOOLCHAIN/bin:/usr/bin:/bin"
unset RUSTFLAGS CARGO_ENCODED_RUSTFLAGS RUSTC_WRAPPER RUSTDOCFLAGS
mkdir "$SOURCE"; tar -xzf "$ARCHIVE" -C "$SOURCE"; cp "$LOCK" "$SOURCE/Cargo.lock"; cd "$SOURCE"
test "$(sha256sum tests/sys_process.rs | cut -d' ' -f1)" = "$TEST_SHA"
cp tests/sys_process.rs "$AGENT_RUNTIME_DIR/sys_process.original.rs"
python3 - "$SOURCE/tests/sys_process.rs" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); text=p.read_text()
start=text.index('fn direct_spawn_try_wait_returns_unit_until_child_exits(')
end=text.index('\n#[cfg(all(unix, not(feature = "no_index"), not(feature = "no_float")))]',start)
part=text[start:end]
old='assert_eq!(terminal_code, 0, "try_wait directly observes the natural exit result");'
new='assert_eq!(terminal_code, 9, "RED control: terminal try_wait result must match wrong exit-code expectation");'
if part.count(old)!=1: raise SystemExit(f'expected one scoped terminal-result assertion, got {part.count(old)}')
p.write_text(text[:start]+part.replace(old,new,1)+text[end:])
PY
sha256sum tests/sys_process.rs > "$ATTEMPT/red-test.sha256"
test "$(cut -d' ' -f1 "$ATTEMPT/red-test.sha256")" != "$TEST_SHA"
"$TOOLCHAIN/bin/rustc" --version --verbose > "$ATTEMPT/rustc-version.txt"; "$TOOLCHAIN/bin/cargo" --version --verbose > "$ATTEMPT/cargo-version.txt"; uname -a > "$ATTEMPT/uname.txt"
extract_exe() {
 python3 - "$1" "$2" <<'PYEXE'
import json,sys
from pathlib import Path
xs=[]
for line in Path(sys.argv[1]).read_text().splitlines():
 try:x=json.loads(line)
 except json.JSONDecodeError:continue
 t=x.get('target',{})
 if x.get('reason')=='compiler-artifact' and t.get('name')=='sys_process' and 'test' in t.get('kind',[]) and x.get('executable'):xs.append(x['executable'])
if len(xs)!=1:raise SystemExit(f'expected one sys_process test executable, got {xs!r}')
Path(sys.argv[2]).write_text(xs[0]+'\n')
PYEXE
}
run_row() {
 phase="$1"; profile="$2"; features="$3"
 set +e
 "$TOOLCHAIN/bin/cargo" test --locked --features "$features" --test sys_process --no-run --message-format=json > "$ATTEMPT/$phase-$profile-build.stdout.jsonl" 2> "$ATTEMPT/$phase-$profile-build.stderr"
 build_status=$?; set -e
 printf '%s\n' "$build_status" > "$ATTEMPT/$phase-$profile-build.status"; test "$build_status" -eq 0
 extract_exe "$ATTEMPT/$phase-$profile-build.stdout.jsonl" "$ATTEMPT/$phase-$profile-executable.txt"
 exe="$(cat "$ATTEMPT/$phase-$profile-executable.txt")"
 "$exe" --list > "$ATTEMPT/$phase-$profile-list.stdout" 2> "$ATTEMPT/$phase-$profile-list.stderr"
 grep -Fx "$SELECTOR: test" "$ATTEMPT/$phase-$profile-list.stdout" >/dev/null
 printf '%s --exact %s --nocapture --test-threads=1\n' "$exe" "$SELECTOR" > "$ATTEMPT/$phase-$profile.command.txt"
 set +e; "$exe" --exact "$SELECTOR" --nocapture --test-threads=1 > "$ATTEMPT/$phase-$profile.log" 2>&1; status=$?; set -e
 printf '%s\n' "$status" > "$ATTEMPT/$phase-$profile.status"
 python3 - "$phase" "$status" "$SELECTOR" "$ATTEMPT/$phase-$profile.log" <<'PYVERIFY'
import os,re,sys
phase,status,selector,path=sys.argv[1:]; status=int(status); text=open(path,encoding='utf-8',errors='replace').read()
if not re.search(r'^test '+re.escape(selector)+r' \.\.\.',text,re.M):raise SystemExit('exact selected test missing')
results=re.findall(r'^test result: (.+)$',text,re.M)
if not results:raise SystemExit('final libtest summary missing')
pid_match=re.search(r'x24_running pid=(\d+)',text)
if not pid_match:raise SystemExit('independent live-child PID checkpoint missing')
pid=int(pid_match.group(1))
try: os.kill(pid,0)
except ProcessLookupError: gone=True
except PermissionError as e: raise SystemExit(f'PID probe permission error is not ESRCH: {e}')
else: gone=False
if not gone:raise SystemExit(f'exact fixture PID {pid} remains observable after exact test')
if phase=='red':
 if status!=101 or 'RED control: terminal try_wait result must match wrong exit-code expectation' not in text or not results[-1].startswith('FAILED. 0 passed; 1 failed;'):
  raise SystemExit(f'intended RED missing: status={status}, final={results[-1]!r}')
 if 'left: 0' not in text or 'right: 9' not in text:raise SystemExit('wrong-result assertion did not report real0 versus expected9')
else:
 if status!=0 or not results[-1].startswith('ok. 1 passed; 0 failed;'):
  raise SystemExit(f'GREEN missing: status={status}, final={results[-1]!r}')
 if not re.search(r'x24_post_exit_try_wait pid='+str(pid)+r' result_observed_before_wait=true code=0 success=true',text):raise SystemExit('terminal try_wait result before wait not observed')
 if not re.search(r'x24_finished pid='+str(pid)+r' wait_code=0 try_wait_code=0 success=true reaped_esrch=true',text):raise SystemExit('cached wait result and exact ESRCH not observed')
PYVERIFY
}
for i in 0 1 2; do run_row red "${PROFILES[$i]}" "${FEATURES[$i]}"; done
cp "$AGENT_RUNTIME_DIR/sys_process.original.rs" tests/sys_process.rs
printf '%s  %s\n' "$(sha256sum tests/sys_process.rs | cut -d' ' -f1)" tests/sys_process.rs > "$ATTEMPT/restored-test.sha256"
test "$(cut -d' ' -f1 "$ATTEMPT/restored-test.sha256")" = "$TEST_SHA"
for i in 0 1 2; do run_row green "${PROFILES[$i]}" "${FEATURES[$i]}"; done
cat > "$ATTEMPT/result.txt" <<EOF
source_archive_sha256=$(sha256sum "$ARCHIVE" | cut -d' ' -f1)
test_source_sha256=$(sha256sum tests/sys_process.rs | cut -d' ' -f1)
lock_sha256=$(sha256sum "$LOCK" | cut -d' ' -f1)
selector=$SELECTOR
profiles=testing-environ,sys,sync; testing-environ,sys,no_float; testing-environ,sys,sync,no_float
red_status=101 all 3 profiles; wrong expected terminal code9 vs actual0; exact PID ESRCH readback
restored_test_sha256=$(cut -d' ' -f1 "$ATTEMPT/restored-test.sha256")
green_status=0 all 3 profiles; terminal try_wait result before wait; cached wait result; exact PID ESRCH
standard_profile=not rerun; compatible accepted Linux standard proof reused from .scratch/all-tickets/process-try-wait-evidence/x24-try-wait-20261007-1705z-6a92d/attempt-04/proof.md
scope_runtime=$AGENT_RUNTIME_DIR
EOF
