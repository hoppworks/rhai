#!/usr/bin/env bash
set -euo pipefail

BASE=$(cd "$1" && pwd)
ATTEMPT="$BASE/attempt06"
: "${AGENT_RUNTIME_DIR:?scoped runner must supply runtime}"
SOURCE="$AGENT_RUNTIME_DIR/source"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_BUILD_JOBS=2
export PYTHONDONTWRITEBYTECODE=1
unset RUSTFLAGS CARGO_ENCODED_RUSTFLAGS RUSTC_WRAPPER RUSTDOCFLAGS
cd "$BASE"
sha256sum -c input-files.sha256
cd "$ATTEMPT"
sha256sum -c attempt-input-files.sha256
TOOLCHAIN=/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu
export RUSTC="$TOOLCHAIN/bin/rustc"
export RUSTDOC="$TOOLCHAIN/bin/rustdoc"
export PATH="$TOOLCHAIN/bin:$PATH"
CARGO="$TOOLCHAIN/bin/cargo"

mkdir "$SOURCE"
tar -xzf "$BASE/source.tar.gz" -C "$SOURCE"
cp "$BASE/Cargo.lock.accepted" "$SOURCE/Cargo.lock"
cd "$SOURCE"
printf '%s\n' "$PWD" > "$ATTEMPT/source-cwd.txt"
printf '%s\n' "uname=$(uname -a)" "rustc=$($RUSTC --version)" "cargo=$($CARGO --version)" "features=testing-environ,sys" "target=x86_64-unknown-linux-gnu" "jobs=$CARGO_BUILD_JOBS" "lock=$(sha256sum Cargo.lock | cut -d' ' -f1)" > "$ATTEMPT/environment.txt"
python3 - "$ATTEMPT" <<'PY'
from pathlib import Path
import hashlib,json,sys
attempt=Path(sys.argv[1])
manifest=json.loads((attempt/"inputs.json").read_text())
path=Path("tests/sys_process.rs")
if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest["base_test_source_sha256"]:
    raise SystemExit("base test source does not match accepted source archive")
import difflib
original=path.read_text()
updated=(attempt/"test-source-instrumented.rs").read_text()
patch="".join(difflib.unified_diff(original.splitlines(True),updated.splitlines(True),fromfile="a/tests/sys_process.rs",tofile="b/tests/sys_process.rs"))
if patch!=(attempt/"fixture-identity.patch").read_text():
    raise SystemExit("fixture identity patch does not match exact test-only instrumentation")
path.write_text(updated)
if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest["instrumented_test_source_sha256"]:
    raise SystemExit("instrumented test source SHA mismatch")
PY
python3 - "$ATTEMPT/owned-red.patch" tests/sys_process.rs "$ATTEMPT/inputs.json" <<'PY'
from pathlib import Path
import difflib,hashlib,json,sys
patch_path,source_path,manifest_path=map(Path,sys.argv[1:])
source=source_path.read_text()
manifest=json.loads(manifest_path.read_text())
if hashlib.sha256(source.encode()).hexdigest()!=manifest["instrumented_test_source_sha256"]:
    raise SystemExit("RED base is not the reviewed instrumented source")
changes=[
("managed_run_closes_worker_after_leader_exit_and_preserves_sentinel",'assert!(sentinel_live, "managed cleanup terminated unrelated sentinel");','assert!(!sentinel_live, "RED control expects unrelated sentinel to be killed");'),
("managed_run_closes_pipe_closed_worker_before_return",'assert_managed_pidfds_exited(&pidfds);','assert_managed_pidfds_live(&pidfds);'),
("direct_run_returns_with_pipe_closed_worker_live_control",'assert_managed_pidfds_live(&pidfds);','assert_managed_pidfds_exited(&pidfds);'),
]
mutated=source
for name,old,new in changes:
    start=mutated.index(f"fn {name}() {{")
    end=mutated.find("\n#[test]",start)
    if end<0: end=len(mutated)
    segment=mutated[start:end]
    if segment.count(old)!=1:
        raise SystemExit(f"{name}: expected one anchored assertion, got {segment.count(old)}")
    mutated=mutated[:start]+segment.replace(old,new,1)+mutated[end:]
