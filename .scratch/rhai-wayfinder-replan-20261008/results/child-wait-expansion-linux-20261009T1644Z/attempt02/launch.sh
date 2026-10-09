#!/usr/bin/env bash
set -euo pipefail
ATTEMPT="/var/roothome/rhai-evidence/child-wait-expansion-linux-20261009T1644Z/attempt02"
SESSION_SCOPE="/root/.local/share/agent-builds/rhai/child-wait-expansion-red-20261009T1648Z"
RUNNER="/var/home/workhorse/projects/agent-skills/tools/run_scoped.py"
test ! -e "$ATTEMPT"
mkdir "$ATTEMPT"
mv /var/roothome/rhai-evidence/child-wait-expansion-linux-20261009T1644Z-attempt02-payload.pending "$ATTEMPT/payload.sh"
mv /var/roothome/rhai-evidence/child-wait-expansion-linux-20261009T1644Z-attempt02-inputs.pending "$ATTEMPT/inputs.json"
mv /var/roothome/rhai-evidence/child-wait-expansion-linux-20261009T1644Z-attempt02-launch.pending "$ATTEMPT/launch.sh"
chmod 600 "$ATTEMPT/payload.sh" "$ATTEMPT/inputs.json" "$ATTEMPT/launch.sh"
test ! -e "$SESSION_SCOPE"
test "$(sha256sum "$RUNNER" | cut -d' ' -f1)" = "25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e"
{
 date -u '+utc=%Y-%m-%dT%H:%M:%SZ'
 uname -a
 printf 'load='; cat /proc/loadavg
 awk '/MemAvailable/ {print "mem_available_kib=" $2}' /proc/meminfo
 df -B1 /root/.local/share/agent-builds/rhai
 printf 'cargo_processes='; ps -eo comm | awk '$1=="cargo" {n++} END {print n+0}'
 printf 'rustc_processes='; ps -eo comm | awk '$1=="rustc" {n++} END {print n+0}'
} > "$ATTEMPT/preflight.txt"
stat -c '%d %i %u %g %a' /root/.local/share/agent-builds/rhai > "$ATTEMPT/scope-parent.identity"
mkdir -m 700 "$SESSION_SCOPE"
stat -c '%d %i %u %g %a' "$SESSION_SCOPE" > "$ATTEMPT/session-scope.identity"
printf '%s\n' "$SESSION_SCOPE" > "$ATTEMPT/session-scope.path"
printf '%s\n' 'TMPDIR=/root/.local/share/agent-builds/rhai/child-wait-expansion-red-20261009T1648Z' 'runner=/var/home/workhorse/projects/agent-skills/tools/run_scoped.py' 'timeout_seconds=600' 'argv=python3 run_scoped.py --timeout 600 -- bash payload.sh' > "$ATTEMPT/runner-command.txt"
cd "$ATTEMPT"
SECONDS=0
set +e
TMPDIR="$SESSION_SCOPE" /usr/bin/python3 "$RUNNER" --timeout 600 -- bash "$ATTEMPT/payload.sh" > "$ATTEMPT/runner.stdout" 2> "$ATTEMPT/runner.stderr"
runner_status=$?
set -e
printf '%s\n' "$runner_status" > "$ATTEMPT/runner.status"
printf '%s\n' "$SECONDS" > "$ATTEMPT/runner.elapsed-seconds"
stat -c '%d %i %u %g %a' "$SESSION_SCOPE" > "$ATTEMPT/session-scope.identity.after-run"
remaining="$(find "$SESSION_SCOPE" -mindepth 1 -maxdepth 1 -print -quit)"
if [ -z "$remaining" ]; then
 rmdir "$SESSION_SCOPE"
 printf 'retired_exact_empty_scope=true\n' > "$ATTEMPT/cleanup.txt"
 test ! -e "$SESSION_SCOPE"
else
 printf 'retired_exact_empty_scope=false\nremaining=%s\n' "$remaining" > "$ATTEMPT/cleanup.txt"
fi
printf 'runner_status=%s\nelapsed_seconds=%s\n' "$runner_status" "$SECONDS" > "$ATTEMPT/outer-result.txt"
exit "$runner_status"
