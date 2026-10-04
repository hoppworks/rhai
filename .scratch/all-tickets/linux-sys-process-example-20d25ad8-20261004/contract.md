# Linux current-MSRV process example preparation

This prepared check builds the `sys`, `net` and `sys_process` examples together
from frozen source `20d25ad8ed4483d4cd4079cf62c8481a629c00e3`, using source
archive SHA-256 `e7a9a118bd29c05e8a70e284196837594fc97811f3d80688d17f55167008be93`
and compatible Cargo.lock SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. The
source archive must be created with the accepted `archive-build-source.py`
helper, which omits `.scratch`; the historical sys/net evidence and its original
stage are retained unchanged. A new unique stage and scope are prescribed by the
paired checker and launcher. The earlier invocation of the original `66379d30`
source ended at build status 101 because its example used an unavailable public
`rhai::Variant` trait; it produced no process-example acceptance. The source pin
below contains a public-API-only correction. Its `examples/sys_process.rs`
SHA-256 is `4ef8c462221c237521a2554be4800b74852b3525e734fdbcab097e869fa12321`.
Before the build, the runner verifies that source hash and checks that the
cloned-result comparison covers success, timeout, both capture-complete flags,
code, signal, stdout and stderr; it records those source facts in
`source-lock-manifests.json` and `package-result.json`. The new `20d25ad8` stage
has not been created or launched.

The existing bounded Linux current-MSRV checker is extended to compile all
three binaries in one locked Cargo invocation with private Rust/Cargo 1.77.2,
two Cargo jobs, and the existing `testing-environ,sys,net` feature set. It keeps
the existing sys/net controls and adds one process control pair. The process
binary re-executes itself only: `run` writes a record and exits 7, while `spawn`
publishes readiness, waits at most five seconds for a host release file, writes
a record, and exits 0. The spawned child writes its PID/readiness record to a
sibling temporary file and renames it to the ready path only after the complete
record has been written. The parent still validates the exact child PID before
releasing it and observing the pending wait. The host uses the exact absolute
current executable as the sole `ProgramPolicy::AllowList` member, bounds its
waits and cleanup, and reads both child-written records independently.

For the process RED control, the checker sets only
`RHAI_SYS_PROCESS_EXAMPLE_EXPECTED_EXIT=8`. The example still verifies the
actual `run` result (exit 7), both host readbacks, pending wait, and matching
cached results through cloned `Child` handles before the deliberately wrong
expectation fails. The checker requires status 101, the named assertion and
the observed/incorrect values in stderr, plus all three behavior/readback
markers in stdout. The process GREEN run omits that variable and requires
status 0 and each independent readback/cached-wait marker. These checks exercise
the real Engine and child processes; they do not use a mock or shell.

The checker restores its privately modified sys/net source files byte-for-byte
before executing the binaries and records the unmodified process example hash.
It verifies the frozen Cargo manifests and lock, captures command output and
resource samples, and requires no remaining `rhai-sys-example-*` or
`rhai-sys-process-example-*` temporary directories. It refuses to overwrite
the new stage's `proof-evidence`. Original sys/net proof at its previous source
and stage is retained as separate evidence and is not claimed to cover process
behavior.

The launcher has a 600-second outer wait bound and starts `run_scoped.py` with
at most 585 seconds, reduced when setup has consumed part of the outer budget
so at least 15 seconds remain for supervisor exit, exact process/group
readback, and scope cleanup; a separate one-second guard covers Bash's integer
`SECONDS` granularity. The helper has a cooperative 540-second deadline;
work stops at 510 seconds, reserving 30 seconds for evidence export. Export
checks the deadline between files, but an individual copy operation cannot be
preempted by that helper deadline. If export fails or is interrupted, partial
original evidence may remain and must be preserved and classified as
incomplete; the outer scoped runner still bounds process-group cleanup. The
check uses two Cargo jobs, at most 16 descendants, a sampled
1,572,864 KiB preemptive storage boundary, 2,097,152 KiB hard storage/RSS
boundaries, and one-second samples. Measurements are sampled maxima, not
continuous peaks or reservations. Setup/build, all six controls, readbacks,
restoration, export and cleanup receipts must fit in the bounded invocation.

The new stage and scope are
`/root/rhai-linux-sys-process-example-20d25ad8-20261004` and
`/root/.local/share/agent-builds/rhai/linux-sys-process-example-20d25ad8-20261004`;
the independent original proof destination is that stage's `proof-evidence`
directory. These paths have not been allocated or created.

This is an examples-only Linux x86_64 current-MSRV check. The process example
itself is explicitly Unix-only and also requires floating-point support for
`wait(0.0)`; its non-Unix fallback message is not process acceptance. It does
not establish Darwin or Windows behavior, all feature combinations, or strict
release acceptance. The process API is not registered on Windows in this
source revision. After staging and before launch, the paired default preflight
requires an empty heavy-run inventory, verifies all ten exact input hashes, and
checks that the prescribed scope and terminal/evidence paths are absent. This
preparation is not native acceptance.
