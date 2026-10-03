# Linux public Child wait-entry proof

Status: accepted for the stated Linux actual wait-entry criterion; combined independent review and live closure verified.

## Requirement and scope

A public Engine `child.wait()` must enter the blocking wait path while an
independently held real child is nonterminal. Another public handle must request
`child.kill()` without monopolized-lock deadlock; the waiter must complete within
three seconds, join, and the independently recorded exact child PID must be reaped.
Normal sync and sync+no_float share a native Linux7.2.7-ogc1.1.fc44.x86_64 / Rust/Cargo1.77.2 run. This does
not prove continuous sleep at the exact cancellation instant (spurious wakes are
allowed), timed waits, other feature combinations or other operating systems.

## Inputs and execution

Frozen source08507d6831f73f28aa0b95a4255c5df8ebe2ec13,
archive37e2b95ac05bcc8291b48eb7aac01ac6c260b27d18669d78935009e6bb579e03,
compatible v3lock2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425.
Test `packages::sys::process::unix::tests::public_wait_is_cancelled_after_entering_condvar`
runs through `cargo test --locked --features <row> --lib <test> -- --exact --nocapture --test-threads=1`.
Although located in a library test module, this case drives actual public Engine
spawn/wait/kill scripts and a real FIFO-held OS child; the test-only counter is
supplementary observation of wait entry, not a substitute for public behavior.
The child atomically writes its readiness/PID record, freshly read by the host.
Counter observation and reacquiring its snapshot mutex establish wait entry
before cancellation; GREEN requires public completion, joined waiter and ESRCH.

## Assertion sensitivity and resource closure

Private unique `entered_waits > 0` becomes deliberately wrong `entered_waits == 0`.
RED must be Cargo101 with intended assertion diagnostic, positive nonterminal
checkpoint and exact fixture cleanup ESRCH. Restore bytes, then require GREEN0
with one exact pass and positive wait-entry/cancel/wakeup/reap receipt per row.
Original logs, lock/manifests/restoration and PID/start identities must be exported
before scoped runtime removal. Independent root process/group/path closure and
combined evidence review are verified below. Limits/history are in coordinator-state.md.
Previous shared Child/scalar proofs remain applicable; all wider requirements stay open.


## Observed native invocation88

| Features | Wrong assertion | Restored assertion | Independent child observation |
| --- | --- | --- | --- |
| testing-environ,sys,sync |101, intended checkpoint assertion|0, one exact test passed|checkpoint PID747237 count1, completion wait_entries2, waiter_woke/reapESRCH|
| testing-environ,sys,sync,no_float |101, intended checkpoint assertion|0, one exact test passed|checkpoint PID747458 count1, completion wait_entries2, waiter_woke/reapESRCH|

RED child PIDs747133 and747360 independently reached cleanupESRCH; each original
log has positive count1/nonterminal checkpoint and the intended assertion
message. GREEN drives public cancellation, receives success, joins the waiter,
then checks ESRCH. RED uses the fixture guard for cancellation and therefore
does not itself prove public kill. All four exact fixture PIDs are absent in
fresh root readback. Original unedited files: linux-wait-entry-evidence-88 and
linux-wait-entry-outer-evidence-88; commands/version/environment are retained.
Source-restoration.json verifies original Unix source
1b60751c6d9ed695f79edc4f8a7972338274684ef53583bd1ea1009c1aca822a,
private wrong overlay6890bbdb3f96645059e2d52db5f652bb799b8b7da4741815943c255564616669,
unchanged manifests and v3lock. Root byte-compared restoration with frozen source
and exported executed helper/launcher with their reviewed bytes.

Export began38.528s after helper start; periodic sampled maxima RSS920012KiB,
private storage762208KiB, descendants6. These are sampled maxima, not continuous
peaks. Scoped/outer exit0 and both PID readback status0; independent root receipt
linux-wait-entry-root-readback-88.json confirms107PID/start identities absent,
all4fixture PIDs absent, relevant groups empty and exact private runtime/scope
absent. Outer log preserves a /proc/stat disappearance during launcher polling;
combined review confirms this conditional polling exit race does not invalidate the successful wait status or independent closure evidence.
Exact stage cleanup checked all52files against the recorded postrun hash manifest,
verified exported original logs against those hashes, removed6directories using
rmdir and confirmed stage absent. Receipts linux-wait-entry-owned-stage-files-88.json
and linux-wait-entry-stage-cleanup-88.json. No own build/stage/private cache remains.

No production change was needed; expected assertion RED is not a product failure.
Unix cumulative88 consumed; no retry. This closes no other platform or wider
process requirement. Review: linux-wait-entry-review.md.
