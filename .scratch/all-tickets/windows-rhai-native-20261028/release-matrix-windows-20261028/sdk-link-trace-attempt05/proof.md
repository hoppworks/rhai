# Native Windows SDK linker microprobe, attempt 05

Outcome: **PASS for the explicit-path linker control only**. The probe is not a
Rhai product test, and it does not identify SDK files selected by Cargo.

## Binding and execution

- The frozen Rust source and Cargo.lock match attempt 04 and fork-main
  `3b71a382393c48038254c766a12331e0721247de`. The source inventory has 448
  archived files and the one existing test overlay; `binding.json` records all
  nine media inputs and exact tool/SDK paths and hashes. Cargo.lock SHA-256 is
  `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
  No Cargo target or Rhai product assertion ran in this attempt.
- The existing scoped POSIX runner (SHA-256
  `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`)
  built the ISO in a fresh owned host session, whose scope was retired. The
  byte-checked ISO SHA-256 is
  `a3b6d29c280eea3f3c9e42e06e96e1fa7b9be26dc570708c0a18bd4e10ae4516`.
  `iso-build-readback.json` preserves the result. The independent source review
  was READY before this build.
- Guest `scope-absence-result.png` showed E:\Start.ps1 present, own scope
  absent and Windows NT 10.0.26300.0. `parser-result.png` showed zero
  PowerShell parse errors. `host-dispatch-preflight-final.json` pinned VM UUID,
  media, source, capacity, COM1 inode/offset and the public Runner/Driver before
  the hash-guarded command in `dispatch-typed.png`. The public native build was
  reused unchanged.
- `RunRhaiContract.cmd` froze the staged input root before changing into the
  private work directory; both `probe.c` and the cleanup helper use that
  absolute root. The bounded run compiled, linked and executed a fresh probe.
  Original stdout records helper, CL, LINK, executable and export exits all 0,
  plus the response file and executable present. The fresh executable wrote
  exactly `RHAI_NATIVE_LINK_PROBE_EXECUTED\n` to `probe-run.log`. The exported
  `probe.exe` SHA-256 is
  `817c7d9a6807ab2d87f26410b5a96881f8140d77f2844fd3649a522713dbeee6`.
  Original `link-inputs.rsp` is UTF-16 and independently decodes to the owned
  `probe.obj` and the explicitly supplied
  `C:\Program Files (x86)\Windows Kits\10\Lib\10.0.26100.0\um\x64\kernel32.lib`.
  Its SHA-256 is `fd18fd1cd070c996f0fde65561ebc8d4ce1ad20c9ba109434290352d0ca8c793`.

## Custody, export and cleanup

- The original Driver exit was 0 in 7.107 seconds. `observer.json` reports
  exited/disposed Driver, drained pipes, stopped owned executables, no pending
  custody and no observer kill. It marks `linker_probe_complete=true`,
  `accepted=true`, `product_test_run=false` and `product_acceptance=false`.
- `serial-capture-binding.json` binds original COM1 inode 126869568 and exact
  offsets 555878–888128. The 332,250-byte `serial-original.bin` has SHA-256
  `89d98a82e932cf6e0ed95751d42a785423d48578364444b0ffb6323006050a46`.
  Independent decoding yielded 202 ordered frames and 16 hash-checked files;
  `original-export-readback.json` lists each original. The eight CRC/length
  valid journal states end in `REMOVED`, payload exit 0; see
  `journal-readback.json`.
- `guest-closure-result.png` shows the exact runtime absent and no
  Driver/Runner process. A reparse-guarded command retired only the owned
  guest `n-1743a389` scope; `guest-retirement-confirm-result.png` separately
  shows it absent and no processes. `cleanup-host.py` checked ISO hash, VM
  identity, live/inactive media and holder absence, restored original live
  sdc, preserved foreign sdb, and removed only this attempt's ISO and host
  stage (50 files). Fresh `virsh domblklist` readback confirmed original sdc
  live/inactive and foreign sdb unchanged; exact stage and ISO were absent.
  `host-cleanup-readback.json` records the result.

The combined independent Standards/Spec/correctness review in
`combined-review.md` found no actionable issue for this narrow control. Attempt
04's path defect is resolved. The next open SDK step is one bounded real Cargo
target diagnostic using the proven pre-retirement export method, followed by
independent hashing of the SDK files that invocation actually selects. Existing
feature and product acceptance rows remain valid without repetition.
