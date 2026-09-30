#!/usr/bin/env bash
set -euo pipefail
# Run on workhorse. Read-only verification of this environment's owned resources.
root=/var/lib/libvirt/images/rhai-win11-quality
expected=bd4307df32bc8af33b39ccecb1174aeb345386630f89a2b86c7a4e36b55ea650
printf '%s  %s\n' "$expected" "$root/windows11-pro.iso" | sha256sum --check
virsh -c qemu:///system dominfo rhai-win11-quality
virsh -c qemu:///system domblklist rhai-win11-quality
virsh -c qemu:///system dumpxml rhai-win11-quality
if [[ -f /var/log/libvirt/qemu/rhai-win11-quality-serial0.log ]]; then
  tail -n 20 /var/log/libvirt/qemu/rhai-win11-quality-serial0.log
fi
