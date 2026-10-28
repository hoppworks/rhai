# Native Windows Rust 1.77.2 combined sys/net contract

This accepts only the named real-OS combined sys/net integration case, not the
Windows release matrix or the full A–F/Ticket03 campaign. The candidate is
fork-main `15eb3c718153fc0642b0e1ca81de611f098b7d15`. The committed
448-file source archive is SHA-256
`99d53135a62d53f8640376af939a1dc46556db89281f0c7dfe676c20cf24e4c8`,
manifest `01f4c77a5860a7bc4a8509af37806535b46b1198f20fe8cb29ae9c927f8173ee`,
and accepted `Cargo.lock`
`12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
The source was frozen from Git HEAD rather than transient worktree contents.

The native Windows 11 VM UUID is `dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19`.
The retained Rust/Cargo toolchain is `1.77.2-x86_64-pc-windows-msvc`; guest
preflight pinned the original scope preflight and the exact `rustc.exe`
(`a95aa2d9…`) and `cargo.exe` (`86e57909…`) bytes. Both exact version strings
were measured inside the supervised Job and exported in the original version
files. The retained home was 423,724,103 bytes, under its accepted 2 GiB
ceiling and before its 2026-11-01 00:00 UTC expiry. The public native
Runner/Driver build manifest `8c625daf…` and executables were pinned to their
accepted hashes. The native ISO `190908e1…` contains the eight hash-bound
inputs in [`binding.json`](binding.json). The three PowerShell sources parsed
with zero errors in the guest; the target scope was absent before dispatch.
The host preflight records the exact live sdc medium, unchanged foreign sdb,
VM UUID, 499,374,510,080 free host bytes, serial inode `126819933` and
starting offset `1482520`.

Inside one native bounded Driver invocation, the payload ran from the frozen
source with scoped Cargo home and target, `--locked`, and features
`testing-environ,sys,net`:

```
cargo test --locked --features testing-environ,sys,net --test combined_sys_net --no-run
cargo test --locked --features testing-environ,sys,net --test combined_sys_net sys_and_net_packages_coexist_in_one_engine_with_os_readback_and_typed_errors -- --exact --nocapture
```

The second command ran twice against the same test binary. With
`RHAI_COMBINED_WRONG_EXPECTATION=1`, Cargo returned 101, and the named test
failed at `fresh host readback must match independent expected bytes` with
actual `filesystem-payload` and deliberately incorrect expected text. With
that variable cleared, Cargo returned 0 and the named test passed 1/1. The
real Rhai script used one public Engine with registered SysPackage and
NetPackage, wrote a file and talked to an independently bound OS TCP peer.
The test read the file fresh from the host, joined the peer, compared exact
bytes and checked typed Sys/Net failures. This wrong control calibrates the
host-file assertion; it does not separately calibrate every peer/error
assertion. Compilation finished in 52.08 seconds; Driver elapsed time was
63.1435 seconds, under the independent 185-second observer bound and the
public 180-second Job bound.

The [original serial slice](serial-original.bin) begins at that recorded inode
and offset, is 338,655 bytes with SHA-256 `b46c04d0…`, and decodes 203
consecutive frames into 15 files (167,896 original bytes). The
[decoder readback](original-export-readback.json) checks every file length,
offset and SHA-256. The [journal readback](journal-readback.json) verifies all
eight length/CRC32-valid records from INTENT to REMOVED with payload exit 0
and confirmed cleanup. The original [observer](original-export/observer.json)
reports Driver 0, drained pipes, disposed process, no pending custody, no
observer kill, stopped owned executables and removed inner runtime. The guest
[closure screenshot](guest-closure.png) independently shows the exact runtime
absent and no named Runner/Driver process. The accepted original logs are in
`original-export/run/.scoped-evidence-*/runtime/`.

After evidence export, the exact new guest outer scope was checked for reparse
entries and removed; [guest retirement](guest-retirement.png) reads back
`False`. The original VM sdc was restored, foreign sdb preserved, and the
owned host ISO and stage were removed after domain-reference, exact fuser,
symlink and serial-copy checks; see
[host cleanup](host-cleanup-readback.json). The older retained toolchain home
remains solely for subsequent Windows 1.77.2 rows under its recorded expiry.

Independent combined review returned PASS for this narrow case; see
[combined review](combined-review.md). Exact Windows SDK identity was not
recorded: `link` and `cl` were absent from the interactive PATH, although the
native compile succeeded. Other Windows feature profiles, process fault
breadth, full three-OS release matrix and production release remain open.
