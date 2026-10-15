#!/usr/bin/env bash
set -Eeuo pipefail
repo=/var/home/Daniel/projects/rhai
attempt=$repo/.scratch/all-tickets/linux-x36-sync-20261015/attempt-01
evidence=$attempt/evidence
scope=/root/.local/share/agent-builds/rhai/x36-sync-20261015-03
runtime=$AGENT_RUNTIME_DIR
runner=/var/home/Daniel/projects/agent-skills/tools/run_scoped.py
revision=0981631785e9e2c2d485544b24d165a3bc21ab0c
toolchain=/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin
cargo=$toolchain/cargo
test_name=managed_scope_kernel_setpgid_denial_cleans_created_group
mkdir -p "$evidence" "$runtime/source" "$runtime/cargo-home" "$runtime/target"
{
  date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
  uname -a
  printf 'revision=%s\nruntime=%s\nTMPDIR=%s\nscope=%s\n' "$revision" "$runtime" "$TMPDIR" "$scope"
  printf 'runner_sha256='; sha256sum "$runner" | awk '{print $1}'
  printf 'cargo_jobs=1\nmax_phase_seconds=300\n'
  free -h
  df -h "$repo"
  printf 'Foreign activity is preserved and not copied into package evidence.\n'
} > "$evidence/environment.txt"
git -C "$repo" archive "$revision" | tar --no-same-owner -xf - -C "$runtime/source"
cp "$repo/.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock" "$runtime/source/Cargo.lock"
cp "$runtime/source/src/packages/sys/process/unix.rs" "$runtime/unix.rs.original"
cd "$runtime/source"
sha256sum Cargo.toml Cargo.lock src/packages/sys/process/unix.rs > "$evidence/source-hashes.txt"
test "$(sha256sum Cargo.lock | awk '{print $1}')" = 2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
printf 'cargo=' > "$evidence/toolchain.txt"; "$cargo" --version >> "$evidence/toolchain.txt"
printf 'rustc=' >> "$evidence/toolchain.txt"; "$toolchain/rustc" --version >> "$evidence/toolchain.txt"
export CARGO_HOME="$runtime/cargo-home" CARGO_TARGET_DIR="$runtime/target" CARGO_BUILD_JOBS=1 CARGO_TERM_COLOR=never
export RUSTC="$toolchain/rustc" RUSTDOC="$toolchain/rustdoc" PATH="$toolchain:$PATH"
phase_run() {
  name=$1
  features=$2
  expected=$3
  if timeout 300s "$cargo" test --locked --features "$features" --lib "$test_name" -- --nocapture --test-threads=1 > "$evidence/$name.log" 2>&1; then rc=0; else rc=$?; fi
  printf '%s features=%s status=%s expected=%s\n' "$name" "$features" "$rc" "$expected" >> "$evidence/statuses.txt"
  test "$rc" = "$expected"
  if [ "$expected" = 101 ]; then
    grep -Fq 'managed scope setup failure must not run the program' "$evidence/$name.log"
    grep -Fq 'test result: FAILED. 0 passed; 1 failed' "$evidence/$name.log"
  else
    grep -Fq 'test result: ok. 1 passed; 0 failed' "$evidence/$name.log"
    python3 - "$evidence/$name.log" "$evidence/$name-readback.txt" <<'PYREAD'
import os, re, sys
text = open(sys.argv[1], encoding='utf-8').read()
pat = re.compile(r'managed-scope-setup operation=(run|spawn) child_pid=([0-9]+) failure_point=KernelSetpgidDenial pid=ESRCH group=ESRCH reservation=retired marker=absent')
rows = pat.findall(text)
assert len(rows) == 2 and {op for op, _ in rows} == {'run', 'spawn'}, rows
with open(sys.argv[2], 'w') as out:
    for op, raw in rows:
        pid = int(raw)
        for label, probe in [('pid', lambda: os.kill(pid, 0)), ('group', lambda: os.killpg(pid, 0))]:
            try:
                probe()
            except ProcessLookupError:
                pass
            else:
                raise AssertionError(f'{op} {label} {pid} remains')
        out.write(f'operation={op} pid={pid} pid_absent=true group_absent=true\n')
PYREAD
  fi
}
mutate() {
  python3 - "$runtime/source/src/packages/sys/process/unix.rs" <<'PYMUT'
from pathlib import Path
import sys
p = Path(sys.argv[1])
source = p.read_text()
needle = "    #[cfg(test)]\n    if let Some(fd) = kernel_setpgid_denial {\n        create_kernel_managed_scope_setpgid_denial(fd)?;\n    }\n"
assert source.count(needle) == 1, source.count(needle)
p.write_text(source.replace(needle, "    #[cfg(test)]\n    let _ = kernel_setpgid_denial;\n"))
PYMUT
}
restore() {
  cp "$runtime/unix.rs.original" "$runtime/source/src/packages/sys/process/unix.rs"
}
features=testing-environ,sys,sync
phase_run checked-sync-green "$features" 0
features=testing-environ,sys,sync,unchecked
mutate
phase_run unchecked-sync-red "$features" 101
restore
restored_sha=$(sha256sum "$runtime/source/src/packages/sys/process/unix.rs" | awk '{print $1}')
source_sha=$(awk '$2=="src/packages/sys/process/unix.rs" {print $1}' "$evidence/source-hashes.txt")
test "$restored_sha" = "$source_sha"
phase_run unchecked-sync-green "$features" 0
sha256sum "$runtime/source/src/packages/sys/process/unix.rs" > "$evidence/restored-source.sha256"
test "$(awk '{print $1}' "$evidence/restored-source.sha256")" = "$(awk '$2=="src/packages/sys/process/unix.rs" {print $1}' "$evidence/source-hashes.txt")"
free -h > "$evidence/capacity-after.txt"
printf 'all four profile phases matched expected assertion results; restored source verified\n' > "$evidence/result.txt"
