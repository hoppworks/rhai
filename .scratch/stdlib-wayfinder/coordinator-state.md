# Standard library wayfinder state

## Current status — 2026-10-07 implementation resumed

All six decision tickets are resolved (specification only). The former unresolved
TCP/release decisions and privacy/remote-cleanup next actions below are historical.
The owner later authorized verified integration only to the hoppworks/rhai fork main;
upstream is excluded. Existing implementation and narrow accepted proof are recorded
in [the campaign state](../all-tickets/coordinator-state.md). This map does not claim
full implementation/release acceptance.

The owner subsequently resumed implementation under the existing acceptance plan.
The active implementation and proof state lives in
[the all-tickets coordinator state](../all-tickets/coordinator-state.md); the
remaining execution plan is [sys-package-plan.md section6](../../docs/sys-package-plan.md#6-remaining-acceptance-plan--revised-2026-10-07).
The goal is active and incomplete. The 2026-10-07 planning-only boundary is
historical and no longer controls current work. The current global/project rules
and relevant skills were re-read for this Session; the loaded central revision and
evidence applicability are recorded in the campaign state. This file preserves the
earlier planning history without creating a second execution plan.

## Historical record — preserved, superseded as current instructions

Earlier scope, owner answers, provisioning proof, causes and consumed attempts follow.
Do not execute their old next steps or infer current guest/build availability from
these snapshots. Accepted baseline scope remains limited to its recorded inputs.

### Original wayfinder record

### Historical: Goal

Chart an implementation-ready plan for sys completion and a separate TCP package,
with high quality, low maintenance, strict verification, and Rhai conventions.

### Historical: Done

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

### Historical: Current step

Tickets 01–03 are resolved. The owner explicitly included managed process groups/jobs
in the first version after reviewing advantages, security and performance effects.
Three decision tickets remain open. No implementation or native process proof has
started. Maximum quality takes precedence over effort.

### Historical: Decisions and constraints

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
- Native Windows baseline now passes (45 tests); the filesystem write control
  failed as intended and passed after restoration. See windows-vm/README.md and
  native-baseline.log. Process/TCP and release-matrix proof remain outstanding.
  Wine is diagnostic evidence only.
- No new research tickets needed yet: prior source inventory and runtime diagnostics
  already answer reuse facts. Delegate research only when a decision exposes a gap.

### Historical: Windows environment provisioning

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
  Owner authorized confirming empty password fields; Windows accepted them.
  Desktop verified through the live guest console. Activation UAC has no usable
  administrator: unattended setup only created RhaiTest in Users. Owner authorized
  a targeted safe-mode recovery with temporary admin rights on 2026-09-30.
  Guest shut down cleanly; baseline disk/UEFI/TPM backup created and qemu-img plus
  SHA256 read-back passed. Cold boot to desktop passed. No restore drill yet.
  Safe mode enabled the built-in Administrator; its console sign-in succeeded
  without a password. net localgroup administrators rhaitest /add succeeded;
  independent group listing includes RhaiTest. Normal boot returned to RhaiTest;
  Change product key opened an empty key-entry dialog. Handed input to owner;
  screenshots were paused to keep their key out of evidence. Temporary rights
  were limited to activation and toolchain setup and have since been removed.
  Owner completed activation. A fresh Settings read showed Active and a digital
  license; PowerShell UAC Yes succeeded. MSVC/SDK and Rust 1.93.0 are installed.
  Native sys_policy 21/21, sys_env 5/5 and sys_fs 19/19 passed. Independent file-read
  expectation control failed with 101, exact source bytes were restored, and the
  correct test passed with 0. No fixture/process leftovers. Temporary RhaiTest
  admin membership was removed; cold-boot token reports Administrator=False.
  Built-in Administrator stays disabled in normal mode; the previously proven
  WinRE/safe-mode recovery path is retained. ready-baseline preserves disk/UEFI/TPM
  after a clean shutdown; image checks and SHA256 read-back passed. Active VM
  cold-booted and remains activated. Restore drill remains unverified.
  The former Path-length cause is closed.
- DVD boot: after missed initial prompt, firmware boot-menu selections failed twice.
  See escalations/02-vm-dvd-boot.answer.md. The answer-justified reset timed out.
  Owner then explicitly authorized one additional attempt with automatic DVD
  acknowledgment. It succeeded: fresh Windows Setup, sustained ISO reads and
  17% installation with disk writes. Boot access and the subsequent desktop are proven.

No existing workloads were stopped, and no host tools were installed.
Reuse ISO verification and unchanged host evidence. Details: windows-vm/README.md.

### Historical: Rules refresh

On 2026-09-30 read global and project AGENTS.md plus current e2e-proof, wayfinder
and rendered wayfinder-pack. The latest global instructions and changed e2e-proof
were reread from their actual repo paths at clean agent-skills
75d0ef5c7c78f0fd3371b4654b5866318c59df3d; wayfinder was unchanged.
Reuse accepted unchanged evidence; retain cause attempt/escalation counts.
Existing owner decisions and privacy constraint remain authoritative.
Future temporary builds use the scoped runner and project output/cache flags.
Windows guest lifecycle adaptation remains a release requirement before another
native build. Retained guest build at C:\RhaiQuality\baseline-source-v2 belongs to
this effort and preserves Cargo.lock, compiled baseline and control diagnostics;
retain until replacement evidence is accepted or the owner ends this VM effort.
The failed source copy C:\RhaiQuality\baseline-source is retained for diagnosis
under the same ownership and cleanup boundary. No shared caches are cleanup targets.

### Historical: Current remote cleanup request

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

### Historical: Next action

Current step: Windows VM/toolchain provisioning and the first native baseline are
complete. Owner authorized resuming on 2026-09-30; no key was read or recorded.
The owned VM is running with RhaiTest as a normal user and activation Active.
MSVC/SDK and Rust 1.93.0 match the initial macOS comparison baseline; the release
toolchain decision remains open. Native evidence is windows-vm/README.md and
native-baseline.log. The first archive failed manifest parsing due to missing
examples; one correction included them and used batch exit-file read-back, then
all targets passed. Preserve the first guest execution copy. The original and
ready backups remain intact; restore drill is not yet proven. Reuse accepted
unchanged ISO, setup and recovery evidence without repeating those operations.

Claimed issues/04-tcp-authority.md while toolchain installation runs; settle its
host-authority decisions with the owner, without production implementation.
Pending owner choice: initial TCP connect plus separately authorized listen/accept
(recommended), or outgoing connections only. Do not resolve this HITL ticket
without the answer. Remote cleanup gate/approval remains separate and unchanged.
Ticket 06 must review process host-config spelling, error-report compatibility and
managed-scope native platform release gates. Cancellation/reaping and scope-setup
prototypes remain implementation gates, not completed evidence. Do not implement
production code during wayfinder planning.
