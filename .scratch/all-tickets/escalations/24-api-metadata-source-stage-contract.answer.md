# Source-stage contract diagnosis

## Verdict

One bounded metadata invocation is justified after one minimal handoff repair: transfer the already verified local `source-full.tar.gz` to the new owned Workhorse scope explicitly as `source.tar.gz`, then check the exact paths consumed by the unchanged `run-recovery-red.sh` before allocating the heavy invocation. Do not rebuild the archive, change the launcher contract, regenerate the lock, add a wrapper, or change product sources to repair these failures.

This is conditional readiness, not executed preflight or metadata acceptance. This review accessed only local evidence and wrote only this answer. No Workhorse access, staging, Cargo, build, or Git command was performed.

## Reasoning and evidence

| Outcome | Immediate defect | Small prelaunch check that catches it |
|---|---|---|
| Allocation 1 | Its archive omitted `build.template`, which `build.rs` requires. Cargo stopped before assertions. | Read the archive at the launcher's exact input path, require the pinned complete-archive hash, and require its `build.template` member. |
| Allocation 2 | `source-full.tar.gz` existed, but `$SESSION_SCOPE/source.tar.gz` did not. `sha256sum` stopped before Cargo. | Check existence and hash of `$SESSION_SCOPE/source.tar.gz`, rather than hashing whichever source-named file was transferred. |

The shared gap is verification of the complete producer-to-consumer handoff. A hash of the correct bytes at a different pathname does not establish launcher readiness. The launcher already binds its input to `$SESSION_SCOPE/source.tar.gz`, the pinned lock to `$SESSION_SCOPE/Cargo.lock`, and extracted source to `$AGENT_RUNTIME_DIR/source`. Its checks happen inside the heavy invocation; moving their input verification into the existing admission command catches both observed errors before that allocation.

Local read-only verification reproduced these facts:

- Complete archive: SHA-256 `a243fc96c513c70d86e0281e0f178d91c95e6338ab3dda24d1656f7dd8863de5`, 422 entries, an exact regular-file `build.template` member, and no absolute or parent-traversing member paths.
- Incomplete archive: SHA-256 `c34c9b889a1e9b4052f9c52b8256d6d7236b92baffdfc26784d1442fdc6381af`, 842 entries, and no `build.template` member. Entry count alone would therefore be misleading.
- Pinned lock: SHA-256 `4ff0a7de6f504510af64092d446d411b86d95228b23a188b396bd188da367627`.
- Existing launcher: SHA-256 `bb0b7b98e0f8f2347d46cdc06f4143b8585a1401111e55876a41d442e814c4dd`.

The cited manifest and current plan preserve the previous per-entry comparison against the worktree. This review verified archive identity and structure, rather than repeating that source-wide comparison. The recorded allocation-2 error and remote inventory independently establish the pathname mismatch. The original staging command is unavailable; neither its contents nor the producer of the observed AppleDouble sidecars can be inferred. Sidecars are not needed to explain either immediate failure.

The public Engine metadata command remains:

```text
cargo test --locked --features testing-environ,sys,net,metadata --test net_metadata --test sys_policy metadata -- --nocapture --test-threads=1
```

Its three named tests and their assertions remain the acceptance target. These runs have reached zero assertions and provide no product RED or acceptance. Package E's runnable examples and OS-effect readback remain separate open criteria.

## Concrete next action

Record this answer under the existing stable cause `api-metadata-source-stage-contract`, preserving two native3 allocations, two infrastructure stops, zero reached assertions and zero product corrections. Treat the following as the single post-escalation follow-up repair, within a 30-minute active-work planning checkpoint and the unchanged run limits.

1. Select an absent, unique owned scope under `/home/workhorse/.local/share/agent-builds/rhai/`. The previous scope has been retired; do not rely on its old identity or admission receipt. Preserve the existing resource lifecycle and exact ownership checks. Transfer the three existing inputs explicitly to `source.tar.gz`, `Cargo.lock`, and `run-recovery-red.sh` in that scope. Preserve the local evidence filename `source-full.tar.gz`. Save the actual transfer command and destination mapping this time.
2. In the existing remote admission shell, bind `SESSION_SCOPE` to that same absolute owned scope and `TMPDIR` to exactly `SESSION_SCOPE`. Leave `AGENT_RUNTIME_DIR` to the existing scoped runner. Verify scope ownership, permissions and resolved path, then run this inline preflight. It is a command fragment, not a new script or wrapper:

