# Independent source and native-run preparation review

The independent combined reviewer examined the argv test and its scoped native
launch preparation. The first review found an unwanted public Cargo binary and
PID reuse before opening the observer handle. Both were removed or corrected:
the test re-executes its existing test binary, and the observer compares the
creation time on the opened process handle before allowing termination.

The follow-up found no further specific source or launch blocker. The six
variants exercise `run`, `run_raw`, and `spawn` for DirectChild and Managed.
Readback includes arguments, a shell-injection marker and exact child exit.
The scoped command requires each wrong control to have exit 101, the matching
assertion and the failed test result; GREEN requires all six child readbacks.
The command works from its copied source directory. Frozen source, lock,
toolchain and control files are hash bound. The Driver and Observer limits are
180 and 185 seconds; exports have a 180-second deadline. The already reviewed
native Driver supplies external Job custody, still to be proven for this run.

This is pre-execution review only. Actual native Windows behavior, cleanup,
controls, readback and the applicability of any result remain unverified until
the complete output and custody journal are recovered and reviewed.
