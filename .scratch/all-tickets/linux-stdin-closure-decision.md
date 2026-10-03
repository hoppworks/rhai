# Early child stdin closure decision

Recommend retaining an actual write BrokenPipe while supplied input remains as the primary input I/O cause, unless a primary terminal cause was already committed. Treating it as successful input completion contradicts the accepted ticket03 matrix's explicit “input error retained” observation. A child closing stdin is not itself an error if no supplied bytes remain or no write fails; successful EOF delivery and ordinary nonzero exit remain their existing outcomes.

Sources: `.scratch/stdlib-wayfinder/issues/03-process-contract.md:62–89` requires concurrent bounded transfer, closing stdin after supplied bytes, first committed cause preservation and owned cleanup for post-spawn I/O failure; its test-first matrix at153 explicitly requires EOF observation, retained input error and no orphaned writer/unreaped child. The spawned Child owner at `src/packages/sys/process/unix.rs:491–519` currently overwrites stdin_offset with input length on BrokenPipe and discards the error. `process_io_cause` at779 already represents the operation, target, ErrorKind and message. `.scratch/all-tickets/linux-managed-lifecycle-next.md:33–41` correctly identifies the gap but its contract-owner-question gate is an agent-authored proposal, not a human scope restriction. The accepted requirements support this recommendation without weakening the matrix.

## Implementation and real-OS acceptance scope

Use the existing non-BrokenPipe error path: record `process_io_cause("write child stdin", …)` only if no primary cause exists, close stdin, request owned termination, then finish bounded capture and exact child/group cleanup. Keep actual progress truthful rather than marking unsent bytes transferred. Preserve earlier deadline/OutputLimit causes and secondary cleanup diagnostics. Review Ok(0) with pending bytes alongside this change: a zero-length successful write cannot truthfully mean full transfer; a WriteZero cause is the analogous outcome. No API enum expansion is needed for the Unix BrokenPipe path.

Start with a self-reexec fixture reached through public Engine spawn and bounded Child.wait. Retain cloned handles and separate the first wait outcome from explicit cleanup. Supply bounded input larger than the recorded actual Linux pipe capacity; the fixture never reads input. Independently verify the live exact PID/start/owned group and acknowledge readiness. Emit and flush both fixed capture markers plus closure intent before closing actual fd0. Do not require any child-authored publication after closure: correct input-error termination may already have killed it.

The known-broken baseline must yield unit from the first bounded wait, with the same live non-zombie identity verified before and after independently observing `/proc/<pid>/fd/0` absent. Then explicitly kill through the public Child handle and save a separate bounded cleanup report. Reap the owned child, prove group absence and preserve live host/sentinel identity before the nominated missing-Io assertion. GREEN must instead return retained BrokenPipe with operation `write child stdin` without an explicit kill needed to obtain it; repeat observations through cloned handles must preserve the error/report. Record truthful capture flags, actual bounded markers and timed_out=false. Guards and the external bounded host retain ownership on unexpected outcomes; fixture watchdog participation is not accepted product evidence. Detailed choreography and limits are in `escalations/16-stdin-api-seam.answer.md`.

Retain the existing successful input/EOF and blocked-stdin deadline cases as affected regressions. Add a separate child-read-all case if existing EOF evidence is insufficient; the closure fixture alone does not prove normal EOF. The spawn input test covers this real post-spawn I/O failure seam, not worker-start failure or every fault class. Keep a separate public run_raw positive regression: its existing synchronous owner already retains BrokenPipe as `write process stdin`, with truthful capture flags. A different operation-name assertion is not a meaningful missing-error RED. Pending-byte Ok(0)/WriteZero remains a separate open branch until its own meaningful evidence exists. Reader-side EPIPE challenge in the escaped output-pipe test is a different direction and supplies no proof of parent stdin failure. Supplementary injection may verify other fault branches but cannot replace this real-OS acceptance.

## Successful cleanup map and exceptional observations

Expert17 verified the actual bounded Child.wait success map: text stdout/stderr,
boolean success/timed_out/capture flags, and required code/signal keys holding an
integer or unit. It exposes neither raw Blob captures nor cleanup_diagnostics.
Baseline explicit cleanup must decode those exact fields and retain provenance;
ASCII marker bytes derived from text are UTF-8-derived, not original raw capture.
Diagnostics are unavailable through this successful map, not an observed zero.
Require a terminal success map with available exit, truthful flags, timed_out=false,
bounded markers, and separately verified exact custody. Typed GREEN continues to
compare real ProcessReport raw bytes/flags/cause/exit/diagnostics across all waits.
This corrects a review schema assumption, not the product's retained-error contract.

Save original API/OS observations before fallible decoding. Only a checked
Ok(None) from actual NotFound proves PID absence; permission/read/parse errors,
missing original identity and reused identity remain incomplete. Probe only a
validated owned group and accept exact ESRCH. Exceptional cleanup distinguishes
terminal typed error from unit; resource retirement and API terminal classification
are separate facts. Bound sentinel reap and preserve its original identity,
kill/wait results, host readback and partial evidence without masking the original
failure. No fixture convenience API or guessed raw signals are authorized.
Details and single bounded follow-up: escalations/17-stdin-fixture-extraction-guard-receipt.answer.md.

## Compatibility and limits

This intentionally changes successful results for commands that stop reading before consuming supplied input into input errors. Programs accepting a prefix (for example an early-exiting filter) are the concrete compatibility risk; document the all-supplied-input contract and preserve unrelated normal-exit behavior. Avoid asserting cross-event ordering: if another terminal cause was committed first, retain it. Empty input, full transfer before closure and nondeterministic ordinary early exits must not be unconditionally rejected. Windows needs its own native write-error mapping and acceptance; no Linux result closes that platform. Source implementation, compilation and native acceptance are still pending. This decision is independent of prior repair causes and does not renew any exhausted chain.


## API-path correction history

The initial run-based fixture and SOURCE READY assessment at c4 were withdrawn before native allocation: they traced the spawned-owner swallow branch as though public run used it. Root found the contradiction, the original reviewer confirmed it, and fresh Expert16 independently mapped both owners. Rejected c39 recipes and the review withdrawal remain preserved. No native RED, product correction or baseline timeout was established by those preparation revisions. The retained-error requirement and prior accepted evidence are unchanged.
