#!/usr/bin/env bash
set -euo pipefail

repo=/Users/hoppworks/projects/rhai-all-tickets
skills=/Users/hoppworks/projects/agent-skills/tools
source_rev=1ca21e32eed2aa40287ba7e1282000add1dd49c7
expected_archive=8251e0429d51ffd330e7eac596a1513d836e43e549ca761852cafc642a2a8155
expected_lock=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
expected_run_scoped=9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d
expected_init=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
expected_pyguard=a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f
stage=/root/rhai-linux-current-features-msrv-1ca21e32-20261002
lock="$repo/.scratch/all-tickets/macos-selected-graph-evidence-03/Cargo.lock"
helper="$repo/.scratch/all-tickets/check-linux-current-feature-compilation.py"
contract="$repo/.scratch/all-tickets/linux-current-feature-compilation-contract.md"
launcher="$repo/.scratch/all-tickets/launch-linux-current-feature-compilation.sh"

git -C "$repo" cat-file -e "$source_rev^{commit}"
test "$(shasum -a 256 "$lock" | awk '{print $1}')" = "$expected_lock"
test "$(shasum -a 256 "$skills/run_scoped.py" | awk '{print $1}')" = "$expected_run_scoped"
test "$(shasum -a 256 "$skills/agentskills/__init__.py" | awk '{print $1}')" = "$expected_init"
test "$(shasum -a 256 "$skills/agentskills/pyguard.py" | awk '{print $1}')" = "$expected_pyguard"

archive_tmp=$(mktemp)
trap 'rm -f -- "$archive_tmp"' EXIT
git -C "$repo" archive --format=tar "$source_rev" > "$archive_tmp"
test "$(shasum -a 256 "$archive_tmp" | awk '{print $1}')" = "$expected_archive"

ssh workhorse "test ! -e '$stage' && install -d -m 700 '$stage' '$stage/runner/tools/agentskills'"
scp "$archive_tmp" "workhorse:$stage/source.tar"
scp "$lock" "workhorse:$stage/Cargo.lock.accepted"
scp "$helper" "workhorse:$stage/run-feature-compilation.py"
scp "$contract" "workhorse:$stage/contract.md"
scp "$launcher" "workhorse:$stage/launch.sh"
scp "$skills/run_scoped.py" "workhorse:$stage/runner/tools/run_scoped.py"
scp "$skills/agentskills/__init__.py" "workhorse:$stage/runner/tools/agentskills/__init__.py"
scp "$skills/agentskills/pyguard.py" "workhorse:$stage/runner/tools/agentskills/pyguard.py"

ssh workhorse "chmod 700 '$stage/launch.sh' && cd '$stage' && sha256sum source.tar Cargo.lock.accepted run-feature-compilation.py contract.md launch.sh runner/tools/run_scoped.py runner/tools/agentskills/__init__.py runner/tools/agentskills/pyguard.py > input-identities.sha256 && sha256sum --check input-identities.sha256 && test \$(sha256sum source.tar | cut -d' ' -f1) = '$expected_archive' && test \$(sha256sum Cargo.lock.accepted | cut -d' ' -f1) = '$expected_lock' && test \$(sha256sum runner/tools/run_scoped.py | cut -d' ' -f1) = '$expected_run_scoped' && test \$(sha256sum runner/tools/agentskills/__init__.py | cut -d' ' -f1) = '$expected_init' && test \$(sha256sum runner/tools/agentskills/pyguard.py | cut -d' ' -f1) = '$expected_pyguard'"
