#!/usr/bin/env bash
set -euo pipefail

repo=/Users/hoppworks/.codex/worktrees/linux-managed-success/rhai
source_rev=523608648dcae99bc0f6b46eaf2bb91fa4ecc752
stage=/root/rhai-linux-managed-escaped-pipe-20261003-52360864-107
scope=/root/.local/share/agent-builds/rhai/linux-managed-escaped-pipe-20261003-52360864-107
lock="$repo/.scratch/all-tickets/current-msrv-examples-evidence/Cargo.lock"
skills=/Users/hoppworks/projects/agent-skills/tools
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
base="$repo/.scratch/all-tickets/check-linux-current-msrv-examples.py"
expected_lock=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
expected_base=59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06
expected_archive=998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b
archive_helper=/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/.scratch/all-tickets/archive-build-source.py
expected_archive_helper=a75b4e807f03e8247ed821df871ceb35e776b7f699046d7a099dd0b85199fd8b
expected_proof=81141bf9aac013f2230337ef0cbff1d5c5638c52a1e2f947a8c67fbd9066c7e5
expected_old_proof=83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0
expected_test=5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb
expected_contract=0edcab444948bce58d7530202ca75688160efee80143f8be17fc29b96cd5da68

git -C "$repo" cat-file -e "$source_rev^{commit}"
git -C "$repo" merge-base --is-ancestor "$source_rev" HEAD
git -C "$repo" diff --quiet "$source_rev" HEAD -- . ":(exclude).scratch/**"
test -z "$(git -C "$repo" status --porcelain --untracked-files=no -- . ":(exclude).scratch/**")"
test "$(shasum -a 256 "$lock" | awk '{print $1}')" = "$expected_lock"
test "$(shasum -a 256 "$base" | awk '{print $1}')" = "$expected_base"
test "$(shasum -a 256 "$repo/.scratch/stdlib-wayfinder/issues/03-process-contract.md" | awk '{print $1}')" = "$expected_contract"
test "$(shasum -a 256 "$script_dir/linux-managed-escaped-pipe-proof.py" | awk '{print $1}')" = "$expected_proof"
test "$(shasum -a 256 "$repo/.scratch/all-tickets/linux-managed-success-proof.py" | awk '{print $1}')" = "$expected_old_proof"
test "$(shasum -a 256 "$repo/tests/sys_process.rs" | awk '{print $1}')" = "$expected_test"
test "$(shasum -a 256 "$archive_helper" | awk '{print $1}')" = "$expected_archive_helper"
archive_sha=$(python3 "$archive_helper" "$repo" "$source_rev" | shasum -a 256 | awk '{print $1}')
test "$archive_sha" = "$expected_archive"

ssh workhorse "umask 077; test ! -e '$stage' && test ! -L '$stage' && test ! -e '$scope' && test ! -L '$scope' && mkdir -m 700 '$stage' '$stage/outer-evidence' '$stage/runner' '$stage/runner/tools' '$stage/runner/tools/agentskills'"
python3 "$archive_helper" "$repo" "$source_rev" | ssh workhorse "umask 077; cat > '$stage/source.tar'"
scp "$lock" workhorse:"$stage/Cargo.lock.accepted"
scp "$base" workhorse:"$stage/check-linux-current-msrv-examples.py"
scp "$archive_helper" workhorse:"$stage/archive-build-source.py"
scp "$script_dir/linux-managed-escaped-pipe-proof.py" workhorse:"$stage/linux-managed-escaped-pipe-proof.py"
scp "$repo/.scratch/all-tickets/linux-managed-success-proof.py" workhorse:"$stage/linux-managed-success-proof.py"
scp "$repo/.scratch/stdlib-wayfinder/issues/03-process-contract.md" workhorse:"$stage/contract-source.md"
scp "$skills/run_scoped.py" workhorse:"$stage/runner/tools/run_scoped.py"
scp "$skills/agentskills/__init__.py" workhorse:"$stage/runner/tools/agentskills/__init__.py"
scp "$skills/agentskills/pyguard.py" workhorse:"$stage/runner/tools/agentskills/pyguard.py"
scp "$script_dir/linux-managed-escaped-pipe-stage.sh" workhorse:"$stage/stage.sh"
scp "$script_dir/linux-managed-escaped-pipe-launch.sh" workhorse:"$stage/launch.sh"
ssh workhorse "cd '$stage' && chmod 700 launch.sh && printf '%s  %s\\n' '$expected_archive' source.tar > source.sha256 && sha256sum --check source.sha256 && printf '%s\\n' \
  \"source_revision=$source_rev\" \"source_archive_sha256=$expected_archive\" \"lock_sha256=$expected_lock\" \"base_helper_sha256=$expected_base\" \"proof_helper_sha256=$expected_proof\" \"test_file_sha256=$expected_test\" \"contract_sha256=$expected_contract\" \"test_file=tests/sys_process.rs\" \"exact_tests=8\" \"feature_rows=4\" \"positive_exact_invocations=7\" \"negative_controls=1\" \"base_regressions=3\" \"test_exact_invocations=8\" \"toolchain_setup_commands=3\" \"helper_commands_expected=11\" \"rust_toolchain=1.77.2-x86_64-unknown-linux-gnu\" \"outer_timeout_seconds=600\" \"run_scoped_timeout_seconds=585\" \"helper_deadline_seconds=540\" \"export_reserve_seconds=30\" \"cargo_build_jobs=2\" \"max_descendants=16\" \"sample_interval_seconds=1\" \"storage_preemptive_stop_kib=1572864\" \"storage_hard_stop_kib=2097152\" \"rss_hard_stop_kib=2097152\" > contract.md && sha256sum archive-build-source.py source.tar Cargo.lock.accepted check-linux-current-msrv-examples.py linux-managed-escaped-pipe-proof.py linux-managed-success-proof.py contract-source.md contract.md stage.sh launch.sh runner/tools/run_scoped.py runner/tools/agentskills/__init__.py runner/tools/agentskills/pyguard.py > input-identities.sha256 && sha256sum --check input-identities.sha256"
