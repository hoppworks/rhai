#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "0cea30ae755133c2a8c46753351e845e"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "2653caa66614cb5e847c77ffea0d4eea2013ebbda36dfeac807083fa3367b0fa"
assert digest(stage / "media-input" / "Start.ps1") == "b3e961b7c76e0c8d4f02e92d2e857a5b6f704daf0fbb5c6bfa49c5b5adb36030"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "67eac4e727aba3bde542a99641d2399d2385f98775cf2ada873a3b0c5300097b"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "625db19008c5aac73bc1c37a0a7ca67aea957cf5c320873251efa94baf8d063a"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "6461aa6c479a386c21f82684a5c1a8f1f017100f43f5783de3efe092e2cf79f6"
assert digest(stage / "dispatch-command.txt") == "0cb51a480bcc386b17aa02d1a82eef868ae99bfe7d845e2892ccf539299842fd"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
