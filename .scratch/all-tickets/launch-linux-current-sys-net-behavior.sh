#!/usr/bin/env bash
set -euo pipefail
umask 077

stage=/root/rhai-linux-current-sys-net-behavior-a2d7a8c2-20261002-policy1
scope=/root/.local/share/agent-builds/rhai/linux-current-sys-net-behavior-a2d7a8c2-20261002-policy1
runner="$stage/runner/tools/run_scoped.py"
helper="$stage/run-sys-net-behavior.py"
evidence="$stage/outer-evidence"
runner_pid=
runner_start=
runner_status=125
launcher_interrupted=0
runtime_status=1
readback_status=1
scope_status=1
outer_status=1
launch_epoch=$SECONDS
wait_limit_seconds=600
finalized=0

if [[ ! -d "$stage" || -L "$stage" ]]; then
  printf 'stage identity validation failed: %s\n' "$stage" >&2
  exit 1
fi
if [[ ! -d "$evidence" || -L "$evidence" || -e "$evidence/outer-status.txt" ]]; then
  printf 'outer evidence directory missing, symlinked, or already used\n' >&2
  exit 1
fi

launcher_pid=$$
launcher_raw=$(<"/proc/$launcher_pid/stat")
launcher_fields=${launcher_raw##*) }
read -ra launcher_fields_array <<< "$launcher_fields"
launcher_ppid=${launcher_fields_array[1]}
launcher_pgid=${launcher_fields_array[2]}
launcher_start_ticks=${launcher_fields_array[19]}
printf 'label\tpid\tppid\tpgid\tstart_ticks\tcmdline\nlauncher\t%s\t%s\t%s\t%s\t%s\n' \
  "$launcher_pid" "$launcher_ppid" "$launcher_pgid" "$launcher_start_ticks" "$stage/launch.sh" \
  > "$evidence/launcher-identities.tsv"
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
  printf 'signal=%s requested_after_seconds=%s\n' "$signal_name" "$SECONDS" \
    > "$evidence/interrupt.request"
}
trap on_exit EXIT
trap 'on_signal TERM' TERM
trap 'on_signal INT' INT

printf 'launch_utc=%s\nrunner_timeout_seconds=600\n' "$(date -u +%FT%TZ)"
printf 'stage=%s\nscope=%s\n' "$stage" "$scope"
canonical_stage=$(realpath -e "$stage")
canonical_expected_stage=$(realpath -e /root/rhai-linux-current-sys-net-behavior-a2d7a8c2-20261002-policy1)
if [[ "$canonical_stage" != "$canonical_expected_stage" ]]; then
  printf 'stage canonical identity mismatch: %s != %s\n' "$canonical_stage" "$canonical_expected_stage"
  exit 1
fi
(cd "$stage" && sha256sum --check input-identities.sha256)
if [[ -e "$scope" || -L "$scope" ]]; then
  printf 'prescribed scope already exists; preserving it: %s\n' "$scope"
  exit 1
fi
mkdir -p "$(dirname "$scope")"
mkdir -m 700 "$scope"

PROOF_STAGE="$stage" EXPECTED_PROOF_STAGE="$stage" \
RUSTUP_BIN=/root/.cargo/bin/rustup TMPDIR="$scope" \
INTERRUPT_REQUEST="$evidence/interrupt.request" \
  python3 "$runner" --timeout 600 -- python3 "$helper" &
runner_pid=$!

python3 - "$evidence/launcher-identities.tsv" "$runner_pid" <<'PY'
import pathlib, sys, time
output, pid = pathlib.Path(sys.argv[1]), int(sys.argv[2])
proc = pathlib.Path('/proc') / str(pid)
for _ in range(100):
    try:
        raw = (proc / 'stat').read_text()
        fields = raw[raw.rfind(')') + 2:].split()
        command = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace').strip()
        if not fields[19].isdigit():
            raise ValueError('non-numeric start tick')
        with output.open('a') as stream:
            stream.write(f'run-scoped\t{pid}\t{fields[1]}\t{fields[2]}\t{fields[19]}\t{command}\n')
            stream.flush()
        break
    except FileNotFoundError:
        time.sleep(.01)
    except (PermissionError, IndexError, ValueError, OSError) as exc:
        with output.open('a') as stream:
            stream.write(f'run-scoped\t{pid}\t<identity-unavailable>\t<identity-unavailable>\t<identity-unavailable>\t{exc!r}\n')
            stream.flush()
        break
