#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "e1644d91699d48e39fc2d5a2cbe90371"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "a526d368d57fbb3ab159ee53ce051a66cf7cf790d8991ce578b2399b5bc41988"
assert digest(stage / "media-input" / "Start.ps1") == "b5229ffc353f02b2ffe6d873ab25072af52d9acb9ca021818c6875678773e625"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "b0753172190a8e495e09e1dbf537d9da55cae556f958b7556306b2de8b3f49f5"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "06c2b506993c458f1d8a254c449449017e04b880166b73d868a3d6a970c0319e"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "5038c25da7de346833cb607320c5fa601828ed40a6d299d902ba9c7ba3e2000d"
assert digest(stage / "dispatch-command.txt") == "d12fb19875fe80cea454b92c37bbffa51187b13ea5c4474b983ccdaab71cf963"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
