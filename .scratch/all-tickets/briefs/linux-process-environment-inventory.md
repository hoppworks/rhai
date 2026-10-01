# Native Linux process acceptance environment inventory

Role: Worker. Read-only bounded task, no implementation or native launch.

## Requirement
Identify the previously accepted Linux transport, process/runtime custody and toolchain inputs that can be reused to prove the immutable Unix process candidate on native Linux. Report exact paths, current acceptance applicability and the next source-only preparation action. Do not invent a substitute environment or weaken native acceptance.

## Context by reference
- Root state: /Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/coordinator-state.md
- Existing briefs: .scratch/all-tickets/briefs/native-linux-io-proof.md, linux-optional-msrv-proof.md, linux-sys-release-features.md
- Existing reviews: .scratch/all-tickets/native-linux-io-proof-review.md, linux-optional-msrv-proof-review.md, linux-sys-followup-proof-review.md
- Candidate: /Users/hoppworks/projects/rhai-process-unix-run, immutable af18bb36a1cbe03563d67abebd1ee8a836922df4; mutable new tests remain owned by process_unix_run and are not frozen.
- Local ticket03/release acceptance: .scratch/stdlib-wayfinder/issues/03-process-contract.md and release decisions referenced by the root state.

## Scope and constraints
Read local files/Git only. No remote connections, VM controls, builds, package/install commands, agent-home/config/login changes, credentials, file edits, pushes or merges. Preserve foreign worktrees. Do not print secrets. Existing transport/toolchain details are evidence of prior availability only, not live availability. No fresh machine inventory or new Expert chain. Work within a 10-minute planning checkpoint; no native resource allocation.

## Deliverable
Reply in at most 15 lines: exact reusable transport/custody/script/toolchain/lock paths and accepted refs, critical differences for production process proofs, unresolved dependencies, and one concrete next preparation action. Completion means the source-only route is grounded in accepted artifact paths, not that Linux is live or process behavior is proven.
