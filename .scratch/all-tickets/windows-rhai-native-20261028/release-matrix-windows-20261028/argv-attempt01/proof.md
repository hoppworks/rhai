# Native Windows argument round-trip: X4–X6

The native Windows 11 x86_64 MSVC run used Rust/Cargo 1.77.2 and
`testing-environ,sys,net`. Source was committed base
`87d838e0ecae5de9a05cf0e29115506c58a780ed` plus the sole new test overlay
`tests/sys_process_windows_argv.rs` (SHA-256
`bb05e1168776c17e5b1480796a5f2d39317dd45a698800f2bbeb5af1b6426f14`).
The [manifest](media-input/source-manifest.json) inventories all 450 source
files; the separately supplied lock SHA-256 is
`12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
The frozen [command](media-input/RunRhaiContract.cmd) explicitly selects the
source working directory and compiles the target once with `--locked`.

The public Rhai `run`, `run_raw`, and `spawn` paths each executed the real test
executable under both DirectChild and Managed supervision. Each child wrote an
independent UTF-16 argument record; the parent verified exact spaces, quotes,
backslashes, `$HOME`, `|`, `;`, `&&`, Unicode, a shell-redirection payload and
a final empty argument. The marker remained absent. PID and process creation
time were matched against a live process handle before the child was released;
the exact handle signaled and the exit code was zero. The GREEN target passed
2 tests with 0 failures or ignored tests.

Each of the six modes had a separate deliberately inverted argument assertion.
The command reports exit 101 for each; the original logs contain the named
assertion, child readback and failed libtest result. These controls establish
sensitivity of the equality comparison; they do not claim a deliberately
broken product. All controls and GREEN used the same native build. See
[original export](original-export/) and [combined review](combined-review.md).

The bounded Driver completed in 114.205 seconds, exit 0. The observer reported
closed custody and stopped owned executables; the original Driver reported
`CLEANUP_CONFIRMED=True` and `RUNTIME_REMOVED=True`. The [journal](journal-readback.json)
has eight CRC- and length-validated states through `REMOVED`. The serial export
contained 248 frames and 21 hash-checked original files. The exact own guest
scope was removed after export, with `Test-Path` returning `False`; the own
host stage and ISO were removed, original `sdc` restored and foreign `sdb`
left unchanged ([host cleanup](host-cleanup.json)).

The first media assembly stopped before dispatch because the macOS transfer
added AppleDouble sidecars, documented in [the saved log](assemble-first.log).
Only the eight exact sidecars from this transfer were removed and the same
media was rebuilt; no product test occurred in that failed preparation. A
later local journal-readback command initially passed the export subdirectory
instead of this attempt root; the corrected readback above succeeded without
repeating the native run.

This accepts only the named Windows argument examples and configuration. It
does not close other OS or feature rows, general cleanup-negative controls,
Ticket03 as a whole, or the release matrix. Other existing native proofs remain
applicable only within their recorded source and configuration bounds.
