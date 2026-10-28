#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "9f3636e89a7447e49cdce5e81ad00f2c"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "c32d1209e6550f2241fb0b2e583b82276bdcc6d3cf5ffe6a3ab2acd795ab40f8"
assert digest(stage / "media-input" / "Start.ps1") == "17b123e77a483913dde4aa9c0d2ec60b68a376e4b583a2594b44e8890c46c195"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "ef471c0d4a48dd333ff304cb4933b1e9795545aee8890da05d739b117eef1f78"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "60d8f88be2bb03174d45341d70637e0cc6c7bd6380b9df313e12bb423846301a"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "121004581447d9e8f133d5d014d0eefb613d3d66688d6f235a5be28dfbd5bf34"
assert digest(stage / "dispatch-command.txt") == "510a7ed2fe955dffdb1901b681cde7e555cf9304a7bce9d09f6fe21ef330a44d"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
