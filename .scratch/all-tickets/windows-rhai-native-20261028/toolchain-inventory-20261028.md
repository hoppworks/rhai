# Native Windows toolchain inventory, 2026-10-28

The Workhorse `rhai-win11-quality` VM was running with its original sdc and
foreign sdb media unchanged. After a read-only screenshot showed an asleep
display, a single left-Control key woke the existing `RhaiTest` PowerShell
session. The command `rustup toolchain list` was entered in that session;
the resulting native console screenshot is `toolchain-inventory-result.png`
(SHA-256 `3be5539e6f9cce7a52792943bc8c9bc0908fe4dcfadb993da61a887a17a9e617`).
It lists only `1.93.0-x86_64-pc-windows-msvc (active, default)`.

This is a current read-only inventory, not a Windows Rust1.77.2 build or an
exhaustive audit of files outside rustup's registered toolchains. It confirms
that the accepted native Windows1.93 evidence cannot by itself close the
optional sys/net Rust1.77.2 release gate. Before that gate, install and bind
the exact 1.77.2 MSVC toolchain under bounded guest custody, confirm the
Windows SDK/dependency lock compatibility, and run the required real
Rhai/Engine/host/OS cases. The existing native Job/monitor route remains the
canonical custody path; a POSIX SSH wrapper alone is insufficient.

The screenshot was hash-matched to the Workhorse original. The exact own host
capture stage was removed after export. Diagnostic asleep/awake screenshots
were discarded; the VM, guest scope, original media and foreign work were
left untouched.
