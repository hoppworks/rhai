#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "113a2b1359e580f2dd9c0b68bf0bc3f3"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "e2dddb462a225808d227326bab60b5f4df2b357c7efceb2b03a4597f389ed87b"
assert digest(stage / "media-input" / "Start.ps1") == "e10051c63f82595dc6972d5b5384ec5dc3f5160b6628174ee98ad460c48f3182"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "f9869a28d073b5e4765e6be110444883bb670886948ae4eaae5260f9bcb88c2c"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "f1a3666b91b0442a6e84f4df5d2f1fc7f5b3bc34c5bee5c2364d092e79733238"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "6d76432f218053b6021ef1229eaad10091ee6263e82265cfac5a8ba43ea49329"
assert digest(stage / "dispatch-command.txt") == "8d60266061b6bfe50c7ccf51a657cc8ad82ab38f860f7b37e6383cf63f163ad5"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
