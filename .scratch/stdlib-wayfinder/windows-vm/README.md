# Windows test VM on workhorse

## Authorization and purpose

The owner authorized SSH work on `workhorse` and creation of a Windows VM on
2026-09-30. This environment supports later native Windows acceptance for Rhai;
creating it does not certify any library feature. Existing workloads and the
unrelated `tauron-lane-wh-a-58a9dddac6c7` VM must remain untouched.

## Owned resources

- Domain: `rhai-win11-quality`, libvirt `qemu:///system`.
- Host directory: `/var/lib/libvirt/images/rhai-win11-quality`.
- Guest disk: `system.qcow2`, sparse 100 GiB; no host disk or directory passed through.
- Guest resources: 4 vCPUs, 8192 MiB RAM, UEFI Secure Boot and emulated TPM 2.0.
- Network: existing `default` NAT network; no changes to shared network configuration.
- Console: VNC bound to host `127.0.0.1`; access via an SSH tunnel, never a public listener.
- Local guest account: `RhaiTest`, ordinary Users group, no supplied password;
  no RDP, WinRM or guest SSH service enabled by this setup. Console access remains
  protected by host SSH access. Do not store credentials in this repository.
- No host reboot, shared service restart, package installation or autostart requested.

## Installation medium

Official Microsoft Windows 11 multi-edition retail ISO, English US, x64,
version 26H2, build 26300.9457. Setup selects Windows 11 Pro. The owner reports
an existing Windows Pro license; activation and license applicability to this VM
remain owner-managed and unverified. No product key is requested or stored.
The earlier Enterprise Evaluation download was stopped and is not used.

- [Download and verification source](https://www.microsoft.com/en-us/software-download/windows11)
- Official EN-US SHA-256: `BD4307DF32BC8AF33B39CCECB1174AEB345386630F89A2B86C7A4E36B55EA650`.
- Downloaded filename: `Windows11_Client_x64_en-us_26300_9457.iso`.
- Owned local filename: `windows11-pro.iso`.

The download is written as `.iso.part`. Verify against Microsoft's hash before
renaming to `.iso` and booting. Domain XML and unattended answer file are beside
this document. The answer file repartitions guest disk 0, which must be only the
new owned `system.qcow2`; never reuse it against an existing or passed-through disk.
XML parsing and libvirt schema validation do not validate Windows answer-file semantics.

## Current evidence

SSH access, host KVM/UEFI/TPM support, resource availability and libvirt domain
schema were checked live. The domain is defined; its sparse disk and seed ISO are
created. The official Pro ISO downloaded completely and matched Microsoft's published
SHA-256. The serial startup failure was diagnosed and fixed by using a PTY with
logging under `/var/log/libvirt/qemu/rhai-win11-quality-serial0.log`, the existing
libvirt log directory. SELinux remains enforcing; no shared service was restarted.
Diagnosis: ../escalations/01-vm-serial-start.answer.md.
The first installation stopped during specialize: the inline readiness command
exceeded the documented 259-character RunSynchronous Path limit. Panther evidence
is in `setup-failure-01.txt`. The corrected answer file calls `record-windows.cmd`
from the seed ISO through a 96-character command. A second installation is running
on a fresh disk; the first disk, NVRAM, TPM state and serial log remain on workhorse
under `failed-install-01/`. After the DVD prompt timed out and firmware menu retries
failed, one Expert diagnosis and its single reset attempt did not recover boot.
The owner authorized one further attempt with automatic DVD acknowledgment; this
reached fresh Setup and installation progress with corroborating disk writes.
See `../escalations/02-vm-dvd-boot.answer.md` and `boot-failure-02.log`. The product-key screen was skipped
using its built-in "I don't have a product key" option. The live serial marker now
reports `RHAI_WINDOWS_READY Microsoft Windows 11 Pro Build=26300`. OOBE reached
first sign-in, where Windows requires a password change for the local RhaiTest
account. Owner authorized empty fields, which Windows accepted. Desktop and a
cold boot were verified. A cleanly stopped baseline with disk, UEFI and TPM is
at `baseline/` on workhorse; image checks and SHA256 read-back passed. Restore
has not yet been exercised. The missing administration account blocked activation.
Owner authorized targeted safe-mode recovery and temporary RhaiTest admin rights.
Built-in Administrator sign-in succeeded in safe mode; adding RhaiTest to
Administrators succeeded and a fresh group listing confirmed membership. Normal
boot returned to RhaiTest; Change product key opens its entry dialog. Owner now
controls key entry; screenshots are paused. Activation and any UAC after key
submission remain unverified. Remove temporary rights after activation
and toolchain provisioning, retaining a usable administration path.
The specialize-pass serial marker proves the installed edition/build, not completed
OOBE or desktop readiness; verify those separately through the console.
Rust/MSVC toolchains and native Rhai tests are not installed or run.

## Read-back and resume

Use `virsh -c qemu:///system dominfo rhai-win11-quality`, `domstate`, `dumpxml`,
`domdisplay`, and a guest screenshot to inspect only this domain. Record actual
Windows readiness separately from hypervisor running state. A cleanly stopped,
installed baseline can be snapshotted before adding compiler/test fixtures.
Do not forcibly stop another domain or delete shared storage. Retain TPM and UEFI
state along with disk state for any subsequent backup or restore.
