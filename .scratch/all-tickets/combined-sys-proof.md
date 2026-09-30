# Integrated sys filesystem and environment proof

Source: 5f87d339a0658b14ffa1259ab94b1b03b9e5bd05 (local integration of
filesystem task HEAD 17287a96 and environment task HEAD 2221517f).
This supersedes macOS proof of 62526323, retained in commit 609e0064. The
unrestricted path resolver now uses host paths directly without an ambient
directory anchor or current_dir precondition; confined roots keep their authority.

Native environment: macOS 27.0 arm64, build 26A428; Rust/Cargo 1.93.0.
Entry point: `python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py
--timeout 300 -- bash .scratch/all-tickets/verify-combined-sys.sh`.
Actual Cargo command and environment are captured in combined-sys.log.

All configured targets passed together: sys_env 7, sys_fs 24, sys_policy 26.
The invalid-UTF8 filename fixture is explicitly unsupported: EILSEQ 92 while
creating the host fixture. Its test reports the skip under --nocapture. This
passing status does not prove public read_dir NotUtf8 behavior on this host.

The integrated public Engine/script/OS assertions cover the configured-root
symlink/parent selection, unrestricted absolute/relative symlinks and symlink/parent
selection, protected sentinel readback, system-prefix aliases and nested root
permissions, and isolated child environment fixtures. Existing confined-root and
permission cases remain green. The new child-only deleted-cwd regression proves
public exists/is_dir match independent std::fs metadata after unlinking that
child's owned working directory. Child and marker guards cover early exits.
Source review accounted for all three filesystem
and three environment Rust files; focused subsequent test corrections were reviewed.

The meaningful failing controls remain applicable: filesystem configured-root
regression failed against original code and a deliberately wrong expected payload;
environment exact-name fixture failed on a wrong expectation and passed after
restoration. See ../filesystem-contract/proof.md and ../environment-fixtures/proof.md
and their original logs. Integration did not change these assertions or their
relevant paths, so no duplicate control build was made. The deleted-cwd test
additionally failed against the previous resolver and passed after the correction;
see unlinked-cwd-red.log, unlinked-cwd-green.log and unlinked-cwd-guarded.log.

Source, Cargo home/target and test temporary fixtures were scoped under runtime
agent-build-ujkv_m3q. Native runner returned 0 and cleanup removed the exact runtime;
an independent existence check confirmed its recorded path absent. No parent
process environment/current-directory mutation, shared server reset or remote Git
write occurred. Test child success/status is observed by exact-name fixture parents;
filesystem effects are independently read through std::fs as recorded in test source.

Previous native Linux proof is retained in ../linux-sys-proof/proof.md; affected
filesystem/policy checks on this corrected source are underway. No new Linux
completion claim yet. Opening host root/drive/share directories under permission
denial was not safely exercised; removing that unrelated open is source-reviewed.
Process/TCP/file handles, Windows native supervision and the release feature/MSRV
matrix remain unverified.
