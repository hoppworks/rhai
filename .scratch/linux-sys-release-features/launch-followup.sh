#!/usr/bin/env bash
set -euo pipefail

: "${PROOF_STAGE:?set the exact owned workhorse stage}"
stage=$PROOF_STAGE
evidence="$stage/evidence"
mkdir -p "$evidence"
exec > >(tee -a "$evidence/outer.log") 2>&1
trap 'rc=$?; if [[ ! -e "$evidence/outer-status.txt" ]]; then printf "%s\n" "$rc" > "$evidence/outer-status.txt"; fi' EXIT

deadline_epoch=$(date -u -d '2026-09-30 18:05:14 UTC' +%s)
now_epoch=$(date -u +%s)
remaining=$((deadline_epoch - now_epoch))
(( remaining > 900 )) && remaining=900
printf 'launch_utc=%s\n' "$(date -u +%FT%TZ)"
printf 'launcher_pid=%s launcher_pgid=%s\n' "$$" "$(ps -o pgid= -p $$ | tr -d ' ')"
printf 'absolute_deadline=2026-09-30T18:05:14Z runner_timeout_seconds=%s max_invocation_seconds=900\n' "$remaining"
if (( remaining <= 0 )); then
  printf 'launcher_status=124\n' > "$evidence/outer-status.txt"
  exit 124
fi

python3 - "$evidence/launcher-identities.tsv" "$$" <<'PY'
import pathlib, sys
out, pid = pathlib.Path(sys.argv[1]), int(sys.argv[2])
raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
f = raw[raw.rfind(')') + 2:].split()
cmd = pathlib.Path('/proc', str(pid), 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace').strip()
out.write_text('label\tpid\tppid\tpgid\tstart_ticks\tcmdline\nlauncher\t' +
              f'{pid}\t{f[1]}\t{f[2]}\t{f[19]}\t{cmd}\n')
PY

PROOF_STAGE="$stage" python3 "$stage/runner/tools/run_scoped.py" \
  --timeout "$remaining" -- python3 "$stage/run-followup.py" &
runner_pid=$!
python3 - "$evidence/launcher-identities.tsv" "$runner_pid" <<'PY'
import pathlib, sys, time
out, pid = pathlib.Path(sys.argv[1]), int(sys.argv[2])
for _ in range(100):
    try:
        raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
        f = raw[raw.rfind(')') + 2:].split()
        cmd = pathlib.Path('/proc', str(pid), 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace').strip()
        with out.open('a') as stream:
            stream.write(f'run-scoped\t{pid}\t{f[1]}\t{f[2]}\t{f[19]}\t{cmd}\n')
            stream.flush()
        break
    except FileNotFoundError:
        time.sleep(.01)
else:
    raise SystemExit('could not sample run_scoped PID identity')
PY
if wait "$runner_pid"; then runner_status=0; else runner_status=$?; fi
printf '%s\n' "$runner_status" > "$evidence/run-scoped.status"

python3 - "$evidence" <<'PY'
import pathlib, subprocess, sys
evidence = pathlib.Path(sys.argv[1])
checks, pgids = [], set()
identity_file = evidence / 'process-identities.tsv'
if not identity_file.is_file():
    raise SystemExit('process identity inventory was not exported')
for line in identity_file.read_text(errors='replace').splitlines()[1:]:
    fields = line.split('\t', 5)
    if len(fields) != 6:
        raise SystemExit(f'malformed PID identity row: {line!r}')
    label, pid_text, _ppid, pgid, start, _cmd = fields
    pid = int(pid_text)
    if pgid not in ('<unknown>', '<exited-before-identity-sample>'):
        pgids.add(int(pgid))
    try:
        raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
        current = raw[raw.rfind(')') + 2:].split()
        alive = (start == '<unknown>' or current[19] == start)
    except (FileNotFoundError, ProcessLookupError):
        alive = False
    checks.append((label, pid, start, alive))
launcher_ids = evidence / 'launcher-identities.tsv'
if not launcher_ids.is_file():
    raise SystemExit('outer PID identity inventory was not exported')
for line in launcher_ids.read_text(errors='replace').splitlines()[1:]:
    fields = line.split('\t', 5)
    if len(fields) != 6:
        raise SystemExit(f'malformed outer PID identity row: {line!r}')
    label, pid_text, _ppid, _pgid, start, _cmd = fields
    pid = int(pid_text)
    try:
        raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
        current = raw[raw.rfind(')') + 2:].split()
        alive = (start == '<unknown>' or current[19] == start)
    except (FileNotFoundError, ProcessLookupError):
        alive = False
    checks.append((label, pid, start, alive))
live_groups = set()
ps = subprocess.check_output(['ps', '-e', '-o', 'pid=,pgid='], text=True)
for row in ps.splitlines():
    cols = row.split()
    if len(cols) == 2 and int(cols[1]) in pgids:
        live_groups.add((int(cols[0]), int(cols[1])))
with (evidence / 'pid-readback.tsv').open('w') as out:
    out.write('label\tpid\tstart_ticks\tmatching_process_alive\n')
    for label, pid, start, alive in checks:
        out.write(f'{label}\t{pid}\t{start}\t{int(alive)}\n')
    out.write(f'scoped_group_live_processes\t{sorted(live_groups)!r}\n')
clean = not any(alive for _, _, _, alive in checks) and not live_groups
(evidence / 'pid-readback.status').write_text(('0' if clean else '1') + '\n')
if not clean:
    raise SystemExit('exact owned PID/start-time or scoped process-group cleanup readback failed')
PY

runtime=$(sed -n 's/^PRIVATE_RUNTIME //p' "$evidence/outer.log" | tail -1)
if [[ -z "$runtime" || -e "$runtime" ]]; then
  cleanup_status=1
else
  cleanup_status=0
fi
printf 'runtime=%s\nruntime_cleanup_status=%s\n' "$runtime" "$cleanup_status" > "$evidence/runtime-readback.txt"

final_status=$runner_status
[[ -f "$evidence/pid-readback.status" && "$(cat "$evidence/pid-readback.status")" == 0 ]] || final_status=1
(( cleanup_status == 0 )) || final_status=1
printf '%s\n' "$final_status" > "$evidence/outer-status.txt"
printf 'outer_status=%s\n' "$final_status"
exit "$final_status"
