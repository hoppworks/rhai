# Native Windows Rust 1.77.2 default Sys+Net gate

Status: **accepted for the ten executed `testing-environ,sys,net` integration targets on native Windows 11** after one combined independent review. The full A–F/Ticket03/release campaign remains open.

## Source, toolchain and custody

- The [binding](binding.json) compared all 448 archived product files byte-for-byte with fork-main `ea56b03f9fa3965bc2da660e5b0a48bb0b22449b`: zero mismatches. Immutable source archive SHA-256 `6ff82b95cbbf65ba919161932a63d74f668f8e6e6d88682418797eca93565384`, manifest `b829308ab356d7aaaf7bf8d3acc9f65aab8fb316192d9b1b69e3365d78c834fd`, and exact Cargo lock `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802` match the current source. The prior Windows combined test and later corrected Net peer fixture were reused as applicable evidence; this run supplies the broad default-profile execution.
- Native guest Windows 11 reported `10.0.26300.0` in the [absent-scope readback](scope-absent.png). Guest preflight pinned the retained Rust/Cargo 1.77.2 toolchain and existing public scoped Runner/Driver binaries; the original exported [Cargo](original-export/run/.scoped-evidence-fc3b4ba7de554275a9ded60ff99a19c6/runtime/cargo-version.txt) and [rustc](original-export/run/.scoped-evidence-fc3b4ba7de554275a9ded60ff99a19c6/runtime/rustc-version.txt) versions confirm both were 1.77.2 inside the supervised run. The retained toolchain and public build remained within their recorded finite lifetimes. No foreign VM process was interrupted.
- The eight [media inputs](media-input/) were copied into one owned host stage and independently read back from its ISO. The ISO SHA-256 was `5e19b2e2efb20c649b1f6e8f69693a40b28990c382473725c9ba81c10355a942`; [assembly](assemble.log) ran under the existing bounded POSIX runner and retired its exact owned scope. The [live host preflight](host-dispatch-preflight-final.json) checked the attached ISO, hashes, VM UUID, disk capacity, serial inode/offset and original/foreign media immediately before the [hash-guarded console command](dispatch-command.txt) was submitted. Guest PowerShell parsed the three input scripts with zero errors ([readback](parser-result.png)); the exact own guest scope was absent before launch. Native Driver and observer limits were 180 and 185 seconds, with private source, Cargo home/target, process-tree custody, output bounds, COM1 export and lifecycle journal.

## Actual result

The [native contract](media-input/RunRhaiContract.cmd) used explicit source working directory and `--locked`. One supervised run compiled ten targets under `testing-environ,sys,net`, ran the exact combined host-readback assertion with `RHAI_COMBINED_WRONG_EXPECTATION=1`, cleared that switch, and ran the complete selected target suites with `--test-threads=1`. The [original compile log](original-export/run/.scoped-evidence-fc3b4ba7de554275a9ded60ff99a19c6/runtime/compile.log) lists all ten executables. `net_metadata` needs the separate `metadata` feature; Unix-only `sys_process` was omitted from this Windows slice.

| Target group | Passed | Failed | Ignored |
|---|---:|---:|---:|
| Combined Sys+Net | 1 | 0 | 0 |
| Sys environment, filesystem, policy | 55 | 0 | 0 |
| Sys process report and native Windows process | 39 | 0 | 0 |
| Net connect, listen, reads, writes | 30 | 0 | 0 |
| **Total** | **125** | **0** | **0** |

The [original RED](original-export/run/.scoped-evidence-fc3b4ba7de554275a9ded60ff99a19c6/runtime/combined-wrong.log) exited 101 at the intended fresh host-file assertion: actual `filesystem-payload`, deliberately expected `incorrect filesystem expectation`. The restored [combined test and nine other named targets](original-export/run/.scoped-evidence-fc3b4ba7de554275a9ded60ff99a19c6/runtime/suite.log) passed; the [readback](readback.json) checks each nonempty target summary, all zero failures/ignored, and the same combined test executable in compile, RED and GREEN. The combined test uses a real Rhai script with registered SysPackage and NetPackage, fresh host file read, an independent OS-selected TCP peer with exact byte checks, and typed error assertions. The control calibrates the host-file assertion, not every assertion in the ten targets.

The [original serial suffix](serial-original.bin) is bound to preflight inode `126890480`, offsets `425816–797327`, 371,511 bytes and SHA-256 `72749abcdac8cf6c486dde7ee7bb9090ed0efb175036bdbd4dfeab5b4b917e63`. [Export readback](original-export-readback.json) reconstructed 221 ordered frames and 16 original files, checking every file length and SHA-256. [Journal readback](journal-readback.json) validated all eight length/CRC32 records through `REMOVED`, payload exit zero and confirmed cleanup. The original [observer](original-export/observer.json) records Driver exit 0 in 121.49 seconds, drained pipes, disposed exact process, no pending custody or observer kill, stopped owned executables and removed inner runtime. Its `product_acceptance:false` correctly denotes the larger unrun release work; `target_suite_complete:true` covers this executed slice.

## Exact cleanup and limits

The [guest runtime check](guest-closure-result.png) showed the exact inner runtime absent and no named Runner/Driver process. After the validated export, the exact own guest outer scope was removed; a fresh [confirmation](guest-retirement-confirm.png) returned `False`. [Host cleanup](host-cleanup.json) restored original `sdc`, preserved foreign `sdb`, and retired only this run's ISO/stage after media and fuser checks. A separate [host readback](host-postcleanup-readback.json) found both own paths absent and the original/foreign media correct in live and inactive VM views. The accepted source, logs and readback remain in this proof folder; the disposable ISO and guest runtime do not.

The [independent combined review](combined-review.md) passed Standards and Spec for the named executed slice. Other native feature profiles, process fault paths, ignored/omitted cfg cases and the full release matrix remain open under their own criteria.
