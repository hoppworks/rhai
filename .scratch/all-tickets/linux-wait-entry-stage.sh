#!/usr/bin/env bash
set -euo pipefail

repo=/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai
source_rev=08507d6831f73f28aa0b95a4255c5df8ebe2ec13
stage=/root/rhai-linux-wait-entry-20261003-08507d68
scope=/root/.local/share/agent-builds/rhai/linux-wait-entry-20261003-08507d68
lock="$repo/.scratch/all-tickets/current-msrv-examples-evidence/Cargo.lock"
skills=/Users/hoppworks/projects/agent-skills/tools
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
base="$repo/.scratch/all-tickets/check-linux-current-msrv-examples.py"
expected_lock=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425

git -C "$repo" cat-file -e "$source_rev^{commit}"
test "$(git -C "$repo" rev-parse HEAD)" = "08507d6831f73f28aa0b95a4255c5df8ebe2ec13"
test "$(shasum -a 256 "$lock" | awk '{print $1}')" = "$expected_lock"
test "$(shasum -a 256 "$base" | awk '{print $1}')" = 59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06
archive_sha=$(git -C "$repo" archive --format=tar "$source_rev" | shasum -a 256 | awk '{print $1}')

ssh workhorse "umask 077; test ! -e '$stage' && test ! -L '$stage' && test ! -e '$scope' && test ! -L '$scope' && mkdir -m 700 '$stage' '$stage/outer-evidence' '$stage/runner' '$stage/runner/tools' '$stage/runner/tools/agentskills'"
git -C "$repo" archive --format=tar "$source_rev" | ssh workhorse "umask 077; cat > '$stage/source.tar'"
scp "$lock" workhorse:"$stage/Cargo.lock.accepted"
scp "$base" workhorse:"$stage/check-linux-current-msrv-examples.py"
scp "$script_dir/linux-wait-entry-proof.py" workhorse:"$stage/linux-wait-entry-proof.py"
scp "$skills/run_scoped.py" workhorse:"$stage/runner/tools/run_scoped.py"
scp "$skills/agentskills/__init__.py" workhorse:"$stage/runner/tools/agentskills/__init__.py"
scp "$skills/agentskills/pyguard.py" workhorse:"$stage/runner/tools/agentskills/pyguard.py"
scp "$script_dir/linux-wait-entry-stage.sh" workhorse:"$stage/stage.sh"
scp "$script_dir/linux-wait-entry-launch.sh" workhorse:"$stage/launch.sh"
ssh workhorse "cd '$stage' && chmod 700 launch.sh && printf '%s  %s\\n' '$archive_sha' source.tar > source.sha256 && sha256sum --check source.sha256 && printf '%s\\n' \"source_revision=$source_rev\" \"archive_sha256=$archive_sha\" \"lock_sha256=$expected_lock\" \"base_helper_sha256=59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06\" \"test=packages::sys::process::unix::tests::public_wait_is_cancelled_after_entering_condvar\" \"feature_rows=testing-environ,sys,sync;testing-environ,sys,sync,no_float\" \"wrong_wait_entry=101; observer acquired snapshot mutex after Condvar wait entry; wait-entry fixture cleanup reap=ESRCH\" \"green=one exact test passed; entered_waits greater than zero; nonterminal_at_cancel=true; waiter_woke=true; reap=ESRCH\" > contract.md && sha256sum source.tar Cargo.lock.accepted check-linux-current-msrv-examples.py linux-wait-entry-proof.py contract.md stage.sh launch.sh runner/tools/run_scoped.py runner/tools/agentskills/__init__.py runner/tools/agentskills/pyguard.py > input-identities.sha256 && sha256sum --check input-identities.sha256"
