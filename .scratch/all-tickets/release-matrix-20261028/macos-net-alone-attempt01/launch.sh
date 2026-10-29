#!/bin/bash
set -u
stage=/Users/hoppworks/.local/share/agent-builds/rhai/macos-net-alone-4c76d812
scope=/Users/hoppworks/.local/share/agent-builds/rhai/macos-net-alone-4c76d812-scope
runner=/Users/hoppworks/projects/agent-skills/tools/run_scoped.py
test -d "$stage" && test ! -L "$stage" || exit 80
test ! -e "$scope" && test ! -L "$scope" || exit 81
test ! -e "$stage/result.json" && test ! -e "$stage/outer.status" || exit 82
printf '%s  %s\n' 25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e "$runner" | shasum -a 256 -c - || exit 83
printf '%s  %s\n' 9d907b35ac094f1f184941f94b94c7d5799d1c953669df71890649ba75ed5d77 "$stage/run.py" | shasum -a 256 -c - || exit 84
printf '%s  %s\n' 254d021566408f44b2b645551e2598f7cf9db5fee63c5e34bcc7ea20012ec9ba "$stage/source-manifest.json" | shasum -a 256 -c - || exit 85
printf '%s  %s\n' 0005b38a387b419802335e141cb259de86f1ec9424e6e4cf2b8bc3beaf30bdd7 "$stage/rhai-source.zip" | shasum -a 256 -c - || exit 86
printf '%s  %s\n' 12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802 "$stage/Cargo.lock" | shasum -a 256 -c - || exit 87
python3 -B -c 'import os; x=os.statvfs("/Users/hoppworks"); assert x.f_bavail*x.f_frsize >= 4*1024**3' || exit 88
mkdir "$scope" || exit 89
TMPDIR="$scope" PYTHONDONTWRITEBYTECODE=1 python3 -B "$runner" --timeout 600 -- python3 -B "$stage/run.py" "$stage" > "$stage/outer.log" 2>&1
status=$?
printf '%s\n' "$status" > "$stage/outer.status"
if ! rmdir "$scope"; then
    printf '%s\n' 'owned session scope not empty; inspect exact path' >> "$stage/outer.log"
    exit 90
fi
exit "$status"
