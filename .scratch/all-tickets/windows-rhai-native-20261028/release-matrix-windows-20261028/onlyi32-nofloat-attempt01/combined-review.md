# Independent combined review

The independent reviewer examined the intended 12-target native Windows
profile before launch. It found three incompatible floating Rhai literals in
the Windows process test under `no_float`. A first correction changed a timed
wait to an integer unconditionally, which would regress the normal
float-enabled overload. The coordinator corrected this to feature-selected
INT/FLOAT calls, gated the intrinsically float-range test, and retained an
integer timeout accepted by both profiles. The final focused pre-execution
recheck returned READY. No native attempt was spent on either rejected source.

Post-run combined Standards/spec, correctness and acceptance review: **PASS
for the exercised native Windows Rust 1.77.2
`testing-environ,sys,net,only_i32,no_float` cases**. The reviewer checked all
448 source entries including the exact overlay, the accepted lock, toolchain
version files, public Engine/host/OS test, wrong101 and restored suite0.
Twelve target summaries contain 124 passing tests; `net_metadata` and Unix
`sys_process` are zero-test targets while `sys_process_windows` contributes
31 passing tests. The reviewer independently checked the serial rotation's
old/new inode and segment binding, 219 ordered frames, 15 file hashes and the
eight journal records through REMOVED. The observer reported Driver0 and
completed owned process custody.

The review limits the PASS to the executed cases: the wrong expectation
calibrates host-file readback only, and neither exhaustive feature semantics
nor all Windows process faults nor the full release matrix follow. At review
time host and guest outer cleanup was pending; its later exact readback is in
`proof.md`.
