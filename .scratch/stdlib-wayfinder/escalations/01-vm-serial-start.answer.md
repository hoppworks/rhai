# Serial startup diagnosis

## Recommendation

Use an owned PTY serial device with persistent logging in libvirt's existing log directory. This preserves COM1 for the unattended Windows marker, gives a managed console, and removes log creation/deletion from the image directory. Change only this shut-off domain's serial/console definition; leave the old empty image-directory log in place.

```xml
<serial type="pty">
  <log file="/var/log/libvirt/qemu/rhai-win11-quality-serial0.log" append="on"/>
  <target type="isa-serial" port="0"/>
</serial>
<console type="pty">
  <target type="serial" port="0"/>
</console>
```

Do not carry the generated file-backed console from live `dumpxml` into the revised definition. The serial and console must reference the same first serial device. Omit any PTY source path: libvirt allocates it. The source-controlled XML currently contains only the serial element, so it can instead replace that element and let libvirt generate the matching console.

Check that the proposed log path is absent or is an explicitly owned regular file before using it. Let virtlogd create it in the existing root-owned log directory; do not precreate it as qemu or change the shared directory. No SELinux policy module, daemon restart, SELinux disablement, directory permission broadening, or image-directory relabeling is needed for this proposal.

## Live evidence

Read-only inspection on 2026-09-30 confirmed domain UUID `dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19`, state `shut off`, libvirt 12.0.0, QEMU 10.2.2, and SELinux `Enforcing`.

At 05:15:09 UTC, the journal records virtlogd failing to open the image-directory log. At 05:15:23 UTC, it fails to delete the precreated log. Audit journal entries at both times identify `comm="virtlogd"`, source context `virtlogd_t`, denied directory `write`, and target context `virt_image_t`. They also deny `dac_read_search`. The actual log daemon runs as root, not qemu. The image directory is qemu:qemu mode 0750 and the empty log is qemu:qemu mode 0600, both `virt_image_t`. Thus qemu ownership and restorecon to an image type do not grant the logging daemon its required access. File precreation cannot fix parent-directory deletion/recreation rights.

The canonical `/var/log/libvirt/qemu` directory is root:root mode 0700, `virt_log_t`. This domain's ordinary QEMU log already exists there as root:root mode 0600, `virt_log_t`. `matchpathcon /var/log/libvirt/qemu/rhai-win11-quality-serial0.log` returns `system_u:object_r:virt_log_t:s0`. These observations support the canonical log location without changing host-wide security.

`ausearch -ts recent` and `ausearch -ts today` returned no matches; the journal's audit transport retained the relevant AVCs. Lack of ausearch results is not evidence that SELinux allowed the operations.

## Why this backend

Libvirt documents PTY serial ports and optional character-device logging, with its example log under `/var/log/libvirt/qemu`. It documents file-source `append` defaulting to off, consistent with the observed replacement attempt. See [Domain XML character devices](https://libvirt.org/formatdomain.html#character-devices) and [virtlogd](https://libvirt.org/manpages/virtlogd.html).

A PTY alone also removes the failing file backend, but the unattended answer file writes `RHAI_WINDOWS_READY` once during specialize. A reader attaching afterwards could miss that output. The canonical persistent log preserves it. `append="on"` preserves installation evidence across later restarts; an old marker must not be treated as proof of a fresh boot.

## Required follow-through

1. Save the current owned domain XML, revise only its serial/console elements, validate the candidate XML, define it, and read back UUID and both device definitions.
2. Record the serial log's initial absence or byte length, then start only `rhai-win11-quality`. Read back domain state, generated PTY, loopback VNC address, and recent virtlogd/audit messages.
3. Read new serial output from the recorded offset with a bounded deadline. The expected marker is produced by the existing `Autounattend.xml` PowerShell command using COM1. A running hypervisor alone does not establish Windows readiness.
4. Confirm installation independently through the guest console and later read back `C:\ProgramData\rhai-windows-ready.txt`. Update `verify-host.sh` and the README to use the canonical serial log path after successful verification.

The fix is a recommendation supported by live configuration and denial evidence; it was not applied or boot-tested in this read-only diagnosis. Windows installation, guest COM1 delivery, and readiness remain unverified.
