# Process prototype proof review

## Decision

Do not accept commit `35a8cf52b5453ead3271f9d643472c27cb2dff3a` as completion of the process-mechanism gate. Preserve its logs as historical native macOS observations. The five escalated concerns are supported by the source. A corrected bounded run is necessary before accepting simultaneous I/O, exceptional cleanup, or a safely supervised harness. No prototype code was changed and no fixture was executed during this review.

Reviewed references: `.scratch/process-prototype/src/main.rs`, `run-scoped.sh`, `Cargo.toml`, `README.md`, and both evidence logs in `/Users/hoppworks/projects/rhai-process-prototype`; the acceptance contract in `/Users/hoppworks/projects/rhai-all-tickets/.scratch/stdlib-wayfinder/issues/03-process-contract.md`; and `/Users/hoppworks/projects/agent-skills/tools/run_scoped.py`. The prototype worktree was clean and its HEAD matched the specified commit. OCR selected three code files; all three were reviewed (3/3, no skips). Its three excluded prose/log files were also read for claim validation.

## Validated findings

| Severity | Location | Finding and consequence |
| --- | --- | --- |
| High | `src/main.rs:85–91` | `read_to_end` finishes before either output write starts. Concurrent parent threads do not create simultaneous bidirectional backpressure. Exact 2 MiB round-trip capture is observed; the simultaneous-I/O requirement is unproved. |
| High | `src/main.rs:95–99`, `112–194` | Fixture children are created before any cleanup owner exists; the escapee handle is forgotten. Readiness/parse assertions, `fcntl` assertions, worker-start failure, join failure, or wait failure can bypass explicit cleanup. Ordinary `Child` and `JoinHandle` drops supply no termination/join path here. The sentinel is also unguarded. Both direct fixtures and escapees have separate process groups, so the scoped runner cannot clean them by terminating its own group. |
| High | `src/main.rs:181–183` | Successful `try_wait` has already reaped the group leader. Its numeric PID is subsequently used as a group identity. In this case the only descendant is in a different group, so there is no retained group member anchoring the original identity. A successful historical run does not establish safe future signaling. Checking with signal zero first would still leave a check/use race. |
| High | `run-scoped.sh:13` | POSIX `sh` reports the pipeline's final command status. `set -e` does not make a failing prototype followed by successful `tee` fail the script. The later negative control can then succeed as a test of failure, masking the earlier failure. The logged pass marker supports this particular historical success, but the wrapper is not a reliable acceptance gate. |
| High | README invocation; `src/main.rs:125–126`, `156–157`, `185–186` | The runner's optional timeout is omitted. Readiness polling has deadlines, but `wait` and `join` remain unbounded. Measuring elapsed time after those operations returns is an assertion, not a watchdog. Adding only `run_scoped.py --timeout` would bound the wrapper while leaving separate-group fixtures outside its cleanup scope. |

The existing wrong-expectation control occurs after all nominal cleanup (`main.rs:196–197`). It proves that one record assertion can fail; it does not exercise cleanup following a failure while resources are live. The log does not show an exceptional-path cleanup proof. PID disappearance checks also are not evidence that the harness itself reaped a grandchild: the fixture forgot its handle and the harness is not its parent.

## Smallest correction plan

Keep this a standalone OS seam prototype. Do not add the production Rhai API, output-limit policy, or a dependency evaluation to this correction.

1. **Make ownership safe before rerunning.** Install an owner immediately at each successful spawn, before pipe setup or assertions. It retains the unreaped `Child`, worker handles and stop tokens, and has an explicit cleanup path that records termination, worker completion and reaping before assertions are reported. Cleanup must continue if one operation fails; a destructor must not panic during unwinding. Preserve failures rather than treating every negative liveness probe as successful cleanup.

   For the smallest pipe-cancellation fixture, replace the forgotten grandchild with a harness-owned independent pipe-holder: construct owned output pipes, give duplicate write ends to the workload and holder, and retain the holder's `Child`. Keep that holder and the sentinel in the runner's group. This proves retained-pipe cancellation while allowing exact termination and reaping by the harness. Describe it as an independent pipe-holder; it does not newly prove descendant ancestry or escape behavior. The old escape observation can remain historical evidence. If actual escaped-descendant ancestry is retained instead, supply a separate retained fixture owner and a shutdown/lease protocol established before the escapee can run, including cleanup when readiness reporting fails. A parsed PID plus a late guard is insufficient.

