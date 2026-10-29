#!/usr/bin/env bash
set -u
stage=/var/roothome/.local/share/agent-builds/rhai/windows-rhai-native-06d6577d5a724d6cb791686d5534d254
scope=/var/roothome/.local/share/agent-builds/rhai/windows-streams-iso-06d6577d-scope
runner=/var/srv/workspaces/agent-skills/tools/run_scoped.py
test -d "$stage" && test ! -L "$stage" || exit 80
test ! -e "$scope" && test ! -L "$scope" || exit 81
test ! -e "$stage/rhai-native.iso" && test ! -e "$stage/assemble.status" || exit 82
printf '%s  %s\n' 25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e "$runner" | sha256sum -c - || exit 83
python3 -B -c 'import os; x=os.statvfs("/var"); assert x.f_bavail*x.f_frsize >= 4*1024**3' || exit 84
mkdir "$scope" || exit 85
TMPDIR="$scope" PYTHONDONTWRITEBYTECODE=1 python3 -B "$runner" --timeout 60 -- python3 -B "$stage/assemble-native-media.py" "$stage" > "$stage/assemble.log" 2>&1
status=$?
printf '%s\n' "$status" > "$stage/assemble.status"
if ! rmdir "$scope"; then
    printf '%s\n' 'owned assembly scope not empty; inspect exact path' >> "$stage/assemble.log"
    exit 86
fi
exit "$status"
