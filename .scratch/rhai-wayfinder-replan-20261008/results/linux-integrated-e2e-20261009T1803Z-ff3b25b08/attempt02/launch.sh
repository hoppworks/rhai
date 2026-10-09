#!/usr/bin/env bash
set -Eeuo pipefail
scope=/root/.local/share/agent-builds/rhai/linux-e2e-20261009T1803Z-ff3b25b08-attempt02
evidence="$scope/evidence"
runner=/var/home/workhorse/projects/agent-skills/tools/run_scoped.py
mkdir -m 700 "$evidence"
stat -c 'scope=%n dev=%d inode=%i owner=%U:%G mode=%a' "$scope" > "$evidence/session-scope.identity"
printf '%s\n' "$scope" > "$evidence/session-scope.path"
start=$(date +%s)
set +e
TMPDIR="$scope" PYTHONDONTWRITEBYTECODE=1 python3 "$runner" --timeout 1200 -- /bin/bash "$scope/run.sh" > "$evidence/runner.stdout" 2> "$evidence/runner.stderr"
status=$?
set -e
end=$(date +%s)
printf '%s\n' "$status" > "$evidence/runner.status"
printf '%s\n' "$((end-start))" > "$evidence/runner.elapsed-seconds"
stat -c 'scope=%n dev=%d inode=%i owner=%U:%G mode=%a' "$scope" > "$evidence/session-scope.identity.after-run"
runtime=''
if test -f "$evidence/environment.txt"; then runtime=$(sed -n 's/^runtime=//p' "$evidence/environment.txt" | head -1); fi
if test -n "$runtime" && test ! -e "$runtime"; then
  printf 'private runtime absent after runner exit: %s\n' "$runtime" > "$evidence/runtime-cleanup.txt"
else
  printf 'private runtime cleanup not verified: %s\n' "$runtime" > "$evidence/runtime-cleanup.txt"
fi
exit "$status"
