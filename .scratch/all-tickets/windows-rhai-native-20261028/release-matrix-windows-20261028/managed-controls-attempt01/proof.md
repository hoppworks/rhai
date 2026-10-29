# Native Windows Managed process controls at Rust 1.77.2

Status: **accepted for the named native Windows Managed kill, timeout and final-drop slice after independent combined review**. This closes no other A–F, Ticket03 or release criterion.

## Binding and execution

- [Source binding](binding.json) compared 448 archived source files byte for byte with fork-main `7dacf2ae09ef657cfbb53d3a0b35b9bb7dc2f4ac`, with zero mismatches. The immutable source archive SHA-256 is `6ff82b95cbbf65ba919161932a63d74f668f8e6e6d88682418797eca93565384`; manifest `b829308ab356d7aaaf7bf8d3acc9f65aab8fb316192d9b1b69e3365d78c834fd`; Cargo.lock `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
- Native Windows 11 `10.0.26300.0` used the retained Rust/Cargo 1.77.2 toolchain. Original exported [rustc](original-export/run/.scoped-evidence-bed00e2827c143939e406078d3462ba5/runtime/rustc-version.txt) and [Cargo](original-export/run/.scoped-evidence-bed00e2827c143939e406078d3462ba5/runtime/cargo-version.txt) versions confirm the run's toolchain. Source, work directory, Cargo target/home and temporary outputs were owned by guest scope `n-73bbed61`. The exact VM and ISO were bound in [host preflight](host-dispatch-preflight-final.json), after script parser checks and an absent-scope readback.
- The [native contract](media-input/RunRhaiContract.cmd) compiled one `sys_process_windows` executable with `testing-environ,sys,net` and `--locked`, then ran four deliberate wrong-expectation controls and the full restored suite. Its source working directory was explicit. Driver/observer deadlines were 180/185 seconds. The [pre-execution independent source review](source-review.md) approved the corrected exact-scope cleanup before launch.

## Actual result and assertion sensitivity

The [original logs](original-export/run/.scoped-evidence-bed00e2827c143939e406078d3462ba5/runtime/) show compile exit 0, four control exits 101 and restored suite exit 0. Each control ran against the same `sys_process_windows-b3e5219af6d50bf7.exe` used for GREEN:

| Control | Independent OS readback | Intended failure |
|---|---|---|
| Managed kill | parent, worker and sentinel PIDs; sentinel alive | wrong descendant closure expectation |
| Managed timeout | parent, worker and sentinel PIDs; sentinel alive | wrong timeout closure expectation |
| Final drop, kill policy | parent/worker exit and live sentinel | wrong termination expectation |
| Final drop, retain policy | kill and retain runs; parent/worker exit and live sentinels | wrong survival expectation |

Each control log contains `test result: FAILED. 0 passed; 1 failed` and its specific assertion text. The restored [suite](original-export/run/.scoped-evidence-bed00e2827c143939e406078d3462ba5/runtime/suite.log) reports **32 passed, 0 failed, 0 ignored**, including kill, timeout and both final-drop modes with fresh Windows process readbacks. The [independent readback](readback.json) checks source/lock, original-file hashes, common executable, all four assertions, exit statuses, suite and custody. Its two cleanup flags describe the state at original-export readback; cleanup happened subsequently and is recorded below.

The [original serial slice](serial-original.bin) is bound to inode `126890480`, offsets `797327–1163524`, 366,197 bytes, SHA-256 `fdf3a536d0e4f5ca62af7425829f025124e1f0f52ea66f60ca0adaf204568019`. [Export readback](original-export-readback.json) reconstructed 225 ordered frames and 19 files, checking every length and SHA-256. [Journal readback](journal-readback.json) validated eight length/CRC records through `REMOVED`, payload exit zero. The [observer](original-export/observer.json) records Driver exit 0 in 153.982094 seconds, drained pipes, disposed process, stopped owned executables, no observer kill or pending custody, and removed inner runtime. Its `product_acceptance:false` correctly refers to the larger campaign; `target_suite_complete:true` covers this target.

## Exact cleanup and limits

After export validation, the [guest inner-runtime check](guest-closure-result.png) returned `False` for the exact path and no named Driver/Runner processes. The exact own outer scope was removed only after checking for reparse entries; a fresh [guest readback](guest-retirement-confirm-result.png) returned `False`. [Host cleanup](host-cleanup.json) restored the original live `sdc`, preserved foreign `sdb`, and retired only this attempt's ISO/stage after hash and fuser checks. An independent [host readback](host-postcleanup-readback.json) found both owned paths absent and original/foreign media correct in live and inactive VM views. Accepted source and results remain here; foreign VM media and the separately retained toolchain remain untouched.

This evidence covers only current-source native Windows Managed kill, timeout and final-drop behavior under the tested default feature profile. Other Windows process faults, argument/IO gaps, feature combinations and full release acceptance remain open.

The [independent combined review](combined-review.md) passed Standards and Spec for this narrow slice without rerunning tests or changing the VM.

## Direct embedded-quote argument: reused assertion calibration

The same current-source Windows 1.77.2 suite also passes `windows_direct_run_preserves_embedded_quote_argument`: a real PowerShell `-File` child wrote `before"after`, the host independently read that file, and the named test finished `ok`. The earlier [attempt42](../../attempt42/proof.md) deliberately inverted this exact assertion after the same child readback; its original RED exited 101 at `deliberately wrong Windows argument expectation`, followed by its restored GREEN. Both archived copies of the test function are byte-identical (SHA-256 `4e29c43741a90cd625c3e5957e7e355f5808d4397786ea72158c9618e04ad421`); `tests/sys_support/mod.rs` is also byte-identical. The exact Cargo.lock is identical. Rechecked exports contain 13 and 19 hash-verified original files respectively, and both source archives match their recorded hashes.

The original RED used Rust 1.93.0 and `testing-environ,sys,metadata`; the current GREEN used Rust 1.77.2 and `testing-environ,sys,net`. Product Windows process code and Cargo.toml changed in between. Therefore the old RED calibrates only the unchanged assertion; the current native GREEN establishes the behavior on the current source. The same Windows guest and PowerShell fixture are used. An independent combined Standards/Spec review passed this reuse without a new run. This accepts only the single Direct-mode ASCII embedded-quote case for this parser and current feature/toolchain profile; other arguments, parsers, Managed mode and release criteria remain open.
