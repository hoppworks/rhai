# Ticket 03 stdin closure — rejected run-path attempt

**Disposition: REJECTED; no product defect or acceptance is established by this packet.** The packet tested the wrong public owner. It remains preserved as cause and budget history; its RED/GREEN results are not Ticket 03 acceptance.

The direct `run`/`run_raw` supervisor is required to retain a pending-input `BrokenPipe` as `SysError::Process` with operation `write process stdin`, then perform owned cleanup. The accepted API-seam decision identifies the genuine missing behavior in public `spawn`/shared `Child`: its spawned-owner pump discards `BrokenPipe` and reports input complete. See `.scratch/all-tickets/escalations/16-stdin-api-seam.answer.md` §§1–5 and `.scratch/stdlib-wayfinder/issues/03-process-contract.md` §§86–90, 143–154.

Attempt02 therefore recorded expected direct-run behavior, not a product failure: `BrokenPipe` at `write process stdin`, followed by the supervisor's cleanup path. Attempts03–05 inverted that required behavior and passed the resulting test, so their RED/GREEN and the temporary production patch are explicitly withdrawn. The temporary `BrokenPipe` and zero-byte-write handling in `src/packages/sys/process/unix.rs` and the corresponding success-expectation test in `tests/sys_process.rs` were removed; neither file has a remaining diff from this work. Zero-byte/WriteZero is a separate open requirement and was not verified here.

## Review

The combined two-axis review is in `combined-review.md`. Standards accepted the localized shape; Spec rejected it against the accepted seam. Spec's rejection controls the disposition. The packet's strong run binding (Workhorse Linux x86_64, Rust/Cargo 1.77.2, `testing-environ,sys`, accepted lock) establishes what was executed, not whether the expectation was correct.

## Preserved attempt history

- Attempt01: malformed SSH preflight first stopped before Cargo. A later exact test run failed before its deliberate assertion because the required run-path error was returned. The wrapper misclassified that result.
- Attempt02: one malformed awk preflight stopped before Cargo; the corrected diagnostic invocation confirmed `BrokenPipe` / `write process stdin` on the direct run path. This is expected behavior under the accepted contract.
- Attempt03: on the temporary, now-withdrawn change, the wrong-success expectation produced RED 101 and then GREEN 0. This is an invalid acceptance oracle.
- Attempt04: the same temporary change was exercised with five selectors. Its run-path selector is invalid for the same reason. The other four selector outcomes are historical diagnostics only and are not asserted as this packet's acceptance.
- Attempt05: both `run` and `run_raw` were tested against the same wrong success expectation; RED 101 and GREEN 0 prove the test's sensitivity to the required behavior, not a defect fix.

All five Workhorse scopes were owned, bounded, SHA-read back, exported, and retired; their individual identities and cleanup receipts remain in the attempt folders. Foreign Tauron work, the Windows guest, and other session resources were preserved. No reusable target cache remains. Preserve all logs and hashes; do not repeat these direct-run executions to reconsider the settled API mapping.

## Next authorized work

Correct the still-open spawn-owner test and its consuming classifier/recipe in one source-only package, following accepted Expert17 and Expert18 answers. Production stays unchanged until a genuine native spawn-owner RED. The current source must first pass the source-derived receipt/schema and actual classifier checks, then receive one affected independent review. Only after that may a fresh native execution be considered under current resource/custody checks. This packet allocates no native run and does not close the Ticket 03 stdin requirement.
