#!/usr/bin/env bash
set -euo pipefail

# Explicit future staging action. Review destination before running.
repo=/Users/hoppworks/projects/rhai-process-unix-run
source_rev=ccaa5ab66771e6dc14b9b193612ef3716e429f78
archive_sha=030bc9630b1348ff1dd540985e3032d2840c4dfb3a462499254758a8d6c8ad91
lock=/Users/hoppworks/projects/rhai-all-tickets/.scratch/core-msrv-compatible-resolution/Cargo.lock
skills=/Users/hoppworks/projects/agent-skills/tools
stage=/root/rhai-linux-process-proof-ccaa5ab

git -C "$repo" cat-file -e "$source_rev^{commit}"
test "$(git -C "$repo" archive --format=tar "$source_rev" | shasum -a 256 | cut -d' ' -f1)" = "$archive_sha"
test "$(shasum -a 256 "$lock" | cut -d' ' -f1)" = 8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa
ssh workhorse "umask 077; test ! -e '$stage' && mkdir -p '$stage/evidence' '$stage/runner/tools/agentskills'"
git -C "$repo" archive --format=tar "$source_rev" | ssh workhorse "cat > '$stage/source.tar'"
scp "$lock" workhorse:"$stage/Cargo.lock.baseline"
scp "$(dirname "$0")/linux-process-proof.py" "$(dirname "$0")/remote-launch.sh" workhorse:"$stage/"
scp "$skills/run_scoped.py" workhorse:"$stage/runner/tools/"
scp "$skills/agentskills/__init__.py" "$skills/agentskills/pyguard.py" workhorse:"$stage/runner/tools/agentskills/"
ssh workhorse "sha256sum '$stage/source.tar' '$stage/Cargo.lock.baseline' '$stage/linux-process-proof.py' '$stage/remote-launch.sh' '$stage/runner/tools/run_scoped.py' '$stage/runner/tools/agentskills/__init__.py' '$stage/runner/tools/agentskills/pyguard.py' | tee '$stage/input-identities.sha256'; test \$(sha256sum '$stage/source.tar' | cut -d' ' -f1) = '$archive_sha'"
