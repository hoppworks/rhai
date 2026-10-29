# Native Windows Managed output-limit closure

Status: **accepted after independent combined review** for one Managed stdout overflow case under the named feature profile. Full X34, Ticket03 and release acceptance remain open.

## Candidate and execution

The [candidate](preparation.json) is base `f7c42546fc62d3082422be7877619719884bbd70` plus the new `tests/sys_process_windows.rs` overlay, SHA-256 `a4f13e031461651f5dcceeebee4f447ccd85edb8c228f1f99a8bebb16af028a5`; the remaining 447 archived files match the base checkout. The 448-file source manifest SHA-256 is `44cdb6bb1301316ce309e1b6adb8798f3097afa944c83988979f5119db55b52d`, source archive `f95cd94c95b2d1923ca689b49e5932fa7d24e1767862da4f0154e8d687b6a439`, Cargo.lock `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`. Independent source and runner reviews returned READY before dispatch. The first local input-generation attempt stopped on an incorrectly ordered string replacement; no native run started. The corrected generator and all eight ISO inputs were reviewed and hash-checked before attachment.

Native Windows `10.0.26300.0` used Rust/Cargo 1.77.2 and `testing-environ,sys,net`. The [native contract](media-input/RunRhaiContract.cmd) compiled `sys_process_windows` once with `--locked`, ran the exact new test with `RHAI_WINDOWS_MANAGED_OVERFLOW_WRONG_EXPECTATION=1`, checked its intended assertion and exit 101, cleared the switch, and ran the complete affected target with `--test-threads=1 --nocapture`. The Driver/observer bounds were 180/185 seconds, with an owned guest scope and the existing supervised route; see [binding](binding.json) and [host preflight](host-dispatch-preflight-final.json).

## Real behavior and assertion control

The public Rhai `spawn` path starts a Managed parent and a real descendant. After independently opening exact handles and observing both live, the test triggers a child-written stdout burst of 16 KiB against a 1,024-byte limit. The fixture records its write intent. The resulting public `try_wait` returns typed `OutputLimit`, a bounded retained output containing the child's bytes, the exact parent's exit status, and no cleanup diagnostics. Exact Windows handles show parent and descendant stopped before the result; a separately spawned sentinel remains alive and is then explicitly stopped and reaped.

The original [wrong control](original-export/run/.scoped-evidence-3effec5a327e4635888c3fff7d0b51cb/runtime/managed-overflow-wrong.log) records stopped parent/worker and live sentinel, then fails at the deliberately inverted worker-closure assertion (101). The restored [full suite](original-export/run/.scoped-evidence-3effec5a327e4635888c3fff7d0b51cb/runtime/managed-overflow-green.log) reports **35 passed, 0 failed, 0 ignored**, including the named overflow case. Both use the same compiled executable. This control calibrates worker closure; it does not independently calibrate every report assertion or prove injected Windows API failures.

The [original serial slice](serial-original.bin) covers inode `126890480`, offsets `1504058–1855878`, 351,820 bytes and SHA-256 `3a050d1ea4d2bd436a8bf3d91e1f2b81443a91612581ae689ef24a1c792821ab`. [Export readback](original-export-readback.json) reconstructed 212 ordered frames and 16 hash-checked originals; [journal readback](journal-readback.json) verified eight length/CRC records through `REMOVED`. The [observer](original-export/observer.json) records Driver exit 0 in 106.6318333 seconds, drained pipes, disposed process, no observer kill or pending custody and stopped owned executables. [Readback](readback.json) checks source, logs and the same executable; its cleanup-pending flag reflects its earlier capture time.

## Exact cleanup

After export verification, [guest closure](guest-closure-result.png) showed the exact inner runtime absent and no named Driver/Runner. The exact own outer scope was removed after a reparse check; [fresh confirmation](guest-confirm-result.png) returned `False`. [Host cleanup](host-cleanup.json) restored original `sdc` and removed this run's own ISO/stage. A separate [host readback](host-postcleanup-readback.json) confirmed those paths absent and the original `sdc` and foreign `sdb` unchanged in live and inactive VM views.

The [independent combined review](combined-review.md) passed Standards and Spec for this named case.
