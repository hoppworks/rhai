#!/usr/bin/env bash
set -Eeuo pipefail

: "${SESSION_SCOPE:?SESSION_SCOPE must name this run scope}"
: "${AGENT_RUNTIME_DIR:?AGENT_RUNTIME_DIR must be provided by run_scoped.py}"

readonly expected_source_sha256=a243fc96c513c70d86e0281e0f178d91c95e6338ab3dda24d1656f7dd8863de5
readonly expected_lock_sha256=4ff0a7de6f504510af64092d446d411b86d95228b23a188b396bd188da367627
readonly toolchain=/home/workhorse/.rustup/toolchains/1.93.0-x86_64-unknown-linux-gnu/bin
readonly source_archive="$SESSION_SCOPE/source.tar.gz"
readonly pinned_lock="$SESSION_SCOPE/Cargo.lock"
readonly source_dir="$AGENT_RUNTIME_DIR/source"

case "$AGENT_RUNTIME_DIR" in
  "$SESSION_SCOPE"/*) ;;
  *) echo "AGENT_RUNTIME_DIR is outside SESSION_SCOPE: $AGENT_RUNTIME_DIR" >&2; exit 20 ;;
esac

actual_source_sha256=$(sha256sum "$source_archive" | cut -d' ' -f1)
actual_lock_sha256=$(sha256sum "$pinned_lock" | cut -d' ' -f1)
test "$actual_source_sha256" = "$expected_source_sha256"
test "$actual_lock_sha256" = "$expected_lock_sha256"
tar -tzf "$source_archive" | grep -Fxq 'build.template'

mkdir -p "$source_dir"
tar --no-same-owner --no-same-permissions -xzf "$source_archive" -C "$source_dir"
test -f "$source_dir/build.template"
cp "$pinned_lock" "$source_dir/Cargo.lock"
test "$(sha256sum "$source_dir/Cargo.lock" | cut -d' ' -f1)" = "$expected_lock_sha256"

export PATH="$toolchain:$PATH"
export RUSTC="$toolchain/rustc"
export RUSTDOC="$toolchain/rustdoc"
export CARGO_HOME="$AGENT_RUNTIME_DIR/cargo-home"
export CARGO_TARGET_DIR="$AGENT_RUNTIME_DIR/target"
export CARGO_BUILD_JOBS=2
export CARGO_INCREMENTAL=0
test "$("$RUSTC" --version)" = 'rustc 1.93.0 (254b59607 2026-01-19)'

cd "$source_dir"
{
  echo "SOURCE_TAR_SHA256=$actual_source_sha256"
  echo "LOCK_SHA256=$actual_lock_sha256"
  echo "RUSTC=$("$RUSTC" --version)"
  echo "CARGO=$(cargo --version)"
  echo 'COMMAND=cargo test --locked --features testing-environ,sys,net,metadata --test net_metadata --test sys_policy metadata -- --nocapture --test-threads=1'
} | tee "$SESSION_SCOPE/launch-inputs.txt"

set +e
python3 - "$SESSION_SCOPE" "$AGENT_RUNTIME_DIR" <<'PY' 2> "$SESSION_SCOPE/resource-guard.log"
import json
import os
import pathlib
import subprocess
import sys
import time

scope = pathlib.Path(sys.argv[1]).resolve(strict=True)
runtime = pathlib.Path(sys.argv[2]).resolve(strict=True)
log_path = scope / 'native-red.log'
samples_path = scope / 'resource-samples.jsonl'
status_path = scope / 'native-red.status'
argv = [
    'cargo', 'test', '--locked', '--features',
    'testing-environ,sys,net,metadata', '--test', 'net_metadata', '--test',
    'sys_policy', 'metadata', '--', '--nocapture', '--test-threads=1',
]
started = time.monotonic()
deadline = started + 510
sampled_max = {'rss_kib': 0, 'storage_kib': 0, 'descendants': 0}
stop_reason = None


def process_snapshot():
    found = {}
    for entry in pathlib.Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            raw = pathlib.Path('/proc', entry.name, 'stat').read_text()
            fields = raw[raw.rfind(')') + 2:].split()
            ppid = int(fields[1])
            status = pathlib.Path('/proc', entry.name, 'status').read_text()
            rss_line = next(line for line in status.splitlines() if line.startswith('VmRSS:'))
            rss_kib = int(rss_line.split()[1])
        except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError, StopIteration, ValueError):
            continue
        found[pid] = (ppid, rss_kib)
    return found


def sample_resources():
    du = subprocess.run(
        ['du', '-sk', str(runtime)], capture_output=True, text=True,
        check=True, timeout=4,
    )
    fields = du.stdout.strip().split()
    if len(fields) < 2 or not fields[0].isdigit() or pathlib.Path(fields[1]).resolve() != runtime:
        raise RuntimeError('malformed private-runtime storage sample')
    storage_kib = int(fields[0])
    processes = process_snapshot()
    root = os.getpid()
    if root not in processes:
        raise RuntimeError('resource-guard process disappeared from /proc sample')
    owned = {root}
    while True:
        children = {pid for pid, (ppid, _rss) in processes.items() if ppid in owned} - owned
        if not children:
            break
        owned.update(children)
    rss_kib = sum(processes[pid][1] for pid in owned)
    descendants = len(owned) - 1
    row = {
        'utc_epoch': round(time.time(), 3),
        'elapsed_seconds': round(time.monotonic() - started, 3),
        'storage_kib': storage_kib,
        'rss_kib': rss_kib,
        'descendants': descendants,
    }
    with samples_path.open('a', encoding='utf-8') as output:
        output.write(json.dumps(row, sort_keys=True) + '\n')
        output.flush()
        os.fsync(output.fileno())
    for key in sampled_max:
        sampled_max[key] = max(sampled_max[key], row[key])
    if storage_kib >= 1_572_864:
        raise RuntimeError(f'sampled private storage reached preemptive stop: {storage_kib} KiB')
    if storage_kib >= 2_097_152:
        raise RuntimeError(f'sampled private storage reached hard stop: {storage_kib} KiB')
    if rss_kib >= 2_097_152:
        raise RuntimeError(f'sampled helper RSS reached hard stop: {rss_kib} KiB')
    if descendants > 16:
        raise RuntimeError(f'helper descendants exceeded limit: {descendants}')


with log_path.open('wb') as log:
    child = subprocess.Popen(
        argv, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
        close_fds=True,
    )
    try:
        while child.poll() is None:
            if time.monotonic() >= deadline:
                stop_reason = '510-second work deadline reached (30-second export reserve retained)'
                raise TimeoutError(stop_reason)
            sample_resources()
            time.sleep(1)
        status = child.wait()
        sample_resources()
    except BaseException as exc:
        stop_reason = stop_reason or f'{type(exc).__name__}: {exc}'
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=3)
        status = child.returncode if child.returncode is not None else 125
    log.flush()
    os.fsync(log.fileno())

(scope / 'resource-maxima.json').write_text(json.dumps({
    'sampling_interval_seconds': 1,
    'sampled_maxima': sampled_max,
    'preemptive_storage_stop_kib': 1_572_864,
    'hard_storage_stop_kib': 2_097_152,
    'hard_rss_stop_kib': 2_097_152,
    'descendant_limit': 16,
    'work_deadline_seconds': 510,
    'outer_helper_limit_seconds': 540,
    'stop_reason': stop_reason,
}, indent=2, sort_keys=True) + '\n', encoding='utf-8')
status_path.write_text(f'{status}\n', encoding='ascii')
if stop_reason:
    print(f'RESOURCE_GUARD_STOP={stop_reason}', file=sys.stderr, flush=True)
    sys.exit(125)
sys.stdout.buffer.write(log_path.read_bytes())
sys.stdout.buffer.flush()
sys.exit(status)
PY
status=$?
set -e
printf '%s\n' "$status" > "$SESSION_SCOPE/native-red.status"
echo "CARGO_TEST_STATUS=$status"

if [ "$status" -eq 0 ]; then
  echo UNEXPECTED_GREEN
  exit 4
fi
if [ -s "$SESSION_SCOPE/resource-guard.log" ]; then
  echo RESOURCE_GUARD_FAILURE
  exit 6
fi
if grep -Eq 'metadata comments are empty|metadata should explain|every .* metadata entry should mention' "$SESSION_SCOPE/native-red.log"; then
  echo EXPECTED_TDD_RED
  exit 0
fi
echo NON_ASSERTION_FAILURE
exit 5
