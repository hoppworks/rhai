#!/usr/bin/env bash
set -euo pipefail
ATTEMPT="$(cd "$(dirname "$0")" && pwd)"
SCOPE='/Users/hoppworks/.local/share/agent-builds/rhai/x24-darwin-sync-20261009T1800Z-01'
test ! -e "$SCOPE"
mkdir -m 700 "$SCOPE"
{
 date -u +%FT%TZ
 sw_vers
 uname -a
 memory_pressure
 sysctl vm.loadavg
 df -Pk /Users/hoppworks/.local/share/agent-builds
 ps -Ao pid,ppid,rss,%cpu,etime,command | rg 'run_scoped.py|cargo|rustc' | head -30 || true
 shasum -a 256 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py
 /usr/bin/python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py --help
} > "$ATTEMPT/macos/preflight.txt" 2>&1
stat -f 'device=%d inode=%i uid=%u gid=%g mode=%Lp' "$SCOPE" > "$ATTEMPT/macos/session-scope.identity"
start=$(date +%s)
set +e
TMPDIR="$SCOPE" PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout 600 -- bash "$ATTEMPT/payload.sh" "$ATTEMPT" > "$ATTEMPT/macos/runner.log" 2>&1
status=$?
set -e
end=$(date +%s)
printf '%s\n' "$status" > "$ATTEMPT/macos/runner.status"
printf '%s\n' "$((end-start))" > "$ATTEMPT/macos/runner.elapsed-seconds"
stat -f 'device=%d inode=%i uid=%u gid=%g mode=%Lp' "$SCOPE" > "$ATTEMPT/macos/session-scope.identity.after-run"
test -z "$(find "$SCOPE" -mindepth 1 -maxdepth 1 -print -quit)"
rmdir "$SCOPE"
test ! -e "$SCOPE"
test "$status" -eq 0
