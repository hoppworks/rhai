#!/usr/bin/env bash
set -euo pipefail

stage=/root/rhai-linux-optional-msrv-proof-task
source_rev=293172363f4929acb166e33e0aa34fff5fc7e1cc
expected_archive=fe8ad5aa459e525e484d84c7a5a90f144ab142b10a96392ec30f5e75c77a4577
lock=/Users/hoppworks/projects/rhai-all-tickets/.scratch/optional-msrv-proof/evidence/Cargo.lock
repo=/Users/hoppworks/projects/rhai-linux-optional-msrv-proof
skills=/Users/hoppworks/projects/agent-skills/tools

git -C "$repo" cat-file -e "$source_rev^{commit}"
test -z "$(git -C "$repo" status --porcelain=v1)"
test "$(shasum -a 256 "$lock" | awk '{print $1}')" = 8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa
ssh workhorse "test ! -e '$stage' && install -d -m 700 '$stage' '$stage/evidence' '$stage/runner/tools/agentskills'"

git -C "$repo" archive --format=tar "$source_rev" | ssh workhorse "cat > '$stage/source.tar'"
scp "$lock" workhorse:"$stage/Cargo.lock.accepted"
scp "$repo/.scratch/linux-optional-msrv-proof/run-proof.py" workhorse:"$stage/run-proof.py"
scp "$repo/.scratch/linux-optional-msrv-proof/remote-launch.sh" workhorse:"$stage/remote-launch.sh"
scp "$skills/run_scoped.py" workhorse:"$stage/runner/tools/run_scoped.py"
scp "$skills/agentskills/__init__.py" workhorse:"$stage/runner/tools/agentskills/__init__.py"
scp "$skills/agentskills/pyguard.py" workhorse:"$stage/runner/tools/agentskills/pyguard.py"
ssh workhorse "chmod 700 '$stage/remote-launch.sh'; sha256sum '$stage/source.tar' '$stage/Cargo.lock.accepted' '$stage/run-proof.py' '$stage/remote-launch.sh' '$stage/runner/tools/run_scoped.py' '$stage/runner/tools/agentskills/pyguard.py' | tee '$stage/input-identities.sha256'; test \$(sha256sum '$stage/source.tar' | cut -d' ' -f1) = '$expected_archive'"
