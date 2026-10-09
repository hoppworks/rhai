#!/usr/bin/env bash
set -euo pipefail
SESSION='/var/home/workhorse/.local/share/agent-builds/rhai/x24-only-i32-20261009T1740Z-01'
EVIDENCE='/var/roothome/rhai-evidence/x24-only-i32-20261009T1740Z-01'
RUNNER='/var/home/workhorse/projects/agent-skills/tools/run_scoped.py'
test ! -e "$SESSION"
test -d "$EVIDENCE"
test ! -e "$SESSION"
mkdir -m 700 "$SESSION"
mkdir -m 700 -p "$EVIDENCE/workhorse"
{
  date -u +%FT%TZ
  uname -a
  free -b
  df -PB1 /var/home
  uptime
  pgrep -a cargo || true
  pgrep -a rustc || true
  sha256sum "$RUNNER"
  /usr/bin/python3 "$RUNNER" --help
} > "$EVIDENCE/workhorse/preflight.txt" 2>&1
stat -c 'device=%d inode=%i uid=%u gid=%g mode=%a' "$SESSION" > "$EVIDENCE/workhorse/session-scope.identity"
sha256sum "$EVIDENCE/source.tar.gz" "$EVIDENCE/Cargo.lock.accepted" "$EVIDENCE/inputs.json" "$EVIDENCE/payload.sh" > "$EVIDENCE/workhorse/staged-inputs.sha256"
start=$(date +%s)
set +e
TMPDIR="$SESSION" PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 "$RUNNER" --timeout 600 -- bash "$EVIDENCE/payload.sh" "$EVIDENCE" > "$EVIDENCE/workhorse/runner.log" 2>&1
status=$?
set -e
end=$(date +%s)
printf '%s\n' "$status" > "$EVIDENCE/workhorse/runner.status"
printf '%s\n' "$((end-start))" > "$EVIDENCE/workhorse/runner.elapsed-seconds"
stat -c 'device=%d inode=%i uid=%u gid=%g mode=%a' "$SESSION" > "$EVIDENCE/workhorse/session-scope.identity.after-run"
test -z "$(find "$SESSION" -mindepth 1 -maxdepth 1 -print -quit)"
rmdir "$SESSION"
test ! -e "$SESSION"
test "$status" -eq 0