expected="".join(difflib.unified_diff(source.splitlines(True),mutated.splitlines(True),fromfile="a/tests/sys_process.rs",tofile="b/tests/sys_process.rs"))
if expected!=patch_path.read_text():
    raise SystemExit("saved RED patch differs from function-anchored mutations")
source_path.write_text(mutated)
( Path(patch_path.parent)/"red-source.sha256" ).write_text(hashlib.sha256(mutated.encode()).hexdigest()+"\n")
PY

capture() {
  local name=$1
  shift
  printf '%s\n' "cwd=$PWD" > "$ATTEMPT/$name.command.txt"
  printf 'argv=' >> "$ATTEMPT/$name.command.txt"
  printf '%q ' "$@" >> "$ATTEMPT/$name.command.txt"
  printf '\n' >> "$ATTEMPT/$name.command.txt"
  set +e
  "$@" > "$ATTEMPT/$name.stdout" 2> "$ATTEMPT/$name.stderr"
  local status=$?
  set -e
  printf '%s\n' "$status" > "$ATTEMPT/$name.status"
  cat "$ATTEMPT/$name.stdout" "$ATTEMPT/$name.stderr" > "$ATTEMPT/$name.combined.log"
  printf '%s %s\n' "$name" "$status" >> "$ATTEMPT/phase-status.txt"
}

validate_build() {
  python3 - "$ATTEMPT/$1-build.stdout" <<'PY'
import hashlib,json,os,sys
rows=[]
for line in open(sys.argv[1]):
    try: rows.append(json.loads(line))
    except json.JSONDecodeError: pass
finished=[x for x in rows if x.get("reason")=="build-finished"]
arts=[x for x in rows if x.get("reason")=="compiler-artifact" and x.get("target",{}).get("name")=="sys_process"]
if len(finished)!=1 or not finished[0].get("success"):
    raise SystemExit("Cargo JSON lacks one successful build-finished record")
if len(arts)!=1:
    raise SystemExit(f"expected one sys_process compiler artifact, got {len(arts)}")
artifact=arts[0]
features=set(artifact.get("features",[]))
expected={"default","std","sys","testing-environ"}
if features!=expected:
    raise SystemExit(f"unexpected compiler artifact features: {sorted(features)}")
exe=artifact.get("executable")
if not exe or not os.path.isfile(exe) or not os.access(exe,os.X_OK):
    raise SystemExit(f"compiler-artifact executable missing or not executable: {exe!r}")
h=hashlib.sha256(open(exe,"rb").read()).hexdigest()
print(json.dumps({"build_finished":finished[0],"artifact":artifact,"executable":exe,"executable_sha256":h},sort_keys=True))
PY
}

artifact_for() {
  python3 - "$ATTEMPT/$1-build-readback.json" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))["executable"])
PY
}

selectors=(
  managed_run_closes_worker_after_leader_exit_and_preserves_sentinel
  managed_run_closes_pipe_closed_worker_before_return
  direct_run_returns_with_pipe_closed_worker_live_control
)
validate_list() {
  python3 - "$ATTEMPT/$1-list.stdout" <<'PY'
from pathlib import Path
import sys
selectors=[
"managed_run_closes_worker_after_leader_exit_and_preserves_sentinel",
"managed_run_closes_pipe_closed_worker_before_return",
"direct_run_returns_with_pipe_closed_worker_live_control",
]
lines=Path(sys.argv[1]).read_text().splitlines()
for selector in selectors:
    expected=selector+": test"
    if lines.count(expected)!=1:
        raise SystemExit(f"expected exact selector once: {selector}; saw {lines.count(expected)}")
print("all three exact X35 selectors listed once")
PY
}
validate_red() {
  local name=$1 selector=$2 expected=$3
  test "$(cat "$ATTEMPT/$name.status")" = 101
  grep -F "test $selector ... FAILED" "$ATTEMPT/$name.combined.log" >/dev/null
  grep -E "$expected" "$ATTEMPT/$name.combined.log" >/dev/null
  python3 - "$ATTEMPT/$name.combined.log" <<'PY'
from pathlib import Path
import re,sys
s=Path(sys.argv[1]).read_text(errors="replace")
rows=re.findall(r"^test result: FAILED\. 0 passed; 1 failed; 0 ignored; 0 measured; [0-9]+ filtered out; finished in .+$",s,re.M)
if len(rows)!=1: raise SystemExit(f"expected one failing-test summary row, got {len(rows)}")
print(rows[0])
PY
}
validate_green() {
  local name=$1 selector=$2
  test "$(cat "$ATTEMPT/$name.status")" = 0
  grep -F "test $selector ... ok" "$ATTEMPT/$name.combined.log" >/dev/null
  grep -F "test result: ok. 1 passed; 0 failed" "$ATTEMPT/$name.combined.log" >/dev/null
}

