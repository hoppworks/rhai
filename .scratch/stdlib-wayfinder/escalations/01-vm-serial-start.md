# Question
How can the owned libvirt Windows VM start with a safe serial readiness channel without changing host-wide security?

# Why escalated
Two start attempts failed: opening serial.log denied, then precreating owned serial.log still produced deletion denied.

# Context by reference
Worktree: /Users/hoppworks/.codex/worktrees/stdlib-net-assessment/rhai.
Configuration: .scratch/stdlib-wayfinder/windows-vm/domain.xml and README.md.
SSH workhorse as root is authorized; domain rhai-win11-quality UUID dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19 is owned and shut off.

# Constraints and decisions
Read-only diagnosis only. Do not disable SELinux, change shared daemons or touch unrelated workloads. Recommend an exact owned-resource fix or switch to a PTY serial backend with evidence. No credentials. Report English without self-attribution.

# Tried so far
Official Pro ISO checksum passed. Serial file under /var/lib/libvirt/images/rhai-win11-quality/serial.log with parent qemu:qemu mode0750 virt_image_t. Initial file absent; precreated mode0600 qemu:qemu and restorecon, next start deletion denied.

# Deliverable
Read live logs/config/audit as needed; write .scratch/stdlib-wayfinder/escalations/01-vm-serial-start.answer.md and return recommendation in at most 15 lines.

# Budget
One bounded diagnosis; no package installations or mutations on host.
