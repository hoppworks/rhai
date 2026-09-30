# Diagnosis and one corrective attempt

The proven failure is an expired DVD-loader keyboard prompt. The later blank menu is a firmware/menu re-entry failure whose exact cause remains unverified. Recommend one reset of the owned domain, with its console already being watched, and acknowledge the DVD prompt during the fresh automatic boot. Keep the existing disk, ISO, NVRAM, TPM and Secure Boot configuration.

## Evidence

Read-only inspection on 2026-09-30 found:

- The serial log explicitly records `BdsDxe: starting Boot0002` for `UEFI QEMU DVD-ROM QM00003`, followed by `failed to start ...: Time out`. The hard disk then fails with `Not Found`, and firmware opens `BootManagerMenuApp`. Thus this boot successfully loaded and started the DVD EFI application; it was not initially blocked by a missing ISO or Secure Boot rejection.
- The live XML attaches the official installation ISO to SATA unit 1 (`sdb`, `sata0-0-1`), with boot order 1. The empty disk is SATA unit 0, boot order 2. The seed ISO is SATA unit 2. The screenshot's selected `QM00003` entry matches the installation medium, not the seed.
- The domain is running, UUID `dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19`, and SELinux is enforcing. QMP reports running. `sda` has zero writes; the new qcow2 is 198,208 bytes. No installation is currently progressing on the new disk.
- `sdb` read counters remained at 4,855 requests / 9,943,040 bytes between this investigation's reads. The serial log remained 39,445 bytes with last modification at 07:33:10 +0200. Together with the supplied two failed selections, this supports lack of renewed loader progress.
- The earlier Panther errors in the serial log belong to the previous installation; their presence does not mean Setup has restarted. The backed-up failed disk remains under `failed-install-01/`.
- Host firmware package: `edk2-ovmf-20260812-8.fc44.noarch`; QEMU: `qemu-kvm-10.2.2-1.fc44.x86_64`.

The [upstream firmware menu implementation](https://github.com/tianocore/edk2/blob/master/MdeModulePkg/Application/BootManagerMenuApp/BootManagerMenu.c) clears the screen and switches console mode before calling the selected boot option, then redraws the menu on return. Therefore a blank rectangle alone does not identify a Windows loader fault. The menu/console transition or an early firmware boot path is the strongest remaining location. Upstream source was inspected as explanatory evidence, not established as the exact packaged binary. Lack of new physical ISO reads alone also cannot exclude cached reads.

Reused persistent firmware state is a possible alternative, but no observed security-violation message or evidence of corrupt variables justifies resetting NVRAM. The exact ISO already booted successfully, and the current initial launch also reached its EFI application. TPM state does not explain failure before Windows Setup. The shortened specialize command cannot affect this firmware stage.

## The one bounded attempt

This is a recommendation for the coordinator; no reset or input was performed during this diagnosis.

1. Confirm the exact domain UUID, live disk paths and zero `sda` writes again. If Setup has started since this inspection, do not reset it. Record the serial byte offset and current disk counters. Keep the failed-install backup untouched.
2. Prepare continuous observation of this domain's VNC console before issuing the reset. Use the existing loopback listener/tunnel. Keep observation and keyboard input in one uninterrupted operation so compaction cannot consume the prompt window.
3. Issue exactly once on `workhorse`:

   ```sh
   virsh -c qemu:///system reset dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19
   ```

4. Allow automatic DVD-first boot. Watch the fresh console continuously, or capture screenshots at intervals no longer than 0.5 seconds. On seeing `Press any key to boot from CD or DVD`, immediately inject one ordinary Space press through the owned domain:

   ```sh
   virsh -c qemu:///system send-key dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19 --codeset linux --holdtime 100 KEY_SPACE
   ```

   The earlier Enter selected a firmware menu item; acknowledging the fresh DVD prompt is a separate input. Do not select the DVD entry again in the existing failed menu. Do not blindly repeat keys after Windows begins loading.
5. Give this single attempt at most 120 seconds to show Windows Setup/WinPE. If the prompt is missed, the boot menu returns, the same blank rectangle persists, or no Windows progress appears, stop. Preserve the new screenshot, serial suffix and counters and consult the owner. No second reset, NVRAM reset, ISO alteration or Secure Boot change belongs to this attempt.

The reset is limited to the presently firmware-only owned domain. It clears transient execution state without replacing persistent NVRAM, TPM or disk contents. Do not use `destroy`, `start --reset-nvram`, host reboot, service restart, or commands against the unrelated domain.

## Independent verification

- Observe a fresh Windows Setup/WinPE screen through VNC, and capture a second screen showing subsequent progress. Hypervisor `running` is insufficient.
- Read `domblkstat ... sdb` again and compare with the pre-reset counters: sustained new ISO reads support Windows image loading. Read `sda` separately; new writes support installation only after Setup starts writing. Zero disk writes at the initial language/product-key screen are not a failure.
- Read only the serial suffix after the saved offset. Confirm a new DVD launch and absence of a new DVD `Time out` before declaring recovery. The absence of normal WinPE serial output is not itself a failure.
- Boot recovery is complete when fresh Setup is visible and advancing with corroborating new ISO activity. Later specialize-marker, installed edition/build, OOBE and desktop checks remain separate acceptance requirements. Do not report native Windows testing or desktop readiness from this boot check.

The corrective attempt is unverified until executed. If it succeeds, transient firmware/menu execution plus missed prompt was sufficient to explain the observed obstruction; this would not prove a specific firmware defect. If it fails, the escalation budget for this cause is exhausted and the owner must choose the next action.
