#!/usr/bin/env bash
set -euo pipefail
scope=/root/.local/share/agent-builds/rhai/stdin-early-close-20261009T2021Z-ff3b25b08
runner=/var/home/workhorse/projects/agent-skills/tools/run_scoped.py
expected='58 119928609 0 700'
actual=$(stat -c '%d %i %u %a' "$scope")
test "$actual" = "$expected"
test -z "$(find "$scope" -mindepth 1 -maxdepth 1 -name 'agent-build-*' -print -quit)"
test -z "$(pgrep -x cargo || true)"
test -z "$(pgrep -x rustc || true)"
test "$(sha256sum "$runner" | cut -d' ' -f1)" = 25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e
date -Is > "$scope/preflight-current.txt"
uptime >> "$scope/preflight-current.txt"
free -h >> "$scope/preflight-current.txt"
df -h /root >> "$scope/preflight-current.txt"
cat /proc/pressure/cpu /proc/pressure/memory /proc/pressure/io >> "$scope/preflight-current.txt"
cat "$scope/scope.identity" >> "$scope/preflight-current.txt"
cd "$scope"
set +e
TMPDIR="$scope" PYTHONDONTWRITEBYTECODE=1 python3 "$runner" --timeout 600 -- bash "$scope/run.sh" "$scope" > "$scope/runner.log" 2>&1
status=$?
set -e
printf '%s\n' "$status" > "$scope/runner.status"
exit "$status"
