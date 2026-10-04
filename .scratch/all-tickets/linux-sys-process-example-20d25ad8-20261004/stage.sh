#!/usr/bin/env bash
set -euo pipefail
umask 077

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
skills=${AGENT_SKILLS_REPO:-/Users/hoppworks/projects/agent-skills}
source_rev=20d25ad8ed4483d4cd4079cf62c8481a629c00e3
expected_archive=e7a9a118bd29c05e8a70e284196837594fc97811f3d80688d17f55167008be93
expected_lock=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
expected_run_scoped=9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d
expected_init=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
expected_pyguard=a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f
expected_archive_helper=a75b4e807f03e8247ed821df871ceb35e776b7f699046d7a099dd0b85199fd8b
stage=/root/rhai-linux-sys-process-example-20d25ad8-20261004
lock="$repo/.scratch/all-tickets/macos-selected-graph-evidence-03/Cargo.lock"
helper="$repo/.scratch/all-tickets/linux-sys-process-example-20d25ad8-20261004/run-examples.py"
contract="$repo/.scratch/all-tickets/linux-sys-process-example-20d25ad8-20261004/contract.md"
launcher="$repo/.scratch/all-tickets/linux-sys-process-example-20d25ad8-20261004/launch.sh"
stage_script="$repo/.scratch/all-tickets/linux-sys-process-example-20d25ad8-20261004/stage.sh"
archive_helper=/Users/hoppworks/.codex/worktrees/linux-managed-success/rhai/.scratch/all-tickets/archive-build-source.py

git -C "$repo" cat-file -e "$source_rev^{commit}"
test "$(shasum -a 256 "$lock" | awk '{print $1}')" = "$expected_lock"
test "$(shasum -a 256 "$skills/tools/run_scoped.py" | awk '{print $1}')" = "$expected_run_scoped"
test "$(shasum -a 256 "$skills/tools/agentskills/__init__.py" | awk '{print $1}')" = "$expected_init"
test "$(shasum -a 256 "$skills/tools/agentskills/pyguard.py" | awk '{print $1}')" = "$expected_pyguard"
test "$(shasum -a 256 "$archive_helper" | awk '{print $1}')" = "$expected_archive_helper"

archive_tmp=$(mktemp)
trap 'rm -f -- "$archive_tmp"' EXIT
python3 "$archive_helper" "$repo" "$source_rev" > "$archive_tmp"
test "$(shasum -a 256 "$archive_tmp" | awk '{print $1}')" = "$expected_archive"

ssh workhorse "test ! -e '$stage' && install -d -m 700 '$stage' '$stage/runner/tools/agentskills' '$stage/outer-evidence'"
scp "$archive_tmp" "workhorse:$stage/source.tar"
scp "$lock" "workhorse:$stage/Cargo.lock.accepted"
scp "$helper" "workhorse:$stage/run-examples.py"
scp "$contract" "workhorse:$stage/contract.md"
scp "$launcher" "workhorse:$stage/launch.sh"
scp "$stage_script" "workhorse:$stage/stage.sh"
scp "$archive_helper" "workhorse:$stage/archive-build-source.py"
scp "$skills/tools/run_scoped.py" "workhorse:$stage/runner/tools/run_scoped.py"
scp "$skills/tools/agentskills/__init__.py" "workhorse:$stage/runner/tools/agentskills/__init__.py"
scp "$skills/tools/agentskills/pyguard.py" "workhorse:$stage/runner/tools/agentskills/pyguard.py"

ssh workhorse "chmod 700 '$stage/launch.sh' && cd '$stage' && sha256sum source.tar Cargo.lock.accepted run-examples.py contract.md launch.sh stage.sh archive-build-source.py runner/tools/run_scoped.py runner/tools/agentskills/__init__.py runner/tools/agentskills/pyguard.py > input-identities.sha256 && sha256sum --check input-identities.sha256 && test \$(sha256sum source.tar | cut -d' ' -f1) = '$expected_archive' && test \$(sha256sum Cargo.lock.accepted | cut -d' ' -f1) = '$expected_lock' && test \$(sha256sum archive-build-source.py | cut -d' ' -f1) = '$expected_archive_helper' && test \$(sha256sum runner/tools/run_scoped.py | cut -d' ' -f1) = '$expected_run_scoped' && test \$(sha256sum runner/tools/agentskills/__init__.py | cut -d' ' -f1) = '$expected_init' && test \$(sha256sum runner/tools/agentskills/pyguard.py | cut -d' ' -f1) = '$expected_pyguard'"
