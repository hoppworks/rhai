#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "1d59b495ed0f35962edeabcf841666d3"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "a241fc28b9987d197481dcc6629c1fe5fe37d57bb1bc0d81533ce8ff5dbe8a64"
assert digest(stage / "media-input" / "Start.ps1") == "976e525e97364a0bd144006e98c8345c153108601026b6f8468d7f7b90061535"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "8635142e2c178362ad36c7de2fd6fdda8c8871ddfb5d8ac7e472d745da0afd1b"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "f00f0dc7c5c5d772d60066a7bf5fd91a197eb00a1a49892e7e4650f9bbc6a35c"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "88df8518bbcd5ed1921e72752099047c854047d9e7acacd2b033f255365deb35"
assert digest(stage / "dispatch-command.txt") == "41399d84502c69253e32b8d6ca1df64e6dc68bced17e4d939a0004a0b1049f3b"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
