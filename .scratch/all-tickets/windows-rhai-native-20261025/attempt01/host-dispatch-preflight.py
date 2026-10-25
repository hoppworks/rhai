#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "3e02fab1e0f047538d581fa4c9a52c85"
stage = Path(f"/var/roothome/.local/share/agent-builds/rhai/windows-rhai-native-{nonce}")
medium = Path(f"/var/lib/libvirt/images/rhai-win11-quality/rhai-native-{nonce}.iso")
serial = Path("/var/log/libvirt/qemu/rhai-win11-quality-serial0.log")
expires = dt.datetime.fromisoformat("2026-10-25T19:14:01.279906+00:00")
now = dt.datetime.now(dt.timezone.utc)
assert now + dt.timedelta(minutes=8) < expires, "retained public build has insufficient original lifetime"
assert subprocess.check_output(["virsh", "domuuid", "rhai-win11-quality"], text=True).strip() == "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19"
assert subprocess.check_output(["virsh", "domstate", "rhai-win11-quality"], text=True).strip() == "running"
devices = subprocess.check_output(["virsh", "domblklist", "rhai-win11-quality", "--details"], text=True)
assert any(line.split()[-2:] == ["sdc", str(medium)] for line in devices.splitlines() if len(line.split()) >= 4)
def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()
assert digest(medium) == digest(stage / "rhai-native.iso") == "4fd6cbe27775c9118458c57b887a1dde640384ca456001921316e5145e27540e"
assert digest(stage / "media-input" / "Start.ps1") == "1931843b66faa535ea16a754876dbfc1398cda7ee91d40fce65de1796d5be091"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "90a0db9dcb380661624ce564964d1a93e53bcc12ce051a8adfdd1f95444324fb"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "2600784687b66ff4a543ea8948d6d2c6e6d5867aa4df8e61ff14db9542d7f672"
assert digest(stage / "dispatch-command.txt") == "214788a7e370b6cd69ef6a05c1395fef42fd353d29a0b7acaefbd949983b45b4"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
