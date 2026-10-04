# Linux final-handle drop with kill_on_drop(false)

Native behavior and original evidence independently reviewed READY in the combined
infrastructure report. Fresh reviewed original custody and exact retirement passed. A post-retirement
receipt-harness error is preserved transparently; separate independent closure
confirms absence. Final affected recipe review is READY at0cec9a19. The narrow Linux final-drop
criterion is accepted; tickets03/06 remain open for their remaining requirements.
Native behavior passed on 2026-10-04; no full platform or release claim.

## Scope and behavior

Baseline523608648dcae99bc0f6b46eaf2bb91fa4ecc752, native Linux x86_64,
private Rust/Cargo1.77.2, features testing-environ,sys, default float/index.
The real public Rhai Engine runs existing direct/managed final-drop tests.
After the final handle is dropped, an independent observer challenges the child
or each managed member, records exact PID/start/PGID and parent ancestry,
and returns an ACK bound to the entire request. Eventual host/child/group closure
is observed separately. A temporary test-only handshake overlay does not change
production behavior; original test and manifest bytes are restored before export.

Four exact Cargo test commands (--locked, --test sys_process, --exact,
--nocapture, --test-threads=1) ran in order:

| Case | Result | Independent effect |
| --- | --- | --- |
| direct-red |101|Named wrong survival assertion panics before observer handshake|
| managed-red |101|Named wrong survival assertion panics before observer handshake|
| direct-green |0|Held child responds after last handle drop; eventual closure|
| managed-green |0|Held sentinel/leader/worker/leaf identities bind; eventual scope closure|

Both green commands report exactly one passed test. Source archive SHA256
998c31fab8c3026f292ef13484a8b112da90e5ead1e0288845bffeee9186179b,
compatible lock2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425,
original test5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb.
Proof input61d828673fa032db6160263b7ba3585e826099fa6baf38f05aa7a0115c972d53.
Outer/run-scoped/PID/runtime/scope statuses0. Native duration about42seconds.

## Original evidence and bounds

69 original files/seven directories and the sole raw tar are preserved in
linux-drop-false-native2-originals. Root independently rehashed every file and tar;
tar SHA25613ac6f082f1fa81526ffc45016042e9d34ce6d3d696b8c6b943529fa2d603569.
Original input manifest verifies all12 frozen inputs. Actual receipts retain
request/ACK bytes, live and terminal reads, wrong assertions, tools, commands,
source restoration and launcher custody. Diagnostic receipts clearly marked
provisional are not acceptance or retirement receipts.

Immediate preflight09:04:29UTC found no heavy run,82,743,096KiB available RAM,
724,368,683,008bytes free; observation is not a reservation. Limits600outer,
570actual runner (maximum585),540helper including30export reserve;2Cargo jobs,
16descendants,1,572,864KiB preemptive storage,2,097,152KiB hard storage/RSS.
Original outer.log contains53 periodic samples: maxima887,404KiB RSS,
732,196KiB storage,7descendants. These are periodic observations, not continuous peaks.
No foreign process or resource was changed.

## Applicability and remaining coverage

At root HEAD63d948b1, all production src/codegen/build.rs, sys_process tests and
support bytes match baseline523. The only Cargo.toml delta adds the separately
accepted sys_process example declaration, not dependencies/features/test routing.
This proof applies to those unchanged Linux final-drop paths after integration.
It does not cover Windows, all macOS paths, no_float/no_index, stdin closure,
post-spawn fault controls, the entire feature/MSRV matrix or final release.
Existing unaffected evidence remains valid at its recorded applicability.

Native1 is consumed setup-only (missing external patch, zero tests); its42-file
originals and exact retirement are preserved. Native2 uses reviewed equivalent
strict Git application. The native2 consumer initially misexpected a resource
file and lexical path spellings; originals remain unchanged during correction.
No extra native execution is justified solely for that consumer repair.

## Fresh closure and infrastructure outcome

Reviewed071 collector fresh-custody-readback.json binds the exact original inventory
and all131 process identities/six groups. Cleanup repeated custody in the same remote
interpreter immediately before gated deletion of the exact69 files/seven directories.
The later read-only postcheck referenced undefined physical and failed; its removed
stdout was not persisted, and no deletion receipt is fabricated. Native behavior
and original evidence were unaffected; no native run or deletion was repeated.
Root-independent-retirement-readback.json freshly verifies all131 PID/start pairs
absent or reused, six groups empty, and logical/canonical stage, scope and runtime
paths absent. post-retirement-harness-failure.txt preserves this distinction.
No owned remote resources remain. The narrow postcheck/receipt-persistence fix
and its affected review belong to the same infrastructure package.

The final combined independent review at0cec9a19 rechecked physical-path binding,
receipt-persistence ordering and full embedded postcheck controls. READY with no
material affected finding; actual original and fresh closure receipts remain valid.
Future corrected cleanup writes remote-retirement.json before postcheck. This does
not recreate the lost native2 deletion receipt or claim this corrected code ran
the already completed deletion. See linux-drop-false-infrastructure-review.md.
