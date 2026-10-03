#!/usr/bin/env bash
set -euo pipefail

repo=/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai
source_rev=257edf695f953271adf17b12dcc70c4287ae76b5
stage=/root/rhai-linux-managed-zombie-20261003-257edf69-95
scope=/root/.local/share/agent-builds/rhai/linux-managed-zombie-20261003-257edf69-95
lock="$repo/.scratch/all-tickets/current-msrv-examples-evidence/Cargo.lock"
skills=/Users/hoppworks/projects/agent-skills/tools
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
base="$repo/.scratch/all-tickets/check-linux-current-msrv-examples.py"
expected_lock=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
expected_base=59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06
expected_archive=ea085b4d28ee5ce3c7b998044242a50c755d9e9252638dbcf28c036b3df7c922
expected_proof=bc2650660bb1c3a576a6f33507f87b8254c74a9e17f7053e7e1f754238eb417d
expected_test=8ec4d456672338920249446618ce768bc2fa1d29798d571dca1e897db87a076b
expected_contract=f8c7520d931144f8e72e90b782455b1e6c32d4c3eb47c392ea7a74f8d3168ec7

git -C "$repo" cat-file -e "$source_rev^{commit}"
test "$(git -C "$repo" rev-parse HEAD)" = "$source_rev"
test "$(shasum -a 256 "$lock" | awk '{print $1}')" = "$expected_lock"
test "$(shasum -a 256 "$base" | awk '{print $1}')" = "$expected_base"
test "$(shasum -a 256 "$repo/.scratch/stdlib-wayfinder/issues/03-process-contract.md" | awk '{print $1}')" = "$expected_contract"
test "$(shasum -a 256 "$script_dir/linux-managed-zombie-proof.py" | awk '{print $1}')" = "$expected_proof"
test "$(shasum -a 256 "$repo/tests/sys_process.rs" | awk '{print $1}')" = "$expected_test"
archive_sha=$(git -C "$repo" archive --format=tar "$source_rev" | shasum -a 256 | awk '{print $1}')
test "$archive_sha" = "$expected_archive"

ssh workhorse "umask 077; test ! -e '$stage' && test ! -L '$stage' && test ! -e '$scope' && test ! -L '$scope' && mkdir -m 700 '$stage' '$stage/outer-evidence' '$stage/runner' '$stage/runner/tools' '$stage/runner/tools/agentskills'"
git -C "$repo" archive --format=tar "$source_rev" | ssh workhorse "umask 077; cat > '$stage/source.tar'"
scp "$lock" workhorse:"$stage/Cargo.lock.accepted"
scp "$base" workhorse:"$stage/check-linux-current-msrv-examples.py"
scp "$script_dir/linux-managed-zombie-proof.py" workhorse:"$stage/linux-managed-zombie-proof.py"
scp "$repo/.scratch/stdlib-wayfinder/issues/03-process-contract.md" workhorse:"$stage/contract-source.md"
scp "$skills/run_scoped.py" workhorse:"$stage/runner/tools/run_scoped.py"
scp "$skills/agentskills/__init__.py" workhorse:"$stage/runner/tools/agentskills/__init__.py"
scp "$skills/agentskills/pyguard.py" workhorse:"$stage/runner/tools/agentskills/pyguard.py"
scp "$script_dir/linux-managed-zombie-stage.sh" workhorse:"$stage/stage.sh"
scp "$script_dir/linux-managed-zombie-launch.sh" workhorse:"$stage/launch.sh"
ssh workhorse "cd '$stage' && chmod 700 launch.sh && printf '%s  %s\\n' '$expected_archive' source.tar > source.sha256 && sha256sum --check source.sha256 && printf '%s\\n' \
  \"source_revision=$source_rev\" \"source_archive_sha256=$expected_archive\" \"lock_sha256=$expected_lock\" \"base_helper_sha256=$expected_base\" \"proof_helper_sha256=$expected_proof\" \"test_file_sha256=$expected_test\" \"contract_sha256=$expected_contract\" \"test_file=tests/sys_process.rs\" \"exact_tests=1\" \"feature_rows=1\" \"positive_exact_invocations=1\" \"negative_controls=2\" \"test_exact_invocations=3\" \"toolchain_setup_commands=3\" \"helper_commands_expected=6\" \"rust_toolchain=1.77.2-x86_64-unknown-linux-gnu\" \"outer_timeout_seconds=600\" \"run_scoped_timeout_seconds=585\" \"helper_deadline_seconds=540\" \"export_reserve_seconds=30\" \"cargo_build_jobs=2\" \"max_descendants=16\" \"sample_interval_seconds=1\" \"storage_preemptive_stop_kib=1572864\" \"storage_hard_stop_kib=2097152\" \"rss_hard_stop_kib=2097152\" > contract.md && sha256sum source.tar Cargo.lock.accepted check-linux-current-msrv-examples.py linux-managed-zombie-proof.py contract-source.md contract.md stage.sh launch.sh runner/tools/run_scoped.py runner/tools/agentskills/__init__.py runner/tools/agentskills/pyguard.py > input-identities.sha256 && sha256sum --check input-identities.sha256"
