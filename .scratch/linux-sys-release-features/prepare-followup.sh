#!/usr/bin/env bash
set -euo pipefail

repo=/Users/hoppworks/projects/rhai-linux-sys-release-features
source_rev=e1db9baafaaf30d94085f0cc6f661f363399f193
expected_archive=c934633c7889e4a427a87d557bbc578146e4db641c4fde2c93ff3fd4f047aa47
stage=/root/rhai-linux-sys-release-features-task/followup-e1db9baa
skills=/Users/hoppworks/projects/agent-skills/tools
task_dir="$repo/.scratch/linux-sys-release-features"
tmp=$(mktemp -d /tmp/rhai-linux-sys-source.XXXXXX)
trap 'rm -rf -- "$tmp"' EXIT

git -C "$repo" cat-file -e "$source_rev^{commit}"
git -C "$repo" archive --format=tar "$source_rev" > "$tmp/source.tar"
actual_archive=$(shasum -a 256 "$tmp/source.tar" | awk '{print $1}')
test "$actual_archive" = "$expected_archive"
tar -tf "$tmp/source.tar" > "$tmp/archive-members.txt"
grep -qx 'codegen/Cargo.toml' "$tmp/archive-members.txt"

ssh workhorse "test ! -e '$stage' && install -d -m 700 '$stage' '$stage/evidence' '$stage/runner/tools/agentskills'"
scp "$tmp/source.tar" workhorse:"$stage/source.tar"
scp "$task_dir/run-followup.py" workhorse:"$stage/run-followup.py"
scp "$task_dir/launch-followup.sh" workhorse:"$stage/launch-followup.sh"
scp "$skills/run_scoped.py" workhorse:"$stage/runner/tools/run_scoped.py"
scp "$skills/agentskills/__init__.py" workhorse:"$stage/runner/tools/agentskills/__init__.py"
scp "$skills/agentskills/pyguard.py" workhorse:"$stage/runner/tools/agentskills/pyguard.py"
ssh workhorse "chmod 700 '$stage/launch-followup.sh'; sha256sum '$stage/source.tar' '$stage/run-followup.py' '$stage/launch-followup.sh' '$stage/runner/tools/run_scoped.py' '$stage/runner/tools/agentskills/__init__.py' '$stage/runner/tools/agentskills/pyguard.py' | tee '$stage/input-identities.sha256'; test \$(sha256sum '$stage/source.tar' | cut -d' ' -f1) = '$expected_archive'"
