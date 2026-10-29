# Native Windows SDK linker diagnostic, attempt 01

## Scope and result

This is a bounded diagnostic on Windows 11 Pro `10.0.26300.0` with native
Rust/Cargo `1.77.2-x86_64-pc-windows-msvc`, features
`testing-environ,sys,net`, and the 448-file selected source tree matching
fork-main `9ff5dea4208fcf15370a8141bb8ce7bf80236583`. The source manifest
SHA-256 is `254d021566408f44b2b645551e2598f7cf9db5fee63c5e34bcc7ea20012ec9ba`;
`Cargo.lock` SHA-256 is
`12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
The source came from the recorded `7019821` archive plus the committed Windows
test overlay; [binding.json](binding.json) records the byte-for-byte current-HEAD
comparison and eight input hashes. The exact VM and bounded run are in that file.

The native `cargo rustc --locked --features testing-environ,sys,net --test
combined_sys_net -- --print=link-args -C link-arg=/VERBOSE:LIB` command exited
0. Its [original trace](original-export/run/.scoped-evidence-9fd1d1f8b32a43f189d482d6c205f131/runtime/link-trace.log)
line 145 identifies
`C:\BuildTools\VC\Tools\MSVC\14.44.35207\bin\HostX64\x64\link.exe`,
the Rust/Cargo library search arguments, named system libraries, and
`/VERBOSE:LIB`. A read-only post-run guest `Get-FileHash` of that exact linker
path returned SHA-256
`A364AF801A8539E4324D9489313DBF001D959128451FC99A27B24676BBAC058F`
([command](guest-linker-hash-command.txt), [screenshot](guest-linker-hash-result.png)).
This hash identifies the file at the path after the run; it is not a
pre-execution hash.

The trace contains **no** library-search output or resolved Windows Kits
paths. It therefore does not identify the selected SDK `.lib` files or their
hashes. The traced executable `combined_sys_net-c551...` differs from the
`combined_sys_net-4c81...` binary used by the following contract control; the
trace must not be attributed to that green executable. Windows Kit Lib
`10.0.26100.0` was inventoried earlier, but that inventory also does not bind
the libraries selected here. This attempt closes only the exact observed
linker path and post-run hash, not the SDK or release-matrix criterion.

## Contract control and custody

The same bounded guest command then ran the public Engine combined host/OS
contract with a deliberately wrong file-read expectation. Cargo exited 101
at the intended fresh host-file assertion: actual `filesystem-payload` versus
`incorrect filesystem expectation`. The restored targeted test exited 0,
one passed, zero failed. See [wrong log](original-export/run/.scoped-evidence-9fd1d1f8b32a43f189d482d6c205f131/runtime/combined-wrong.log),
[green log](original-export/run/.scoped-evidence-9fd1d1f8b32a43f189d482d6c205f131/runtime/combined-green.log)
and the original command in [RunRhaiContract.cmd](media-input/RunRhaiContract.cmd).
This is a sensitivity control, not a new full-suite run or blanket product
acceptance.

The bounded Driver exited 0 in 164.90 seconds within its 180-second limit;
the observer reported drained pipes, disposed process, stopped owned
executables, absent inner runtime, no observer kill and no pending custody
([observer](original-export/observer.json)). The original COM1 capture SHA-256
`2d4b2f86414a6c3ba10fec10acb6f8b35d34bdf50b277472b8a792e3a5ccc0a5`
decoded to 217 ordered frames and 15 hash-verified files
([export readback](original-export-readback.json)). The eight original journal
records passed CRC/length verification through `REMOVED`
([journal readback](journal-readback.json)).

The guest [closure readback](guest-closure-result.png) showed the exact inner
runtime absent and no named runner/driver process. The exact owned outer guest
scope was removed after a reparse-point guard, then [checked at a fresh
prompt](guest-retirement-confirm-result.png) as absent. The host
[cleanup readback](host-cleanup-readback.json) restored the VM's original live
and inactive `sdc`, preserved foreign `sdb`, and removed only this attempt's
owned ISO and stage; a separate `domblklist`/absence readback agreed.

## Independent review and remaining route

[Combined review](combined-review.md) accepts the bounded diagnostic and
custody, while rejecting any exact-SDK-file or full-release claim. The
`/VERBOSE:LIB` option was passed, but the captured successful Rust invocation
did not surface its linker progress. Before another native run, use a method
that yields resolved absolute input paths in a bounded output file. Microsoft's
`/LINKREPROFULLPATHRSP:<file>` is a candidate: its documented purpose is a
response file listing absolute paths of the files LINK used. Validate its
availability in the installed linker and the exact per-run output/export
path before dispatch. Reuse the accepted prior platform and feature results;
only the unresolved SDK binding needs a new observation.
