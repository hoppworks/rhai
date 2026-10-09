#!/usr/bin/env bash
set -euo pipefail
EVIDENCE="$1"
ARCHIVE="$EVIDENCE/source.tar.gz"
LOCK="$EVIDENCE/Cargo.lock.accepted"
OUT="$EVIDENCE/workhorse"
SOURCE="$AGENT_RUNTIME_DIR/source"
TOOLCHAIN="/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu"
SELECTOR='direct_spawn_try_wait_returns_unit_until_child_exits'
FEATURES='testing-environ,sys,only_i32,no_float'
EXPECTED_SOURCE_SHA="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["test_source_sha256"])' "$EVIDENCE/inputs.json")"
EXPECTED_LOCK_SHA="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["accepted_lock_sha256"])' "$EVIDENCE/inputs.json")"
test -n "$AGENT_RUNTIME_DIR"
test "$(sha256sum "$ARCHIVE" | cut -d' ' -f1)" = "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["source_archive_sha256"])' "$EVIDENCE/inputs.json")"
test "$(sha256sum "$LOCK" | cut -d' ' -f1)" = "$EXPECTED_LOCK_SHA"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target" CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=2 CARGO_TERM_COLOR=never PYTHONDONTWRITEBYTECODE=1
export RUSTC="$TOOLCHAIN/bin/rustc" RUSTDOC="$TOOLCHAIN/bin/rustdoc" PATH="$TOOLCHAIN/bin:/usr/bin:/bin"
unset RUSTFLAGS CARGO_ENCODED_RUSTFLAGS RUSTC_WRAPPER RUSTDOCFLAGS
mkdir -m 700 "$SOURCE"
tar -xzf "$ARCHIVE" -C "$SOURCE"
cp "$LOCK" "$SOURCE/Cargo.lock"
cd "$SOURCE"
test "$(sha256sum tests/sys_process.rs | cut -d' ' -f1)" = "$EXPECTED_SOURCE_SHA"
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
if part.count(old)!=1: raise SystemExit(f'expected one terminal-result assertion, got {part.count(old)}')
p.write_text(text[:start]+part.replace(old,new,1)+text[end:])
PY
sha256sum tests/sys_process.rs > "$OUT/red-test.sha256"
"$TOOLCHAIN/bin/rustc" --version --verbose > "$OUT/rustc-version.txt"
"$TOOLCHAIN/bin/cargo" --version --verbose > "$OUT/cargo-version.txt"
uname -a > "$OUT/uname.txt"
run_phase() {
  phase="$1"
  set +e
  "$TOOLCHAIN/bin/cargo" test --locked --features "$FEATURES" --test sys_process --no-run --message-format=json > "$OUT/$phase-build.stdout.jsonl" 2> "$OUT/$phase-build.stderr"
  build_status=$?
  set -e
  printf '%s\n' "$build_status" > "$OUT/$phase-build.status"
  test "$build_status" -eq 0
  python3 - "$OUT/$phase-build.stdout.jsonl" "$OUT/$phase-executable.txt" <<'PYEXE'
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
  exe="$(cat "$OUT/$phase-executable.txt")"
  "$exe" --list > "$OUT/$phase-list.stdout" 2> "$OUT/$phase-list.stderr"
  grep -Fx "$SELECTOR: test" "$OUT/$phase-list.stdout" >/dev/null
  printf '%s --exact %s --nocapture --test-threads=1\n' "$exe" "$SELECTOR" > "$OUT/$phase.command.txt"
  set +e
  "$exe" --exact "$SELECTOR" --nocapture --test-threads=1 > "$OUT/$phase.log" 2>&1
  status=$?
  set -e
  printf '%s\n' "$status" > "$OUT/$phase.status"
  python3 - "$phase" "$status" "$SELECTOR" "$OUT/$phase.log" <<'PYVERIFY'
import os,re,sys
phase,status,selector,path=sys.argv[1:]; status=int(status); text=open(path,encoding='utf-8',errors='replace').read()
if not re.search(r'^test '+re.escape(selector)+r' \.\.\.',text,re.M):raise SystemExit('exact selected test missing')
results=re.findall(r'^test result: (.+)$',text,re.M)
if not results:raise SystemExit('final libtest summary missing')
m=re.search(r'x24_running pid=(\d+)',text)
if not m:raise SystemExit('live-child PID checkpoint missing')
pid=int(m.group(1))
try: os.kill(pid,0)
except ProcessLookupError: gone=True
except PermissionError as e: raise SystemExit(f'permission failure is not ESRCH: {e}')
else: gone=False
if not gone:raise SystemExit(f'exact fixture PID {pid} still exists')
if phase=='red':
 if status!=101 or 'RED control: terminal try_wait result must match wrong exit-code expectation' not in text or not results[-1].startswith('FAILED. 0 passed; 1 failed;'):raise SystemExit(f'intended RED absent status={status}, summary={results[-1]}')
 if 'left: 0' not in text or 'right: 9' not in text:raise SystemExit('wrong expectation did not show actual0/expected9')
else:
 if status!=0 or not results[-1].startswith('ok. 1 passed; 0 failed;'):raise SystemExit(f'GREEN absent status={status}, summary={results[-1]}')
 if not re.search(r'x24_post_exit_try_wait pid='+str(pid)+r' result_observed_before_wait=true code=0 success=true',text):raise SystemExit('terminal try_wait result before wait not observed')
 if not re.search(r'x24_finished pid='+str(pid)+r' wait_code=0 try_wait_code=0 success=true reaped_esrch=true',text):raise SystemExit('cached wait or ESRCH observation missing')
PYVERIFY
}
run_phase red
cp "$AGENT_RUNTIME_DIR/sys_process.original.rs" tests/sys_process.rs
sha256sum tests/sys_process.rs > "$OUT/restored-test.sha256"
test "$(cut -d' ' -f1 "$OUT/restored-test.sha256")" = "$EXPECTED_SOURCE_SHA"
run_phase green
printf 'accepted Linux X24 only_i32,no_float RED/GREEN payload complete\n' > "$OUT/result.txt"
