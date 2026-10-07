# First committed Child cause: Linux native recipe

This package validates only the ticket03 first committed Child cause for `DirectChild` and `Managed`. It reuses the accepted process-overlap custody base, private build source copy, `run_scoped.py` supervision, exact process identity capture, resource sampler, partial export and separate closure procedure. It does not copy accepted overlap evidence or reuse its old archive-bound collector; command identities are recorded from each checked `Popen` handle, including setup commands whose `/proc/PID/cmdline` is empty.

## Frozen behavior and six selected executions

The only selected tests are `committed_stdout_cause_survives_stderr_overflow_direct_child` and `committed_stdout_cause_survives_stderr_overflow_managed`, each invoked with Cargo's `--exact` filter in its own process.

1. Two baseline REDs run against the frozen source. Each must reach the public exact stdout-cause assertion after child acknowledgments, real reap and (Managed) group closure.
2. Two post-fix stderr-overwrite REDs apply the proposed primary-cause patch, then remove only the existing `state.error.is_none()` guard around the real stderr Overflow assignment. Each must fail that same stdout-cause assertion after cleanup.
3. Restore the patch bytes and run two GREENs. Each selected test must pass with exactly one selected test.

All phases use the same private source copy and Cargo allocation. The test fixture performs genuine writes and acknowledgments. The test adapter releases the child-owned stderr gate only after the stdout cause assignment, waits for the child's stderr-write acknowledgment, then waits for the main test thread to acknowledge its live `/proc` PID/PGID/start-tick and non-zombie readback before returning to supervisor cancellation. The child also remains behind a bounded identity gate until that parent acknowledgment. The adapter does not set a cause or alter IO/status.

## Bounds and custody

Outer launcher: 600 seconds. Scoped runner: at most 585 seconds. Helper deadline: 540 seconds, with 510 seconds for work and 30 seconds for partial export. Cargo jobs: 2. Descendants: 16. Preemptive storage stop: 1,572,864 KiB. Hard RSS and storage stop: 2,097,152 KiB. No build/native allocation is authorized by this preparation.

Before a future launch, require the exact frozen input hashes, a fresh Linux x86_64 capacity/inventory sample, zero foreign heavy process groups, at least 16 GiB available RAM and disk, and absent exact stage/scope paths. Keep outer receipts, partial evidence and source inputs outside the private runtime. Preserve every command status/stdout/stderr as it completes. Restore `unix.rs`, verify its original and final hash, verify Cargo manifests/lock bytes, independently read back fixture and process identities, then retire only this launch's exact runtime and stage. Perform final PID/start/group and path closure in a separate fresh readback.

The producer uses the checked-spawn `Popen` PID as the owner identity. It stores the observed command line literally, including empty bytes if `/proc` reports an empty command line; the `argv` and Popen ownership record remain separate evidence and are not substituted for that observation.
