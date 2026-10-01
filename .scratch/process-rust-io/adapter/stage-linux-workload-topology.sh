#!/usr/bin/env bash
set -euo pipefail

repo=$(git rev-parse --show-toplevel)
stage=/root/rhai-linux-native-io-task/native-workload-topology-attempt3-20261001-0729UTC
skills=/Users/hoppworks/projects/agent-skills/tools
expected_commit=595c941de042da4f08ceb750119c6c274eb37d13

test "$(git -C "$repo" rev-parse HEAD^ )" = "$expected_commit"
ssh workhorse "test ! -e '$stage' && install -d -m 700 '$stage' '$stage/source' '$stage/evidence' '$stage/runner/tools/agentskills'"
git -C "$repo" archive --format=tar "$expected_commit" | ssh workhorse "tar -xf - -C '$stage/source'"
scp "$repo/.scratch/process-rust-io/adapter/launch-linux-workload-topology.sh" \
  workhorse:"$stage/launch-linux-workload-topology.sh"
scp "$repo/.scratch/process-rust-io/adapter/stage-linux-workload-topology.sh" \
  workhorse:"$stage/stage-linux-workload-topology.sh"
scp "$skills/run_scoped.py" workhorse:"$stage/runner/tools/run_scoped.py"
scp "$skills/agentskills/__init__.py" workhorse:"$stage/runner/tools/agentskills/__init__.py"
scp "$skills/agentskills/pyguard.py" workhorse:"$stage/runner/tools/agentskills/pyguard.py"
ssh workhorse "chmod 700 '$stage/launch-linux-workload-topology.sh'; cd '$stage'; sha256sum \
  source/.scratch/process-rust-io/Cargo.toml \
  source/.scratch/process-rust-io/src/main.rs \
  source/.scratch/process-rust-io/adapter/controller.py \
  source/.scratch/process-rust-io/adapter/custodian.py \
  source/.scratch/process-rust-io/adapter/process_identity.py \
  source/.scratch/process-rust-io/adapter/run_native_acceptance.py \
  source/.scratch/process-rust-io/adapter/test_process_identity.py \
  source/.scratch/process-rust-io/adapter/test_workload_topology_receipt.py \
  source/.scratch/process-prototype/Cargo.toml \
  source/.scratch/process-prototype/src/main.rs \
  launch-linux-workload-topology.sh stage-linux-workload-topology.sh \
  runner/tools/run_scoped.py runner/tools/agentskills/__init__.py \
  runner/tools/agentskills/pyguard.py | tee input-identities.sha256"
