#!/usr/bin/env bash
set -euo pipefail
scope=/root/.local/share/agent-builds/rhai/stdin-early-close-run-raw-20261009T2041Z-ff3b25b08
runner=/var/home/workhorse/projects/agent-skills/tools/run_scoped.py
expected=$(sed -n 's/.*dev=\([0-9][0-9]*\) inode=\([0-9][0-9]*\) owner=root:root mode=700/\1 \2 0 700/p' "$scope/scope.identity")
test "$(stat -c '%d %i %u %a' "$scope")" = "$expected"
test -z "$(find "$scope" -mindepth 1 -maxdepth 1 -name 'agent-build-*' -print -quit)"
test "$(sha256sum "$runner" | cut -d' ' -f1)" = 25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e
TMPDIR="$scope" PYTHONDONTWRITEBYTECODE=1 python3 "$runner" --timeout 600 -- bash "$scope/run.sh" "$scope" > "$scope/runner.log" 2>&1
