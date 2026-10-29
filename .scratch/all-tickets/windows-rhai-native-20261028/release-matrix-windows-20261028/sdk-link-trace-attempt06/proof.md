# Native Windows Cargo SDK selection, attempt 06

Outcome: **the narrow Cargo-selected SDK input diagnostic is proven** by the
original successful link trace, recovered UTF-16 linker response file and
post-run guest file hashes. The native Runner did **not** complete its evidence
and disposition contract. No Rhai product test ran; this does not close the
Windows release gate or a product criterion.

## Binding and execution

- Fork-main at preparation was `9d3753793a9de646dbcfcc1f54b858b663223bfe`.
  The frozen 448-file Rust archive at source commit `7019821fc9d7814d0632fea06de50933aa9e35ee`
  plus the recorded `tests/sys_process_windows.rs` overlay matches the
  integrated source tree. Cargo.lock SHA-256 was
  `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
  `binding.json` pins all nine media inputs, nonce and the single
  `combined_sys_net` target with `testing-environ,sys,net` and zero product tests.
- The existing scoped POSIX runner, SHA-256
  `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`,
  assembled the byte-checked ISO in an owned host scope, then that scope was
  retired. ISO SHA-256 was
  `644286a85b99ee2e3baf1a784688c2ef54be982abe23d298c1ffad8bbb0383e9`.
  The independent source review found the missing Cargo compiler pin, which
  was corrected before assembly: `RunRhaiContract.cmd` sets `RUSTC` to the
  prehashed absolute Rust 1.77.2 path and clears wrapper overrides. It binds
  the runtime root, Cargo home/target, one real target and a bounded response
  file export before Runner work retirement. Its final source review was READY.
- The live guest showed E:\Start.ps1 present, own scope absent and Windows NT
  10.0.26300.0; all three PowerShell files parsed with zero errors.
  `host-dispatch-preflight-final.json` pins VM UUID, ISO/Start hashes, all
  media inputs, original COM1 inode/offset, capacity and the public native
  build immediately before the hash-guarded dispatch. That public Driver and
  Runner were reused unchanged.

## Original outcome and recovered link evidence

- The original payload stdout has exact helper, Cargo, response-file export
  and log-bound exit markers all **0**. The original Driver exited **2** after
  106.736 seconds. Its observer reports exact Driver exit, drained pipes,
  disposed process, stopped owned executables, no pending custody and no
  observer kill, but `accepted=false`. The Driver stderr says its completion
  journal lacks the required eight-record grammar. The original COM1 suffix
  (inode 126869568, offsets 888128–1036410) has SHA-256
  `2832902fecb7b1702254b89837b7236280953710c1a9eeccb029d4e2bc46645a`;
  the decoder recovered 96 ordered frames and nine hash-checked original
  files. The original four CRC/length-valid journal states are `INTENT`,
  `IDENTITY`, `STAGED`, `LIFECYCLE`. `EVIDENCE`, `OUTCOME`, `REMOVE_INTENT` and
  `REMOVED` are absent. The original `work` tree remained; later guest readback
  counted 378 files and 74 directories. The precise failure inside retirement
  or evidence capture is unproven; a cleanup time-limit cause is a hypothesis.
- Guest originals in that still-owned runtime were recovered through an
  independently bounded COM1 read, with a separate inode/offset preflight,
  four named file frames, contiguous byte chunks, length and SHA-256 checks.
  `recovery-serial-original.bin` SHA-256 is
  `9c9d5b7ee90c3ab34f70bf71d61dccef6f135755c9ad157f42326b4b2a2304e0`.
  `recovery-readback.json` lists the four files. Cargo and rustc report exact
  version 1.77.2. The recovered `cargo-link.log` ends in `Finished dev` and
  prints the real MSVC `link.exe` invocation for
  `combined_sys_net-c5510176c67b6571.exe` with
  `/LINKREPROFULLPATHRSP`. Its original hash is
  `4b1528f31a57a23ef0853c98370909b2995e84a1050f70f39790d82b0e590b7d`.
- The 23,488-byte UTF-16 response file has SHA-256
  `675379d3f282e579b24155053682b3f347fa2d880cafc5bfccca55cc20261bbc`.
  Independent decoding shows six unique Windows Kit UM library paths at
  `C:\Program Files (x86)\Windows Kits\10\lib\10.0.26100.0\um\x64`:
  `advapi32`, `bcrypt`, `kernel32`, `ntdll`, `userenv`, `ws2_32`. It also names
  `C:\BuildTools\VC\Tools\MSVC\14.44.35207\lib\x64\msvcrt.lib`.
  `sdk-selection-readback.json` ties those paths to the Cargo log, source,
  feature and response-file pins. A subsequent independent guest query hashed
  those seven files and the selected `link.exe` into original COM1 bytes;
  `sdk-hash-readback.json` records each post-run size/hash. These hashes show
  post-run file identity, not an atomic snapshot at link time. The `kernel32`
  and `link.exe` hashes also match the earlier native control.

## Cleanup and limits

- With the original and recovery records saved, a reparse-guarded command
  removed only guest `n-9dd1f408`; a fresh console query showed it absent and
  no Driver/Runner process. `cleanup-host.py` checked exact ISO hash, no holder,
  VM UUID and live/inactive media, restored original live sdc, preserved
  foreign sdb, and removed only this ISO and 66-file host stage. Fresh
  `virsh domblklist` readback confirmed original sdc live/inactive and foreign
  sdb unchanged; exact owned stage/ISO were absent. This later cleanup does
  not turn the incomplete Runner journal into a success.
- `combined-review.md` records the one independent Standards/Spec/correctness
  review. It accepted only the SDK-selection diagnostic and found no actionable
  issue with that narrow evidence. The next native work should diagnose this
  exact post-Cargo Runner finalization failure from the original journal and
  retained source before another expensive full-target run. No automatic
  rebuild or product-test repetition follows from the SDK binding.
