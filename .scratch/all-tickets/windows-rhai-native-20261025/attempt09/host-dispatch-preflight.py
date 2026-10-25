#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "9655c547808242c482b9212e0d5451e3"
stage = Path(f"/var/roothome/.local/share/agent-builds/rhai/windows-rhai-native-{nonce}")
medium = Path(f"/var/lib/libvirt/images/rhai-win11-quality/rhai-native-{nonce}.iso")
serial = Path("/var/log/libvirt/qemu/rhai-win11-quality-serial0.log")
expires = dt.datetime.fromisoformat("2026-10-25T21:16:54+00:00")
now = dt.datetime.now(dt.timezone.utc)
assert now + dt.timedelta(seconds=210) < expires, "retained public build has insufficient original lifetime"
assert subprocess.check_output(["virsh", "domuuid", "rhai-win11-quality"], text=True).strip() == "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19"
assert subprocess.check_output(["virsh", "domstate", "rhai-win11-quality"], text=True).strip() == "running"
devices = subprocess.check_output(["virsh", "domblklist", "rhai-win11-quality", "--details"], text=True)
assert any(line.split()[-2:] == ["sdc", str(medium)] for line in devices.splitlines() if len(line.split()) >= 4)
def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()
assert digest(medium) == digest(stage / "rhai-native.iso") == "17b9d508e75949286454bf1ebd4efb1f8ccd4c4daa7f80372975546ae2574f9a"
assert digest(stage / "media-input" / "Start.ps1") == "f6b82ae6d0e14aa4a3bdb94ab5c0c4b762662552a6bb3bddd632075d14abd281"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "c4d347633d4203c8852f58d031745921f096ce7e0905c9b64f4871ee98c81a21"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "06c2b506993c458f1d8a254c449449017e04b880166b73d868a3d6a970c0319e"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "a1b8db0b7e923db0fda851f4406cf0f239486932547a7a8642b7e03b6247f6e0"
assert digest(stage / "dispatch-command.txt") == "ee321e352c90a0eea4cdb32b25b7c6aa00f5d7241c2fce7555acb18ea0399c62"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
