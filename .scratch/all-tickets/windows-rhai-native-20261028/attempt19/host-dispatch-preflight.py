#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "5cac6ebc2209265ceb215920655aaf60"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "6415e2ca54680c0bd20e5b96749b894e3b5e5ce17e9868888ebacc15a82a6670"
assert digest(stage / "media-input" / "Start.ps1") == "a19dae425fcd2784d3031ea7d2546fc600c022b3832df17c4f6a31c51988cbea"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "acab371bcdead45384d7f0825c95a415a9a1915d24010344d288fe0406aeff88"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "ac53e221d2b2df9c0e7735720896a7d0350dd485a6617936a6c6cf8ee4d84fe3"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "e4670c07b534708b46eda6f8c2aeecef957d3ad4a60495a17ccad4fb32b20ee6"
assert digest(stage / "dispatch-command.txt") == "000bf58321a438e5994157115367bc3c5cf005dc7a5e25a1e80cfe05a4695891"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
