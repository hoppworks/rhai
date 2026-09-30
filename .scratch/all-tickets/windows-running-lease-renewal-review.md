# Running lease renewal source review

Candidate `43d2f067` in the owned Windows scoped-runner worktree was independently
reviewed across all three changed files: LeaseMonitor.cs, README.md, and the
OCR-excluded LeaseProtocolFixture.cs. Zero skipped; 100% source review. Default
correctness, security, resource and coverage rules apply. Whitespace checks pass.

Running can now issue fresh outstanding challenges. Accepted responses renew
only the capped short lease, do not set create/resume handshakes, and preserve
phase/sequence/nonce validation, single consumption and terminal Stopping.
The authored renewal timeline explicitly accepts each response and checks Running
through t29, beyond initial lease t8 and setup t12, before absolute expiry t30.
The revised exact-boundary fixture aligns lease and challenge expiry t12 and
checks Running at t11 then rejection/Stopping at t12. Invalid sequence/nonce and
old create/resume responses cannot consume the current valid renewal; replay,
blackholed client and post-Stopping response cases are present.

No source findings remain for this bounded correction. Compilation, authored
fixture execution, TDD RED/GREEN, transport/native behavior and full process/job
acceptance remain unverified. No workload launch or exact-job proof is enabled.
This is a substep of the existing incomplete custody correction, not a separate
completed native correction attempt.
