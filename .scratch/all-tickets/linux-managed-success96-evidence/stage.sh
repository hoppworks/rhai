#!/usr/bin/env bash
set -euo pipefail

repo=/Users/hoppworks/.codex/worktrees/linux-managed-success/rhai
source_rev=003da06421fbd11c26e0c96ab5013416c0939a1d
stage=/root/rhai-linux-managed-success-20261003-7d045f21-96
scope=/root/.local/share/agent-builds/rhai/linux-managed-success-20261003-7d045f21-96
lock="$repo/.scratch/all-tickets/current-msrv-examples-evidence/Cargo.lock"
skills=/Users/hoppworks/projects/agent-skills/tools
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
base="$repo/.scratch/all-tickets/check-linux-current-msrv-examples.py"
expected_lock=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
expected_base=59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06
expected_archive=f62ea7430f8a92db7210055373f9e96b2d850d3564c4962844c80056b7294d1a
archive_helper=/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/.scratch/all-tickets/archive-build-source.py
expected_archive_helper=a75b4e807f03e8247ed821df871ceb35e776b7f699046d7a099dd0b85199fd8b
expected_proof=83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0
expected_test=e0034cf3a69ccf6107a9dfbc0854c0147ec2d93fdda8acf5ed6b07e683e1dc14
expected_contract=1d8a61b5dffefc4f5891d12ed2b19b438637e4e752607e68c6495f96eb553d41

git -C "$repo" cat-file -e "$source_rev^{commit}"
test "$(git -C "$repo" rev-parse HEAD)" = "$source_rev"
test "$(shasum -a 256 "$lock" | awk '{print $1}')" = "$expected_lock"
test "$(shasum -a 256 "$base" | awk '{print $1}')" = "$expected_base"
test "$(shasum -a 256 "$repo/.scratch/stdlib-wayfinder/issues/03-process-contract.md" | awk '{print $1}')" = "$expected_contract"
test "$(shasum -a 256 "$script_dir/linux-managed-success-proof.py" | awk '{print $1}')" = "$expected_proof"
test "$(shasum -a 256 "$repo/tests/sys_process.rs" | awk '{print $1}')" = "$expected_test"
test "$(shasum -a 256 "$archive_helper" | awk '{print $1}')" = "$expected_archive_helper"
archive_sha=$(python3 "$archive_helper" "$repo" "$source_rev" | shasum -a 256 | awk '{print $1}')
test "$archive_sha" = "$expected_archive"

ssh workhorse "umask 077; test ! -e '$stage' && test ! -L '$stage' && test ! -e '$scope' && test ! -L '$scope' && mkdir -m 700 '$stage' '$stage/outer-evidence' '$stage/runner' '$stage/runner/tools' '$stage/runner/tools/agentskills'"
python3 "$archive_helper" "$repo" "$source_rev" | ssh workhorse "umask 077; cat > '$stage/source.tar'"
scp "$lock" workhorse:"$stage/Cargo.lock.accepted"
scp "$base" workhorse:"$stage/check-linux-current-msrv-examples.py"
scp "$archive_helper" workhorse:"$stage/archive-build-source.py"
scp "$script_dir/linux-managed-success-proof.py" workhorse:"$stage/linux-managed-success-proof.py"
scp "$repo/.scratch/stdlib-wayfinder/issues/03-process-contract.md" workhorse:"$stage/contract-source.md"
scp "$skills/run_scoped.py" workhorse:"$stage/runner/tools/run_scoped.py"
scp "$skills/agentskills/__init__.py" workhorse:"$stage/runner/tools/agentskills/__init__.py"
scp "$skills/agentskills/pyguard.py" workhorse:"$stage/runner/tools/agentskills/pyguard.py"
scp "$script_dir/linux-managed-success-stage.sh" workhorse:"$stage/stage.sh"
scp "$script_dir/linux-managed-success-launch.sh" workhorse:"$stage/launch.sh"
ssh workhorse "cd '$stage' && chmod 700 launch.sh && printf '%s  %s\\n' '$expected_archive' source.tar > source.sha256 && sha256sum --check source.sha256 && printf '%s\\n' \
  \"source_revision=$source_rev\" \"source_archive_sha256=$expected_archive\" \"lock_sha256=$expected_lock\" \"base_helper_sha256=$expected_base\" \"proof_helper_sha256=$expected_proof\" \"test_file_sha256=$expected_test\" \"contract_sha256=$expected_contract\" \"test_file=tests/sys_process.rs\" \"exact_tests=2\" \"feature_rows=4\" \"positive_exact_invocations=4\" \"negative_controls=3\" \"test_exact_invocations=7\" \"toolchain_setup_commands=3\" \"helper_commands_expected=10\" \"rust_toolchain=1.77.2-x86_64-unknown-linux-gnu\" \"outer_timeout_seconds=600\" \"run_scoped_timeout_seconds=585\" \"helper_deadline_seconds=540\" \"export_reserve_seconds=30\" \"cargo_build_jobs=2\" \"max_descendants=16\" \"sample_interval_seconds=1\" \"storage_preemptive_stop_kib=1572864\" \"storage_hard_stop_kib=2097152\" \"rss_hard_stop_kib=2097152\" > contract.md && sha256sum archive-build-source.py source.tar Cargo.lock.accepted check-linux-current-msrv-examples.py linux-managed-success-proof.py contract-source.md contract.md stage.sh launch.sh runner/tools/run_scoped.py runner/tools/agentskills/__init__.py runner/tools/agentskills/pyguard.py > input-identities.sha256 && sha256sum --check input-identities.sha256"
