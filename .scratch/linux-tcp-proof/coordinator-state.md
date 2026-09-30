# Coordinator state: linux-tcp-proof

## Goal
Prove the integrated public TCP API on native Linux for the baseline, sync, and no_index feature sets using actual OS peers and independent byte readback.

## Done when
All requested net integration targets pass serially in one remote scoped build, a wrong peer-byte assertion fails and the restored assertion passes, all result logs and runtime cleanup are independently read back, and an immutable proof commit is handed to root.

## Steps
1. Native Linux matrix — done when net, net+sync, and net+no_index each pass net_connect, net_listen, net_reads, and net_writes on workhorse with logs.
2. Assertion control and cleanup — done when wrong expected byte fails at the actual-peer assertion, restored expected bytes pass, and remote process/runtime cleanup is confirmed.
3. Proof handoff — done when evidence is committed with exact lowercase hoppworks author/committer and handed to root by the brief deadline.

## Done steps

- [x] 1 Native Linux matrix — ref: `2e945d9f3547a45e73e0fa8a8913847aec58cf1d` — verified: 12 serial Cargo integration-target runs passed under native Linux for net/net+sync/net+no_index; canonical output and statuses retained in `.scratch/linux-tcp-proof/`.
- [x] 2 Assertion control and cleanup — ref: `.scratch/linux-tcp-proof/proof.md` — verified: actual peer byte control failed at the wrong expected byte, restored expectation passed, sampled limits were within bounds, and exact runner/runtime absence was read back.
- [x] 3 Proof handoff — ref: this proof commit — verified: proof files committed as exact lowercase `hoppworks` author and committer; no push or merge.

## Accepted evidence
- Existing macOS TCP reviews and proofs in `.scratch/all-tickets/*-review.md` and sibling proof directories provide source/check context only; they do not prove Linux runtime behavior.
- `.scratch/linux-tcp-proof/proof.md` and `native-linux-tcp.log` cover only this exact Linux source/environment/feature slice; first harness diagnostic is retained separately.

## Retained resources
- Local proof records under `.scratch/linux-tcp-proof/` are committed. Exact remote stage `/root/rhai-linux-tcp-proof-task/2e945d9f/` was removed after export; parent historical staging directory was preserved.

## Cause history
- Harness matcher cause: first run passed the matrix and produced expected exit 101, but checker expected `... FAILED` inline while Rust emitted a separate `FAILED` line. One bounded matcher correction; second run passed. No implementation correction or infrastructure recovery.

## Current step
none — campaign done.

## Open escalations
- None.

## Decisions
- Original allowance 15:38–16:08 UTC inclusive root review; handoff by 16:01 UTC. No extension/reset.
- Exact owned branch `task/linux-tcp-proof` at base `2e945d9f3547a45e73e0fa8a8913847aec58cf1d`; source checkout was clean.
- Workhorse read-only probe succeeded (Linux 7.2.4, Rust/Cargo 1.97.1); fresh exact remote staging path `/root/rhai-linux-tcp-proof-task/2e945d9f` was absent. The configured runner must be copied there and invoked remotely so it owns the Linux process group and runtime.
- Budgets: private source + Cargo home + target <= 2 GiB sampled disk; max 16 owned sockets/handles; Cargo jobs=2; remote scoped invocation <=900s; original deadline includes staging, build, transfer, cleanup and review.
- Commit attribution must be author and committer `hoppworks` (lowercase), configured email retained; no push or merge.

## Next action
Hand root the immutable proof commit, evidence paths, and explicitly unverified release coverage.

## Retrospective
The first run demonstrated why the false-green result alone was insufficient: the independent byte assertion failed correctly, but the checker required the wrong output shape. Inspecting the retained log exposed the matcher issue; one bounded correction made the same control's exact evidence check and restored pass succeed. The 12 matrix targets ran once in the canonical invocation. The plan did not change.
