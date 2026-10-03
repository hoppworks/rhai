#!/usr/bin/env bash
set -euo pipefail

repo=/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai
source_rev=9e56d5f2ef42303493907907454562f72a24b60b
stage=/root/rhai-linux-process-io-20261003-9e56d5f2
scope=/root/.local/share/agent-builds/rhai/linux-process-io-20261003-9e56d5f2
lock="$repo/.scratch/all-tickets/current-msrv-examples-evidence/Cargo.lock"
skills=/Users/hoppworks/projects/agent-skills/tools
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
base="$repo/.scratch/all-tickets/check-linux-current-msrv-examples.py"
expected_lock=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
expected_base=59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06
expected_archive=40ddedbf8ff27d21c4be7066cb54f20be4192f5ae01de05579064cca4a254a61

git -C "$repo" cat-file -e "$source_rev^{commit}"
test "$(git -C "$repo" rev-parse HEAD)" = "$source_rev"
test "$(shasum -a 256 "$lock" | awk '{print $1}')" = "$expected_lock"
test "$(shasum -a 256 "$base" | awk '{print $1}')" = "$expected_base"
archive_sha=$(git -C "$repo" archive --format=tar "$source_rev" | shasum -a 256 | awk '{print $1}')
test "$archive_sha" = "$expected_archive"

ssh workhorse "umask 077; test ! -e '$stage' && test ! -L '$stage' && test ! -e '$scope' && test ! -L '$scope' && mkdir -m 700 '$stage' '$stage/outer-evidence' '$stage/runner' '$stage/runner/tools' '$stage/runner/tools/agentskills'"
git -C "$repo" archive --format=tar "$source_rev" | ssh workhorse "umask 077; cat > '$stage/source.tar'"
scp "$lock" workhorse:"$stage/Cargo.lock.accepted"
scp "$base" workhorse:"$stage/check-linux-current-msrv-examples.py"
scp "$script_dir/linux-process-io-proof.py" workhorse:"$stage/linux-process-io-proof.py"
scp "$skills/run_scoped.py" workhorse:"$stage/runner/tools/run_scoped.py"
scp "$skills/agentskills/__init__.py" workhorse:"$stage/runner/tools/agentskills/__init__.py"
scp "$skills/agentskills/pyguard.py" workhorse:"$stage/runner/tools/agentskills/pyguard.py"
scp "$script_dir/linux-process-io-stage.sh" workhorse:"$stage/stage.sh"
scp "$script_dir/linux-process-io-launch.sh" workhorse:"$stage/launch.sh"
ssh workhorse "cd '$stage' && chmod 700 launch.sh && printf '%s  %s\\n' '$expected_archive' source.tar > source.sha256 && sha256sum --check source.sha256 && printf '%s\\n' \"source_revision=$source_rev\" \"source_archive_sha256=$expected_archive\" \"lock_sha256=$expected_lock\" \"base_helper_sha256=$expected_base\" \"test_file=tests/sys_process.rs\" \"exact_tests=10\" \"feature_rows=5\" \"positive_exact_invocations=50\" \"negative_controls=10\" \"rust_toolchain=1.77.2-x86_64-unknown-linux-gnu\" \"outer_timeout_seconds=600\" \"run_scoped_timeout_seconds=585\" \"helper_deadline_seconds=540\" \"export_reserve_seconds=30\" \"cargo_build_jobs=2\" \"max_descendants=16\" \"sample_interval_seconds=1\" \"storage_preemptive_stop_kib=1572864\" \"storage_hard_stop_kib=2097152\" \"rss_hard_stop_kib=2097152\" > contract.md && sha256sum source.tar Cargo.lock.accepted check-linux-current-msrv-examples.py linux-process-io-proof.py contract.md stage.sh launch.sh runner/tools/run_scoped.py runner/tools/agentskills/__init__.py runner/tools/agentskills/pyguard.py > input-identities.sha256 && sha256sum --check input-identities.sha256"
