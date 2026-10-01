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

## Corrected frozen inputs and staged readback

Root independently reviewed source911fe6fc047cfc5240347ccc4cd11fa56a282ff8: public O asserts recognized successful report or exact closure Io with matching cleanup diagnostic before boundary ACK; driver64a8831611de0d73fe81f875c899fe111beb5848ee7e2058181067f2ac6de596 applies the corresponding gate and outer32 count. Independent git archive44b60f1d1260d90b4bb546aad92ff44f673c3257fc0cd9b1e35faf01c33240d5 resolves the former inconsistent archive. Those two findings are closed source-only.

Root independently read seven SSH workhorse stage hashes at /root/rhai-managed-unix-scope-close-911fe6fc: archive44b60; baseline8bd35; driver64a883; launcher531a075; runner9edd5; empty init e3b0c442; pyguard a3739. Root then checked the actual invocation paths and found linux-process-proof.py and source.tar absent: seven artifact hashes alone do not establish runnable stage wiring. Responsible owner is creating exact copies/aliases to these required names. No native launch consumed by these setup readbacks; root must check those bindings and empty evidence directory before release. macOS73 is terminal/rejected as recorded in native73-review.md; next actual Linux diagnostic74 remains unconsumed until execution starts.

Required basename corrections are independently closed: source.tar SHA44b60 and linux-process-proof.py SHA64a883 match; stage and evidence are real non-symlink directories, evidence empty immediately before release. Root released one bounded actual74 diagnostic under preserved limits. Owner reports attached86682, launcher3855354/PGID3855296, deadline1790895600. No terminal result or native acceptance yet.
