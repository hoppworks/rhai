#!/usr/bin/env bash
set -euo pipefail
scope=/root/.local/share/agent-builds/rhai/stdin-early-close-diagnostic-20261009T2032Z-ff3b25b08
runner=/var/home/workhorse/projects/agent-skills/tools/run_scoped.py
expected='58 119989208 0 700'
actual=$(stat -c '%d %i %u %a' "$scope")
test "$actual" = "$expected"
test -z "$(find "$scope" -mindepth 1 -maxdepth 1 -name 'agent-build-*' -print -quit)"
test -z "$(pgrep -x cargo || true)"
test -z "$(pgrep -x rustc || true)"
test "$(sha256sum "$runner" | cut -d' ' -f1)" = 25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e
TMPDIR="$scope" PYTHONDONTWRITEBYTECODE=1 python3 "$runner" --timeout 600 -- bash "$scope/run.sh" "$scope" > "$scope/runner.log" 2>&1
