#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "2c2b7a1d7501e41eae4a50966d1d290f"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "34dbd1829cdb4bcd4b7cef4d03499e0442127e56acfe255775c2e4a048d856f4"
assert digest(stage / "media-input" / "Start.ps1") == "58465eea88f875c1dc6a3104b792ef645c753e6c3314004a2c6eee143b7ce0c9"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "c7c9ff519a0f50bff546ce309b755141a59af51b817fb4205c75c8e6103d93ff"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "4359330ab38694aa973fb6921ec284f174c954bce4e2dfebcfa26fe197386992"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "259ca5adb57122a33ebefe01c3dd93ec80dae5406f01d59033b9e3314f6c048d"
assert digest(stage / "dispatch-command.txt") == "7fb1a2af9af8bd4aa085529a4955f8866b0ba9605accabf10bd1b49d1a5de886"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
