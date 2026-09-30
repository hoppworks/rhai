#!/bin/sh
set -u
repo=/Users/hoppworks/projects/rhai-macos-sys-release-features
evidence="$repo/.scratch/macos-sys-release-evidence"
runner=/Users/hoppworks/projects/agent-skills/tools/run_scoped.py
remaining=1400
set +e
python3 "$runner" --timeout "$remaining" -- python3 "$repo/.scratch/macos-sys-release-proof.py"
status=$?
set -e
mkdir -p "$evidence"
printf '%s\n' "$status" > "$evidence/terminal-wrapper-status.txt"
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$evidence/terminal-wrapper-finished-utc.txt"
exit "$status"
