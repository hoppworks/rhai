#!/usr/bin/env bash
set -euo pipefail
scope=/root/.local/share/agent-builds/rhai/stdin-early-close-adjacent-20261009T2038Z-ff3b25b08
mkdir -p /root/.local/share/agent-builds/rhai
test ! -e "$scope"
install -d -m 700 "$scope"
stat -c 'scope=%n dev=%d inode=%i owner=%U:%G mode=%a' "$scope" > "$scope/scope.identity"
date -Is > "$scope/preflight.txt"
uptime >> "$scope/preflight.txt"
free -h >> "$scope/preflight.txt"
df -h /root >> "$scope/preflight.txt"
cat /proc/pressure/cpu /proc/pressure/memory /proc/pressure/io >> "$scope/preflight.txt"
test -z "$(find "$scope" -mindepth 1 -maxdepth 1 -name 'agent-build-*' -print -quit)"
