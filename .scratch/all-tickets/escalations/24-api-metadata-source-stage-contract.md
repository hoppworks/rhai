# Escalation 24: api-metadata-source-stage-contract

## Question
For Package E's open public Engine metadata criterion, identify the smallest reliable check across the existing archive, Workhorse staging path, and `run-recovery-red.sh` input contract that would have caught both pre-Cargo failures before a heavy launch. Recommend one concrete repair and preflight using the existing bounded launcher, without an added wrapper layer or a product-source change. State whether the next bounded metadata invocation is justified after that repair and what result would stop this path.

## Why escalated
- Two Workhorse recoveries in the same unverified source-input handoff stopped before Cargo and before every assertion: allocation 1 had an incomplete source archive; allocation 2 had the complete archive staged under a name the launcher does not read.
- The immediate allocation-2 error proves `run-recovery-red.sh` required `source.tar.gz`, while the exact remote scope contained only `source-full.tar.gz`.
- The full archive's 422 entries and hashes are already verified; rebuilding it or rerunning Cargo to diagnose transport would add no evidence.
- The complete transfer-to-launch path was not tested for exact staged names and contents before allocation. Treat the two observed immediate errors separately while assessing this shared handoff gap; do not infer the unsaved staging command or the source of the observed AppleDouble sidecars.

## Context by reference
- `docs/sys-package-plan.md`, Package E row and current next-action section
- `.scratch/all-tickets/coordinator-state.md`, current Package E step and attempt history
- `.scratch/all-tickets/api-metadata-evidence/native3-20261007/native3-infrastructure-failure.json`
- `.scratch/all-tickets/api-metadata-evidence/native3-20261007/native3-source-manifest.txt`
- `.scratch/all-tickets/api-metadata-evidence/native3-20261007/source-full.tar.gz`
- `.scratch/all-tickets/api-metadata-evidence/native3-20261007/run-recovery-red.sh`
- `.scratch/all-tickets/api-metadata-evidence/native3-20261007/attempt-02/classification.json`
- `.scratch/all-tickets/api-metadata-evidence/native3-20261007/attempt-02/outer.log`
- `.scratch/all-tickets/api-metadata-evidence/native3-20261007/attempt-02/outer.status`
- `.scratch/all-tickets/api-metadata-evidence/native3-20261007/attempt-02/remote-readback.txt`
- `/Users/hoppworks/.agents/AGENTS.md`, project `AGENTS.md`, and `/Users/hoppworks/.agents/skills/campaign/SKILL.md`

## Constraints and decisions
- Preserve the open metadata requirement and the actual command/tests in `docs/sys-package-plan.md`; no product implementation is justified until valid assertion RED.
- Keep the existing `run_scoped.py` path, exact scope, private runtime/cache routing, and existing limits: 600/585/540 seconds, two Cargo jobs, 16 descendants, 1,572,864 KiB storage preemption, 2,097,152 KiB sampled RSS/storage caps, 16 GiB admission reserves, and fresh heavy-slot checks.
- Do not interrupt Tauron or other Workhorse work, change shared services, add a general wrapper/runner, reset retry history, or start a build from this Expert review.
- The latest readback verified the Rhai run is terminal and its exact owned scope has been removed. Any later Workhorse allocation requires a new measured admission and slot coordination.
- The owner authorized ordinary implementation/tests and requested an atomic commit and push; Git changes are outside this diagnostic brief and may target only the authorized `hoppworks/rhai` fork.

## Tried so far
- Stable cause: `api-metadata-source-stage-contract` (the source-input handoff contract; immediate defects remain distinct).
- Allocation 1: incomplete source archive omitted tracked `build.template`, required by `build.rs` -> infrastructure before assertions; allocation 1, assertions 0, product corrections 0; `.scratch/all-tickets/api-metadata-evidence/native3-20261007/native3-infrastructure-failure.json`.
- Allocation 2: complete archive SHA-256 `a243fc96c513c70d86e0281e0f178d91c95e6338ab3dda24d1656f7dd8863de5` was staged as `source-full.tar.gz`; launcher expects `source.tar.gz` -> `sha256sum` exited 1 before Cargo; allocation 2, assertions 0, product corrections 0; evidence under `attempt-02/`.
- The allocation-2 private runtime is absent; after local export/hash verification, only the exact owned scope files were removed and the scope was verified absent. No compiled artifact exists to reuse.
- Prior Expert21 addressed API assertions/documentation and is not reopened by this staging diagnosis.

## Deliverable
- Write the full answer to: `.scratch/all-tickets/escalations/24-api-metadata-source-stage-contract.answer.md`
- Format: verdict first, then reasoning, then the concrete next action for the Coordinator to take.
- Return to the Coordinator at most 15 lines plus this path — the reasoning stays in the file.

## Budget
Use the configured Expert role from `config/roles.toml`; complete a read-only review of the cited path and one concise repair recommendation, then stop. Do not run Cargo, access Workhorse, stage files, edit product/tests/runner, or create another wrapper.
