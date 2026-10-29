# Native Windows SDK link-input diagnostic, attempt 02

## Intended observation and input identity

The installed MSVC `link.exe` help in the `RhaiTest` guest lists
`/LINKREPROFULLPATHRSP:filename` ([exact read-only query](guest-linker-support-command.txt),
[guest result](guest-linker-support-result.png)). This attempt supplied that
option to the one `combined_sys_net` Cargo rustc target, requesting an absolute
input-path response file in the owned runtime work directory. [Microsoft's
documentation](https://learn.microsoft.com/en-us/cpp/build/reference/link-repro-full-path-rsp?view=msvc-170)
describes the option as writing absolute paths of files the linker used.

The selected 448 source files and lock are byte-identical to integrated
fork-main `6d4abe077d5d0ee1b1d89568c53f9fb6c1204c94` for those paths.
[Binding](binding.json) records the source manifest SHA-256
`254d021566408f44b2b645551e2598f7cf9db5fee63c5e34bcc7ea20012ec9ba`,
lock SHA-256 `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`,
all eight immutable media inputs, VM UUID and finite run bounds. The owned ISO
SHA-256 was `dacab5673ad6302decdac93caae32487bc1ba92c9d73689aa0890eb2489546af`;
the [attach readback](attach-readback.json) verified its live `sdc` placement,
original inactive `sdc` and unchanged foreign `sdb`. The guest read back its
OS, absent new scope and three zero-error PowerShell parses before the
hash-guarded dispatch. The [final host preflight](host-dispatch-preflight-final.json)
bound source, ISO, public tool binary pins, capacity, expiry and serial offset.

## Actual result: infrastructure diagnostic, not SDK acceptance

The native `cargo rustc --locked --features testing-environ,sys,net --test
combined_sys_net -- --print=link-args -C
link-arg=/LINKREPROFULLPATHRSP:<owned-work>/link-inputs.rsp` command exited
0. The [original trace](original-export/run/.scoped-evidence-b23b8a7d5f6d4541be7bb2b443b6a26a/runtime/link-trace.log)
line 145 prints the absolute MSVC linker path and the new option with its
absolute owned runtime path. The command then ran the existing host-file
wrong-expectation control (Cargo 101, expected independent-readback assertion)
and corrected one-test control (Cargo 0), as the original logs and markers
show. The observer stopped before validating those controls because the
response file was absent from the retained runtime snapshot. It therefore
honestly recorded `accepted=false`, `product_test_run=false` and
`product_acceptance=false`; this attempt accepts no new product or SDK row.
The [guest failure console](guest-failure-result.png) independently displays
the same missing-file error after the Driver returned.

The evidence snapshot [manifest](original-export/run/.scoped-evidence-b23b8a7d5f6d4541be7bb2b443b6a26a/manifest.txt)
contains `link-trace.log`, wrong and green logs, but no `link-inputs.rsp`.
A [read-only search](guest-rsp-search-command.txt) after runtime removal
found no retained file in the exact outer guest scope
([guest result](guest-rsp-search-result.png)). That later search does **not**
prove whether the file existed earlier. The trace proves that Rust supplied
the option; it does not prove that the linker created the response file. The
cause of the missing file is unconfirmed. It is neither an observed Rhai
product failure nor evidence of selected SDK library paths.

## Custody and cleanup

The Driver exited 0 in 148.87 seconds; the [observer](original-export/observer.json)
reports drained pipes, disposed process, stopped owned executables, absent
inner runtime, no observer kill and no pending custody. The original COM1
capture SHA-256 `8f205dea48fbf1fcebc5b65bcc94e104f44b72398affb6085bd371d6bb51e5f2`
decoded to 218 ordered frames and 15 hash-checked original files
([readback](original-export-readback.json)). The eight journal records passed
CRC/length verification through `REMOVED`
([journal readback](journal-readback.json)). The [guest closure](guest-closure-result.png)
showed the exact runtime absent and no named runner/driver process. The own
outer scope was then removed after a reparse guard and [checked absent at a
fresh prompt](guest-retirement-confirm-result.png). The
[host cleanup](host-cleanup-readback.json) restored original live/inactive
`sdc`, preserved foreign `sdb`, and removed only this attempt's ISO and stage;
separate readback agreed. The accepted prior Windows profiles remain valid.

## Next diagnostic

The independent [combined review](combined-review.md) permits exact cleanup
and rejects SDK acceptance. Before repeating a complete Cargo build, run a
small bounded native linker control inside an owned supervised guest scope.
Observe the response file **before** runtime cleanup, with a second marker
that proves the linker actually executed. If that works, apply the same
file-capture method to the real Cargo target and export the original response
file before cleanup. Resolve and hash the SDK paths from that file. If the
small control fails, investigate option behavior instead of another full
build. All prior matrix rows and this attempt's spent run remain recorded.
