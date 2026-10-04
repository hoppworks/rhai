#!/usr/bin/env bash
set -euo pipefail

source_rev=523608648dcae99bc0f6b46eaf2bb91fa4ecc752
stage=/root/rhai-linux-drop-false-523-20261004
scope=/root/.local/share/agent-builds/rhai/linux-drop-false-523-20261004
skills=/Users/hoppworks/projects/agent-skills/tools
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
repo=$(git -C "$script_dir" rev-parse --show-toplevel)
lock="$repo/.scratch/all-tickets/current-msrv-examples-evidence/Cargo.lock"
base="$repo/.scratch/all-tickets/check-linux-current-msrv-examples.py"
archive_helper="$repo/.scratch/all-tickets/archive-build-source.py"
expected_lock=2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425
expected_base=c5422e7895f5afacf987be55df2297b63b0763618ccbdc2a8374116a1421edd9
expected_archive=998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b
expected_archive_helper=a75b4e807f03e8247ed821df871ceb35e776b7f699046d7a099dd0b85199fd8b
expected_test=5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb
expected_contract=5f26d4fd99bddda2fcd5f3a0ee863b361c930a69f915be4c9f8389bfadb072f5
expected_patch=78d7f123c570e5efb94563b77c737fd4ed97ac9a594090c4a7dba664b461e9dd
expected_observer=07d2ab6e1f2015a18b1ee83f59585b16b97852a00cc45dfb5778f836d78ad0d2
expected_proof=61d828673fa032db6160263b7ba3585e826099fa6baf38f05aa7a0115c972d53

git -C "$repo" cat-file -e "$source_rev^{commit}"
test "$(git -C "$repo" rev-parse "$source_rev:tests/sys_process.rs" | xargs -I{} git -C "$repo" show "$source_rev:tests/sys_process.rs" | shasum -a 256 | awk '{print $1}')" = "$expected_test"
test "$(shasum -a 256 "$lock" | awk '{print $1}')" = "$expected_lock"
test "$(shasum -a 256 "$base" | awk '{print $1}')" = "$expected_base"
test "$(shasum -a 256 "$archive_helper" | awk '{print $1}')" = "$expected_archive_helper"
test "$(shasum -a 256 "$script_dir/contract.md" | awk '{print $1}')" = "$expected_contract"
test "$(shasum -a 256 "$repo/.scratch/all-tickets/linux-drop-false-observer-handshake.patch" | awk '{print $1}')" = "$expected_patch"
test "$(shasum -a 256 "$script_dir/drop-false-observer.py" | awk '{print $1}')" = "$expected_observer"
test "$(shasum -a 256 "$script_dir/linux-drop-false-proof.py" | awk '{print $1}')" = "$expected_proof"
archive_sha=$(python3 "$archive_helper" "$repo" "$source_rev" | shasum -a 256 | awk '{print $1}')
test "$archive_sha" = "$expected_archive"

ssh workhorse "umask 077; test ! -e '$stage' && test ! -L '$stage' && test ! -e '$scope' && test ! -L '$scope' && mkdir -m 700 '$stage' '$stage/outer-evidence' '$stage/runner' '$stage/runner/tools' '$stage/runner/tools/agentskills'"
python3 "$archive_helper" "$repo" "$source_rev" | ssh workhorse "umask 077; cat > '$stage/source.tar'"
scp "$lock" workhorse:"$stage/Cargo.lock.accepted"
scp "$archive_helper" workhorse:"$stage/archive-build-source.py"
scp "$base" workhorse:"$stage/check-linux-current-msrv-examples.py"
scp "$repo/.scratch/all-tickets/linux-drop-false-observer-handshake.patch" workhorse:"$stage/drop-false-observer-handshake.patch"
scp "$script_dir/drop-false-observer.py" workhorse:"$stage/drop-false-observer.py"
scp "$script_dir/linux-drop-false-proof.py" workhorse:"$stage/linux-drop-false-proof.py"
scp "$script_dir/contract.md" workhorse:"$stage/contract.md"
scp "$skills/run_scoped.py" workhorse:"$stage/runner/tools/run_scoped.py"
scp "$skills/agentskills/__init__.py" workhorse:"$stage/runner/tools/agentskills/__init__.py"
scp "$skills/agentskills/pyguard.py" workhorse:"$stage/runner/tools/agentskills/pyguard.py"
scp "$script_dir/launch.sh" workhorse:"$stage/launch.sh"
ssh workhorse "cd '$stage' && chmod 700 launch.sh && printf '%s  %s\\n' '$expected_archive' source.tar > source.sha256 && sha256sum --check source.sha256 && sha256sum archive-build-source.py source.tar Cargo.lock.accepted check-linux-current-msrv-examples.py drop-false-observer-handshake.patch drop-false-observer.py linux-drop-false-proof.py contract.md launch.sh runner/tools/run_scoped.py runner/tools/agentskills/__init__.py runner/tools/agentskills/pyguard.py > input-identities.sha256 && sha256sum --check input-identities.sha256"
