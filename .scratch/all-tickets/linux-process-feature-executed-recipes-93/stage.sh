#!/usr/bin/env bash
set -euo pipefail

repo=/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai
source_rev=6c451c5c99e751e50023a08912a035a2c8754ff6
stage=/root/rhai-linux-process-feature-20261003-6c451c5c-93
scope=/root/.local/share/agent-builds/rhai/linux-process-feature-20261003-6c451c5c-93
lock="$repo/.scratch/all-tickets/current-msrv-examples-evidence/Cargo.lock"
skills=/Users/hoppworks/projects/agent-skills/tools
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
base="$repo/.scratch/all-tickets/check-linux-current-msrv-examples.py"
expected_lock=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
expected_base=59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06
expected_archive=a158051f476cddc02744ab551c76a5b2458d3a69910f673ee6fb39745411d391
expected_patch=5cf5d4533ca3adb99a9313e710b91f184bf5f2ee90ce2e215644fddf71b17693
expected_options_helper=ac679734a00a39aec0369f96861655982320c75b637ae86d41adbe3104024503
expected_io_helper=00aba0d09535ab63e0ef4cf344f9d1ad31197456ad6adca11decab1ab2ec3396
expected_patch_applier=4533ca87a0e668225e34382d259eb439edfa4a12bea608755e22fce95ddb807f
feature_patch="$repo/.scratch/all-tickets/process-feature.patch"
patch_applier="$repo/.scratch/all-tickets/apply-process-feature-patch.py"
options_helper="$script_dir/linux-process-options-proof.py"
io_helper="$script_dir/linux-process-io-proof.py"

git -C "$repo" cat-file -e "$source_rev^{commit}"
test "$(git -C "$repo" rev-parse HEAD)" = "$source_rev"
test "$(shasum -a 256 "$lock" | awk '{print $1}')" = "$expected_lock"
test "$(shasum -a 256 "$base" | awk '{print $1}')" = "$expected_base"
test "$(shasum -a 256 "$feature_patch" | awk '{print $1}')" = "$expected_patch"
test "$(shasum -a 256 "$patch_applier" | awk '{print $1}')" = "$expected_patch_applier"
test "$(shasum -a 256 "$options_helper" | awk '{print $1}')" = "$expected_options_helper"
test "$(shasum -a 256 "$io_helper" | awk '{print $1}')" = "$expected_io_helper"
archive_sha=$(git -C "$repo" archive --format=tar "$source_rev" | shasum -a 256 | awk '{print $1}')
test "$archive_sha" = "$expected_archive"

ssh workhorse "umask 077; test ! -e '$stage' && test ! -L '$stage' && test ! -e '$scope' && test ! -L '$scope' && mkdir -m 700 '$stage' '$stage/outer-evidence' '$stage/runner' '$stage/runner/tools' '$stage/runner/tools/agentskills'"
git -C "$repo" archive --format=tar "$source_rev" | ssh workhorse "umask 077; cat > '$stage/source.tar'"
scp "$lock" workhorse:"$stage/Cargo.lock.accepted"
scp "$base" workhorse:"$stage/check-linux-current-msrv-examples.py"
scp "$script_dir/linux-process-feature-proof.py" workhorse:"$stage/linux-process-feature-proof.py"
scp "$feature_patch" workhorse:"$stage/process-feature.patch"
scp "$patch_applier" workhorse:"$stage/apply-process-feature-patch.py"
scp "$options_helper" workhorse:"$stage/linux-process-options-control.py"
scp "$io_helper" workhorse:"$stage/linux-process-io-control.py"
scp "$skills/run_scoped.py" workhorse:"$stage/runner/tools/run_scoped.py"
scp "$skills/agentskills/__init__.py" workhorse:"$stage/runner/tools/agentskills/__init__.py"
scp "$skills/agentskills/pyguard.py" workhorse:"$stage/runner/tools/agentskills/pyguard.py"
scp "$script_dir/linux-process-feature-stage.sh" workhorse:"$stage/stage.sh"
scp "$script_dir/linux-process-feature-launch.sh" workhorse:"$stage/launch.sh"
ssh workhorse "cd '$stage' && chmod 700 launch.sh && printf '%s  %s\\n' '$expected_archive' source.tar > source.sha256 && sha256sum --check source.sha256 && printf '%s\\n' \"source_revision=$source_rev\" \"source_archive_sha256=$expected_archive\" \"lock_sha256=$expected_lock\" \"base_helper_sha256=$expected_base\" \"process_feature_patch_sha256=$expected_patch\" \"strict_patch_applier_sha256=$expected_patch_applier\" \"options_control_helper_sha256=$expected_options_helper\" \"io_control_helper_sha256=$expected_io_helper\" \"baseline_test_sha256=379db748d4b84a60538d172059df1feafaa62b337eaf49c1178d3e6467d40c74\" \"patched_test_sha256=8ec4d456672338920249446618ce768bc2fa1d29798d571dca1e897db87a076b\" \"test_file=tests/sys_process.rs\" \"exact_tests=11\" \"feature_rows=3\" \"positive_exact_invocations=32\" \"negative_controls=33\" \"test_exact_invocations=65\" \"baseline_compatibility_no_run_checks=2\" \"patch_application_commands=1\" \"toolchain_setup_commands=3\" \"all_helper_commands_expected=71\" \"rust_toolchain=1.77.2-x86_64-unknown-linux-gnu\" \"outer_timeout_seconds=600\" \"run_scoped_timeout_seconds=585\" \"helper_deadline_seconds=540\" \"export_reserve_seconds=30\" \"cargo_build_jobs=2\" \"max_descendants=16\" \"sample_interval_seconds=1\" \"storage_preemptive_stop_kib=1572864\" \"storage_hard_stop_kib=2097152\" \"rss_hard_stop_kib=2097152\" > contract.md && sha256sum source.tar Cargo.lock.accepted check-linux-current-msrv-examples.py linux-process-feature-proof.py process-feature.patch apply-process-feature-patch.py linux-process-options-control.py linux-process-io-control.py contract.md stage.sh launch.sh runner/tools/run_scoped.py runner/tools/agentskills/__init__.py runner/tools/agentskills/pyguard.py > input-identities.sha256 && sha256sum --check input-identities.sha256"
