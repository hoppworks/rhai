#!/usr/bin/env bash
set -Eeuo pipefail
: "$SESSION_SCOPE"
: "$AGENT_RUNTIME_DIR"
scope="$SESSION_SCOPE"
runtime="$AGENT_RUNTIME_DIR"
attempt="$scope/attempt-01"
mkdir -p "$attempt"
printf 'started_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf 'runner_user=%s\n' "$(id -un)"
printf 'runtime=%s\n' "$runtime"
printf 'source_revision=4ec8fb1094885223d4e1923ee70825214512a5be\n'
printf 'test_source_sha256='
sha256sum "$scope/source/tests/sys_process.rs" | awk '{print $1}'
printf 'toolchain='
rustc --version
uname -a
sha256sum "$scope/source.tar" "$scope/source/tests/sys_process.rs" "$scope/source/Cargo.lock" "$scope/source/build.template" > "$attempt/input-identities.sha256"
cp -a "$scope/source" "$runtime/source"
export CARGO_TARGET_DIR="$runtime/target"
export CARGO_HOME="$runtime/cargo-home"
export CARGO_BUILD_JOBS=2
export RUSTUP_TOOLCHAIN=1.93.0
cd "$runtime/source"
cargo metadata --locked --offline --no-deps --format-version 1 > "$attempt/cargo-metadata.json" 2> "$attempt/cargo-metadata.stderr"
test_file=tests/sys_process.rs
test_name=missing_program_and_cwd_report_not_found_without_starting_child
mutate_expectation() {
  python3 - "$test_file" "$1" <<'PY'
import pathlib, sys
p=pathlib.Path(sys.argv[1]); which=sys.argv[2]; text=p.read_text()
start=text.index("fn missing_program_and_cwd_report_not_found_without_starting_child()")
end=text.index("\n#[cfg(not(feature = \"no_index\"))]\nfn assert_child_record", start)
head, body, tail=text[:start], text[start:end], text[end:]
needle="assert_eq!(kind, std::io::ErrorKind::NotFound);"
if body.count(needle) != 2: raise SystemExit("expected two target assertions")
replacement="assert_eq!(kind, std::io::ErrorKind::PermissionDenied);"
if which == "x2": body=body.replace(needle, replacement, 1)
elif which == "x8":
    pos=body.rfind(needle); body=body[:pos]+replacement+body[pos+len(needle):]
else: raise SystemExit("unknown mutation")
p.write_text(head+body+tail)
PY
}
restore_test() { cp "$scope/source/tests/sys_process.rs" "$test_file"; }
run_case() {
  local label="$1"
  set +e
  cargo test --locked --features testing-environ,sys --test sys_process "$test_name" -- --exact --nocapture --test-threads=1 > "$attempt/$label.stdout" 2> "$attempt/$label.stderr"
  local status=$?
  set -e
  printf '%s\n' "$status" > "$attempt/$label.exit"
  printf '%s_exit=%s\n' "$label" "$status"
}
mutate_expectation x2
run_case x2-red
restore_test
mutate_expectation x8
run_case x8-red
restore_test
run_case restored-green
if [[ "$(cat "$attempt/restored-green.exit")" != 0 ]]; then
  printf 'restored green failed\n' >&2
  exit 30
fi
sha256sum "$test_file" > "$attempt/restored-test.sha256"
printf 'completed_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
