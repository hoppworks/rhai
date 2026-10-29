#!/bin/bash
set -u
out=/Users/hoppworks/.codex/worktrees/darwin-capture-cleanup/rhai/.scratch/all-tickets/release-matrix-20261028/macos-net-noobject-attempt01
prior=/Users/hoppworks/.codex/worktrees/darwin-capture-cleanup/rhai/.scratch/all-tickets/release-matrix-20261028/macos-net-alone-attempt02
scope=/Users/hoppworks/.local/share/agent-builds/rhai/macos-net-noobject-20261029-cc2976f1
runner=/Users/hoppworks/projects/agent-skills/tools/run_scoped.py
test ! -e "$scope" && test ! -L "$scope" || exit 81
test ! -e "$out/outer.status" && test ! -e "$out/result.json" || exit 82
printf '%s  %s\n' 25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e "$runner" | shasum -a 256 -c - || exit 83
printf '%s  %s\n' b829308ab356d7aaaf7bf8d3acc9f65aab8fb316192d9b1b69e3365d78c834fd "$prior/source-manifest.json" | shasum -a 256 -c - || exit 84
printf '%s  %s\n' 6ff82b95cbbf65ba919161932a63d74f668f8e6e6d88682418797eca93565384 "$prior/rhai-source.zip" | shasum -a 256 -c - || exit 85
printf '%s  %s\n' 12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802 "$prior/Cargo.lock" | shasum -a 256 -c - || exit 86
python3 -B -c 'import os; x=os.statvfs("/Users/hoppworks"); assert x.f_bavail*x.f_frsize >= 4*1024**3' || exit 87
mkdir "$scope" || exit 88
TMPDIR="$scope" PYTHONDONTWRITEBYTECODE=1 python3 -B "$runner" --timeout 600 -- python3 -B "$out/run.py" "$out" "$prior" > "$out/outer.log" 2>&1
status=$?
printf '%s\n' "$status" > "$out/outer.status"
if ! rmdir "$scope"; then
    printf '%s\n' 'owned scope not empty; inspect exact path' >> "$out/outer.log"
    exit 89
fi
exit "$status"
