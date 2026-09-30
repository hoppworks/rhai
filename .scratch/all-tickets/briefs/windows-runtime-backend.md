# Windows runtime custody backend source substep

## Task and context

Continue the existing correction in the owned checkout
/Users/hoppworks/projects/rhai-windows-scoped-runner, task/windows-scoped-runner,
starting at 0999a552. Read its AGENTS.md and the complete design answer at
/Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/escalations/02-windows-runtime-custody.answer.md.
Previous source review is windows-monitor-lease-review.md in the same effort.
Implement the filesystem custody and durable journal backend as an intermediate
source requirement. Leave workload launch disabled until full integration and
native acceptance; never call the unsafe legacy copying/deletion implementation.

## Required contract

- Pin the existing authorized local root C:\RhaiQuality\runs and every ancestor
  through checked non-reparse directory handles, without delete sharing. Reject
  unsupported/nonlocal paths, replacement, sharing or identity failures. Capture
  volume and file identities from handles.
- Generate an exclusive runtime child, protected explicit DACL for the current
  user and necessary SYSTEM access, verified through its opened handle. Do not
  alter any existing root/foreign ACL. Keep runtime pinned throughout custody.
- Evidence/journal live outside payload-writable runtime, with exact owned paths.
  Flush allocation intent before creation and identity after creation. Preserve
  uncertainty in the crash gap; no path-only recovery deletion or successful
  cleanup receipt after monitor loss. Bound records and check write/flush errors.
- Stage opened source handles without following reparses. Pin all relevant
  components; reject mutation/sharing failures. Destination files/directories
  belong to the exclusive recorded runtime. Validate Windows relative executable
  syntax (drive-relative, device, ADS, parent traversal included) and open checked
  staged components. Avoid attribute-check then ordinary path-copy races.
- Cleanup is permitted only with explicit confirmed job emptiness (or before
  payload creation). Enumerate only the pinned runtime; open/check children,
  pin directories, reject reparses, delete verified handles bottom-up. Do not
  clear read-only flags or reparse data. Close disposition handles then check
  absence through pinned parent. Deadline/identity/sharing/read failure retains
  exact data and a failed receipt. No broad cleanup or foreign enumeration.
- Keep watchdog safety explicit: filesystem workers cannot block the monitor's
  lease/process termination. Define bounded integration points; do not pretend
  synchronous Win32 calls provide hard I/O cancellation. Full integration remains
  a subsequent source substep and native behavior remains unverified.

## Verification and deliverable

Write meaningful contract fixture source first. With no safely scoped native
compiler available, leave fixtures unexecuted and say so; do not fabricate
RED/GREEN, use text assertions as behavioral proof, or run process fixtures.
Use primary Microsoft documentation when API details need verification. Implement
one bounded backend slice and report any contract remainder precisely if the
coupled backend cannot fit; do not shrink final acceptance. Commit atomically as
configured human author, no remote writes. Return ref, files, actual checks,
source limitations and exact remaining integration requirements. Coordinator
independently reviews; candidate stays separate.

## Boundaries and history

No guest execution/input, installation/bootstrap, credentials, administrator or
shared configuration changes, agent-home changes, compiler execution or temporary
process fixtures. No new Expert chain. This is the existing single custody
correction justified by escalation 02, with zero completed failed full-custody
corrections. Intermediate source review corrections preserve that history and
do not establish native acceptance. Do not stop merely because native compiler
access is unavailable: the local source substep is authorized.