2. **Separate pipe cancellation after exit from group closure.** In the post-exit retained-pipe case, remove the group signal after `try_wait` and cancel the I/O workers directly. Reap the direct child and owned holder, and report this as post-exit I/O cancellation only. Active cancellation may signal the unreaped owned group leader before reaping. Proving managed-scope closure after normal exit remains a separate gate: retain a valid scope identity through observation and signaling, using a validated non-reaping exit observation or a live scope guardian. Do not re-label cancellation of readers as managed-scope cleanup, and never signal a previously reaped group ID.

3. **Make the stream fixture require overlap.** Read and echo bounded chunks to both outputs before reading the rest of stdin. Use a payload large enough to encounter pipe backpressure and an explicit protocol gate: the parent must receive a child-written output record before supplying the final input segment/EOF. Record byte counts or checksums for independently known, preferably distinct, stdout/stderr patterns. Assert exact capture and successful exit. This distinguishes real overlap from the old read-all-then-write fixture without a scheduler-sensitive timing assertion. Keep readiness parsing line-complete rather than accepting a partially received marker.

4. **Bound execution and cleanup together.** Add `--timeout` to the scoped invocation, but also supply fixture supervision that survives harness failure and accounts for every group created outside the runner group. A fixture lease/control-pipe shutdown plus an independently enforced lifetime, or an owned supervisor that anchors and closes its private group, can provide that fallback; validate the selected method before running it. A main-thread RAII guard alone does not cover the runner killing the harness, and the runner alone does not cover private groups. Give each case a deadline covering input, child execution, output collection and joins, with diagnostic records identifying the exact owned resources. On expiry request stop, terminate only still-owned identities, and complete/read back cleanup. Do not rely on a post-join elapsed assertion.

5. **Preserve the actual exit status.** Replace `binary | tee` with execution redirected to a scoped log, capture its status explicitly, then print/export the log and fail on a nonzero passing-case status. Require the negative control to show the intended assertion diagnostic, not merely any nonzero exit. Keep related build and controls in one scoped invocation.

6. **Exercise the missing failure path.** Retain the current late wrong-record control, and add a deliberate failure after fixture and pipe-holder readiness while workers are still active. The independent owner must report all fixture children reaped and workers finished, and the sentinel must remain alive until its own cleanup. Include a bounded intentional-stall control for the watchdog and demonstrate that the wrapper returns failure rather than leaving a fixture running. Export commands, toolchain/OS, control failure reasons and cleanup readback before the scoped runtime exits. Update the README to the corrected, narrow claims.

This is one responsible correction attempt. If safe scope ownership or shutdown cannot be established, stop with the concrete remaining limitation and consult the owner; do not use another Expert escalation for this cause or weaken the acceptance contract.

## Evidence disposition

| Claim | Existing evidence | Required next action |
| --- | --- | --- |
| Native macOS standalone prototype ran and captured 2 MiB on each output | Retain as historical observation, supported by source assertions and pass log | Recheck in the corrected run because the fixture and harness change |
| Simultaneous large stdin/stdout/stderr backpressure | Not accepted | Run the overlap-enforcing stream fixture |
| Child first-code group record equals PID | Retain for the two recorded fixture runs | Recheck relevant setup in corrected fixtures; this is not partial-setup-failure or host-context proof |
| Active group kill followed by direct-child wait and token-driven worker shutdown with held pipes | Retain as a successful-run macOS observation (approximately 3.5–3.7 ms as logged) | Rerun under safe ownership and watchdog; timing is observed, not a promised bound |
| Escaped fixture remains outside its original group | Retain the historical recorded behavior | No new ancestry claim if replaced with a harness-owned holder; actual descendant coverage remains open |
| Reader/writer cancellation after direct-child exit despite retained pipes | Retain the narrow successful-run observation | Rerun without the stale group signal and with owned cleanup |
| Safe managed-group closure after normal direct-child exit | Not accepted | Prove valid identity retention and real remaining in-group member cleanup separately |
| Unrelated sentinel survived this run | Retain for the observed run | Rerun; does not establish every existing-host-group context |
| Wrong expected record causes assertion failure | Retain the specific logged failure | Rerun with reliable status propagation; add the live-resource failure control |
| Cleanup on assertion/setup/I/O failure and watchdog timeout | Not accepted | Run the owned cleanup and stall controls with independent readback |
| Rust 1.77.2 compile, other Unix, Windows, full Rhai behavior, limits/deadline policy and managed-scope matrix | Unverified, already largely disclosed by README | Keep open; this correction does not supply those gates |

No new build or native execution was needed to validate these source-level defects. Existing logs are evidence of those particular outcomes, not live confirmation that all historical fixture PIDs are currently absent.
