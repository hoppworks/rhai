#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "5b0ec646505e4e9bac799a1810bfad94"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "52f4371ddf4c24429191efd3550e181a4200af5335a5ffe9c75b875bbe66ae66"
assert digest(stage / "media-input" / "Start.ps1") == "59e3bf325c1dbbffb5df21218cc4241c2cc4dfe3e947c1a11627ea95c4de91f7"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "c96de48330e0e68088e3cfa9973d400bf6aa615276143eb5e2b6c439e63a2515"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "e723596ac3bb1c4c3b26ed03cbf8bf7d333b066e237495718f0014293f11dc2a"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "6f6e805641f8a929d352ff060d7fabe962e4f154634433121885672d45e4af90"
assert digest(stage / "dispatch-command.txt") == "39b3f70adaca83eaaea1c2a36f3ee616c130bb67ab9c97bcaa55d81ec2f83061"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
