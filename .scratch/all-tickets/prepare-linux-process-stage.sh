#!/usr/bin/env bash
set -euo pipefail

# Source staging only. This script does not launch Cargo or native tests.
repo=/Users/hoppworks/projects/rhai-process-unix-run
source_rev=ccaa5ab66771e6dc14b9b193612ef3716e429f78
archive_sha=030bc9630b1348ff1dd540985e3032d2840c4dfb3a462499254758a8d6c8ad91
lock=/Users/hoppworks/projects/rhai-all-tickets/.scratch/core-msrv-compatible-resolution/Cargo.lock
skills=/Users/hoppworks/projects/agent-skills/tools
stage=/root/rhai-linux-process-proof-ccaa5ab-aaf08426
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)

git -C "$repo" cat-file -e "$source_rev^{commit}"
test -z "$(git -C "$repo" status --porcelain=v1 --untracked-files=no)"
actual_archive=$(git -C "$repo" archive --format=tar "$source_rev" | shasum -a 256 | awk '{print $1}')
test "$actual_archive" = "$archive_sha"
test "$(shasum -a 256 "$lock" | awk '{print $1}')" = 8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa

manifest="$(shasum -a 256 "$lock" | awk '{print $1 "  Cargo.lock.baseline"}')"
manifest+=$'\n'"$(shasum -a 256 "$script_dir/linux-process-proof.py" | awk '{print $1 "  linux-process-proof.py"}')"
manifest+=$'\n'"$(shasum -a 256 "$script_dir/remote-launch.sh" | awk '{print $1 "  remote-launch.sh"}')"
manifest+=$'\n'"$(shasum -a 256 "$skills/run_scoped.py" | awk '{print $1 "  runner/tools/run_scoped.py"}')"
manifest+=$'\n'"$(shasum -a 256 "$skills/agentskills/__init__.py" | awk '{print $1 "  runner/tools/agentskills/__init__.py"}')"
manifest+=$'\n'"$(shasum -a 256 "$skills/agentskills/pyguard.py" | awk '{print $1 "  runner/tools/agentskills/pyguard.py"}')"

# Absent-only creation pins an exact fresh target. Partial transfer is left as
# evidence and cannot be mistaken for a complete package on retry.
ssh workhorse "umask 077; test ! -e '$stage' && mkdir -m 700 '$stage' '$stage/evidence' '$stage/runner' '$stage/runner/tools' '$stage/runner/tools/agentskills'"
git -C "$repo" archive --format=tar "$source_rev" | ssh workhorse "umask 077; cat > '$stage/source.tar'"
scp "$lock" workhorse:"$stage/Cargo.lock.baseline"
scp "$script_dir/linux-process-proof.py" "$script_dir/remote-launch.sh" workhorse:"$stage/"
scp "$skills/run_scoped.py" workhorse:"$stage/runner/tools/run_scoped.py"
scp "$skills/agentskills/__init__.py" workhorse:"$stage/runner/tools/agentskills/__init__.py"
scp "$skills/agentskills/pyguard.py" workhorse:"$stage/runner/tools/agentskills/pyguard.py"

{
  printf '%s  %s\n' "$archive_sha" source.tar
  printf '%s\n' "$manifest"
} | ssh workhorse "cat > '$stage/input-identities.sha256'"
ssh workhorse "cd '$stage' && sha256sum -c input-identities.sha256 && chmod 700 remote-launch.sh && sha256sum source.tar Cargo.lock.baseline linux-process-proof.py remote-launch.sh runner/tools/run_scoped.py runner/tools/agentskills/__init__.py runner/tools/agentskills/pyguard.py | tee '$stage/input-readback.sha256'"
