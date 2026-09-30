#!/usr/bin/env bash
set -euo pipefail
repo=/Users/hoppworks/projects/rhai-combined-package-proof
out="$repo/.scratch/combined-package-proof/f32-followup"
source_revision=$(git -C "$repo" rev-parse HEAD)
dirty=$(git -C "$repo" status --porcelain=v1 -- . ':(exclude).scratch/combined-package-proof/f32-followup')
if [[ -n "$dirty" ]]; then printf 'Source worktree is dirty outside owned f32 evidence:\n%s\n' "$dirty" >&2; exit 1; fi
deadline_epoch=$(date -u -j -f '%Y-%m-%dT%H:%M:%SZ' '2026-09-30T19:18:29Z' +%s)
now_epoch=$(date -u +%s)
remaining=$((deadline_epoch-now_epoch))
(( remaining > 600 )) && remaining=600
mkdir -p "$out"
printf '%s\n' "$source_revision" > "$out/source-gate-head.txt"
exec > >(tee -a "$out/outer.log") 2>&1
printf 'launcher_start_utc=%s\nlauncher_pid=%s\nlauncher_pgid=%s\n' "$(date -u +%FT%TZ)" "$$" "$(ps -o pgid= -p $$ | tr -d ' ')"
printf 'absolute_deadline_utc=2026-09-30T19:18:29Z remaining_timeout_seconds=%s\n' "$remaining"
python3 - "$out/launcher-identities.tsv" "$$" <<'PY'
import pathlib, subprocess, sys
out, wanted = pathlib.Path(sys.argv[1]), int(sys.argv[2])
table = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,pgid=,lstart=,command='], text=True)
rows = {}
for line in table.splitlines():
    fields = line.strip().split(None, 8)
    if len(fields) >= 8:
        rows[int(fields[0])] = fields
fields = rows.get(wanted)
if fields is None:
    raise SystemExit('launcher missing from its original ps snapshot')
out.write_text('label\tidentity\nlauncher\t'+' '.join(fields)+'\n')
PY
if (( remaining <= 0 )); then printf 'No execution time remains before absolute cutoff.\n'; exit 124; fi
scoped_status=0
python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout "$remaining" -- python3 "$repo/.scratch/combined-package-proof/run-f32-followup.py" &
scoped_pid=$!
printf 'run_scoped_pid=%s\n' "$scoped_pid" | tee -a "$out/outer.log"
python3 - "$out/launcher-identities.tsv" "$scoped_pid" <<'PY'
import pathlib, subprocess, sys
out, wanted = pathlib.Path(sys.argv[1]), int(sys.argv[2])
table = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,pgid=,lstart=,command='], text=True)
for line in table.splitlines():
    fields = line.strip().split(None, 8)
    if len(fields) >= 8 and int(fields[0]) == wanted:
        with out.open('a') as stream:
            stream.write('run_scoped\t'+' '.join(fields)+'\n')
        break
else:
    raise SystemExit('run_scoped process missing from original identity snapshot')
PY
wait "$scoped_pid" || scoped_status=$?
printf '%s\n' "$scoped_status" > "$out/run-scoped.status"
printf 'launcher_finish_utc=%s scoped_status=%s\n' "$(date -u +%FT%TZ)" "$scoped_status"
(( scoped_status == 0 ))
