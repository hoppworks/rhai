# Revised Windows cwd development RED

Native Windows 11 x86_64, Rust/Cargo 1.77.2 and
`testing-environ,sys,net` compiled committed base
`6dc2565bebe137063c218cc90fa748d24559d1a5` plus the revised
`tests/sys_process_windows.rs` overlay (SHA-256
`abf2f00b4023205160cb5da3422bc4372f367cbfd4a1bd57e0481847e76370a0`).
The accepted lock SHA-256 is
`12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
The [source manifest](media-input/source-manifest.json) binds 450 files.

Compilation succeeded. All three selectors produced Cargo exit 101 and one
failed test. The first records typed unsupported-`cwd` Denied. The root test
first proves a sibling can be renamed, observes Windows sharing violation 32 on
the pinned root, then fails with a `SysError` at `CWD_ROOT_IDENTITY`. The denial
test sees outside Denied and unchanged Job totals 2→2, then receives Denied
instead of NotFound for a missing cwd. It does not reach the positive Job
calibration. Original logs and command markers are in [the export](original-export/).

The observer reports `accepted=false`, correctly, because its root-token
check expects Denied's message where the root test only prints the payload's
type. The message is present in the separate baseline and denial logs, not in
the root log. The [independent review](combined-review.md) accepts the individual
observations with that limitation, without changing the original observer or
repeating the build. No GREEN or product acceptance is claimed.

Driver exit 0 in 72.245 seconds, `CLEANUP_CONFIRMED=True`,
`RUNTIME_REMOVED=True` and closed observer custody are recorded in the
originals. The [journal](journal-readback.json) has eight CRC- and
length-validated states through `REMOVED`. The serial export contained 214
ordered frames and 17 hash-checked original files. After independent readback,
the exact guest scope was removed; the [guest receipt](guest-retire-result.png)
reports `False`. The [host cleanup](host-cleanup.json) confirms removal of the
owned stage and ISO, restoration of original `sdc`, and preservation of foreign
`sdb`.

The root rename result does not prove race-safe cwd handling. In particular,
the behavior of inner components and reparse points remains open; Windows
`CreateProcessW` accepts a directory path, so passing a previously authorized
directory handle requires further work. No product code was changed by this
development run.
