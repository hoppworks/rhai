#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "ee369f78f6c44ca8a5a7c9abe3a9ba99"
stage = Path(f"/var/roothome/.local/share/agent-builds/rhai/windows-rhai-native-{nonce}")
medium = Path(f"/var/lib/libvirt/images/rhai-win11-quality/rhai-native-{nonce}-r1.iso")
serial = Path("/var/log/libvirt/qemu/rhai-win11-quality-serial0.log")
expires = dt.datetime.fromisoformat("2026-10-26T11:40:00+00:00")
now = dt.datetime.now(dt.timezone.utc)
assert now + dt.timedelta(seconds=210) < expires, "retained public build has insufficient original lifetime"
assert subprocess.check_output(["virsh", "domuuid", "rhai-win11-quality"], text=True).strip() == "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19"
assert subprocess.check_output(["virsh", "domstate", "rhai-win11-quality"], text=True).strip() == "running"
devices = subprocess.check_output(["virsh", "domblklist", "rhai-win11-quality", "--details"], text=True)
assert any(line.split()[-2:] == ["sdc", str(medium)] for line in devices.splitlines() if len(line.split()) >= 4)
def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()
assert digest(medium) == digest(stage / "rhai-native-r1.iso") == "de16baad5df299ce135e319706b584cbbf0dddb94ff6b4554f50ce913238e9a0"
assert digest(stage / "media-input" / "Start.ps1") == "cfd109f29f18425833fe7b0125d396ddfa11f41e2df2b81c0d2d1114376e7828"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "f3de5810880d000107447f95dff40b9c4f260c8cc01e965c7aa0ad7623f16583"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "18fb77a0f08e9e14670d21ad76abaea7512cf7475bf6e4be4f9d5e8fae64cad9"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "0615fa1d025fa9dce8deb4a4388550889f42ab4fd5403545eac4af8e2f2a5661"
assert digest(stage / "dispatch-command.txt") == "e2d73cd7a57e1f63c9f552a9fe00bb1d21b4e0e688439c18168496854f1a3284"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
