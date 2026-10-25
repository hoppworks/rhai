# Native Windows memory-limit denial: named custody prerequisite

Status: **accepted for the named real-memory-denial slice only**. The overall
Windows custody gate, native Rhai API matrix, packages A–F and release remain
open. This packet uses the existing `rhai-win11-quality` VM on workhorse and
the public Windows Runner/Driver path with one separately compiled fixture.

## Source and run binding

- `attempt03/input-manifest.json` pins the 15 source inputs (SHA-256
  `58ceb47e7ff658bac8e8a9ce75687ce7682640fbefe84eec716b0719a7e7ea1a`).
  `Start.ps1` is `3ff2c93d4abc8b34ba14d8acfd300699e64ebd3471b3be37f162f12eac7f6167`;
  the ISO was independently read back as
  `827fd7cf7138df1c7d5a48e7eafcd624d876dbf3617c7f8a6a695017fcafb8f0`.
- The changed `PayloadFixture.cs` is
  `f073b677a74cdb0e02f51034bc149163e545109415ec1f4fbab99c67783ffa72`.
  One fixture-only Csc produced `PayloadFixture.exe`
  `dd672cd0c4c666e885dd099d0379019b021dd45b76a61ea492fc583502cdf469`.
  The unchanged default public Runner/Driver were reused from the exact pinned
  build in `../windows-process-quota-20261025/retained-default-build.json`.
- `attempt03/dispatch.json` records the host UTC, exact media/source hash guard,
  serial inode/offset, one fixture compiler and one public Driver. Driver exit
  was 0 in 2.7212673 seconds; 37 original files and 567 sequential frames
  with eight CRC-verified custody records were exported. The independently
  decoded originals and verifier result are in `attempt03/`.

## Observable contract and sensitivity

The native Job reported kill-on-close/no-breakaway flags 2308, an active-process
limit of 16, 1 GiB per-process committed-memory limit and 2 GiB per-Job limit.
The root's 1 GiB commit failed with native error 1455 while system available
commit was 6,267,580,416 bytes. Two exact child identities each committed
768 MiB (private bytes 819,957,760 and 819,986,432). While they remained
owned by the Job, the root's 512 MiB attempt failed with native error 1455;
system available commit was still 4,617,801,728 bytes and root private bytes
were 13,316,096. The protected marker was unchanged. After the recorded child
exited and was reaped, the *same* 512 MiB allocation succeeded with zero
retries. A wrong-limit expectation was rejected, then the intended expectation
passed. The effect and actor records are in the exported fixture files and
`attempt03/host-accepted-readback.json`.

The final control observer reports exact Driver exit, drained channels, stopped
owned executables, no pending custody and removed runtime. The independent
saved-data verifier checks file hashes, source/build pins, journal CRCs,
actual denial/recovery records and the protected marker. A combined independent
review passed the named slice. The later fresh Windows census and cleanup
receipt are in `retirement/`: five exact original actor generations were absent,
the two completed own scopes were removed, and the retained default build's
manifest and three binaries were verified before and after. A separate console
readback printed `MEMORY_READBACK False False True` for those two scopes and
the retained build.

## Attempts, reuse and resource lifecycle

- Attempt 01 stopped at a `Start.ps1` parse error before compiler/Driver.
  Attempt 02 passed that parse check, then a guest-only UTC comparison falsely
  rejected the still-valid retained build before compiler/Driver. The VM's
  clock was about one hour ahead of workhorse; attempt 03 checked the finite
  expiry against workhorse UTC instead. The original attempted media, logs and
  failure records remain preserved.
- A completed fixture-build readback exported 48 original files in 1,321
  sequential frames without compiler or Driver re-execution. Its first frames
  were recovered from the original `.1`, `.0` and live libvirt log inodes after
  rotation. `build-readback/serial-reconstruction.json` records the exact
  inode/offset sources; `build-readback/build-export-readback.json` hashes all
  files. Its `accepted:false` flag correctly means it is a read-only export,
  not a product acceptance run.
- The cleanup manifest binds only the two own scopes and their 37/48 exported
  file hashes. `retirement/guest-cleanup-receipt.json`,
  `retirement/host-cleanup-readback.json` and the fresh console screenshot
  preserve the actual result. The retained default build is outside both
  deletion roots and retains its original finite expiry. Five exact ISO images
  and the host staging were locally archived before host retirement; consult
  `retirement/host-staging-before.json` and `retirement/host-retirement.json`.

## Still open

Actual failed backend export/cleanup and bounded project-command behavior,
then native Rhai Engine/process/filesystem/TCP behavior and the release OS,
feature and MSRV matrix. This memory fixture is a custody prerequisite; it
does not establish those application contracts or authorize Windows Cargo yet.
