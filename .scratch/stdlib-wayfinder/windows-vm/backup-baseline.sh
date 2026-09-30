#!/usr/bin/env bash
set -euo pipefail
# Run on workhorse after a clean guest shutdown. Never replaces a previous baseline.
vm=rhai-win11-quality
uuid=dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19
root=/var/lib/libvirt/images/rhai-win11-quality
backup="$root/baseline"
nvram=/var/lib/libvirt/qemu/nvram/rhai-win11-quality_VARS.qcow2
tpm="/var/lib/libvirt/swtpm/$uuid"
[[ "$(virsh -c qemu:///system domuuid "$vm")" == "$uuid" ]]
[[ "$(LC_ALL=C virsh -c qemu:///system domstate "$vm")" == 'shut off' ]]
[[ ! -e "$backup" ]]
qemu-img check "$root/system.qcow2"
mkdir -m 0700 "$backup"
virsh -c qemu:///system dumpxml --inactive "$vm" > "$backup/domain.xml"
cp --reflink=auto --sparse=always --preserve=all "$root/system.qcow2" "$backup/system.qcow2"
cp --preserve=all "$nvram" "$backup/nvram.qcow2"
cp -a "$tpm" "$backup/tpm"
cp --preserve=all "$root/Autounattend.xml" "$backup/Autounattend.xml"
cp --preserve=all /var/log/libvirt/qemu/rhai-win11-quality-serial0.log "$backup/serial.log"
qemu-img check "$backup/system.qcow2"
sha256sum "$backup/system.qcow2" "$backup/nvram.qcow2" "$backup/tpm/tpm2/tpm2-00.permall" > "$backup/SHA256SUMS"
sha256sum --check "$backup/SHA256SUMS"
printf 'Baseline created at %s\n' "$backup"
