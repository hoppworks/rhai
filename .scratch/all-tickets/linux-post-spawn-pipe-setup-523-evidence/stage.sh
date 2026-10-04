#!/usr/bin/env bash
set -euo pipefail
source_rev=523608648dcae99bc0f6b46eaf2bb91fa4ecc752
stage=/root/rhai-linux-post-spawn-pipe-setup-523-20261004
scope=/root/.local/share/agent-builds/rhai/linux-post-spawn-pipe-setup-523-20261004
skills=/Users/hoppworks/projects/agent-skills/tools
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
repo=$(git -C "$script_dir" rev-parse --show-toplevel)
lock="$script_dir/Cargo.lock.accepted"
contract="$repo/.scratch/all-tickets/linux-post-spawn-pipe-setup-contract.md"
base="$script_dir/check-linux-current-msrv-examples.py"
archive_helper="$script_dir/archive-build-source.py"
expected_lock=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
expected_base=c5422e7895f5afacf987be55df2297b63b0763618ccbdc2a8374116a1421edd9
expected_archive=998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b
expected_archive_helper=a75b4e807f03e8247ed821df871ceb35e776b7f699046d7a099dd0b85199fd8b
expected_test=1b60751c6d9ed695f79edc4f8a7972338274684ef53583bd1ea1009c1aca822a
expected_contract=ff4c5ed27bbdb55ef2ad66c28cddc31a1e624726cb7ec3f98078bc49cfc81b9d
expected_proof=236b6d8279274ca6b8d21174469ec632aad298df36191bd85ee49c15510a2a83
expected_collector=3f6ac7028f936270ab61ee1cb332ebae0f3e549a2499284a0a7c0b9332844f71
expected_probes=9747de6fd0c588cf38b843eb3aa2f109422077d2eeb56195ba7b2d35b77da313
expected_launcher=9f67bf3211d609f88684de4f3b2af8de36f3a9f6fdb73124c2011be26f409b3e

test "$(git -C "$repo" rev-parse "$source_rev^{tree}:src/packages/sys/process/unix.rs" 2>/dev/null || git -C "$repo" rev-parse "$source_rev:src/packages/sys/process/unix.rs")" = a80a4fb2e15f1331bd688e79a1d8fa9b8673b4da
test "$(shasum -a 256 "$lock" | awk '{print $1}')" = "$expected_lock"
test "$(shasum -a 256 "$base" | awk '{print $1}')" = "$expected_base"
test "$(shasum -a 256 "$archive_helper" | awk '{print $1}')" = "$expected_archive_helper"
test "$(shasum -a 256 "$script_dir/source.tar" | awk '{print $1}')" = "$expected_archive"
test "$(shasum -a 256 "$contract" | awk '{print $1}')" = "$expected_contract"
test "$(shasum -a 256 "$script_dir/linux-post-spawn-pipe-setup-proof.py" | awk '{print $1}')" = "$expected_proof"
test "$(shasum -a 256 "$script_dir/collect-originals.py" | awk '{print $1}')" = "$expected_collector"
test "$(shasum -a 256 "$script_dir/recipe-probes.py" | awk '{print $1}')" = "$expected_probes"
test "$(shasum -a 256 "$script_dir/launch.sh" | awk '{print $1}')" = "$expected_launcher"
ssh workhorse "umask 077; test ! -e '$stage' && test ! -L '$stage' && test ! -e '$scope' && test ! -L '$scope' && mkdir -m 700 '$stage' '$stage/outer-evidence' '$stage/runner' '$stage/runner/tools' '$stage/runner/tools/agentskills'"
scp "$script_dir/source.tar" workhorse:"$stage/source.tar"
scp "$lock" workhorse:"$stage/Cargo.lock.accepted"
scp "$archive_helper" workhorse:"$stage/archive-build-source.py"
scp "$base" workhorse:"$stage/check-linux-current-msrv-examples.py"
scp "$contract" workhorse:"$stage/contract.md"
scp "$script_dir/linux-post-spawn-pipe-setup-proof.py" workhorse:"$stage/linux-post-spawn-pipe-setup-proof.py"
scp "$script_dir/launch.sh" workhorse:"$stage/launch.sh"
scp "$skills/run_scoped.py" workhorse:"$stage/runner/tools/run_scoped.py"
scp "$skills/agentskills/__init__.py" workhorse:"$stage/runner/tools/agentskills/__init__.py"
scp "$skills/agentskills/pyguard.py" workhorse:"$stage/runner/tools/agentskills/pyguard.py"
ssh workhorse "cd '$stage' && chmod 700 launch.sh && printf '%s  %s\\n' '$expected_archive' source.tar > source.sha256 && sha256sum --check source.sha256 && sha256sum archive-build-source.py source.tar Cargo.lock.accepted check-linux-current-msrv-examples.py contract.md linux-post-spawn-pipe-setup-proof.py launch.sh runner/tools/run_scoped.py runner/tools/agentskills/__init__.py runner/tools/agentskills/pyguard.py > input-identities.sha256 && sha256sum --check input-identities.sha256"
