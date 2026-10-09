#!/usr/bin/env bash
set -euo pipefail
ATTEMPT="$(cd "$(dirname "$0")" && pwd)"
BASE="/var/roothome/rhai-evidence/linux-managed-drop-attempt02-20261009T1733Z-a7c3e1/linux-managed-drop-20261009T1518Z-6cf30d"
ARCHIVE="$BASE/source.tar.gz"; LOCK="$BASE/Cargo.lock.accepted"
TOOLCHAIN="/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu"
SOURCE="$AGENT_RUNTIME_DIR/source"
MAIN_SHA="86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41"
FIXTURE_SHA="1faf45c57a4fefeaa05683043e064d3485e892887986fef749bedc974230b217"
SELECTOR='shared_child_contract::nonfinal_child_clone_drop_keeps_the_real_child_available'
test -n "$AGENT_RUNTIME_DIR"
test "$(sha256sum "$ARCHIVE" | cut -d' ' -f1)" = "68444772248d81587ee19d157c4d49d35a6ba12482233264bba0c622a113f644"
test "$(sha256sum "$LOCK" | cut -d' ' -f1)" = "2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target" CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=2 CARGO_TERM_COLOR=never PYTHONDONTWRITEBYTECODE=1
export RUSTC="$TOOLCHAIN/bin/rustc" RUSTDOC="$TOOLCHAIN/bin/rustdoc" PATH="$TOOLCHAIN/bin:/usr/bin:/bin"
unset RUSTFLAGS CARGO_ENCODED_RUSTFLAGS RUSTC_WRAPPER RUSTDOCFLAGS
mkdir "$SOURCE"; tar -xzf "$ARCHIVE" -C "$SOURCE"; cp "$LOCK" "$SOURCE/Cargo.lock"; cd "$SOURCE"
test "$(sha256sum tests/sys_process.rs | cut -d' ' -f1)" = "$MAIN_SHA"
test "$(sha256sum tests/fixtures/sys_process_shared_child_contract.rs | cut -d' ' -f1)" = "$FIXTURE_SHA"
cp tests/fixtures/sys_process_shared_child_contract.rs "$AGENT_RUNTIME_DIR/shared-child.original.rs"
python3 - "$SOURCE/tests/fixtures/sys_process_shared_child_contract.rs" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); text=p.read_text()
start=text.index('fn drop_final_client('); end=text.index('\nfn panic_with_live_fixture(', start)
part=text[start:end]
branch_start=part.index('    if kill_on_drop {'); branch_end=part.index('    } else {',branch_start)
branch=part[branch_start:branch_end]
old='        wait_for_pid_gone(pid, Duration::from_secs(5));'
new='''        wait_for_pid_gone(pid, Duration::from_secs(5));
        assert!(
            !pid_is_esrch(pid),
            "RED control: kill_on_drop=true child unexpectedly disappeared after final drop"
        );'''
if branch.count(old)!=1: raise SystemExit(f'expected true-branch final-reap anchor once, got {branch.count(old)}')
branch=branch.replace(old,new,1)
part=part[:branch_start]+branch+part[branch_end:]
p.write_text(text[:start]+part+text[end:])
PY
sha256sum tests/fixtures/sys_process_shared_child_contract.rs > "$ATTEMPT/red-fixture.sha256"
test "$(cut -d' ' -f1 "$ATTEMPT/red-fixture.sha256")" != "$FIXTURE_SHA"
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
run_red() {
 profile="$1"; features=testing-environ,sys; [ "$profile" = standard ] || features=testing-environ,sys,sync
 set +e
 "$TOOLCHAIN/bin/cargo" test --locked --features "$features" --test sys_process --no-run --message-format=json > "$ATTEMPT/red-$profile-build.stdout.jsonl" 2> "$ATTEMPT/red-$profile-build.stderr"
 build_status=$?; set -e
 printf '%s\n' "$build_status" > "$ATTEMPT/red-$profile-build.status"; test "$build_status" -eq 0
 extract_exe "$ATTEMPT/red-$profile-build.stdout.jsonl" "$ATTEMPT/red-$profile-executable.txt"
 exe="$(cat "$ATTEMPT/red-$profile-executable.txt")"
 "$exe" --list > "$ATTEMPT/red-$profile-list.stdout" 2> "$ATTEMPT/red-$profile-list.stderr"
 grep -Fx "$SELECTOR: test" "$ATTEMPT/red-$profile-list.stdout" >/dev/null
 printf '%s --exact %s --nocapture --test-threads=1\n' "$exe" "$SELECTOR" > "$ATTEMPT/red-$profile.command.txt"
 set +e; "$exe" --exact "$SELECTOR" --nocapture --test-threads=1 > "$ATTEMPT/red-$profile.log" 2>&1; status=$?; set -e
 printf '%s\n' "$status" > "$ATTEMPT/red-$profile.status"
 python3 - "$status" "$SELECTOR" "$ATTEMPT/red-$profile.log" <<'PYVERIFY'
import re,sys
status,selector,log=sys.argv[1:]; status=int(status); text=open(log,encoding='utf-8',errors='replace').read()
if status!=101:raise SystemExit(f'expected RED exit 101, got {status}')
if not re.search(r'^test '+re.escape(selector)+r' \.\.\.',text,re.M):raise SystemExit('exact selector missing from parent output')
if 'RED control: kill_on_drop=true child unexpectedly disappeared after final drop' not in text:raise SystemExit('final kill_on_drop(true) RED assertion missing')
if 'shared-child nonfinal-drop pid=' not in text:raise SystemExit('RED did not reach and pass the nonfinal-clone challenge')
if 'shared-child final-drop kill_on_drop=true' in text:raise SystemExit('final-drop scenario unexpectedly passed its control')
if 'reap=ESRCH verified=true' not in text or 'watchdog fixture_closure=verified' not in text:raise SystemExit('fixture cleanup/reap not independently verified')
results=re.findall(r'^test result: (.+)$',text,re.M)
if not results or not results[-1].startswith('FAILED. 0 passed; 1 failed;'):raise SystemExit(f'expected one failed exact test, got {results[-1:]!r}')
PYVERIFY
}
run_red standard
run_red sync
cat > "$ATTEMPT/result.txt" <<EOF
source_archive_sha256=$(sha256sum "$ARCHIVE" | cut -d' ' -f1)
sys_process_test_baseline_sha256=$(sha256sum tests/sys_process.rs | cut -d' ' -f1)
committed_shared_fixture_sha256=$FIXTURE_SHA
lock_sha256=$(sha256sum "$LOCK" | cut -d' ' -f1)
red_mutated_fixture_sha256=$(cut -d' ' -f1 "$ATTEMPT/red-fixture.sha256")
selector=$SELECTOR
red_profiles=testing-environ,sys; testing-environ,sys,sync
red_exit_status=101 for both profiles
red_assertion=final kill_on_drop=true ESRCH expectation inverted after the nonfinal challenge and final-client release
cleanup=watchdog fixture_closure verified and exact PID ESRCH verified in both logs
green_reused_from=../attempt02/workhorse/green-standard-nonfinal_child_clone_drop_keeps_the_real_child_available.log and green-sync-nonfinal_child_clone_drop_keeps_the_real_child_available.log; original fixture restored hash matches committed fixture; source/toolchain/features/lock unchanged
scope_runtime=$AGENT_RUNTIME_DIR
EOF
