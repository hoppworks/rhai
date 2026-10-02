Source is **not ready for the existing finite native controls**: the new outer runner introduces one high-severity custody finding. The previously accepted four source closures remain valid; this range does not change their adapter, reader, observer-overlay or measurement implementation.

Confirmed the current instruction repository revision is `958a4538b0191c53f2ccb2cd00d96c15045fbf68`. I read current global/project `AGENTS.md`, `ocr-delegate`, `config/roles.toml`, and both Codex Expert templates. This is the requested combined independent review, not another cause-09 escalation.

Review range:

- Baseline: `5ed13c10a341250755372bf03445f0b597294848`
- Target: `7e8183a6b416c481fe7d165d4dbe834f1ff3e93c`

OCR preview failed because sandbox-denied macOS Git cache diagnostics contaminated its revision output. I stopped that flow without retrying and inspected the immutable diff using the installed Command Line Tools Git binary. OCR-selected files and resolved rule groups are therefore unavailable; coverage below uses the actual immutable changed-file list.

**High — forced escalation destroys the custody chain**

| Field | Value |
|---|---|
| Path | `.scratch/all-tickets/run-macos-overhead-scoped-runner.py` |
| Lines | 35–52; timeout caller at 109–118 |
| Category | Bug |
| Severity | High |

At the 585-second soft deadline, the runner sends TERM, waits approximately 14 seconds, then unconditionally sends KILL to its registered direct child and reserves the remaining second for reaping. This establishes bounded supervision of that child, but not preservation or closure of its descendants.

The wrapper supplies two different kinds of child:

- **Normal mode:** the child is the adapter itself. Killing it destroys the sole owner of the gate, anchor, command and client handles. Anchored groups can remain independently live; the anchor deliberately ignores TERM. The outer runner has no custody transfer or independent descendant-closure mechanism.
- **Control mode:** the child is the control-package controller, whose adapter is a grandchild of the outer runner. The controller can spend its own cancellation window waiting until approximately 600 seconds. The outer runner can kill it around 599 seconds, before that window finishes, destroying the only registered parent handle for the adapter.

Reaping either child does not prove workload closure. The wrapper correctly returns failure and retains a nonempty runtime, so this is not a false acceptance result. However, retained files and a ledger do not preserve live signal/reaping authority. The `outer_child_reap_unconfirmed` diagnostic also appears only when the outer child remains unreaped; successful forced reaping can lose descendant custody without that diagnostic.

The new mocked timeout test explicitly expects KILL followed by successful direct-child reaping and status 124. It therefore does not challenge this integration failure.

Before source acceptance, the shutdown design must preserve the actual custodian through uncertain closure, or provide reviewed custody handoff covering the remaining owned processes. It must distinguish **direct child reaped** from **workload custody closed**, without broad group signaling or census-PID signaling.

Other reviewed conclusions:

| Area | Assessment |
|---|---|
| Registration/unmask race | Parent interruption is blocked before `Popen`; the child handle is assigned before restoring the mask inside the protected `try`. Pending-signal delivery during that restore reaches cleanup with the registered handle. Source structure addresses the parent-side race; native delivery remains unverified. |
| 585/600 budgets | Wait arguments reserve time for escalation/reaping, but the control controller’s own 600-second deadline overlaps the outer runner’s shutdown window. Synchronous spawn, filesystem and OS calls also prevent these calculations from being an absolute wall-clock guarantee. |
| Timeout/errors | Nonzero results and retained runtime prevent acceptance on uncertainty. They do not establish descendant closure after forced killing. |
| External outer SIGKILL | No handler or `finally` can run. Exact later ownership/readback inspection is required; neither automatic cleanup nor whole-tree termination is proven. |
| Scope/environment | The runner preserves the wrapper’s unique central scope and exact `scope/tmp` environment. It avoids the global runner’s nested temporary-directory replacement and group teardown. Existing build environment code retains private HOME, Cargo/Rustup caches, target and temporary outputs. |
| Output lifecycle | Evidence remains outside disposable runtime; runtime deletion remains adapter-controlled and identity-checked. Wrapper cleanup uses exact empty-directory removal. Forced escalation leaves closure incomplete rather than authorizing deletion. |
| Provenance/authorization | The declared global-runner SHA-256 matches the current file: `9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d`. The project explicitly authorizes this narrow local adaptation and requires independent review before execution. |

I read the actual immutable `source-green-94.log`: it records **94 tests, OK**, plus `runner_ast=ok`. I also read all four newly added RED/targeted GREEN logs. These are source/mock evidence, not native signal, ABI, wait, process-list, escaped-leaf or runtime-cleanup proof. I did not rerun tests. The immutable range’s whitespace check passed.

Coverage:

| Changed files | Reviewed | Skipped | Coverage |
|---:|---:|---:|---:|
| 10 | 10 | 0 | 100% |

This covers the runner, wrapper, readiness record, control contract, pure tests and five evidence logs.

After the source custody finding is corrected, the remaining native prerequisite is unchanged: the existing finite package must prove actual Darwin registration/signal behavior, wait/list ABI behavior, setup/build interruption, unfinished Managed dual-stream capture, deadline cleanup, exact direct-child reaping, complete escaped-leaf/group absence and runtime removal. Its child-interruption cases alone do not establish whole-runner interruption custody; that project requirement still needs applicable native evidence within the existing bounded contract. Pure tests, source audits and retained files are not substitutes.

No builds, Cargo, native controls, workload descendants, edits, installs or configuration changes were performed. No review file was written. Foreign dirty work and assets were untouched. Cause-09 history, count **84**, measurement **85 unlaunched**, four controls **unallocated**, and the **false launch guard** remain unchanged. The local coordinator snapshot contains older counts; I have not used it to override the current user-supplied state.