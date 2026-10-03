# Linux process IO/options/deadline evidence

Status: combined independent review accepts the two sensitivity-backed claims below; other positive cases remain awaiting strict sensitivity closure.

## Inputs and execution

Frozen source `9e56d5f2ef42303493907907454562f72a24b60b`, archive SHA256
`40ddedbf8ff27d21c4be7066cb54f20be4192f5ae01de05579064cca4a254a61`.
Compatible v3 Cargo lock `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
Native workhorse Linux x86_64, private Rust/Cargo 1.77.2. Original version logs
are in `linux-process-io-evidence-89`. Exact executed recipes and contract are
in `linux-process-io-outer-evidence-89`; they match the local recipe bytes.

Five rows share one bounded scoped invocation89:

- `testing-environ,sys`
- `testing-environ,sys,sync`
- `testing-environ,sys,metadata,serde`
- `testing-environ,sys,net,sync,metadata,serde`
- `testing-environ,sys,f32_float`

Every command uses `cargo test --locked --features <row> --test sys_process
<exact-test> -- --exact --nocapture --test-threads=1`. The recipe's TESTS tuple
and original commands/status/logs identify ten selected public Engine tests;
50 exact original-source invocations pass0, each one test with no ignored cases.
No managed/census/overhead suite is selected. This establishes feature coexistence,
not independent network or serialization behavior.

## Real behavior and sensitivity

Tests drive real Rhai scripts through Engine and sys to actual OS children, with
fresh host reads of child-written records and explicit ESRCH checks. Positive
runs cover raw/text exact capture and nonzero exit, simultaneous stdin/stdout/
stderr with per-stream caps, cap+1 and zero caps, two deadline cases, unit stdin
EOF, unit timeout override, capability-held cwd/escape denial, and lossy decoded
string limits. See combined review for the precise limits of each assertion.

Ten intended RED101 controls are two cases per feature row:

1. Simultaneous IO expects byte x120 while the fixture writes o111. A private-only
   overlay moves the identical independent completed-input/PID/reap assertion
   before the intentionally wrong byte comparison, then prints a record-derived
   ESRCH receipt. The intended stdout mismatch occurs only after that check.
2. Blocked-stdin/active-stream deadline expects a wrong stderr marker while the
   independent fixture output remains unchanged. The preexisting independent
   child-record/reap assertion executes before the marker check; an added private
   receipt records its PID. The intended missing-marker assertion fails.

All ten RED diagnostics and child receipts are preserved. Private overlays are
recorded incrementally and byte-restored; all 50 positives run original source.
Root independently compared original/restored test hash with current source,
manifests before/after, lock and executed recipe bytes. The two controls prove
sensitivity of these two cases; other positive cases require their own valid
sensitivity evidence before individual strict closure is claimed.

## Closure and resources

Native/outer status0. Independent root readback checks425 exact PID/start
identities absent, ten exported control-fixture PIDs absent, the scoped process
group empty and private runtime/central scope absent. Positive-case short-lived
fixture PIDs are not all exported: the native tests execute their independent
reap assertions, while periodic outer sampling is not a complete fixture census.
Root verified exported evidence hashes before removing221 exact owned staging
files and six directories. No retained build/cache/stage and no foreign cleanup.
Receipts: `linux-process-io-root-readback-89.json`,
`linux-process-io-owned-stage-files-89.json`, `linux-process-io-stage-cleanup-89.json`.

Export elapsed76.589s; periodic maxima989296KiB RSS,1114264KiB storage,
seven descendants. These are sampled observations, not continuous peaks.
Bounds600s outer/585s scoped/540s helper with30s export reserve, jobs2,
16 descendants/2GiB policy and1572864KiB storage preemptive stop unchanged.
The conditional launcher /proc/stat disappearance warning is retained as an
exit-poll race; final runner and custody/readback statuses are0.

## Remaining acceptance

No no_float/unchecked/no_index or broader platform claim. Raw and text ordinary
capture reuse a record path, positive cwd lacks a PID receipt, and deadline
cases do not assert a per-call elapsed upper bound. No exact latency guarantee
or complete per-child PID/start census follows. Previously accepted source/
platform evidence remains recorded for its original applicability; changes to
retained-owner supervision justify these affected Linux checks. Native Windows,
Darwin, managed groups, remaining feature/fault/latency/performance and final
release criteria remain open. No production source change was needed here.
