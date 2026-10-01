#!/bin/bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
marker="$here/runtime-path.txt"
log="$here/replay.log"
set +e
REPLAY_RUNTIME_MARKER="$marker" python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout 90 -- python3 "$here/replay.py" 2>&1 | tee "$log"
status=${PIPESTATUS[0]}
set -e
if [[ ! -s "$marker" ]]; then
  printf 'cleanup-readback=UNVERIFIED runtime-marker-missing\n' | tee "$here/cleanup-readback.txt"
  exit 1
fi
runtime_path="$(cat "$marker")"
if [[ -e "$runtime_path" ]]; then
  printf 'cleanup-readback=FAIL path-still-exists %s\n' "$runtime_path" | tee "$here/cleanup-readback.txt"
  exit 1
fi
printf 'cleanup-readback=PASS runtime-absent %s\n' "$runtime_path" | tee "$here/cleanup-readback.txt"
exit "$status"
