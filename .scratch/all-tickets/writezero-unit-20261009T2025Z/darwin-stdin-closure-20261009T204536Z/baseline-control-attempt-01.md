# Darwin stdin known-broken baseline attempt 01

The correct test fixture ran against the BrokenPipe-only revert at `b04b486d2f7a6d80729c90d276523bfcdd89e6b9`. It independently observed fd 0 absent while the same child remained live, then the first bounded `Child.wait` returned the baseline's missing-error result. Explicit fallback kill/wait completed. Classification stopped before the nominated RED assertion because `/bin/ps -p <reaped-pid>` returned status 1 with empty output and `darwin_process_identity` treated this valid absence result as a tool error. Therefore this is not accepted RED and does not count as product failure or pass. Raw output and status are retained in `baseline-control-attempt-01.log` and `.status`; runner status and exact scope retirement are separately recorded.

Correction: accept only `/bin/ps` status 1 with empty stdout and stderr as absent PID; other nonzero results remain errors.
