#!/usr/bin/env bash
set -euo pipefail
umask 077
stage=/root/rhai-linux-process-overlap-d79-20261004-1259
scope=/root/.local/share/agent-builds/rhai/linux-process-overlap-d79-20261004-1259
skills=/Users/hoppworks/projects/agent-skills/tools
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
repo=$(git -C "$script_dir" rev-parse --show-toplevel)
freeze="$script_dir/source-freeze.json"
contract="$script_dir/contract.md"
guard=/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery/.scratch/all-tickets/linux-process-overlap-preflight.py
slot_wrapper=/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery/.scratch/all-tickets/linux-process-overlap-slot-wrapper.py
python3 - "$freeze" <<'PYFREEZE'
import json,pathlib,sys
f=json.loads(pathlib.Path(sys.argv[1]).read_text())
assert f['source_revision']=='9dc92b16dad173eaffbde521310d1e2480e7be9c'
assert f['test_source_sha256']=='6b088870e6f4ed758c88e6fdc7e50475cae7cda90ba10dae58e45718a2ba3a98'
assert f['files']['source.tar']=='2b46a48f0978de3f7c1a7958678d3474232a0b2246ac8ff8f85e9e931345c039'
assert f['files']['Cargo.lock.accepted']=='2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425'
PYFREEZE
(cd "$script_dir" && sha256sum --check package-pins.sha256)
test -f "$guard" && test -f "$slot_wrapper"
(cd "$script_dir" && sha256sum --check source-freeze.json.package.sha256)
ssh workhorse "umask 077; test ! -e '$stage' && test ! -L '$stage' && test ! -e '$scope' && test ! -L '$scope' && mkdir -m 700 '$stage' '$stage/outer-evidence' '$stage/runner' '$stage/runner/tools' '$stage/runner/tools/agentskills'"
for file in source.tar Cargo.lock.accepted archive-build-source.py check-linux-current-msrv-examples.py source-freeze.json contract.md linux-process-overlap-proof.py collect-originals.py linux-process-overlap-fresh-closure.py recipe-probes.py launch.sh; do scp "$script_dir/$file" "workhorse:$stage/$file"; done
scp "$guard" "workhorse:$stage/linux-process-overlap-preflight.py"
scp "$slot_wrapper" "workhorse:$stage/linux-process-overlap-slot-wrapper.py"
scp "$skills/run_scoped.py" "workhorse:$stage/runner/tools/run_scoped.py"
scp "$skills/agentskills/__init__.py" "workhorse:$stage/runner/tools/agentskills/__init__.py"
scp "$skills/agentskills/pyguard.py" "workhorse:$stage/runner/tools/agentskills/pyguard.py"
ssh workhorse "cd '$stage' && chmod 700 launch.sh && sha256sum source.tar > source.sha256 && sha256sum --check source.sha256 && sha256sum archive-build-source.py source.tar Cargo.lock.accepted check-linux-current-msrv-examples.py source-freeze.json contract.md linux-process-overlap-proof.py collect-originals.py linux-process-overlap-fresh-closure.py recipe-probes.py launch.sh runner/tools/run_scoped.py runner/tools/agentskills/__init__.py runner/tools/agentskills/pyguard.py > input-identities.sha256 && sha256sum --check input-identities.sha256"
