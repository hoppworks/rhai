# Integrated sys filesystem and environment proof

Source: 6252632335d3564f92dc03ea9679c15509339ac7 (local integration of
filesystem task HEAD 30821b55 and environment task HEAD 2221517f).
Current subsequent commits change only campaign documentation/scripts; relevant
production source and integration assertions are unchanged.

Native environment: macOS 27.0 arm64, build 26A428; Rust/Cargo 1.93.0.
Entry point: `python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py
--timeout 300 -- bash .scratch/all-tickets/verify-combined-sys.sh`.
Actual Cargo command and environment are captured in combined-sys.log.

All configured targets passed together: sys_env 7, sys_fs 23, sys_policy 26.
The invalid-UTF8 filename fixture is explicitly unsupported: EILSEQ 92 while
creating the host fixture. Its test reports the skip under --nocapture. This
passing status does not prove public read_dir NotUtf8 behavior on this host.

The integrated public Engine/script/OS assertions cover the configured-root
symlink/parent selection, unrestricted absolute/relative symlinks and symlink/parent
selection, protected sentinel readback, system-prefix aliases and nested root
permissions, and isolated child environment fixtures. Existing confined-root and
permission cases remain green. Source review accounted for all three filesystem
and three environment Rust files; focused subsequent test corrections were reviewed.

The meaningful failing controls remain applicable: filesystem configured-root
regression failed against original code and a deliberately wrong expected payload;
environment exact-name fixture failed on a wrong expectation and passed after
restoration. See ../filesystem-contract/proof.md and ../environment-fixtures/proof.md
and their original logs. Integration did not change these assertions or their
relevant paths, so no duplicate control build was made.

Source, Cargo home/target and test temporary fixtures were scoped under runtime
agent-build-w7hckza5. Native runner returned 0 and cleanup removed the exact runtime;
an independent existence check confirmed its recorded path absent. No parent
process environment/current-directory mutation, shared server reset or remote Git
write occurred. Test child success/status is observed by exact-name fixture parents;
filesystem effects are independently read through std::fs as recorded in test source.

Other native operating systems, the invalid-name API behavior on a supporting
filesystem, process/TCP/file handles and the release feature/MSRV matrix remain
unverified. Native Linux proof of this exact integrated source is underway separately;
Windows must first prove the new guest supervision adapter.
