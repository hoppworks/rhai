#!/usr/bin/env bash
set -u
stage=/var/roothome/.local/share/agent-builds/rhai/linux-netconnect-overlay-d95b638e
scope=/var/roothome/.local/share/agent-builds/rhai/linux-netconnect-overlay-d95b638e-scope
runner=/var/srv/workspaces/agent-skills/tools/run_scoped.py
test -d "$stage" && test ! -L "$stage" || exit 80
test ! -e "$scope" && test ! -L "$scope" || exit 81
test ! -e "$stage/result.json" && test ! -e "$stage/outer.status" || exit 82
printf '%s  %s\n' 25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e "$runner" | sha256sum -c - || exit 83
printf '%s  %s\n' c8bb3dbcc16a33f8a3b9b46abe311e7aeca990049632835df46df02863e61db0 "$stage/run.py" | sha256sum -c - || exit 84
printf '%s  %s\n' b829308ab356d7aaaf7bf8d3acc9f65aab8fb316192d9b1b69e3365d78c834fd "$stage/source-manifest.json" | sha256sum -c - || exit 85
printf '%s  %s\n' 6ff82b95cbbf65ba919161932a63d74f668f8e6e6d88682418797eca93565384 "$stage/rhai-source.zip" | sha256sum -c - || exit 86
printf '%s  %s\n' 12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802 "$stage/Cargo.lock" | sha256sum -c - || exit 87
python3 -B -c 'import os; x=os.statvfs("/var"); assert x.f_bavail*x.f_frsize >= 4*1024**3' || exit 88
mkdir "$scope" || exit 89
TMPDIR="$scope" PYTHONDONTWRITEBYTECODE=1 python3 -B "$runner" --timeout 600 -- python3 -B "$stage/run.py" "$stage" > "$stage/outer.log" 2>&1
status=$?
printf '%s\n' "$status" > "$stage/outer.status"
if ! rmdir "$scope"; then
    printf '%s\n' 'owned session scope not empty; inspect exact path' >> "$stage/outer.log"
    exit 90
fi
exit "$status"
