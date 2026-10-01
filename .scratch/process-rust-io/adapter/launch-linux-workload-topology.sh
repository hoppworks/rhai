#!/usr/bin/env bash
set -euo pipefail
# The caller starts this script through nohup + setsid. Keep HUP ignored if
# the SSH control connection disappears after the launch acknowledgement.
trap '' HUP

: "${PROOF_STAGE:?set the exact owned Linux stage}"
stage=$PROOF_STAGE
source_root="$stage/source"
evidence="$stage/evidence"
mkdir -p "$evidence"
exec >"$evidence/outer.log" 2>&1
trap 'rc=$?; if [[ ! -e "$evidence/outer-status.txt" ]]; then printf "%s\n" "$rc" > "$evidence/outer-status.txt"; fi' EXIT

deadline_epoch=$(/usr/bin/date -u -d '2026-10-01 07:50:00 UTC' +%s)
now_epoch=$(/usr/bin/date -u +%s)
remaining=$((deadline_epoch - now_epoch))
(( remaining > 600 )) && remaining=600
printf 'launch_utc=%s\nlauncher_pid=%s launcher_pgid=%s\nremaining_seconds=%s\n' \
  "$(/usr/bin/date -u +%FT%TZ)" "$$" "$(/usr/bin/ps -o pgid= -p $$ | tr -d ' ')" "$remaining"
(( remaining > 0 )) || exit 124

python3 - "$evidence/launcher-identities.tsv" "$$" <<'PY'
import pathlib, sys
out, pid = pathlib.Path(sys.argv[1]), int(sys.argv[2])
raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
fields = raw[raw.rfind(')') + 2:].split()
cmd = pathlib.Path('/proc', str(pid), 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace').strip()
out.write_text('label\tpid\tppid\tpgid\tstart_ticks\tcmdline\n' +
              f'launcher\t{pid}\t{fields[1]}\t{fields[2]}\t{fields[19]}\t{cmd}\n')
PY

PROOF_STAGE="$stage" /usr/bin/python3 "$stage/runner/tools/run_scoped.py" \
  --timeout "$remaining" -- /usr/bin/python3 \
  "$source_root/.scratch/process-rust-io/adapter/run_native_acceptance.py" \
  --source-root "$source_root" --topology-only &
runner_pid=$!
python3 - "$evidence/launcher-identities.tsv" "$runner_pid" <<'PY'
import pathlib, sys, time
out, pid = pathlib.Path(sys.argv[1]), int(sys.argv[2])
for _ in range(100):
    try:
        raw = pathlib.Path('/proc', str(pid), 'stat').read_text()
        fields = raw[raw.rfind(')') + 2:].split()
        cmd = pathlib.Path('/proc', str(pid), 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace').strip()
        with out.open('a') as stream:
            stream.write(f'run-scoped\t{pid}\t{fields[1]}\t{fields[2]}\t{fields[19]}\t{cmd}\n')
            stream.flush()
        break
    except FileNotFoundError:
        time.sleep(.01)
else:
    raise SystemExit('could not capture run_scoped PID start identity')
PY

if wait "$runner_pid"; then runner_status=0; else runner_status=$?; fi
printf '%s\n' "$runner_status" > "$evidence/run-scoped.status"
python3 - "$evidence/launcher-identities.tsv" "$evidence/pid-readback.txt" <<'PY'
import pathlib, sys
identities, output = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
rows = identities.read_text().splitlines()[1:]
result = []
for row in rows:
    label, pid, _ppid, _pgid, start, _cmd = row.split('\t', 5)
    try:
        raw = pathlib.Path('/proc', pid, 'stat').read_text()
        current = raw[raw.rfind(')') + 2:].split()[19]
        alive = current == start
    except FileNotFoundError:
        alive = False
    result.append((label, pid, start, alive))
output.write_text('\n'.join(f'{a}\t{b}\t{c}\t{int(d)}' for a,b,c,d in result) + '\n')
if any(alive for label, _, _, alive in result if label == 'run-scoped'):
    raise SystemExit('run_scoped identity remains live after wait')
PY

python3 - "$source_root" "$evidence/custody-readback.txt" <<'PY'
import json, pathlib, subprocess, sys
root, output = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
export = root / '.scratch/process-rust-io/evidence/native-linux-workload-topology-attempt3-20261001-0729UTC'
custody_path = export / 'custody.json'
if not custody_path.is_file():
    output.write_text('custody_missing\n')
    raise SystemExit('driver custody metadata is missing')
custody = json.loads(custody_path.read_text())
runtime = pathlib.Path(custody['runtime_path'])
supervisor = custody['supervisor']
rows = subprocess.check_output(['/usr/bin/ps', '-e', '-o', 'pid=,pgid='], text=True, timeout=2)
group = [(int(pid), int(pgid)) for line in rows.splitlines()
         if len((parts := line.split())) == 2
         for pid, pgid in [parts] if int(pgid) == int(supervisor['pgid'])]
result = {'runtime_path': str(runtime), 'runtime_absent': not runtime.exists(),
          'supervisor_pgid': supervisor['pgid'], 'live_group_processes': group}
output.write_text(json.dumps(result, sort_keys=True) + '\n')
if runtime.exists() or group:
    raise SystemExit('runtime or scoped supervisor process group remains live')
PY

final_status=$runner_status
[[ -e "$evidence/custody-readback.txt" ]] || final_status=1
[[ "$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(int(d["runtime_absent"] and not d["live_group_processes"]))' "$evidence/custody-readback.txt")" == 1 ]] || final_status=1
printf '%s\n' "$final_status" > "$evidence/outer-status.txt"
exit "$final_status"
