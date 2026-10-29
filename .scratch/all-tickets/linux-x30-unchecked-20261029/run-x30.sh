#!/usr/bin/env bash
set -euo pipefail
repo="$1"
evidence="$2"
scope="$3"
pinned_lock="$4"
toolchain="$5"
commit="$6"
runtime="$AGENT_RUNTIME_DIR"
test -n "$runtime"
test "$(git -C "$repo" rev-parse HEAD)" = "$commit"
test "$(sha256sum "$repo/Cargo.toml" | cut -d" " -f1)" = 62fc31d2eaf0d74aa9f631032606ded135ab910bbaf0ac09493427b975d47c81
test "$(sha256sum "$pinned_lock" | cut -d" " -f1)" = 12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802
mkdir -p "$runtime/source"
git -C "$repo" archive "$commit" | tar -x -C "$runtime/source"
cp "$pinned_lock" "$runtime/source/Cargo.lock"
cp "$runtime/source/tests/sys_process.rs" "$runtime/test-original.rs"
export PATH="$toolchain:$PATH"
export RUSTC="$toolchain/rustc"
export CARGO_TARGET_DIR="$runtime/target"
export CARGO_HOME="$runtime/cargo-home"
export CARGO_BUILD_JOBS=2
mkdir -p "$CARGO_HOME"
printf 'commit=%s\nCargo.toml_sha256=%s\nCargo.lock_sha256=%s\ntest_source_original_sha256=%s\nuname=' "$commit" "$(sha256sum "$runtime/source/Cargo.toml" | cut -d" " -f1)" "$(sha256sum "$runtime/source/Cargo.lock" | cut -d" " -f1)" "$(sha256sum "$runtime/test-original.rs" | cut -d" " -f1)" > "$evidence/source-binding.txt"
uname -a >> "$evidence/source-binding.txt"
printf 'cargo=%s\nrustc=%s\nfeatures=testing-environ,sys,unchecked\ntest=repeated_public_run_calls_keep_fd_count_stable\n' "$(cargo --version)" "$(rustc --version)" >> "$evidence/source-binding.txt"
python3 - "$runtime/source/tests/sys_process.rs" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
old = 'assert_eq!(after.1, baseline.1, "200 sequential public run calls changed the descriptor count");'
new = 'assert_eq!(after.1, baseline.1 + 1, "200 sequential public run calls changed the descriptor count");'
if s.count(old) != 1:
    raise SystemExit(f"expected one X30 assertion to mutate, found {s.count(old)}")
p.write_text(s.replace(old, new))
PY
printf 'RED command: cargo test --locked --features testing-environ,sys,unchecked --test sys_process repeated_public_run_calls_keep_fd_count_stable -- --exact --nocapture --test-threads=1\n' > "$evidence/commands.txt"
set +e
(cd "$runtime/source" && cargo test --locked --features testing-environ,sys,unchecked --test sys_process repeated_public_run_calls_keep_fd_count_stable -- --exact --nocapture --test-threads=1) > "$evidence/red.log" 2>&1
red_status=$?
set -e
printf 'red_exit=%s\n' "$red_status" >> "$evidence/commands.txt"
if [ "$red_status" -ne 101 ]; then
  echo "expected assertion RED exit 101, got $red_status" >&2
  tail -100 "$evidence/red.log" >&2
  exit 31
fi
grep -F '200 sequential public run calls changed the descriptor count' "$evidence/red.log" >/dev/null
grep -F 'assertion `left == right` failed' "$evidence/red.log" >/dev/null
cp "$runtime/test-original.rs" "$runtime/source/tests/sys_process.rs"
set +e
(cd "$runtime/source" && cargo test --locked --features testing-environ,sys,unchecked --test sys_process repeated_public_run_calls_keep_fd_count_stable -- --exact --nocapture --test-threads=1) > "$evidence/green.log" 2>&1
green_status=$?
set -e
printf 'GREEN command: cargo test --locked --features testing-environ,sys,unchecked --test sys_process repeated_public_run_calls_keep_fd_count_stable -- --exact --nocapture --test-threads=1\ngreen_exit=%s\n' "$green_status" >> "$evidence/commands.txt"
if [ "$green_status" -ne 0 ]; then
  echo "expected restored GREEN exit 0, got $green_status" >&2
  tail -120 "$evidence/green.log" >&2
  exit 32
fi
grep -F 'test repeated_public_run_calls_keep_fd_count_stable ... ok' "$evidence/green.log" >/dev/null
grep -F 'x30_process_run_fd_stability iterations=200' "$evidence/green.log" >/dev/null
python3 - "$evidence/green.log" <<'PY'
from pathlib import Path
import re, sys
s = Path(sys.argv[1]).read_text()
m = re.search(r'x30_process_run_fd_stability iterations=200 baseline_tasks=(\d+) baseline_fds=(\d+) baseline_cleanup_workers=(\d+) after_tasks=(\d+) after_fds=(\d+) after_cleanup_workers=(\d+)', s)
if not m:
    raise SystemExit('missing exact 200-run independent census marker')
values = tuple(map(int, m.groups()))
if values[1] != values[4]:
    raise SystemExit(f'descriptor readback differs: baseline={values[1]} after={values[4]}')
Path(sys.argv[1] + '.readback.txt').write_text('tasks baseline/after=%s/%s\nfds baseline/after=%s/%s\ncleanup_workers baseline/after=%s/%s\n' % (values[0], values[3], values[1], values[4], values[2], values[5]))
PY
printf 'mutant_test_source_sha256=%s\nrestored_test_source_sha256=%s\n' "$(sha256sum "$runtime/source/tests/sys_process.rs" | cut -d" " -f1)" "$(sha256sum "$runtime/test-original.rs" | cut -d" " -f1)" >> "$evidence/source-binding.txt"
printf 'RED status 101 plus intended descriptor assertion; restored GREEN status 0; exact 200-call marker and /proc readback verified.\n' > "$evidence/result.txt"
