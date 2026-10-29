# Native Windows combined `no_index,sync,metadata` profile

Status: **accepted for the named combined test and profile only**. The full
release matrix and A–F/Ticket03 contracts remain open.

## Binding and execution

- Fork-main was `fd93185293a870bdeb10a637a032b3f0f4922fc2` at preparation.
  All 448 archived source files were independently compared with that tree.
  The frozen archive is `0005b38a...`, manifest `254d0215...`, and exact
  `Cargo.lock` SHA-256 is
  `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
  [binding.json](binding.json) pins every media file and the VM UUID
  `dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19`.
- The unchanged POSIX scoped runner, SHA-256 `25d42cec...`, assembled and
  independently read back all eight ISO entries inside its own temporary
  scope, which was retired. ISO SHA-256 was
  `6feb43ed5f060dba9b29f57e2225e8935d4b273d8d0438f7bfcb5cbe1a45f8a4`.
  Original live/inactive `sdc` and foreign `sdb` were checked before attachment.
- The guest read back `E:\Start.ps1` SHA-256
  `82227025c9a05922d8498a8f973f2ff0623ff19d34b4e0d5c9706c7a61ddfc94`;
  the PowerShell entries parsed successfully. The immediate
  [host preflight](host-dispatch-preflight-final.json) pins the ISO, all eight
  media inputs, VM, free space, retained binary lifetime and original serial
  inode/offset. The hash-guarded dispatch is shown in
  [dispatch-typed.png](dispatch-typed.png).
- Inside the owned guest source/runtime, exact Cargo and rustc 1.77.2 ran
  `cargo test --locked --features testing-environ,sys,net,no_index,sync,metadata
  --test combined_sys_net --no-run`, followed by the single exact named test
  with `RHAI_COMBINED_WRONG_EXPECTATION=1` and then with that override cleared.
  The CMD sets its working directory to the copied source, pins `RUSTC`,
  clears compiler wrappers, and bounds the Driver/observer at 180/185 seconds.

## Original results and independent observation

- The native compile finished in 51.66 seconds. The [wrong-expectation
  log](original-export/run/.scoped-evidence-5d282a09230d4f919f53ea822831448b/runtime/combined-wrong.log)
  records one executed test and the intended assertion: fresh OS host readback
  was `filesystem-payload`, while the deliberately wrong expected value was
  `incorrect filesystem expectation`. Exit was 101. The [restored
  log](original-export/run/.scoped-evidence-5d282a09230d4f919f53ea822831448b/runtime/combined-green.log)
  reports 1 passed, 0 failed, exit 0. The pinned test uses a real Rhai Engine,
  registered Sys/Net packages, fresh host file read, an independent TCP peer
  on an OS-selected port, and typed denied/error checks.
- `cargo clean --locked` succeeded and removed 760 generated files / 312.4 MiB
  before Runner retirement. The original payload stdout records the clean,
  attribute-clear, RED101 and GREEN0 markers. The [observer](original-export/observer.json)
  reports Driver 0 after 62.318 seconds, drained pipes, disposed process,
  stopped owned executables, no custody pending and no observer kill. Its
  `product_acceptance:false` is the broad suite classifier (`diagnostic_suites_complete:false`),
  not a failure of this executed narrow criterion.
- The original COM1 suffix has inode `126869568`, offsets `1094309–1436321`,
  342,012 bytes and SHA-256
  `63d565ac36fda79b4b6b693fc6c6bf20236bd3cb3b65e906666ccf619a126dbe`.
  [Original export readback](original-export-readback.json) reconstructed 208
  ordered frames and 16 hash-checked files. [Journal readback](journal-readback.json)
  verifies eight CRC/length-valid states through `REMOVED`, payload exit 0.

## Cleanup and review

- After exporting the original files, a reparse-guarded command removed only
  guest `n-5f7c712a`. The [result](guest-retire-result.png) and fresh
  [readback](guest-retire-confirm2.png) show the scope absent and no named
  Driver/Runner process. Host cleanup restored original live `sdc`, preserved
  foreign `sdb`, checked no ISO holder, and removed only the own ISO/stage.
  [Fresh host readback](host-postcleanup-readback.json) confirms both absent
  and original/foreign media live and inactive.
- One independent combined review checked source, binding, RED/GREEN,
  OS observations, lifecycle and final cleanup and returned PASS for this
  named profile/test; see [combined-review.md](combined-review.md). It made no
  broader matrix or release claim.

Attempt06's earlier post-Cargo Runner finalization failure remains historical
and its precise cause remains unproven. This run used the accepted `cargo clean`
retirement route and completed its own eight-state journal; it does not
retroactively turn attempt06 into a successful Runner run.
