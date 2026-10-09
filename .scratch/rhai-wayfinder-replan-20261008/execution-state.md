# Current coordinator state

Updated 2026-10-09. Owner-authorized A–F implementation continues; no new Goal.

**Next action:** Repair the Ticket 03 stdin regression at the accepted public `spawn`/shared-`Child` seam. Keep production unchanged. Update the test/fixture and its consuming receipt/classifier according to the accepted Expert17 and Expert18 decisions, then prove the source-derived schema and actual classifier with bounded source-only checks. Get one affected independent review. Only a genuine native baseline RED may authorize a production correction or a later bounded Workhorse run; verify live resources and custody at that time. Do not repeat the invalid `run`/`run_raw` attempts in `results/linux-stdin-early-close-20261009T2021Z/`.

The attempted direct-run fix was rejected by combined review and removed. The accepted contract requires direct `run`/`run_raw` to retain pending-input `BrokenPipe` as `Io` / `write process stdin`; the missing behavior belongs to public `spawn`/shared `Child`, whose owner currently discards `BrokenPipe`. The prior `Ok(0)` change was also unsupported and remains a separate open WriteZero requirement. Review details and preserved attempt causes are in the linked packet. This does not close Ticket 03 or A–F.

## Current rule sources

- Project `AGENTS.md` SHA-256 `37f95ff6a80be28bc21e9e523674f46f3ce6153a1923c708b86333bf21bba37c`.
- `~/.agents/AGENTS.md` is absent; do not claim other sessions share a loaded revision.
- `build-efficiently` SHA-256 `58f676b48691ea2ed476f67f13ef68aedcdb73cd4cabf13925db1927c9ccaf04`; `code-review` `09eb147f793e4647949edd32dbad278f0554dfb56e0d46b699cd4c2c55bf0357`; TDD `5505d25bbaa8fc14a79e4d20163936958992a2995b7f1dd1d6197edc9ed722e0`.
- Memory index SHA-256 `6119ac79bb299052f8fc124465ab8a97da7e62c978f6c66dea5e3ba32aa53409`; no Rhai-specific memory entry applies.
- Both review agents reloaded these current sources before review. They are complete; no active subagent is awaiting an instruction. The global entrypoint absence is not an authorization to synchronize or install skills.

## Accepted evidence and remaining scope

- Fork `main` was last read back at `ff3b25b0889c32e0e505517fc605d4b6cd2d5208`; it was the sole remote branch. Push only verified work to `https://github.com/hoppworks/rhai.git` `main`; never write to public upstream. Commit author and committer must be exactly lowercase `hoppworks`, configured email retained.
- The integrated Linux real-OS slice at that revision accepted 11 targets (165 passed, 0 failed, 3 ignored): `results/linux-integrated-e2e-20261009T1803Z-ff3b25b08/`.
- The combined Workhorse Linux process-lifecycle review accepts only twelve named selectors at their exact shared inputs: `results/linux-process-completion-capture-20261009T1915Z/` plus its three linked packets. X24 and other platform/profile evidence remain limited to their named rows.
- X24, X31, prior Unix/Windows custody and all other accepted evidence remain reusable only when their exact source, test, lock, feature, toolchain and environment bindings apply. Histories and consumed attempts stay in result packets and `history/`; do not repeat them for a new session.
- Ticket 03 remains open for spawn-owner pending-input errors, cleanup/capture/cache behavior and remaining platform/profile coverage. Native Windows Cargo remains gated on its custody contract. The full A–F package, other platform/MSRV rows and release acceptance remain open.

## Boundaries and resource custody

Use Workhorse via SSH when native Linux work is authorized by its current source/custody gates. Preserve foreign Tauron activity, the Windows guest, foreign worktrees, and all other session fixtures. Do not revive old run-slot counts, process identities, model assignments or expired exceptions from memory; consult current instructions, live capacity and exact ownership. For POSIX builds use the project-scoped runner, a new owned session scope under `~/.local/share/agent-builds/rhai/`, absolute `TMPDIR`, and Cargo target/home under the runner-provided `AGENT_RUNTIME_DIR`; export evidence before retiring only that exact empty scope.

The five invalid stdin attempts and their consumed work are preserved in the result packet; their launch/preflight errors are separated from the valid run-path `BrokenPipe` observation. The full prior coordinator state is preserved at `history/execution-state-before-stdin-review-20261009.md`. `.worktrees/` remains foreign/untracked and unstaged.
