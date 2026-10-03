#!/usr/bin/env bash
set -euo pipefail

repo=/Users/hoppworks/.codex/worktrees/linux-managed-success/rhai
source_rev=31a61e752d0ffb747be827475278e3fc5d9dbe30
stage=/root/rhai-linux-managed-deadline-20261003-bcecd9eb-105
scope=/root/.local/share/agent-builds/rhai/linux-managed-deadline-20261003-bcecd9eb-105
lock="$repo/.scratch/all-tickets/current-msrv-examples-evidence/Cargo.lock"
skills=/Users/hoppworks/projects/agent-skills/tools
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
base="$repo/.scratch/all-tickets/check-linux-current-msrv-examples.py"
expected_lock=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
expected_base=59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06
expected_archive=aa3916aeb2cfb842cb2572032e398fc1c3f43f3811e6c60abc3e73d51dba4796
archive_helper=/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/.scratch/all-tickets/archive-build-source.py
expected_archive_helper=a75b4e807f03e8247ed821df871ceb35e776b7f699046d7a099dd0b85199fd8b
expected_proof=44cb3867771c93af50fb50dbbf496fcf35fc645dfdfd7d59d248d9a663783f55
expected_old_proof=83e84145fdec770ee5469b8ef2d85eacb813bc073abbd2a37e80e605a224a1a0
expected_kill_proof=4a80d60a826e1db80e174fe0627e01194d46cc54c4d22e55c1c49425637e50d1
expected_final_drop_proof=b94913dd6e7baaf8140c24d1a609086ae0367a62f1c2c30277ccff5393031e99
expected_test=8d6af23f45ac24ce640ca624800b3e40daff9e10941047a786ce5f7bd233f02b
expected_contract=0edcab444948bce58d7530202ca75688160efee80143f8be17fc29b96cd5da68

git -C "$repo" cat-file -e "$source_rev^{commit}"
git -C "$repo" merge-base --is-ancestor "$source_rev" HEAD
git -C "$repo" diff --quiet "$source_rev" HEAD -- . ":(exclude).scratch/**"
test -z "$(git -C "$repo" status --porcelain --untracked-files=no -- . ":(exclude).scratch/**")"
test "$(shasum -a 256 "$lock" | awk '{print $1}')" = "$expected_lock"
test "$(shasum -a 256 "$base" | awk '{print $1}')" = "$expected_base"
test "$(shasum -a 256 "$repo/.scratch/stdlib-wayfinder/issues/03-process-contract.md" | awk '{print $1}')" = "$expected_contract"
test "$(shasum -a 256 "$script_dir/linux-managed-deadline105-proof.py" | awk '{print $1}')" = "$expected_proof"
test "$(shasum -a 256 "$repo/.scratch/all-tickets/linux-managed-success-proof.py" | awk '{print $1}')" = "$expected_old_proof"
test "$(shasum -a 256 "$repo/.scratch/all-tickets/linux-managed-kill-proof.py" | awk '{print $1}')" = "$expected_kill_proof"
test "$(shasum -a 256 "$repo/.scratch/all-tickets/linux-managed-final-drop-proof.py" | awk '{print $1}')" = "$expected_final_drop_proof"
test "$(shasum -a 256 "$repo/tests/sys_process.rs" | awk '{print $1}')" = "$expected_test"
test "$(shasum -a 256 "$archive_helper" | awk '{print $1}')" = "$expected_archive_helper"
archive_sha=$(python3 "$archive_helper" "$repo" "$source_rev" | shasum -a 256 | awk '{print $1}')
test "$archive_sha" = "$expected_archive"

ssh workhorse "umask 077; test ! -e '$stage' && test ! -L '$stage' && test ! -e '$scope' && test ! -L '$scope' && mkdir -m 700 '$stage' '$stage/outer-evidence' '$stage/runner' '$stage/runner/tools' '$stage/runner/tools/agentskills'"
python3 "$archive_helper" "$repo" "$source_rev" | ssh workhorse "umask 077; cat > '$stage/source.tar'"
scp "$lock" workhorse:"$stage/Cargo.lock.accepted"
scp "$base" workhorse:"$stage/check-linux-current-msrv-examples.py"
scp "$archive_helper" workhorse:"$stage/archive-build-source.py"
scp "$script_dir/linux-managed-deadline105-proof.py" workhorse:"$stage/linux-managed-deadline105-proof.py"
scp "$repo/.scratch/all-tickets/linux-managed-success-proof.py" workhorse:"$stage/linux-managed-success-proof.py"
scp "$repo/.scratch/all-tickets/linux-managed-kill-proof.py" workhorse:"$stage/linux-managed-kill-proof.py"
scp "$repo/.scratch/all-tickets/linux-managed-final-drop-proof.py" workhorse:"$stage/linux-managed-final-drop-proof.py"
scp "$repo/.scratch/stdlib-wayfinder/issues/03-process-contract.md" workhorse:"$stage/contract-source.md"
scp "$skills/run_scoped.py" workhorse:"$stage/runner/tools/run_scoped.py"
scp "$skills/agentskills/__init__.py" workhorse:"$stage/runner/tools/agentskills/__init__.py"
scp "$skills/agentskills/pyguard.py" workhorse:"$stage/runner/tools/agentskills/pyguard.py"
scp "$script_dir/linux-managed-deadline105-stage.sh" workhorse:"$stage/stage.sh"
scp "$script_dir/linux-managed-deadline105-launch.sh" workhorse:"$stage/launch.sh"
ssh workhorse "cd '$stage' && chmod 700 launch.sh && printf '%s  %s\\n' '$expected_archive' source.tar > source.sha256 && sha256sum --check source.sha256 && printf '%s\\n' \
  \"source_revision=$source_rev\" \"source_archive_sha256=$expected_archive\" \"lock_sha256=$expected_lock\" \"base_helper_sha256=$expected_base\" \"proof_helper_sha256=$expected_proof\" \"test_file_sha256=$expected_test\" \"contract_sha256=$expected_contract\" \"test_file=tests/sys_process.rs\" \"exact_tests=9\" \"feature_rows=4\" \"positive_exact_invocations=8\" \"negative_controls=1\" \"base_regressions=4\" \"test_exact_invocations=9\" \"toolchain_setup_commands=3\" \"helper_commands_expected=12\" \"rust_toolchain=1.77.2-x86_64-unknown-linux-gnu\" \"outer_timeout_seconds=600\" \"run_scoped_timeout_seconds=585\" \"helper_deadline_seconds=540\" \"export_reserve_seconds=30\" \"cargo_build_jobs=2\" \"max_descendants=16\" \"sample_interval_seconds=1\" \"storage_preemptive_stop_kib=1572864\" \"storage_hard_stop_kib=2097152\" \"rss_hard_stop_kib=2097152\" > contract.md && sha256sum archive-build-source.py source.tar Cargo.lock.accepted check-linux-current-msrv-examples.py linux-managed-deadline105-proof.py linux-managed-success-proof.py linux-managed-kill-proof.py linux-managed-final-drop-proof.py contract-source.md contract.md stage.sh launch.sh runner/tools/run_scoped.py runner/tools/agentskills/__init__.py runner/tools/agentskills/pyguard.py > input-identities.sha256 && sha256sum --check input-identities.sha256"
