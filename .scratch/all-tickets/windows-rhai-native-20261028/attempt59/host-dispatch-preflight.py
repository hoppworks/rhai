#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "3d6e4701fab4530e3c3e8d68af3c882f"
stage = Path(f"/var/roothome/.local/share/agent-builds/rhai/windows-rhai-native-{nonce}")
medium = Path(f"/var/lib/libvirt/images/rhai-win11-quality/rhai-native-{nonce}.iso")
serial = Path("/var/log/libvirt/qemu/rhai-win11-quality-serial0.log")
expires = dt.datetime.fromisoformat("2026-10-30T12:00:00+00:00")
now = dt.datetime.now(dt.timezone.utc)
assert now + dt.timedelta(seconds=300) < expires, "retained public build has insufficient original lifetime"
assert subprocess.check_output(["virsh", "domuuid", "rhai-win11-quality"], text=True).strip() == "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19"
assert subprocess.check_output(["virsh", "domstate", "rhai-win11-quality"], text=True).strip() == "running"
devices = subprocess.check_output(["virsh", "domblklist", "rhai-win11-quality", "--details"], text=True)
assert any(line.split()[-2:] == ["sdc", str(medium)] for line in devices.splitlines() if len(line.split()) >= 4)
def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()
assert digest(medium) == digest(stage / "rhai-native.iso") == "2200f752fd9a398e729987c082f51ccafc1d4c5d9adf3eed5dfdd9b38a3f6da7"
assert digest(stage / "media-input" / "Start.ps1") == "a951df1c5a54e509722b22e1e32526043e1310288aafe62a4c98004e8e2decd5"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "34dbe31a91fca60b9ebe6d6f8f316c88a51c7fd62f265a8b30d5f736cd8208aa"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "93cf81b1fd7b0dece4ca4c08ded6d7a460a72a61f196f2b1ca6434df9097ef0c"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "a4856c1c71d73dae91a1a7657eabcca9489b0cd6467522872806dc0983c1eba0"
assert digest(stage / "dispatch-command.txt") == "71c49f46222b11dfe3bda1242e2944bb6a1565edff385542e6c6e14bf5b50ac5"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
