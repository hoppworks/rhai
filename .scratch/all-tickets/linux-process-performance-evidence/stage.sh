#!/usr/bin/env bash
set -euo pipefail
source_rev=8c0ee4634355aee4e841b455461a7dd5aac2aa18
stage=/root/rhai-linux-process-performance-8c0ee-20261004
scope=/root/.local/share/agent-builds/rhai/linux-process-performance-8c0ee-20261004
skills=/Users/hoppworks/projects/agent-skills/tools
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
repo=$(git -C "$script_dir" rev-parse --show-toplevel)
expected_archive=4f049fda78ab245c5e482eef9392f7e8ae059d4fd4fada904941c631c43611f4
expected_lock=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
expected_base=c5422e7895f5afacf987be55df2297b63b0763618ccbdc2a8374116a1421edd9
expected_archive_helper=a75b4e807f03e8247ed821df871ceb35e776b7f699046d7a099dd0b85199fd8b
expected_test=78b057927126c3a6525ece12b193e1163330ac2fbd6630663164ddcac8e75489
expected_contract=bb9981dbce7d4694660e20b6ec4d8fe9966d88645348d644eaea090c8422f551
test "$(shasum -a 256 "$script_dir/measurement-contract.md" | awk '{print $1}')" = "$expected_contract"

# Frozen baseline and source-under-test are checked independently of the working tree.
test "$(git -C "$repo" rev-parse "$source_rev:src/packages/sys/process/unix.rs")" = a80a4fb2e15f1331bd688e79a1d8fa9b8673b4da
test "$(shasum -a 256 "$script_dir/source.tar" | awk '{print $1}')" = "$expected_archive"
test "$(shasum -a 256 "$script_dir/Cargo.lock.accepted" | awk '{print $1}')" = "$expected_lock"
test "$(shasum -a 256 "$script_dir/check-linux-current-msrv-examples.py" | awk '{print $1}')" = "$expected_base"
test "$(shasum -a 256 "$script_dir/archive-build-source.py" | awk '{print $1}')" = "$expected_archive_helper"
test "$(shasum -a 256 "$script_dir/linux_process_performance.rs" | awk '{print $1}')" = "$expected_test"
test "$(shasum -a 256 "$script_dir/linux-process-performance-proof.py" | awk '{print $1}')" = 0e4d218e35c4c627516362b80591f9ea7ab5e991427f4d6fe921a8e77704ec32
ssh workhorse "umask 077; test ! -e '$stage' && test ! -L '$stage' && test ! -e '$scope' && test ! -L '$scope' && mkdir -m 700 '$stage' '$stage/outer-evidence' '$stage/runner' '$stage/runner/tools' '$stage/runner/tools/agentskills'"
scp "$script_dir/source.tar" workhorse:"$stage/source.tar"
scp "$script_dir/Cargo.lock.accepted" workhorse:"$stage/Cargo.lock.accepted"
scp "$script_dir/check-linux-current-msrv-examples.py" workhorse:"$stage/check-linux-current-msrv-examples.py"
scp "$script_dir/archive-build-source.py" workhorse:"$stage/archive-build-source.py"
scp "$script_dir/linux_process_performance.rs" workhorse:"$stage/linux_process_performance.rs"
scp "$script_dir/measurement-contract.md" workhorse:"$stage/measurement-contract.md"
scp "$script_dir/linux-process-performance-proof.py" workhorse:"$stage/linux-process-performance-proof.py"
scp "$script_dir/launch.sh" workhorse:"$stage/launch.sh"
scp "$skills/run_scoped.py" workhorse:"$stage/runner/tools/run_scoped.py"
scp "$skills/agentskills/__init__.py" workhorse:"$stage/runner/tools/agentskills/__init__.py"
scp "$skills/agentskills/pyguard.py" workhorse:"$stage/runner/tools/agentskills/pyguard.py"
ssh workhorse "cd '$stage' && chmod 700 launch.sh && printf '%s  %s\\n' '$expected_archive' source.tar > source.sha256 && sha256sum --check source.sha256 && sha256sum source.tar Cargo.lock.accepted check-linux-current-msrv-examples.py archive-build-source.py linux_process_performance.rs measurement-contract.md linux-process-performance-proof.py launch.sh runner/tools/run_scoped.py runner/tools/agentskills/__init__.py runner/tools/agentskills/pyguard.py > input-identities.sha256 && sha256sum --check input-identities.sha256"
