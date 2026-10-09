#!/usr/bin/env bash
set -euo pipefail
ATTEMPT="$(cd "$(dirname "$0")" && pwd)"
BASE="/var/roothome/rhai-evidence/linux-managed-drop-attempt02-20261009T1733Z-a7c3e1/linux-managed-drop-20261009T1518Z-6cf30d"
ARCHIVE="$BASE/source.tar.gz"; LOCK="$BASE/Cargo.lock.accepted"
TOOLCHAIN="/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu"
SOURCE="$AGENT_RUNTIME_DIR/source"
MAIN_SHA="86f1142ff1ae8de5a8b813e892e407a90c1bec70eab864c20b7735f53015bf41"
FIXTURE_SHA="1faf45c57a4fefeaa05683043e064d3485e892887986fef749bedc974230b217"
BASE_PROFILES=(standard sync)
BASE_SELECTORS=(
 'shared_child_contract::spawn_returns_while_large_stdin_is_blocked_and_wait_snapshots_are_stable'
 'shared_child_contract::nonfinal_child_clone_drop_keeps_the_real_child_available'
 'shared_child_contract::final_drop_honors_both_kill_on_drop_policies'
 'shared_child_contract::script_throw_drops_and_reaps_a_live_child'
)
SYNC_SELECTOR='shared_child_contract::sync_waiter_can_be_cancelled_through_another_shared_child_handle'
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
scoped=[
('fn blocked_input_wait_snapshot(', 'fn drop_final_client(', 'assert_eq!(first["code"].as_int().unwrap(), 17);', 'assert_eq!(first["code"].as_int().unwrap(), 18, "RED control: blocked-input child exit code unexpectedly matched");'),
('fn drop_final_client(', 'fn panic_with_live_fixture(', 'issue_probe(&engine, &mut scope, root, pid, "one");', 'assert!(!try_issue_probe(&engine, &mut scope, root, pid, "one", Duration::from_secs(3)), "RED control: nonfinal child clone unexpectedly preserved the live child");'),
('fn drop_final_client(', 'fn panic_with_live_fixture(', 'try_issue_probe(&engine, &mut scope, root, pid, "two", Duration::from_secs(3)),', '!try_issue_probe(&engine, &mut scope, root, pid, "two", Duration::from_secs(3)),'),
('fn script_throw_with_live_fixture(', 'fn assert_script_throw_error(', 'assert_script_throw_error(&detail, "intentional Rhai script throw with live child");', 'assert_script_throw_error(&detail, "RED control: expected unrelated Rhai error");'),
('#[cfg(feature = "sync")]\nfn sync_wait_cancel(', 'fn issue_probe(', 'assert!(final_result.contains_key("code"));', 'assert!(!final_result.contains_key("code"), "RED control: cancelled sync wait unexpectedly returned the retained process report");'),
]
for i,(startmark,endmark,old,new) in enumerate(scoped):
    start=text.index(startmark)
    end=text.index(endmark,start+len(startmark))
    part=text[start:end]
    if i==2:
        anchor='"kill_on_drop=false must leave the child operational after final-client drop"'
        if part.count(anchor)!=1: raise SystemExit(f'expected one false-drop diagnostic; got {part.count(anchor)}')
        part=part.replace(anchor, '"RED control: kill_on_drop=false child unexpectedly remained operational"',1)
    else:
        if part.count(old)!=1: raise SystemExit(f'expected one scoped anchor in {startmark}; got {part.count(old)}')
        part=part.replace(old,new,1)
    text=text[:start]+part+text[end:]