```bash
set -Eeuo pipefail
: "${SESSION_SCOPE:?exact owned scope required}"
export SESSION_SCOPE
export TMPDIR="$SESSION_SCOPE"
(
  cd "$SESSION_SCOPE"
  for input in source.tar.gz Cargo.lock run-recovery-red.sh; do
    test -f "$input"
    test -r "$input"
    test ! -L "$input"
  done
  sha256sum --check --strict <<'HASHES'
a243fc96c513c70d86e0281e0f178d91c95e6338ab3dda24d1656f7dd8863de5  source.tar.gz
4ff0a7de6f504510af64092d446d411b86d95228b23a188b396bd188da367627  Cargo.lock
bb0b7b98e0f8f2347d46cdc06f4143b8585a1401111e55876a41d442e814c4dd  run-recovery-red.sh
HASHES
  tar -tzf source.tar.gz | grep -Fx 'build.template'
  bash -n run-recovery-red.sh
)
```

The hash pins the previously verified complete archive, including the regular-file member; the full tar listing check also verifies archive readability and explicit membership. `grep` deliberately has no early-exit `-q`, so the listing is consumed under `pipefail`. Any failure must prevent the allocation and launcher call through checked command status, not merely print a diagnostic. Require this check against the remote staged paths; a local-only check cannot catch allocation 2.

3. Keep the existing toolchain/runner identity checks, including the recorded runner hash `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e` and pinned Rust 1.93.0. Immediately before allocation, freshly check the actual output filesystem and RAM against both 16-GiB reserves, current heavy-work inventory and slot availability, and the owned scope/terminal state. Coordinate with Tauron under existing authorization. The earlier zero-heavy snapshot and expired project concurrency exceptions do not reserve a slot. No foreign process or service may be interrupted.
4. Invoke the same existing bounded launcher once, passing the checked `SESSION_SCOPE` and `TMPDIR` through to the runner child and executing the checked launcher in that scope. Retain 600-second outer, 585-second runner and 540-second helper limits, the 510-second work deadline and 30-second export reserve, two Cargo jobs, 16 descendants, 1,572,864-KiB storage preemption and 2,097,152-KiB sampled storage/RSS caps. Preserve private runtime source/cache/output routing and export original evidence before exact owned cleanup. No artifact exists to reuse.

## Stop and result classification

A failed staged-input preflight means no heavy allocation. Correct only the named transfer/binding repair inside this finite follow-up; repeated failure without new evidence stops the path. A resource or occupied-slot refusal means do not launch; resume only after a relevant fresh admission change.

After launch, another setup, transport, extraction, compiler or guard failure without the intended assertion RED stops this repaired route. Preserve original evidence and counters; do not start another suite, rename this cause or create a second escalation chain. Resource/time stops likewise end the invocation without product acceptance. An unexpected GREEN is not the requested RED and must be reconciled with actual test execution before any implementation.

Only actual failure of the named metadata assertions for the documented missing/inadequate metadata constitutes TDD RED. Inspect exact test output rather than trusting the launcher's marker or exit status alone. Once valid RED is established, the source-stage diagnosis is resolved and the Coordinator may return to the already authorized smallest documentation correction and affected metadata verification under the existing plan. That subsequent product work does not close Package E's remaining criteria automatically.

## Loaded instructions and revision

Re-read the current `/Users/hoppworks/.agents/AGENTS.md`, the project instructions at `/Users/hoppworks/projects/rhai/.worktrees/all-tickets-environment-recovery/AGENTS.md`, `/Users/hoppworks/.agents/skills/campaign/SKILL.md`, and its `references/escalation-brief-template.md`; also read the role table. The checkout root `/Users/hoppworks/projects/rhai/AGENTS.md` is absent; the cited worktree's project instructions are present and were applied.

Central agent-skills HEAD was read directly from `.git/HEAD` and `refs/heads/main`, without a Git command: `14617043b70d1ba2d40b720832cbad294fa8c008`. The global instructions and campaign skill symlinks resolve into that central checkout. This is the loaded revision for this diagnosis; other Sessions' loaded revisions remain unverified.
