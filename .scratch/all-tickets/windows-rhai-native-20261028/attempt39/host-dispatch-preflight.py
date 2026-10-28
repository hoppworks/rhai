#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "2cb45485c2606bf8824397e2a2aed6a4"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "329f0fbaa0f9fe45406a0f07206a8267706da34a062b0d23e8bad7bd9c548496"
assert digest(stage / "media-input" / "Start.ps1") == "28a37d943b68da11361f407ecf2ee85ea097e95c8f3350922bcbf1d97316dc00"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "3abb53ce24005365283bd38f6e56fca33917010c4452522506c67958017e92f4"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "b9059d502ff27c8998597cf246bc0c6c860ee7be8d57f1e91c140a5d5048c88d"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "39d190d45a09dee911902af88d19dfd17e25149db8cb7337d3983023442b8879"
assert digest(stage / "dispatch-command.txt") == "5df169212014b385c413153bc4fdc95e3e6e04693459b58b4366c7f7d2ff54cd"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