p.write_text(text)
PY
sha256sum tests/fixtures/sys_process_shared_child_contract.rs > "$ATTEMPT/red-fixture.sha256"
test "$(cut -d' ' -f1 "$ATTEMPT/red-fixture.sha256")" != "$FIXTURE_SHA"
"$TOOLCHAIN/bin/rustc" --version --verbose > "$ATTEMPT/rustc-version.txt"; "$TOOLCHAIN/bin/cargo" --version --verbose > "$ATTEMPT/cargo-version.txt"; uname -a > "$ATTEMPT/uname.txt"
extract_exe() {
  python3 - "$1" "$2" <<'PY'
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
PY
}
run_profile() {
  phase="$1"; profile="$2"
  if [ "$profile" = standard ]; then features=testing-environ,sys; selectors=("${BASE_SELECTORS[@]}"); else features=testing-environ,sys,sync; selectors=("${BASE_SELECTORS[@]}" "$SYNC_SELECTOR"); fi
  set +e
  "$TOOLCHAIN/bin/cargo" test --locked --features "$features" --test sys_process --no-run --message-format=json > "$ATTEMPT/$phase-$profile-build.stdout.jsonl" 2> "$ATTEMPT/$phase-$profile-build.stderr"
  build_status=$?
  set -e
  printf '%s\n' "$build_status" > "$ATTEMPT/$phase-$profile-build.status"
  test "$build_status" -eq 0
  extract_exe "$ATTEMPT/$phase-$profile-build.stdout.jsonl" "$ATTEMPT/$phase-$profile-executable.txt"
  exe="$(cat "$ATTEMPT/$phase-$profile-executable.txt")"
  "$exe" --list > "$ATTEMPT/$phase-$profile-list.stdout" 2> "$ATTEMPT/$phase-$profile-list.stderr"
  for selector in "${selectors[@]}"; do grep -Fx "$selector: test" "$ATTEMPT/$phase-$profile-list.stdout" >/dev/null; done
  if [ "$profile" = standard ]; then ! grep -Fx "$SYNC_SELECTOR: test" "$ATTEMPT/$phase-$profile-list.stdout" >/dev/null; fi
  for selector in "${selectors[@]}"; do
    label="$(printf '%s' "$selector" | sed 's/.*:://')"
    printf '%s --exact %s --nocapture --test-threads=1\n' "$exe" "$selector" > "$ATTEMPT/$phase-$profile-$label.command.txt"
    set +e
    "$exe" --exact "$selector" --nocapture --test-threads=1 > "$ATTEMPT/$phase-$profile-$label.log" 2>&1
    test_status=$?
    set -e
    printf '%s\n' "$test_status" > "$ATTEMPT/$phase-$profile-$label.status"
    python3 - "$phase" "$test_status" "$selector" "$ATTEMPT/$phase-$profile-$label.log" <<'PYVALIDATE'
import re,sys
phase,status,selector,log_path=sys.argv[1:]
status=int(status); text=open(log_path, encoding="utf-8", errors="replace").read()
if not re.search(r"^test "+re.escape(selector)+r" \.\.\.", text, re.M):
    raise SystemExit("selected exact test missing from parent harness output")
results=re.findall(r"^test result: (.+)$", text, re.M)
if not results: raise SystemExit("test result summary missing")
summary=results[-1]
if phase == "red":
    if status != 101: raise SystemExit(f"expected exact-test RED exit 101, got {status}")
    if "RED control:" not in text: raise SystemExit("intended RED assertion marker missing")
    if not summary.startswith("FAILED. 0 passed; 1 failed;"):
        raise SystemExit(f"expected one failing exact test in final summary, got {summary!r}")
else:
    if status != 0: raise SystemExit(f"expected GREEN exit 0, got {status}")
    if not summary.startswith("ok. 1 passed; 0 failed;"):
        raise SystemExit(f"expected one passing exact test in final summary, got {summary!r}")
PYVALIDATE

  done
}
run_profile red standard
run_profile red sync
cp "$AGENT_RUNTIME_DIR/shared-child.original.rs" tests/fixtures/sys_process_shared_child_contract.rs
sha256sum tests/fixtures/sys_process_shared_child_contract.rs > "$ATTEMPT/restored-fixture.sha256"
test "$(cut -d' ' -f1 "$ATTEMPT/restored-fixture.sha256")" = "$FIXTURE_SHA"
run_profile green standard
run_profile green sync
cat > "$ATTEMPT/result.txt" <<EOF
source_archive_sha256=$(sha256sum "$ARCHIVE" | cut -d' ' -f1)
sys_process_test_baseline_sha256=$(sha256sum tests/sys_process.rs | cut -d' ' -f1)
shared_fixture_baseline_sha256=$(cut -d' ' -f1 "$ATTEMPT/restored-fixture.sha256")
lock_sha256=$(sha256sum "$LOCK" | cut -d' ' -f1)
profiles=testing-environ,sys; testing-environ,sys,sync
red_builds=standard:0 sync:0
green_builds=standard:0 sync:0
red_selectors=standard:4 sync:5
green_selectors=standard:4 sync:5
scope_runtime=$AGENT_RUNTIME_DIR
EOF
