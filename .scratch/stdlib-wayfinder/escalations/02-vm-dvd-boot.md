# Question

Why does selecting the Windows installation DVD now leave a blank blue firmware
menu and fail to start Setup? Recommend one bounded corrective attempt.

## Why escalated

Two selections from the firmware boot menu failed to progress. Stop retrying the
same action. This is a fresh cause; the earlier serial-log cause is closed.

## Context by reference

- Worktree: /Users/hoppworks/.codex/worktrees/stdlib-net-assessment/rhai.
- windows-vm/README.md, Autounattend.xml, domain.xml and setup-failure-01.txt.
- SSH workhorse works with BatchMode. Owned domain rhai-win11-quality,
  UUID dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19.
- Owned directory /var/lib/libvirt/images/rhai-win11-quality.
- Live console screenshot /tmp/rhai-win11-quality-screen.png locally; host
  screen.png in owned directory. Serial /var/log/libvirt/qemu/rhai-win11-quality-serial0.log.

## Constraints and decisions

Read current /Users/hoppworks/.codex/AGENTS.md and project AGENTS.md.
Read-only diagnosis; no mutations, reboots, resets, installs or host service changes.
Work remains private: no push, GitHub issue, PR or other external publication.
Preserve unrelated VM tauron-lane-wh-a-58a9dddac6c7 and workloads. SELinux enforcing.
No credentials or activation key handling. Answer must propose scoped recovery.

## Tried so far

First installation booted this exact, SHA256-verified Microsoft ISO successfully,
then failed because specialize RunSynchronous Path exceeded 259 characters.
The command was shortened to 96 characters calling record-windows.cmd on seed ISO.
After clean shutdown, first disk was moved to failed-install-01/system.qcow2 and
NVRAM, TPM and serial states backed up there. A new empty 100 GiB qcow2 disk was
created at system.qcow2. Updated seed ISO. NVRAM and TPM remain reused in place.
VM starts. Initial DVD prompt expired during compaction, then Enter showed boot
menu. First DVD entry UEFI QEMU DVD-ROM QM00003 matches Windows ISO sdb. Repeated
Enter (default and 100 ms hold) clears text leaving solid blue rectangle, with no
new ISO reads or serial text and no disk writes. ESC redraws boot menu. QMP
query-status says running. Other DVD is seed sdc. No QEMU log errors seen.

## Deliverable

Write 02-vm-dvd-boot.answer.md beside this brief. Identify evidence-backed cause
or narrow alternatives, exact one-attempt correction and independent verification.
Reply at most 15 lines plus path. Avoid additional planning artifacts.

## Budget

One fresh Expert diagnosis for this cause; root may perform one justified attempt.
If cause remains after that attempt, root must consult the owner.
