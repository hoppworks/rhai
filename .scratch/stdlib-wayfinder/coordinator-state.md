# Standard library wayfinder state

## Goal

Chart an implementation-ready plan for sys completion and a separate TCP package,
with high quality, low maintenance, strict verification, and Rhai conventions.

## Done

- Owner accepted both recommendations on 2026-09-30: initial scope sys plus TCP;
  scripts are owned or reviewed, with explicit host authority and no OS sandbox claim.
- Read wayfinder, grilling, domain-modeling, local tracker and ponytail checkpoint.
- Reused the session-owned worktree and preserved all existing scratch evidence.
- Created map.md and six decision tickets. No production code changed.
- Owner accepted the concrete acceptance contract; ticket 01 is resolved, indexed
  from the map, and its E2E configuration is recorded in AGENTS.md.
- Owner accepted the exact filesystem path contract; ticket 02 is resolved and
  indexed. The sys plan records P14/F22/F23 and historical implementation limits.
- Read back nine planning/glossary files; local links resolve and dependency graph
  is acyclic. The main checkout is clean after relocating the new own files.
- Existing evidence: ../../docs/sys-package-plan.md and
  ../../docs/net-package-assessment.md; prior assessment state remains untouched.

## Current step

Tickets 01–03 are resolved. The owner explicitly included managed process groups/jobs
in the first version after reviewing advantages, security and performance effects.
Three decision tickets remain open. No implementation or native process proof has
started. Maximum quality takes precedence over effort.

## Decisions and constraints

- Verification strict; Coordinator merges automatic only green.
- Owner selected fully private work on 2026-09-30 after public fork visibility
  was verified. Current effort is local/workhorse only; no further remote pushes.
  Previously pushed fork HEAD: 0c88657b; existing remote history is preserved.
- Worktree: /Users/hoppworks/.codex/worktrees/stdlib-net-assessment/rhai.
- Branch: task/stdlib-net-assessment; origin: https://github.com/hoppworks/rhai.git.
- No production implementation, merge, upstream action or new library dependency.
  Owner explicitly authorized Windows VM provisioning on workhorse.
- Strict verification config is accepted and recorded in AGENTS.md. No runtime
  acceptance proof has been claimed in this planning step.
- Four sys review findings remain unresolved: configured-root symlink/parent semantics,
  permissive symlink handling, macOS configured-root aliases, and non-UTF-8 fixtures.
  Review source: /Users/hoppworks/projects/rhai-review-sys-windows;
  captured details: /Users/hoppworks/projects/rhai-review-sys-windows/.scratch.
- Real Windows verification is outstanding; Wine is diagnostic evidence only.
- No new research tickets needed yet: prior source inventory and runtime diagnostics
  already answer reuse facts. Delegate research only when a decision exposes a gap.

## Windows environment provisioning

The owner authorized SSH work on workhorse and a Windows VM on 2026-09-30.
SSH works; KVM/QEMU/libvirt/UEFI/TPM are present. The owned domain is
`rhai-win11-quality` (4 vCPUs, 8 GiB, sparse 100 GiB disk), with resources under
`/var/lib/libvirt/images/rhai-win11-quality`. Official Windows 11 retail media
for Pro downloaded completely and matched Microsoft's published SHA-256.

Cause history:
- Serial startup: two failures, one Expert escalation, one successful corrected
  attempt using PTY plus the canonical libvirt log directory. Closed; reuse
  escalations/01-vm-serial-start.answer.md. SELinux remains enforcing.
- Windows specialize: first installation failed because RunSynchronous Path
  exceeded Microsoft's 259-character limit. Guest Panther evidence is
  windows-vm/setup-failure-01.txt. One correction applied: call a separate
  record-windows.cmd through a 96-character Path. The first disk, firmware, TPM
  and serial evidence are preserved on workhorse in failed-install-01/.
  The second installation uses a new disk and corrected seed. Specialize succeeded:
  the live serial log reports RHAI_WINDOWS_READY Microsoft Windows 11 Pro Build=26300.
  OOBE completed to first sign-in. Windows demands a password change for RhaiTest.
  No password entered or changed; explicit permission to confirm empty fields is
  pending under the credential rule. Desktop, baseline and cold boot remain pending.
  The former Path-length cause is closed.
- DVD boot: after missed initial prompt, firmware boot-menu selections failed twice.
  See escalations/02-vm-dvd-boot.answer.md. The answer-justified reset timed out.
  Owner then explicitly authorized one additional attempt with automatic DVD
  acknowledgment. It succeeded: fresh Windows Setup, sustained ISO reads and
  17% installation with disk writes. Boot access is proven; desktop is pending.

No existing workloads were stopped, and no host tools were installed.
Reuse ISO verification and unchanged host evidence. Details: windows-vm/README.md.

## Rules refresh

On 2026-09-30 read global and project AGENTS.md plus current e2e-proof, wayfinder
and rendered wayfinder-pack. Sources resolve to agent-skills d8dfb0b (clean).
Reuse accepted unchanged evidence; retain cause attempt/escalation counts.
Existing owner decisions and privacy constraint remain authoritative.

## Current remote cleanup request

Owner explicitly requested cleaning the existing public fork while new work stays
private. Remove remote branches only after their existing public heads are merged
into main. Backup: remote-cleanup/fork-before-cleanup.bundle, verified complete.
No remote mutation yet. Three public heads: claude/vibrant-sagan-3g1pxn 118745c6,
replace-smartstring-with-compact-str 6a64e7ec, task/stdlib-net-assessment 0c88657b.
Private HEAD 869c9b75 and later private commits must not be included in remote cleanup.
Candidate worktree /Users/hoppworks/projects/rhai-remote-cleanup, task/remote-cleanup.
Merge of public assessment head is staged, uncommitted, with .scratch, AGENTS.md,
CONTEXT.md and docs removed from the index (local files preserved). The first gate
failed at macOS non-UTF-8 filename fixture creation, before Rhai. The separately
run policy target also failed test_symlinked_root at the absolute configured-root
alias read; this is inherited runtime behavior, not a fixture problem. Results:
env 6/6, filesystem 20/21, policy 22/23. Owner approval for the fixture correction
is pending; a runtime repair is also required before the selected gate can pass.
Do not merge/push/delete while failed checks remain.
No private changes, remote history rewrite or upstream action is authorized.

## Next action

Current step: finish and verify the owned Windows Pro VM installation.
After that: claim issues/04-tcp-authority.md and settle TCP permissions.
Ticket 06 must review process host-config spelling, error-report compatibility and
managed-scope native platform release gates. Cancellation/reaping and scope-setup
prototypes remain implementation gates, not completed evidence. Do not implement
production code during wayfinder planning.
