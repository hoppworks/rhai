#!/usr/bin/env bash
set -euo pipefail

EVIDENCE=/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery/.scratch/all-tickets/darwin-x31-wait-entry-20261008/attempt-01
SESSION=/Users/hoppworks/.local/share/agent-builds/rhai/x31-darwin-wait-entry-20261008-1218bf21a1ad461dd954609f62527fb92
RUN_SCOPED=/Users/hoppworks/projects/agent-skills/tools/run_scoped.py

if [[ -e "$SESSION" ]]; then
    printf 'refusing pre-existing session path: %s\n' "$SESSION" >&2
    exit 2
fi
mkdir -p "${SESSION%/*}"
mkdir "$SESSION"
printf 'session_scope=%s\n' "$SESSION" > "$EVIDENCE/session-scope.txt"
printf 'df_before:\n' > "$EVIDENCE/resources-before.txt"
df -h "$SESSION" "$EVIDENCE" >> "$EVIDENCE/resources-before.txt"
memory_pressure -Q >> "$EVIDENCE/resources-before.txt"

runner_status=0
TMPDIR="$SESSION" python3 "$RUN_SCOPED" --timeout 600 -- bash "$EVIDENCE/run-x31.sh" > "$EVIDENCE/runner.stdout" 2> "$EVIDENCE/runner.stderr" || runner_status=$?
printf 'runner_status=%s\n' "$runner_status" > "$EVIDENCE/runner.status"

cleanup_status=0
if rmdir "$SESSION"; then
    printf 'session_scope_removed=true\n' > "$EVIDENCE/session-cleanup.txt"
else
    cleanup_status=1
    printf 'session_scope_removed=false\nremaining_entries:\n' > "$EVIDENCE/session-cleanup.txt"
    ls -la "$SESSION" >> "$EVIDENCE/session-cleanup.txt" 2>&1 || true
fi
printf 'cleanup_status=%s\n' "$cleanup_status" >> "$EVIDENCE/session-cleanup.txt"

python3 - "$EVIDENCE" <<'PY'
import hashlib
import pathlib
import sys
root = pathlib.Path(sys.argv[1])
manifest = root / "evidence.sha256"
lines = []
for path in sorted(root.rglob("*")):
    if path.is_file() and path != manifest:
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root)}")
manifest.write_text("\n".join(lines) + "\n")
PY

if [[ "$runner_status" != 0 ]]; then
    exit "$runner_status"
fi
exit "$cleanup_status"
