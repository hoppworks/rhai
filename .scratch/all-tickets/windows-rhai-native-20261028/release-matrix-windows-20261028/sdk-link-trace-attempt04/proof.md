# Native Windows SDK linker microprobe, attempt 04

Outcome: **pre-link infrastructure RED**. This attempt ran neither a Rhai
product test nor a successful linker probe. Earlier accepted native profiles
remain applicable; this result does not bind Cargo-selected SDK inputs.

## Binding and original execution

- Frozen Rust source/lock and public native Driver/Runner are the same as
  attempt 03, at integrated fork-main head
  `71fed877b9f22a64148cc5ba4350507177a64f72`. `binding.json` records
  the 448-file source inventory, one test overlay, all nine media files,
  selected CL/LINK/SDK paths and hashes, and own nonce
  `e1534746c0394e61a2defda7c3a79c08`. No Cargo target was planned.
- The central scoped runner copy had SHA-256
  `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`.
  It built the owned ISO in a private host scope, returned 0, and that scope
  was retired. `iso-build-readback.json` records nine byte-checked inputs and
  ISO SHA-256 `84a44b22ff78870e9cc786035519cc6b8ad9740b6716d2cc4184096708494d35`.
  The ISO alone replaced live sdc; original inactive sdc and foreign sdb were
  unchanged.
- The independent source review was READY before ISO build. Guest
  `scope-absence-result.png` shows E:\Start.ps1 present, own guest scope
  absent and Windows NT 10.0.26300.0. `parser-result.png` shows zero errors
  for the three PowerShell files. `host-dispatch-preflight-final.json` binds
  source, ISO, VM UUID, original COM1 inode/offset and current capacity
  immediately before `dispatch-typed.png` and native execution. Driver,
  observer and export bounds remained 180/185/180 seconds.

## Failure and custody

- The original Driver returned 2 in 5.69 seconds. `observer.json` reports
  exact exit, drained pipes, disposed process, no pending custody, no observer
  kill and stopped owned executables. `serial-original.bin` is the original
  same-inode COM1 suffix from preflight offset 237465 to 555878; SHA-256
  `e50b26dbbb5230041aef5ce3042a8243c8c30c69b90e2dcb9aee84c962d69dea`.
  Decoder recovered 185 ordered frames and 11 hash-checked files. The eight
  CRC-valid journal phases end in `REMOVED`, with payload exit `0000003D`
  (decimal 61) and cleanup confirmed; see `journal-readback.json`.
- The original `compile.log` records CL C1083: `probe.c` was sought in
  `runtime\work`, not the staged runtime root. The original payload stdout
  also shows PowerShell seeking `ClearOwnedWorkReadOnly.ps1` under `work` and
  failing to find it. The script used `%~dp0` after `cd` into `work`, while
  CMD had been launched by relative script name; that expansion followed
  the changed directory. CL exit 2 caused batch exit 61. The missing cleanup
  helper message did not itself stop the batch; no helper success markers
  appeared. The runner still closed custody and retired the private work.
  No linker invocation, response-file readback or fresh probe run occurred.
- `guest-closure-result.png` shows the exact scoped runtime absent and no
  Driver/Runner process. A reparse-guarded command removed only guest
  `n-e1534746`; `guest-retirement-confirm-result.png` independently shows
  the outer scope absent. `cleanup-host.py` restored the original live sdc,
  verified inactive sdc and foreign sdb, exact ISO hash, no holder, and
  retired only this attempt's ISO and host stage (49 files). Fresh readback
  showed the original live/inactive sdc and foreign sdb, with own stage/ISO
  absent; `host-cleanup-readback.json` records the result.

## Next corrected control

Capture the validated runtime root before `cd` and use that absolute source
path for `probe.c` and the cleanup helper. Require both helper success markers
before reporting payload success. Preserve bounded generated outputs under
private `work`, copy only the selected diagnostics to the runtime root before
automatic work retirement, and require a fresh executable marker. The
independent result review is `combined-review.md`. This is a specific
preparation correction, not grounds for another full Cargo build.