else:
    with output.open('a') as stream:
        stream.write(f'run-scoped\t{pid}\t<identity-unavailable>\t<identity-unavailable>\t<identity-unavailable>\texited before identity sample\n')
        stream.flush()
PY
while IFS=$'\t' read -r label _pid _ppid _pgid start _command; do
  if [[ "$label" == run-scoped ]]; then runner_start=$start; fi
done < "$evidence/launcher-identities.tsv"
if [[ ! "$runner_start" =~ ^[0-9]+$ ]]; then
  printf 'run-scoped process identity missing or malformed; preserving scope\n'
  exit 1
fi

while :; do
  if (( SECONDS - launch_epoch >= wait_limit_seconds )); then
    printf 'outer wait deadline reached; leaving runner and scope for exact later readback\n'
    break
  fi
  if IFS= read -r runner_raw < "/proc/$runner_pid/stat"; then
    runner_fields=${runner_raw##*) }
    read -ra runner_fields_array <<< "$runner_fields"
    runner_state=${runner_fields_array[0]}
    current_start=${runner_fields_array[19]}
    if [[ -n "$runner_start" && "$current_start" != "$runner_start" ]]; then
      printf 'runner PID identity changed while waiting; fail closed\n'
      break
    fi
    runner_start=$current_start
    if [[ "$runner_state" == Z ]]; then
      set +e
      wait "$runner_pid"
      runner_status=$?
      set -e
      break
    fi
    sleep 0.1
    continue
  fi
  if [[ -e "/proc/$runner_pid/stat" ]]; then
    if (( launcher_interrupted )); then
      sleep 0.1
      continue
    fi
    printf 'runner proc identity is unreadable; failing closed and preserving scope\n'
    break
  fi
  set +e
  wait "$runner_pid"
  runner_status=$?
  set -e
  break
done
printf '%s\n' "$runner_status" > "$evidence/run-scoped.status"
printf 'run_scoped_status=%s\n' "$runner_status"

runtime=$(sed -n 's/^PRIVATE_RUNTIME //p' "$evidence/outer.log" | tail -1)
if [[ -z "$runtime" ]]; then
  printf 'runtime_cleanup_status=1 reason=helper-runtime-path-not-recorded\n' > "$evidence/runtime-cleanup.tsv"
elif [[ "$runtime" != "$scope"/agent-build-* ]]; then
  printf 'runtime_cleanup_status=1 runtime=%s reason=outside-prescribed-scope\n' "$runtime" > "$evidence/runtime-cleanup.tsv"
elif [[ -e "$runtime" ]]; then
  printf 'runtime_cleanup_status=1 runtime=%s reason=runtime-still-exists\n' "$runtime" > "$evidence/runtime-cleanup.tsv"
else
  runtime_status=0
  printf 'runtime_cleanup_status=0 runtime=%s\n' "$runtime" > "$evidence/runtime-cleanup.tsv"
fi

if (( runner_status != 125 )) && [[ -f "$stage/proof-evidence/process-identities.tsv" ]]; then
  set +e
  python3 - "$evidence" "$runner_pid" "$runner_start" "$stage/proof-evidence/process-identities.tsv" <<'PY'
import pathlib, subprocess, sys
outer, runner_pid, runner_start, helper_ids = pathlib.Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3], pathlib.Path(sys.argv[4])
def alive(pid, start):
    try:
        raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
        fields = raw[raw.rfind(')') + 2:].split()
        return fields[19] == start
    except (FileNotFoundError, ProcessLookupError):
        return False
    except (PermissionError, OSError, IndexError, ValueError):
        return None

