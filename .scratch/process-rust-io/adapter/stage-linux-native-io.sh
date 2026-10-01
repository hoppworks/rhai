#!/usr/bin/env bash
set -euo pipefail

repo=$(git rev-parse --show-toplevel)
stage=/root/rhai-linux-native-io-task/native-linux-io-20261001-060839UTC
skills=/Users/hoppworks/projects/agent-skills/tools
expected_commit=072e11f715d363435437d00727f8dd30e286632d

test "$(git -C "$repo" rev-parse HEAD^)" = "$expected_commit"
ssh workhorse "test ! -e '$stage' && install -d -m 700 '$stage' '$stage/source' '$stage/evidence' '$stage/runner/tools/agentskills'"
git -C "$repo" archive --format=tar "$expected_commit" | ssh workhorse "tar -xf - -C '$stage/source'"
scp "$repo/.scratch/process-rust-io/adapter/launch-linux-native-io.sh" \
  workhorse:"$stage/launch-linux-native-io.sh"
scp "$skills/run_scoped.py" workhorse:"$stage/runner/tools/run_scoped.py"
scp "$skills/agentskills/__init__.py" workhorse:"$stage/runner/tools/agentskills/__init__.py"
scp "$skills/agentskills/pyguard.py" workhorse:"$stage/runner/tools/agentskills/pyguard.py"
ssh workhorse "chmod 700 '$stage/launch-linux-native-io.sh'; cd '$stage'; sha256sum source/.scratch/process-rust-io/adapter/run_native_acceptance.py source/.scratch/process-rust-io/adapter/process_identity.py source/.scratch/process-rust-io/adapter/launch-linux-native-io.sh launch-linux-native-io.sh runner/tools/run_scoped.py runner/tools/agentskills/pyguard.py | tee input-identities.sha256"
