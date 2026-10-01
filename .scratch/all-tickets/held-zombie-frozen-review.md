# Frozen held-zombie diagnostic review

Reviewed range b801968d221a9f7baac592770d3ac7e2b315e8fd..d9ac39f94a7488877ea182488c85670b18310477 with OCR delegate preview and file rules. Two reviewable files, both reviewed: tests/sys_process.rs and .scratch/managed-unix-scope-close/managed-linux-process-proof.py. Coverage2/2 (100%); coordinator-state.md excluded by OCR unsupported extension, read separately as metadata. This is source review, not native acceptance.

## Blocking findings sent to responsible source context

1. Driver ARCHIVE_SHA=b5f4b962248fcdaec6e0eea983869d6cf0c50ca470015ad91b8fcfedbc7cdc8f disagrees with git archive of emitted source0dcd6e6b7c42fbc4fc4cc3384118f866869ed849. Independent archive readback is0a2f6b2115f29a72a0547533415f042ae04cb6172aec1e9c46f5ce63df7db001. No stage or native invocation is justified with these inconsistent immutable inputs.
2. Public boundary assertions recognize only success bool, exit and capture completeness. An unrelated typed ProcessIo with these report facts could count as a valid boundary. Require successful report or the expected group-closure Io with matching immutable cleanup diagnostics. The driver must also recognize the corresponding exact outcome, instead of checking only stopped-zombie/group/reap receipt fields.

## Static custody assessment

Only fixture R sets subreaper; H public Engine does not change host policy. Exact live PID/start/parent/group identities are acquired with pidfds before ACK. At public return O verifies exact direct leader absence, live H custody, exact W/F stopped zombies held by R and zero-time exit handles. Original PGID signal-zero result/errno is observational evidence only. H remains live until O acknowledges return; R reaps only after O's separate ACK. Shared20s absolute CLOCK_MONOTONIC budget reserves distinct cleanup margins. Prelaunch guards cancel without creating begin-run; H guard drops before R drain. Drain rediscovers early leader-identity and W/F records until deadline, validates exact adopted parent/start and pidfd custody, and writes incomplete/mismatch/syscall receipts without panicking. Missing identities remain incomplete. Existing known-broken gate/SIGKILL omission and restoration retain meaningful ordinary-safety control.

These checks make the bounded diagnostic reasonable after correction and exact staging review. They do not prove exceptional guards execute correctly, general managed normal completion independent of foreign reaping, older Linux fallback, macOS, Windows, MSRV, final feature matrix or release integration. Accepted71 narrower ordinary Linux/shared safety evidence remains applicable to unchanged production inputs.

## Related macOS diagnosis

Actual72 rejected before its intended assertion; new typed SysError diagnostic is required before a further affected native diagnosis. Cause08 Expert/follow-up history and resource limits remain unchanged. No source findings consume a native slot; next actual number73 is unallocated.
