# Native Windows Rust 1.77.2 integer-only combined profile

This accepts the exercised `testing-environ,sys,net,only_i32,no_float`
integration profile on the native Windows 11 VM, UUID
`dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19`. It does not close exhaustive
integer/float semantics, other profiles or the release matrix.

The candidate is fork-main base
`7019821fc9d7814d0632fea06de50933aa9e35ee` plus exactly the reviewed
`tests/sys_process_windows.rs` overlay SHA-256 `b8340cf4…`. The overlay gates
a float-only out-of-range timeout test, selects the proper INT/FLOAT `wait(0)`
overload by feature, and uses a six-second integer timeout under `no_float`.
The deterministic 448-file ZIP is SHA-256 `0005b38a…`, manifest `254d0215…`,
and accepted lock `12084a90…`; [binding](binding.json) includes their complete
hashes and the eight immutable ISO inputs. The retained MSVC Rust/Cargo 1.77.2
executables and public native Runner/Driver build were pinned to their
previously accepted hashes. Both exact toolchain versions were measured inside
the supervised Job and exported in the original version files. The guest
parsed all three PowerShell inputs without errors and showed the exact new
scope absent before the hash-guarded dispatch. The owned ISO was
`c0cb980b…`; the [host preflight](host-dispatch-preflight.json) checked its
live sdc attachment, unchanged foreign sdb, VM identity, capacity and serial
inode/offset.

One bounded native Driver invocation ran from the frozen owned source, with
private Cargo home/target, `--locked` and the exact feature tuple. It compiled
12 named integration targets with `--no-run` in 1m33s. The public combined
Engine/SysPackage/NetPackage test ran first with
`RHAI_COMBINED_WRONG_EXPECTATION=1`: Cargo exited 101 at `fresh host readback
must match independent expected bytes`, showing actual
`filesystem-payload` against the intentionally wrong expectation. The
restored 12-target suite exited 0: **124 passed, 0 failed, 0 ignored**.
`net_metadata` and Unix-only `sys_process` each ran zero tests; the native
`sys_process_windows` target ran 31 tests and `sys_process_report` ran seven.
The combined script wrote a real host file and talked to an independent TCP
peer; process cases assert their real child/handle/record observations in the
pinned test source. The deliberate RED calibrates the combined host-file
assertion, not every suite assertion. The Driver elapsed 156.022 seconds,
inside its 180-second Job and 185-second independent observer bounds.

The libvirt serial log rotated while the guest exported evidence. The
[capture binding](serial-capture-binding.json) ties the preflight inode
`126819933` at offset `1821175` to the original `.log.0` tail (275,977 bytes,
SHA-256 `c4c5a9c2…`) and the next inode `126867980` (94,998 bytes,
`0f0647ad…`). Their byte-for-byte concatenation is the preserved
[original serial slice](serial-original.bin), 370,975 bytes, SHA-256
`ce15dde0…`. The [decoder readback](original-export-readback.json) verified
219 consecutive frames through END and 15 original files (184,134 bytes),
each with exact offset, length and SHA-256. The
[journal readback](journal-readback.json) validates eight length/CRC32 records
from INTENT through REMOVED with payload exit 0. The
[original observer](original-export/observer.json) reports Driver 0, drained
pipes, disposed process, stopped owned executables, no pending custody and
removed inner runtime. The [guest closure](guest-closure.png) independently
reads back the runtime absent and no named Runner/Driver process.

After export, the exact guest outer scope was checked for reparse entries and
removed; [guest retirement](guest-retirement.png) returned `False`. The
original VM sdc was restored and foreign sdb left intact. The owned host ISO
and stage were retired after active/persistent domain reference, exact fuser,
symlink and serial-copy checks; see [host cleanup](host-cleanup-readback.json).
The older Rust 1.77.2 toolchain scope remains intentionally retained until
the recorded expiry. There was one native run and no repeated build after the
serial rotation.

The [independent combined review](combined-review.md) returned PASS for this
profile's executed cases. The installed Windows Kit `10.0.26100.0` is recorded
in the parent [SDK inventory](../sdk-inventory.md); the exact linker/SDK files
selected by Rust were not captured. Full Windows feature/fault breadth and
release approval remain open.
