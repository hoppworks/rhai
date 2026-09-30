#!/usr/bin/env bash
set -euo pipefail
repo=/Users/hoppworks/projects/rhai-combined-package-proof
out="$repo/.scratch/combined-package-proof/followup"
source_revision=$(git -C "$repo" rev-parse HEAD)
dirty=$(git -C "$repo" status --porcelain=v1 -- . ':(exclude).scratch/combined-package-proof/followup')
if [[ -n "$dirty" ]]; then printf 'Source worktree is dirty outside owned follow-up evidence:\n%s\n' "$dirty" >&2; exit 1; fi
deadline_epoch=$(date -u -j -f '%Y-%m-%dT%H:%M:%SZ' '2026-09-30T18:19:18Z' +%s)
now_epoch=$(date -u +%s)
remaining=$((deadline_epoch-now_epoch))
(( remaining > 600 )) && remaining=600
mkdir -p "$out"
printf '%s\n' "$source_revision" > "$out/source-gate-head.txt"
exec > >(tee -a "$out/outer.log") 2>&1
printf 'launcher_start_utc=%s\nlauncher_pid=%s\nlauncher_pgid=%s\n' "$(date -u +%FT%TZ)" "$$" "$(ps -o pgid= -p $$ | tr -d ' ')"
printf 'absolute_deadline_utc=2026-09-30T18:19:18Z remaining_timeout_seconds=%s\n' "$remaining"
python3 - "$out/launcher-identities.tsv" "$$" <<'PY'
import pathlib, subprocess, sys
out, pid = pathlib.Path(sys.argv[1]), sys.argv[2]
row = subprocess.check_output(['ps', '-p', pid, '-o', 'pid=,ppid=,pgid=,lstart=,command='], text=True).strip()
out.write_text('label\tidentity\nlauncher\t'+row+'\n')
PY
if (( remaining <= 0 )); then printf 'No execution time remains before absolute cutoff.\n'; exit 124; fi
scoped_status=0
python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout "$remaining" -- python3 "$repo/.scratch/combined-package-proof/run-followup.py" &
scoped_pid=$!
printf 'run_scoped_pid=%s\n' "$scoped_pid" | tee -a "$out/outer.log"
scoped_identity=$(ps -p "$scoped_pid" -o pid=,ppid=,pgid=,lstart=,command=)
printf 'run_scoped	%s\n' "$scoped_identity" >> "$out/launcher-identities.tsv"
wait "$scoped_pid" || scoped_status=$?
printf '%s\n' "$scoped_status" > "$out/run-scoped.status"
printf 'launcher_finish_utc=%s scoped_status=%s\n' "$(date -u +%FT%TZ)" "$scoped_status"
(( scoped_status == 0 ))