capture red-build "$CARGO" test --locked --features testing-environ,sys --test sys_process --no-run --message-format=json
 test "$(cat "$ATTEMPT/red-build.status")" = 0
validate_build red > "$ATTEMPT/red-build-readback.json"
RED_EXE=$(artifact_for red)
capture red-list "$RED_EXE" --list
 test "$(cat "$ATTEMPT/red-list.status")" = 0
validate_list red > "$ATTEMPT/red-list-readback.txt"
for i in 0 1 2; do
  n=$((i + 1))
  selector=${selectors[$i]}
  name=$(printf 'red-%02d' "$n")
  printf '%s\n' "selector=$selector" "source_sha256=$(sha256sum tests/sys_process.rs | cut -d' ' -f1)" > "$ATTEMPT/$name.started"
  capture "$name" "$RED_EXE" --exact "$selector" --nocapture --test-threads=1
  case "$n" in
    1) validate_red "$name" "$selector" 'RED control expects unrelated sentinel to be killed' ;;
    2) validate_red "$name" "$selector" 'control member pid=[0-9]+ start=[0-9]+ unexpectedly exited before API return' ;;
    3) validate_red "$name" "$selector" 'managed member pid=[0-9]+ start=[0-9]+ remained live at API return' ;;
  esac
done

cp "$ATTEMPT/test-source-instrumented.rs" tests/sys_process.rs
test "$(sha256sum tests/sys_process.rs | cut -d' ' -f1)" = "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["instrumented_test_source_sha256"])' "$ATTEMPT/inputs.json")"
printf '%s\n' "$(sha256sum tests/sys_process.rs | cut -d' ' -f1)" > "$ATTEMPT/green-source.sha256"
capture green-build "$CARGO" test --locked --features testing-environ,sys --test sys_process --no-run --message-format=json
test "$(cat "$ATTEMPT/green-build.status")" = 0
validate_build green > "$ATTEMPT/green-build-readback.json"
GREEN_EXE=$(artifact_for green)
capture green-list "$GREEN_EXE" --list
test "$(cat "$ATTEMPT/green-list.status")" = 0
validate_list green > "$ATTEMPT/green-list-readback.txt"
for i in 0 1 2; do
  n=$((i + 1))
  selector=${selectors[$i]}
  name=$(printf 'green-%02d' "$n")
  printf '%s\n' "selector=$selector" "source_sha256=$(sha256sum tests/sys_process.rs | cut -d' ' -f1)" > "$ATTEMPT/$name.started"
  capture "$name" "$GREEN_EXE" --exact "$selector" --nocapture --test-threads=1
  validate_green "$name" "$selector"
done
python3 - "$ATTEMPT" <<'PY'
from pathlib import Path
import json,sys
attempt=Path(sys.argv[1])
(attempt/"payload-summary.txt").write_text("Three X35 exact selectors: each function-anchored RED101 at its named assertion and restored instrumented-source GREEN0; independent PIDfd/process and fixture cleanup readbacks required.\n")
PY
