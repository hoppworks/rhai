#!/usr/bin/env bash
set -euo pipefail

REPO=/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery
EVIDENCE="$REPO/.scratch/all-tickets/darwin-x31-wait-entry-20261008/attempt-02"
SCOPED_RUNNER=/Users/hoppworks/projects/agent-skills/tools/run_scoped.py
SESSION_ID="x31-darwin-wait-entry-20261008-attempt02-$(uuidgen | tr -d '-')"
SESSION_SCOPE="$HOME/.local/share/agent-builds/rhai/$SESSION_ID"

mkdir -p "$(dirname "$SESSION_SCOPE")"
if [[ -e "$SESSION_SCOPE" || -L "$SESSION_SCOPE" ]]; then
    echo "refusing existing session scope: $SESSION_SCOPE" >&2
    exit 2
fi
mkdir "$SESSION_SCOPE"
printf 'session_scope=%s\n' "$SESSION_SCOPE" > "$EVIDENCE/session-scope.txt"
printf 'session_id=%s\n' "$SESSION_ID" >> "$EVIDENCE/session-scope.txt"

set +e
TMPDIR="$SESSION_SCOPE" python3 "$SCOPED_RUNNER" --timeout 600 -- bash "$EVIDENCE/run-x31.sh" \
    > "$EVIDENCE/run-scoped.stdout" 2> "$EVIDENCE/run-scoped.stderr"
runner_status=$?
set -e
printf 'runner_status=%s\n' "$runner_status" > "$EVIDENCE/runner.status"

if rmdir "$SESSION_SCOPE" 2> "$EVIDENCE/session-cleanup.stderr"; then
    echo 'session_scope_removed=true' > "$EVIDENCE/session-cleanup.txt"
else
    printf 'session_scope_removed=false\npath=%s\n' "$SESSION_SCOPE" > "$EVIDENCE/session-cleanup.txt"
fi

find "$EVIDENCE" -type f ! -name evidence.sha256 -print | LC_ALL=C sort | while IFS= read -r file; do
    shasum -a 256 "$file"
done > "$EVIDENCE/evidence.sha256"
exit "$runner_status"
