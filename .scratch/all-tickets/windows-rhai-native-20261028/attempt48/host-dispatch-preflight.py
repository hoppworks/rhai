#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "8d56e91209f3cb7641d0c31020e9d248"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "82686079c543832d58e7b88500d3a2d3fda07e34628bc4e1efd625a705c80734"
assert digest(stage / "media-input" / "Start.ps1") == "ec838f73c4e3afb3b57e8915e62c1b6c4241c1f8b0d34352d697bcbcd44544ee"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "fd6092b71bb078a6da158b6d53ac00fb87c0fc99fee5730c0c678af2ed44f083"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "34960f552c0e43d0b4041fcf208088c9291503249080a12415481f0a21719849"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "2c60cb0b8d6fbf9a57b266f0aabb3411bfe188f40fbbea928772e87f3f4194fc"
assert digest(stage / "dispatch-command.txt") == "e992ed5a5c3ad012235b4d8b084d00c3f5969ae7e5b2f4fec989c7f7031ff468"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
