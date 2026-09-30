#!/bin/sh
set -u
repo=/Users/hoppworks/projects/rhai-macos-sys-release-features
evidence="$repo/.scratch/macos-sys-release-evidence"
runner=/Users/hoppworks/projects/agent-skills/tools/run_scoped.py
deadline=$(date -u -j -f '%Y-%m-%d %H:%M:%S' '2026-09-30 17:38:30' '+%s')
now=$(date '+%s')
remaining=$((deadline - now))
if [ "$remaining" -le 0 ]; then
    printf '%s\n' 'launch refused: absolute execution stop has passed' >&2
    exit 88
fi
set +e
python3 "$runner" --timeout "$remaining" -- python3 "$repo/.scratch/macos-sys-release-proof.py"
status=$?
set -e
mkdir -p "$evidence"
printf '%s\n' "$status" > "$evidence/terminal-wrapper-status.txt"
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$evidence/terminal-wrapper-finished-utc.txt"
exit "$status"
