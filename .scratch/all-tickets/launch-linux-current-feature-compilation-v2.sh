#!/usr/bin/env bash
set -euo pipefail
umask 077

stage=/root/rhai-linux-current-features-v2-1ca21e32-20261002
scope=/root/.local/share/agent-builds/rhai/linux-current-features-v2-1ca21e32-20261002
runner="$stage/runner/tools/run_scoped.py"
helper="$stage/run-feature-compilation.py"
evidence="$stage/outer-evidence"
runner_pid=
runner_status=125
launcher_interrupted=0
readback_status=1
runtime_status=1
scope_status=1
outer_status=1
finalized=0

test -d "$stage"
(cd "$stage" && sha256sum --check input-identities.sha256)
test ! -e "$evidence"
mkdir -m 700 "$evidence"
exec > >(tee -a "$evidence/outer.log") 2>&1

on_exit() {
  status=$?
  if (( finalized == 0 )) && [[ ! -e "$evidence/outer-status.txt" ]]; then
    printf '%s\n' "$status" > "$evidence/outer-status.txt"
  fi
}
on_signal() {
  signal_name=$1
  trap '' TERM INT
  launcher_interrupted=1
  printf 'launcher_signal=%s\n' "$signal_name"
  printf 'signal=%s requested_utc=%s\n' "$signal_name" "$(date -u +%FT%TZ)" \
    > "$evidence/interrupt.request"
}
trap on_exit EXIT
trap 'on_signal TERM' TERM
trap 'on_signal INT' INT

printf 'launch_utc=%s\n' "$(date -u +%FT%TZ)"
printf 'runner_timeout_seconds=590\n'
printf 'stage=%s\nscope=%s\n' "$stage" "$scope"

python3 - "$evidence/launcher-identities.tsv" launcher "$$" <<'PY'
import pathlib, sys
output, label, pid = pathlib.Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
proc = pathlib.Path('/proc') / str(pid)
try:
    raw = (proc / 'stat').read_text()
    fields = raw[raw.rfind(')') + 2:].split()
    command = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace').strip()
    row = f'{label}\t{pid}\t{fields[1]}\t{fields[2]}\t{fields[19]}\t{command}\n'
except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError):
    row = f'{label}\t{pid}\t<exited-before-identity-sample>\n'
output.write_text('label\tpid\tppid\tpgid\tstart_ticks\tcmdline\n' + row)
PY

test ! -e "$scope"
mkdir -p "$(dirname "$scope")"
mkdir -m 700 "$scope"
PROOF_STAGE="$stage" TMPDIR="$scope" INTERRUPT_REQUEST="$evidence/interrupt.request" \
  python3 "$runner" --timeout 590 -- python3 "$helper" &
runner_pid=$!
python3 - "$evidence/launcher-identities.tsv" run-scoped "$runner_pid" <<'PY'
import pathlib, sys, time
output, label, pid = pathlib.Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
for _ in range(100):
    proc = pathlib.Path('/proc') / str(pid)
    try:
        raw = (proc / 'stat').read_text()
        fields = raw[raw.rfind(')') + 2:].split()
        command = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace').strip()
        with output.open('a') as stream:
            stream.write(f'{label}\t{pid}\t{fields[1]}\t{fields[2]}\t{fields[19]}\t{command}\n')
            stream.flush()
        break
    except FileNotFoundError:
        time.sleep(.01)
    except (PermissionError, IndexError, ValueError):
        with output.open('a') as stream:
            stream.write(f'{label}\t{pid}\t<identity-unavailable>\n')
        break
else:
    with output.open('a') as stream:
        stream.write(f'{label}\t{pid}\t<exited-before-identity-sample>\n')
PY

while :; do
  set +e
  wait "$runner_pid"
  wait_status=$?
  set -e
  if (( launcher_interrupted )); then
    # Bash wait can return early when the launcher's signal trap runs. Re-enter
    # wait on the exact child; run_scoped retains its prescribed 590-second cap.
    launcher_interrupted=0
    continue
  fi
  runner_status=$wait_status
  break
done
printf '%s\n' "$runner_status" > "$evidence/run-scoped.status"
printf 'run_scoped_status=%s\n' "$runner_status"

runtime=$(sed -n 's/^PRIVATE_RUNTIME //p' "$evidence/outer.log" | tail -1)
if [[ -z "$runtime" ]]; then
  runtime_status=1
  printf 'runtime_cleanup_status=1 reason=helper-runtime-path-not-recorded\n' \
    > "$evidence/runtime-cleanup.tsv"
elif [[ "$runtime" != "$scope"/agent-build-* ]]; then
  runtime_status=1
  printf 'runtime_cleanup_status=1 runtime=%s reason=outside-prescribed-scope\n' "$runtime" \
    > "$evidence/runtime-cleanup.tsv"
elif [[ -e "$runtime" ]]; then
  runtime_status=1
  printf 'runtime_cleanup_status=1 runtime=%s reason=runtime-still-exists\n' "$runtime" \
    > "$evidence/runtime-cleanup.tsv"
