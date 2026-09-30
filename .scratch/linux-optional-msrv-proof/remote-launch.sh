#!/usr/bin/env bash
set -euo pipefail

: "${PROOF_STAGE:?set exact owned stage path}"
stage=$PROOF_STAGE
evidence="$stage/evidence"
mkdir -p "$evidence"
exec > >(tee -a "$evidence/outer.log") 2>&1
trap 'rc=$?; if [[ ! -e "$evidence/outer-status.txt" ]]; then printf "%s\n" "$rc" > "$evidence/outer-status.txt"; fi' EXIT

deadline_epoch=$(date -u -d '2026-09-30 17:18:30 UTC' +%s)
now_epoch=$(date -u +%s)
remaining=$((deadline_epoch - now_epoch))
printf 'launch_utc=%s\n' "$(date -u +%FT%TZ)"
printf 'launcher_pid=%s launcher_pgid=%s\n' "$$" "$(ps -o pgid= -p $$ | tr -d ' ')"
printf 'execution_deadline=2026-09-30T17:19:00Z runner_timeout_seconds=%s\n' "$remaining"
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
  --timeout "$remaining" -- python3 "$stage/run-proof.py" &
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
printf 'run_scoped_status=%s\n' "$runner_status"

# Independently compare every sampled exact PID/start-time identity and the
# scoped process group after run_scoped has completed its owned-group cleanup.
if python3 - "$evidence" "$runner_pid" <<'PY'
import pathlib, subprocess, sys
evidence, runner_pid = pathlib.Path(sys.argv[1]), int(sys.argv[2])
identities = evidence / 'process-identities.tsv'
checks = []
pgids = set()
if identities.exists():
    for line in identities.read_text(errors='replace').splitlines()[1:]:
        fields = line.split('\t', 5)
        if len(fields) != 6:
            continue
        label, pid_text, ppid, pgid, start, cmd = fields
        pid = int(pid_text)
        if label == 'scoped-supervisor':
            pgids.add(int(pgid))
        try:
            raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
            current = raw[raw.rfind(')') + 2:].split()
            same = current[19] == start
        except (FileNotFoundError, ProcessLookupError):
            same = False
        checks.append((pid, start, same))
runner_ids = evidence / 'launcher-identities.tsv'
if runner_ids.exists():
    for line in runner_ids.read_text(errors='replace').splitlines()[1:]:
        fields = line.split('\t', 5)
        if len(fields) == 6 and fields[0] == 'run-scoped':
            pid, start = int(fields[1]), fields[4]
            try:
                current = pathlib.Path('/proc', str(pid), 'stat').read_text()
                current = current[current.rfind(')') + 2:].split()
                same = current[19] == start
            except (FileNotFoundError, ProcessLookupError):
                same = False
            checks.append((pid, start, same))
live_groups = set()
ps = subprocess.check_output(['ps', '-e', '-o', 'pid=,pgid='], text=True)
for row in ps.splitlines():
    cols = row.split()
    if len(cols) == 2 and int(cols[1]) in pgids:
        live_groups.add((int(cols[0]), int(cols[1])))
with (evidence / 'pid-readback.tsv').open('w') as out:
    out.write('pid\tstart_ticks\tmatching_process_alive\n')
    for pid, start, alive in checks:
        out.write(f'{pid}\t{start}\t{int(alive)}\n')
    out.write('scoped_group_live_processes\t' + repr(sorted(live_groups)) + '\n')
    out.write(f'run_scoped_pid_absent\t{int(not any(pid == runner_pid and alive for pid, _, alive in checks))}\n')
clean = not any(alive for _, _, alive in checks) and not live_groups
(evidence / 'pid-readback.status').write_text(('0' if clean else '1') + '\n')
if not clean:
    raise SystemExit('exact owned PID or scoped process-group cleanup readback failed')
PY
then readback_status=0; else readback_status=1; fi
printf '%s\n' "$readback_status" > "$evidence/pid-readback-launcher.status"

runtime=$(sed -n 's/^PRIVATE_RUNTIME //p' "$evidence/outer.log" | tail -1)
if [[ -z "$runtime" || -e "$runtime" ]]; then
  printf 'runtime_cleanup_status=1 runtime=%s\n' "$runtime"
  cleanup_status=1
else
  printf 'runtime_cleanup_status=0 runtime=%s\n' "$runtime"
  cleanup_status=0
fi

final_status=$runner_status
(( readback_status == 0 && cleanup_status == 0 )) || final_status=1
printf '%s\n' "$final_status" > "$evidence/outer-status.txt"
printf 'outer_status=%s\n' "$final_status"
exit "$final_status"
