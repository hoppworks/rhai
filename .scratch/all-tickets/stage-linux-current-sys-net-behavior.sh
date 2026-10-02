#!/usr/bin/env bash
set -euo pipefail
umask 077

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
skills=${AGENT_SKILLS_REPO:-/Users/hoppworks/projects/agent-skills}
source_rev=a2d7a8c2ace21e63c18b2e64cdce74e5e10afc94
expected_archive=551c03dbe3f4550db1b144b3e65d83f5bc66c132c1a9cffa59c83fce16bc41e1
expected_lock=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
expected_run_scoped=9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d
expected_init=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
expected_pyguard=a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f
stage=/root/rhai-linux-current-sys-net-behavior-a2d7a8c2-20261002-policy1
lock="$repo/.scratch/all-tickets/macos-selected-graph-evidence-03/Cargo.lock"
helper="$repo/.scratch/all-tickets/check-linux-current-sys-net-behavior.py"
contract="$repo/.scratch/all-tickets/linux-current-sys-net-behavior-contract.md"
launcher="$repo/.scratch/all-tickets/launch-linux-current-sys-net-behavior.sh"
stage_script="$repo/.scratch/all-tickets/stage-linux-current-sys-net-behavior.sh"

git -C "$repo" cat-file -e "$source_rev^{commit}"
test "$(shasum -a 256 "$lock" | awk '{print $1}')" = "$expected_lock"
test "$(shasum -a 256 "$skills/tools/run_scoped.py" | awk '{print $1}')" = "$expected_run_scoped"
test "$(shasum -a 256 "$skills/tools/agentskills/__init__.py" | awk '{print $1}')" = "$expected_init"
test "$(shasum -a 256 "$skills/tools/agentskills/pyguard.py" | awk '{print $1}')" = "$expected_pyguard"

archive_tmp=$(mktemp)
trap 'rm -f -- "$archive_tmp"' EXIT
git -C "$repo" archive --format=tar "$source_rev" > "$archive_tmp"
test "$(shasum -a 256 "$archive_tmp" | awk '{print $1}')" = "$expected_archive"

ssh workhorse "test ! -e '$stage' && install -d -m 700 '$stage' '$stage/runner/tools/agentskills' '$stage/outer-evidence'"
scp "$archive_tmp" "workhorse:$stage/source.tar"
scp "$lock" "workhorse:$stage/Cargo.lock.accepted"
scp "$helper" "workhorse:$stage/run-sys-net-behavior.py"
scp "$contract" "workhorse:$stage/contract.md"
scp "$launcher" "workhorse:$stage/launch.sh"
scp "$stage_script" "workhorse:$stage/stage.sh"
scp "$skills/tools/run_scoped.py" "workhorse:$stage/runner/tools/run_scoped.py"
scp "$skills/tools/agentskills/__init__.py" "workhorse:$stage/runner/tools/agentskills/__init__.py"
scp "$skills/tools/agentskills/pyguard.py" "workhorse:$stage/runner/tools/agentskills/pyguard.py"

ssh workhorse "chmod 700 '$stage/launch.sh' && cd '$stage' && sha256sum source.tar Cargo.lock.accepted run-sys-net-behavior.py contract.md launch.sh stage.sh runner/tools/run_scoped.py runner/tools/agentskills/__init__.py runner/tools/agentskills/pyguard.py > input-identities.sha256 && sha256sum --check input-identities.sha256 && test \$(sha256sum source.tar | cut -d' ' -f1) = '$expected_archive' && test \$(sha256sum Cargo.lock.accepted | cut -d' ' -f1) = '$expected_lock' && test \$(sha256sum runner/tools/run_scoped.py | cut -d' ' -f1) = '$expected_run_scoped' && test \$(sha256sum runner/tools/agentskills/__init__.py | cut -d' ' -f1) = '$expected_init' && test \$(sha256sum runner/tools/agentskills/pyguard.py | cut -d' ' -f1) = '$expected_pyguard'"
