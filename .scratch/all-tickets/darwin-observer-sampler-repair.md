# Darwin observer sampler repair

## Result

The original Darwin launch failed during the first resource sample before
Rustup, Cargo, or a test command ran. Its traceback identifies sampled descendant
20811 as unidentifiable. The preserved runtime and scope readback is recorded in
the continuation checkout; the original immutable stage and evidence remain at
`.scratch/all-tickets/current-darwin-sys-net-behavior-2f795ece-20261002/`.
In particular, `proof-evidence/failure.txt`, `resource-samples.jsonl`,
`process-identities.tsv`, `early-runtime-identity.json`, and `export.json` retain
the failure and exact runtime custody. Export reports 0.502 seconds from the
helper-start timestamp through the export timestamp. The complete outer launch
duration is unknown and is not inferred from this value.

The diagnosis is reproduced by a meaningful source regression: a census lists
the helper and its short-lived direct `/bin/ps` observer after the observer has
been waited. The old sampler then tries `process_identity(observer_pid)` and
fails. The correction retains the Popen handle, PID and waited exit status,
checks successful exit and direct-child PPID, and excludes only that observer
PID from the already captured snapshot. Unknown identity for another owned
descendant still raises an error.

## RED and GREEN

- RED: `test_resource_census_excludes_only_its_reaped_ps_observer` failed in the
  old implementation when `process_identity` was called for observer PID 777.
- GREEN: the focused observer test passes and records only the helper's RSS;
  `test_resource_census_still_fails_for_unknown_real_descendant` confirms PID
  888 still fails closed when its identity is unavailable.
- RED: `test_resource_census_interrupt_kills_and_reaps_exact_observer` failed
  before cleanup was added; interrupted `communicate()` left the exact observer
  without terminate/reap cleanup.
- GREEN: the interruption regression verifies terminate, bounded wait, kill
  after timeout, and final bounded reap of that exact child.
- GREEN: `PYTHONDONTWRITEBYTECODE=1 /Users/hoppworks/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 .scratch/all-tickets/test-current-darwin-sys-net-behavior.py`
  passed all 13 source-only categories. `git diff --check` passed.
- These are pure Python/source checks, not native Darwin acceptance. No Rustup,
  Cargo, test binary, VM, native slot, or process fixture was launched.

## Changed files

- `.scratch/all-tickets/check-current-darwin-sys-net-behavior.py`
- `.scratch/all-tickets/test-current-darwin-sys-net-behavior.py`
- `.scratch/all-tickets/current-darwin-sys-net-behavior-2f795ece-sampler2-20261002/run-sys-net-behavior.py`
- `.scratch/all-tickets/current-darwin-sys-net-behavior-2f795ece-sampler2-20261002/contract.md`
- `.scratch/all-tickets/darwin-observer-sampler-repair.md`

The source prep, helper constant, test pin, and contract now agree on the new
unique prospective stage/scope identifier
`current-darwin-sys-net-behavior-2f795ece-sampler2-20261002`. A separate stage
directory is prepared at
`.scratch/all-tickets/current-darwin-sys-net-behavior-2f795ece-sampler2-20261002/`.
Its archive and lock hashes independently match the original frozen inputs.
The staged helper byte-matches the repaired working helper. The staged contract
adds the pinned Python, bytecode, and outer timeout requirements. The three
scoped-runner package hashes remain the staged expected pins.
The original stage was not modified. Stage2 contains the staged archive and launch
inputs and has no proof-evidence or interrupt request. No disposable build scope
was created. Final SHA-256: helper and staged helper `dad67e6e7e434a1333534012fd138e7932592b7b3bdd5355dcc8da94b3736918`; regression suite `b95610130b0b773dae49dbbfcab86d4ebc1f0a9753055e7f19b6192accbbce03`; staged contract `16428e1393c5a04c3935a93cff04f42750590c116356e18a8d4f0e38d0b1b978`.

## Preserved decisions and finite follow-up

This is a distinct sampler infrastructure cause. Preserve cause11's Expert
history and accepted source conclusions at `322ac6be`; neither is reset or
reopened by this correction. The original actual launch count remains 1. This
source-only repair consumed no additional launch. The only observed elapsed span
remains 0.502 s from helper start through export; whole outer duration is unknown.
Original limits remain outer 600 s, helper 540 s, work 510 s, export reserve
30 s, jobs 2,
maximum descendants 16, sampled RSS hard stop 2 GiB, storage preemption 1.5 GiB,
and storage hard stop 2 GiB. No allocations for native84/85 or cause09 work were
made.

Recommendation under the standing acceptance of concrete finite follow-up
recommendations: after one independent review of the changed helper, regression,
stage contract and prospective inputs, dispatch one follow-up Darwin run using
the new exact stage/scope identifier. This would be original launch count 1 plus
one follow-up launch (2 total), with no change to any per-run or cumulative hard
cap. Stop if the sampler still fails to identify a non-observer descendant,
if scope/source pins differ, or any resource/deadline bound is reached. This
recommendation authorizes only that finite Darwin follow-up package; it does not
authorize a process84/85 or cause09 launch.

After review, the next launch command must create the absent exact build scope,
set `TMPDIR` to it, and invoke the staged helper through the staged scoped
runner, for example:

```sh
scope="$HOME/.local/share/agent-builds/rhai/current-darwin-sys-net-behavior-2f795ece-sampler2-20261002"
stage="/Users/hoppworks/.codex/worktrees/current-darwin-sys-net-behavior/rhai/.scratch/all-tickets/current-darwin-sys-net-behavior-2f795ece-sampler2-20261002"
test ! -e "$scope"
mkdir -m 700 "$scope"
PYTHONDONTWRITEBYTECODE=1 DARWIN_PROOF_STAGE="$stage" \
INTERRUPT_REQUEST="$stage/outer-evidence/interrupt.request" TMPDIR="$scope" \
  /Users/hoppworks/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  /Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout 600 -- \
  /Users/hoppworks/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  "$stage/run-sys-net-behavior.py"
```

The scoped runner supplies `AGENT_RUNTIME_DIR`; the helper validates the stage,
runner hashes, lock/archive pins, and runtime ancestry before toolchain use. The
heavy command remains gated on the independent affected review. Preserve the
first launch evidence and export all new receipts to the second stage.
