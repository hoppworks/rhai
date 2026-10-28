# Native Windows SDK inventory

Read-only guest console inventory on 2026-10-28, after the first accepted
Windows Rust 1.77.2 combined case and before the integer-only profile, found
`KitsRoot10=C:\Program Files (x86)\Windows Kits\10\` and exactly one
`Lib` directory, `10.0.26100.0`; see [guest result](sdk-result.png) and its
[command](sdk-command.txt). No Visual Studio product directory was visible
under either checked `Program Files` root; only `Installer` and `Shared`
appeared in the x86 root; see [guest result](vs-result.png). The earlier
interactive `where.exe link; where.exe cl` found neither command on PATH.
These observations identify an installed Windows Kit, not the exact linker or
SDK files selected by Rust's successful builds.

Both console result images and their commands were copied with matching
SHA-256 from the unique owned Workhorse host scope. That scope was then
removed; [readback](host-sdk-scope-cleanup.json) records the exact file hashes
and absence. No SDK, Visual Studio installation or VM configuration changed.