else
  runtime_status=0
  printf 'runtime_cleanup_status=0 runtime=%s\n' "$runtime" \
    > "$evidence/runtime-cleanup.tsv"
fi

if python3 - "$evidence" "$runner_pid" "$stage/proof-evidence" <<'PY'
import pathlib, subprocess, sys
evidence, runner_pid = pathlib.Path(sys.argv[1]), int(sys.argv[2])
checks = []
pgids = set()

def same_process(pid, start_ticks):
    try:
        raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
        fields = raw[raw.rfind(')') + 2:].split()
        return fields[19] == start_ticks
    except (FileNotFoundError, ProcessLookupError):
        return False
    except (PermissionError, IndexError, ValueError):
        return None

launcher_ids = evidence / 'launcher-identities.tsv'
for line in launcher_ids.read_text(errors='replace').splitlines()[1:]:
    fields = line.split('\t', 5)
    if len(fields) == 6 and fields[0] == 'run-scoped':
        pid, start = int(fields[1]), fields[4]
        checks.append(('run-scoped', pid, start, same_process(pid, start)))

helper_ids = pathlib.Path(sys.argv[3]) / 'process-identities.tsv'
required_labels = {'helper', 'scoped-supervisor'}
seen_labels = set()
if helper_ids.is_file():
    for line in helper_ids.read_text(errors='replace').splitlines()[1:]:
        fields = line.split('\t', 5)
        if len(fields) != 6 or not fields[1].isdigit() or not fields[3].isdigit() or not fields[4].isdigit():
            raise SystemExit(f'malformed required helper identity row: {line!r}')
        label, pid_text, _ppid, pgid_text, start, _command = fields
        pid, pgid = int(pid_text), int(pgid_text)
        alive = same_process(pid, start)
        if alive is None:
            raise SystemExit(f'cannot determine exact process identity status: {label} {pid}')
        checks.append((label, pid, start, alive))
        seen_labels.add(label)
        if label in ('helper', 'scoped-supervisor'):
            pgids.add(pgid)
else:
    raise SystemExit(f'helper identity file missing: {helper_ids}')
if not required_labels.issubset(seen_labels):
    raise SystemExit(f'required helper/supervisor identities missing: {required_labels - seen_labels}')

launcher_rows = []
for line in launcher_ids.read_text(errors='replace').splitlines()[1:]:
    fields = line.split('\t', 5)
    if len(fields) != 6 or not fields[1].isdigit() or not fields[4].isdigit():
        raise SystemExit(f'malformed launcher identity row: {line!r}')
    label, pid_text, _ppid, _pgid, start, _command = fields
    pid = int(pid_text)
    alive = same_process(pid, start)
    if alive is None:
        raise SystemExit(f'cannot determine exact process identity status: {label} {pid}')
    launcher_rows.append((label, pid, start, alive))
if not any(row[0] == 'launcher' and row[3] for row in launcher_rows):
    raise SystemExit('current launcher identity is absent or changed')
for label, pid, start, alive in launcher_rows:
    if label == 'run-scoped':
        checks.append((label, pid, start, alive))

ps = subprocess.check_output(['ps', '-e', '-o', 'pid=,pgid='], text=True, timeout=5)
live_groups = []
for row in ps.splitlines():
    fields = row.split()
    if len(fields) == 2 and int(fields[1]) in pgids:
        live_groups.append((int(fields[0]), int(fields[1])))

with (evidence / 'pid-readback.tsv').open('w') as output:
    output.write('label\tpid\tstart_ticks\tmatching_process_alive\n')
    for label, pid, start, alive in checks:
        output.write(f'{label}\t{pid}\t{start}\t{int(alive)}\n')
    output.write('scoped_group_live_processes\t' + repr(sorted(live_groups)) + '\n')
clean = not any(alive for _, _, _, alive in checks) and not live_groups and bool(pgids)
(evidence / 'pid-readback.status').write_text(('0' if clean else '1') + '\n')
if not clean:
    raise SystemExit('exact owned process or scoped process-group cleanup readback failed')
PY
then
  readback_status=0
else
  readback_status=1
fi
printf '%s\n' "$readback_status" > "$evidence/pid-readback-launcher.status"

if (( runtime_status == 0 && readback_status == 0 )) && rmdir "$scope"; then
  scope_status=0
  printf 'scope_cleanup_status=0 scope=%s\n' "$scope" > "$evidence/scope-cleanup.tsv"
else
  scope_status=1
  printf 'scope_cleanup_status=1 scope=%s reason=readback-failed-or-scope-not-empty\n' "$scope" \
    > "$evidence/scope-cleanup.tsv"
fi

outer_status=$runner_status
(( runtime_status == 0 && readback_status == 0 && scope_status == 0 )) || outer_status=1
printf '%s\n' "$outer_status" > "$evidence/outer-status.txt"
printf 'runtime_cleanup_status=%s pid_readback_status=%s scope_cleanup_status=%s\n' \
  "$runtime_status" "$readback_status" "$scope_status"
printf 'outer_status=%s\n' "$outer_status"
finalized=1
exit "$outer_status"