checks = []
if not runner_start.isdigit():
    raise SystemExit('run-scoped identity missing or malformed')
required = {'helper', 'scoped-supervisor'}
seen, groups = set(), set()
for line in helper_ids.read_text(errors='replace').splitlines()[1:]:
    fields = line.split('\t', 5)
    if len(fields) != 6 or not fields[1].isdigit() or not fields[3].isdigit() or not fields[4].isdigit():
        raise SystemExit(f'malformed helper process identity row: {line!r}')
    label, pid_text, _ppid, pgid_text, start, _cmd = fields
    pid, pgid = int(pid_text), int(pgid_text)
    present = alive(pid, start)
    if present is None:
        raise SystemExit(f'exact PID/start readback is unknown: {label} {pid}')
    checks.append((label, pid, start, present))
    seen.add(label)
    if label in required:
        groups.add(pgid)
if not required.issubset(seen):
    raise SystemExit(f'required helper custody rows missing: {required - seen}')
launcher_rows = []
for line in (outer / 'launcher-identities.tsv').read_text(errors='replace').splitlines()[1:]:
    fields = line.split('\t', 5)
    if len(fields) != 6 or not fields[1].isdigit() or not fields[4].isdigit():
        raise SystemExit(f'malformed launcher custody row: {line!r}')
    label, pid_text, _ppid, _pgid, start, _cmd = fields
    pid = int(pid_text)
    present = alive(pid, start)
    if present is None:
        raise SystemExit(f'exact launcher PID/start readback is unknown: {pid}')
    launcher_rows.append((label, pid, start, present))
    if label == 'run-scoped':
        checks.append((label, pid, start, present))
if not any(label == 'launcher' and present for label, _pid, _start, present in launcher_rows):
    raise SystemExit('current launcher process identity is absent or changed')
ps = subprocess.check_output(['/bin/ps', '-e', '-o', 'pid=,pgid='], text=True, timeout=5)
live_groups = []
for row in ps.splitlines():
    fields = row.split()
    if len(fields) == 2 and int(fields[1]) in groups:
        live_groups.append((int(fields[0]), int(fields[1])))
with (outer / 'pid-readback.tsv').open('w') as output:
    output.write('label\tpid\tstart_ticks\tmatching_process_alive\n')
    for label, pid, start, present in checks:
        output.write(f'{label}\t{pid}\t{start}\t{int(present)}\n')
    output.write('scoped_group_live_processes\t' + repr(sorted(live_groups)) + '\n')
clean = not any(present for _label, _pid, _start, present in checks) and not live_groups and bool(groups)
(outer / 'pid-readback.status').write_text(('0' if clean else '1') + '\n')
if not clean:
    raise SystemExit('exact owned processes or scoped process groups remain')
PY
  readback_status=$?
  set -e
else
  printf '1\n' > "$evidence/pid-readback.status"
fi
printf '%s\n' "$readback_status" > "$evidence/pid-readback-launcher.status"

if (( runtime_status == 0 && readback_status == 0 )) && rmdir "$scope"; then
  scope_status=0
  printf 'scope_cleanup_status=0 scope=%s\n' "$scope" > "$evidence/scope-cleanup.tsv"
else
  printf 'scope_cleanup_status=1 scope=%s reason=readback-failed-or-scope-not-empty\n' "$scope" > "$evidence/scope-cleanup.tsv"
fi
outer_status=$runner_status
(( runtime_status == 0 && readback_status == 0 && scope_status == 0 )) || outer_status=1
(( launcher_interrupted == 0 )) || outer_status=1
printf '%s\n' "$outer_status" > "$evidence/outer-status.txt"
printf 'runtime_cleanup_status=%s pid_readback_status=%s scope_cleanup_status=%s\n' "$runtime_status" "$readback_status" "$scope_status"
printf 'outer_status=%s\n' "$outer_status"
finalized=1
exit "$outer_status"
