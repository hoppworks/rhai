#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "c1edb3295b7adca388523d436a6d2443"
stage = Path(f"/var/roothome/.local/share/agent-builds/rhai/windows-rhai-native-{nonce}")
medium = Path(f"/var/lib/libvirt/images/rhai-win11-quality/rhai-native-{nonce}.iso")
serial = Path("/var/log/libvirt/qemu/rhai-win11-quality-serial0.log")
expires = dt.datetime.fromisoformat("2026-10-30T12:00:00+00:00")
now = dt.datetime.now(dt.timezone.utc)
assert now + dt.timedelta(seconds=210) < expires, "retained public build has insufficient original lifetime"
assert subprocess.check_output(["virsh", "domuuid", "rhai-win11-quality"], text=True).strip() == "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19"
assert subprocess.check_output(["virsh", "domstate", "rhai-win11-quality"], text=True).strip() == "running"
devices = subprocess.check_output(["virsh", "domblklist", "rhai-win11-quality", "--details"], text=True)
assert any(line.split()[-2:] == ["sdc", str(medium)] for line in devices.splitlines() if len(line.split()) >= 4)
def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()
assert digest(medium) == digest(stage / "rhai-native.iso") == "04f9d6bf75f3e2234cf35ce673bf7f4daed86326ab21890b620351e5753dec4c"
assert digest(stage / "media-input" / "Start.ps1") == "9c20c06c05dbb6225f570bfa4d706b3be396eb2617dbc0464e4fe17e512b5f36"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "7bf2e1b4df3f85db72bfd20a50d83289b29b6176f97600775373cf89b21a9fb4"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "1d09b3366e86a69e1c06b2d295e37b12971f23c966fe8cd6fc661f6bf360f698"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "13d7ee43e3334d9296b17a8804b7a926819df195061e38ee0b0ca36fac48151c"
assert digest(stage / "dispatch-command.txt") == "c2f8ac2b2ababd1364535f62d38cd466f4269ad64ba4c56a18cd02463934f9c5"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
