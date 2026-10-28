# Windows Rust1.77.2 bootstrap attempt 01 — media preflight failure

The guest PowerShell parser accepted `Start.ps1` SHA-256
`a19bfd8fc926a837ba9020f1f86b012d63e40c3a90d05c1130d597c39cd9df1e`.
The host preflight bound VM UUID, original sdb, own sdc ISO SHA-256
`27d63cb9f7ce46c29ca0e538750709057f4387091f98e914a2927970c77a7f49`,
serial inode/offset and current capacity. The typed hash-guarded command was
visually read back before Enter. Original screens and preflight are retained
beside this document.

The script stopped at line 6: enumerating D:, E: and F: called `Join-Path`
on nonexistent F: under `$ErrorActionPreference='Stop'`. This is a setup
failure before any guest scope, Driver, toolchain installation or product
assertion. `after-failure.png` shows `Test-Path` for exact planned guest scope
`n-a7e54f39` returned False and no named Runner/Driver process. The original
sdc was restored; the exact owned attempt-01 ISO was detached, checked for
open users and removed. Foreign sdb was unchanged.

Only the media candidate guard changed. It now checks `Get-PSDrive` before
`Join-Path`, as in the accepted prior native path; independent focused review
returned READY and found same-nonce reuse reasonable because the scope was
never created. Attempt 02 media SHA-256 is
`e16c3f6122cb8a28c5ba24cc4ba5b6423fa8f989094e3922d5e6f1841e34c0b6`
with corrected `Start.ps1` SHA-256
`b18feb739936e50aa53a780328980804beeb8a359a19e19120c70bee4dcbf80c`.
The guest parser accepted that exact corrected source before another dispatch.
No bootstrap or release criterion is accepted by this attempt.
