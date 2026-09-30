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
version 26H2, build 26300.9457. Setup selects Windows 11 Pro. Activation remains
owner-managed. On 2026-09-30 the owner reported activation complete; a fresh guest
Settings view independently showed Windows 11 Pro, Active, activated with a digital
license. This confirms activation state, not the provenance or terms of the license.
No product key is requested or stored.
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
boot returned to RhaiTest; Change product key opened its entry dialog. Screenshots
were paused during owner key entry. Activation is now confirmed in Settings; a
subsequent PowerShell elevation offered Yes and succeeded. Temporary RhaiTest
Administrators membership was removed after provisioning; a fresh cold-boot token
reports Administrator=False. Built-in Administrator remains disabled in normal
mode. The previously verified WinRE/safe-mode recovery path is unchanged.
The specialize-pass serial marker proves the installed edition/build, not completed
OOBE or desktop readiness; verify those separately through the console.
The Microsoft-signed VS 2022 Build Tools bootstrapper completed with exit 0,
installing MSVC x64/x86 and Windows 11 SDK 26100. Rust 1.93.0 installed with the
x86_64-pc-windows-msvc target; rustc and Cargo version commands succeeded and the
serial log emitted RHAI_TOOLCHAIN_READY. See provision-toolchain.ps1; official
instructions: https://rust-lang.github.io/rustup/installation/windows-msvc.html.
The pin matches the accepted macOS baseline, not a final release/MSRV matrix.
run-native-baseline.ps1 completed diagnostic runs of inherited sys_policy (21/21),
sys_env (5/5) and sys_fs (19/19), each with exit 0, from source commit f548fc13.
The initial archive omitted the manifest's examples directory, so Cargo rejected
it before compilation. One correction included examples and replaced unreliable
PowerShell process exit reporting with independently read batch exit files. The
original failed source directory was preserved; the corrected copy is
C:\RhaiQuality\baseline-source-v2. No production source changed.
Guest logs are under C:\RhaiQuality; status/output is copied to the existing host
serial log. The archive excludes planning files and resolves dependencies afresh.

A second cleanly stopped backup is at ready-baseline/ on workhorse, preserving
disk, UEFI, TPM and domain XML after activation, toolchain setup and admin removal.
qemu-img checks and SHA256 read-back passed. The original baseline remains intact.
The active VM cold-booted to RhaiTest; Settings still shows activation Active
([screenshot](ready-screen.png)). This is a cold-boot check, not a restore drill.
The installation ISO was ejected from the domain; its verified file is retained.

## Native filesystem write proof

**Entry point and stack:** real Rhai scripts through Engine, SysPackage and native
Windows filesystem calls in tests/sys_fs.rs::test_write_append_blob.

**Steps:** the declared Cargo integration-test configuration compiled and executed
all three targets. check-native-control.ps1 then ran
`cargo test --features testing-environ,sys,metadata --test sys_fs test_write_append_blob -- --exact --test-threads=1`
with an intentionally wrong file-read expectation and again after restoration.

**Evidence:** [native-baseline.log](native-baseline.log), guest logs and exit files
under C:\RhaiQuality, and the host serial log. Toolchain: Rust 1.93.0,
x86_64-pc-windows-msvc, Windows 11 Pro build 26300.9457. Fresh Cargo resolution
locked 130 packages; its Cargo.lock is preserved in the guest source directory.

**Reused proof:** unchanged ISO verification and VM setup/recovery evidence above.
This native runtime/control check is new; no macOS result substitutes for it.

**Independent read-back:** the test freshly reads real files via std::fs after
script writes. It observes truncation to `second`, string append to `onetwo`, and
exact binary append bytes. Exit files are separately read by PowerShell; output is
observed through the host serial log.

**False-green check:** the `w.txt` expectation was changed to WRONG-CONTROL in the
owned guest execution copy only. The intended assertion failed with exit 101.
Original bytes were restored with matching SHA256; the correct test passed, exit 0.

**Data reset:** TempDir guards removed the owned fixtures, including on the failed
assertion. Independent inspection reported Fixtures=0 and Processes=0. No shared
service or another session's resources were reset.

**Verified:** native build/test baseline and this write/truncate/append contract.
The other 44 baseline tests passed but were not individually given failing controls.

**Unverified:** Windows symlink/junction coverage (the inherited symlink tests are
Unix-only), process/TCP contracts, the release feature/MSRV matrix and an actual
backup restore. The four existing sys review findings remain open; these Windows
results do not invalidate the macOS failures or certify the whole package.

## Read-back and resume

Use `virsh -c qemu:///system dominfo rhai-win11-quality`, `domstate`, `dumpxml`,
`domdisplay`, and a guest screenshot to inspect only this domain. Record actual
Windows readiness separately from hypervisor running state. A cleanly stopped,
installed baseline can be snapshotted before adding compiler/test fixtures.
Do not forcibly stop another domain or delete shared storage. Retain TPM and UEFI
state along with disk state for any subsequent backup or restore.
