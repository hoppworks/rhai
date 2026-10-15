# Linux X38 unchecked acceptance (2026-10-15)

## Accepted scope

Combined independent review accepts only the two named X38 assertions on native
LLLM Linux x86_64, Bazzite 44, Rust/Cargo 1.77.2, with
testing-environ,sys,unchecked and the pinned lockfile. The accepted selectors
are:

- managed_spawn_kill_finishes_capture_when_escaped_descendant_holds_pipes
- managed_spawn_post_reap_cancel_bounds_escaped_capture

This is partial Ticket 03 evidence. It does not close X34/X37/X38 generally,
the remaining process package, other features, toolchains, operating systems,
or A–F.

## Inputs and reuse

The test source restored for the run is SHA-256
ddd5a6259b80647528fc1640f77f2c9f69acd913a20bf84b2a0942d3aec09cbf.
The pinned Cargo.lock is
2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425;
the Unix product source is
7abd009fcccf9ad81a5a60de4c5978177243c66c3a73118d44aa99b1bcdcc234.
Both exact test functions and their escaped-pipe fixture are byte-identical to
the reviewed Linux base-profile source at commit
34e0fa61a3d12fe6c41902c44618ff44e20d73d4. Its accepted
testing-environ,sys evidence is reused for the base-profile rows; no
unchanged base-profile build was repeated. The stdin-pumping change in the current
Unix file is outside these selectors, which do not supply stdin.

## Results and limitations

Attempt 01 stopped at compile time because two existing stdin tests called the
Engine string-size API, which is not present under unchecked; no X38 test
ran. The narrow harness correction gates only those two calls with
cfg(not(feature = "unchecked")). The 4 MiB fixture remains unchanged and
is valid without an Engine string cap in this profile.

Attempt 02 produced intended assertion REDs (Cargo status 101) for X38 and
post-reap, and restored X38 GREEN (status 0). Its harness then failed to launch
post-reap GREEN because it required the test name and ok to share a line;
--nocapture interleaves diagnostics. The classification and raw outputs
are in attempt-02/.

Attempt 03 did not reach Cargo because its non-login launcher lacked Cargo on
PATH (status 127). Its raw post-reap log path was later overwritten by a
successful run; the loss and duplicated artifact locations are documented in
attempt-03/attempt-03-failure.md. Do not treat attempt 03 as test evidence.

Attempt 04 records post-reap Cargo status 0 and one passing test. Readback shows
the direct leader reaped before cancellation, holder and sentinel alive through
the relevant waits/challenge, exact leader/holder/sentinel cleanup, and EPIPE on
both capture writers. The runtime path and empty owned session scope were
confirmed absent and the scope retired. The outer run_scoped.py status is
127, its captured outer log is empty, and the source remains unexplained. Therefore
we do not claim the outer runner succeeded.

The independent combined review concluded Standards PASS and accepted these
named rows, based on the separately recorded Cargo/test/readback evidence and
cleanup, while preserving the unexplained outer status 127 as a limitation. The
review does not generalize beyond the named selectors and exact environment.
See combined-review.md for the independent decision and its bounds.

Raw commands, logs, status files, environment, source snapshots, capacity
samples and cleanup receipts are retained under attempt-01/ through attempt-04/.
No build cache is retained or claimed reusable. The attempt history is preserved
even where the launcher or evidence-export path failed.
