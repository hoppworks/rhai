# Independent combined review, attempt 04

The existing Terra reviewer read the corrected source before the ISO build and
found the hash chain, explicit SDK path, intended work-root outputs, bounded
export and custody layout ready for a small native control. The post-run review
then inspected original compile/driver/journal evidence.

The original `compile.log` has C1083 for `runtime\work\probe.c`. The payload
stdout shows the PowerShell `-File` argument also resolved to
`runtime\work\ClearOwnedWorkReadOnly.ps1` and failed to find the helper.
The batch used `%~dp0` after changing directories; it was launched by relative
name from `runtime`, so that expansion followed `work`. CL exit 2 led to
payload exit 61 (`0x3D`). No link or fresh probe execution occurred.

The next correction must capture the validated runtime-root path before `cd`,
use it for both input files, and require the cleanup helper's exact success
markers. The helper's missing-file message did not itself stop the batch, so
`if errorlevel` alone is insufficient. The original serial frames, CRC journal
and observer support this pre-link failure and closed custody; the guest scope
was separately retired. `host-cleanup-readback.json` records the coordinator's
exact host cleanup and fresh live/inactive readback, which the reviewer did
not independently observe.

**Claim:** bounded preparation failure only. No SDK selection or product
acceptance.
