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
created. Windows installation and guest readiness remain pending until explicitly
recorded below. Rust/MSVC toolchains and native Rhai tests are not installed or run.

## Read-back and resume

Use `virsh -c qemu:///system dominfo rhai-win11-quality`, `domstate`, `dumpxml`,
`domdisplay`, and a guest screenshot to inspect only this domain. Record actual
Windows readiness separately from hypervisor running state. A cleanly stopped,
installed baseline can be snapshotted before adding compiler/test fixtures.
Do not forcibly stop another domain or delete shared storage. Retain TPM and UEFI
state along with disk state for any subsequent backup or restore.
