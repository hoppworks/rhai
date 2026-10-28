# Native Windows Rust 1.77.2 toolchain prerequisite

This package establishes a retained native Windows MSVC Rust/Cargo 1.77.2
toolchain for the pending release matrix. It does **not** accept any Rhai product
behavior or release row. The VM is `rhai-win11-quality`, UUID
`dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19`, user `RhaiTest`. The public native
`ScopedRunner.exe`/`MonitorAcceptanceDriver.exe` BuildOnly manifest and binary
hashes are recorded in the exported `preflight.json`; that build expires
2026-10-30 12:00 UTC.

## Attempts and cause history

1. [Attempt 01](attempt01-proof.md) stopped on the absent F: drive before scope
   creation or Driver launch. The media-discovery guard was reviewed and fixed.
2. Attempt 02 used corrected `Start.ps1` SHA-256 `b18feb73...` on ISO
   `e16c3f61...`. The native Job installed the toolchain, then the batch
   `findstr /X` check returned payload exit 77 despite exact 36-byte rustc
   output SHA-256 `8d95dab8...`. The terminal `REMOVED` journal and original
   logs are in [attempt 03's export](attempt03-original-export/), which binds
   the prior scope by preflight SHA-256 `34907dd6...`. The empty Driver stdout
   caused a separate null-string Match exception in the outer script. This
   attempt did not produce a bootstrap acceptance record.
3. Attempt 03 reused the installed toolchain but selected `run-verify` below
   the prior session. The public Driver rejected this before starting
   `ScopedRunner`: `custody root must be <private-project-root>\<unique-session>\run`.
   Its [27,065 original COM1 bytes](attempt03-serial-slice.bin), starting at
   host inode 126819933/offset 1,434,109, reconstruct 14 files (9,169 bytes)
   with matching file hashes and chunk offsets. The scriptblock wrote frame
   sequence zero on each frame; the decoder explicitly checks that observed
   limitation, all file hashes, BEGIN/END and file count. The failed Driver
   exited 2, with no new scoped journal. Original result and [capture
   binding](attempt03-serial-capture.json) are retained. This was a runner
   path preflight failure, not a Rhai assertion.
4. Attempt 04 used a new absent `n-a7e54f39-v\run` scope, with only the
   original owned `n-a7e54f39\toolchain-home` reused. The fresh host preflight
   pins ISO SHA-256 `6a527854...`, `Start.ps1` SHA-256 `6e1d484c...`, corrected
   command SHA-256 `ad351600...`, VM UUID, foreign sdb, sdc and serial
   inode/offset. Native PowerShell parser accepted the exact source. Guest
   readback showed the new scope absent and no named Runner/Driver process
   before Enter. Source and focused correction reviews returned READY.

## Accepted prerequisite evidence from attempt 04

The [21,346 original COM1 bytes](attempt04-serial-slice.bin) begin at host
inode 126819933/offset 1,461,174. The [decoder](attempt04-decode-export.py)
reconstructed 36 consecutive frames and 11 files (7,144 bytes), checking
offsets, lengths and SHA-256 on every file. Its [readback](attempt04-export-readback.json)
and [capture binding](attempt04-serial-capture.json) retain the observations.
The exported [bootstrap record](attempt04-original-export/bootstrap.json)
reports `accepted=true`, Driver exit 0, no outer timeout, no pending custody,
and removed inner runtime. The original [Driver stdout](attempt04-original-export/driver.stdout)
reports client exit `0x0000004E`, payload exit `00000000`, confirmed cleanup and
runtime removal; stderr is empty. The eight journal records independently pass
payload-length and CRC32 checks in order from `INTENT` to `REMOVED`; see the
[journal readback](attempt04-journal-readback.json).

The [runner version files](attempt04-original-export/run/) contain exact
`rustc 1.77.2 (25ef9e3d8 2024-04-09)` and
`cargo 1.77.2 (e52e36006 2024-03-26)`, with a zero-exit payload and the
success marker. The retained `rustc.exe` and `cargo.exe` were independently
hashed in the guest after completion; [screen readback](attempt04-toolchain-readback.png)
matches record SHA-256 `a95aa2d9...` and `86e57909...`. A separate
[screen readback](attempt04-cleanup-readback.png) found the exact inner runtime
absent and no named Runner/Driver process. The retained toolchain home held
423,724,103 bytes with no reparse point, and guest C: had 60,760,199,168 free
bytes after the run. The declared retention ceiling is 2 GiB, expiry
2026-11-01 00:00 UTC; no disk quota is enforced. Preserve this toolchain for
the Windows 1.77.2 release cases, then retire its exact owned scope.

The corrected batch compares version-file contents exactly in the outer
acceptance record; the batch itself only requires both executables to exit
successfully. This avoids the observed `findstr` mismatch and retains an
independent accepted-output check. The combined independent Standards/Spec,
correctness and acceptance review returned PASS for this prerequisite.

## Resource closure

[Host cleanup](attempt04-host-cleanup-readback.json) restored the original
VM sdc and left foreign sdb unchanged. The three exact owned ISO images were
unreferenced by active and inactive domains, had no exact file users and were
removed. The [owned staging directory](attempt04-host-stage-cleanup-readback.json)
had no symlinks or exact file users and was retired after local proof export.
The successful attempt's disposable guest outer `n-a7e54f39-v` was removed;
[guest readback](attempt04-guest-retirement.png) returned False for its exact
path. The prior `n-a7e54f39` remains intentionally retained for the stated
toolchain reuse boundary and finite expiry. Its attempt-03 diagnostic files
remain with that retained scope and will be retired with it after the Windows
1.77.2 matrix work or at expiry.
