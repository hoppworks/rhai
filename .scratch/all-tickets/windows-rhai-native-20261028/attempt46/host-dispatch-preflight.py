#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "9cb2383011c0d3f44f84003b3a0b5737"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "c77616d8ce2a1ba812200df9d810e60fdf78f019c71994ba582842f170202d85"
assert digest(stage / "media-input" / "Start.ps1") == "f89540104631c21a09210781df838e7e1b2dbd96397f07129a8c33ea55f82f94"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "e860ce471374bb06855336b8688a6bb07b0b90990bcb471ee4fb900962eda3e4"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "64c319a687181d5fc07b140871b884559fa4db5b79c67faff8d5002e5abfa049"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "dc3d59aefb30919153173ea89cd658babf1fdbc9dfee51aaa9f929d0f583f3ec"
assert digest(stage / "dispatch-command.txt") == "4a106b8edbd4d0f958547f454da167b103e9432093c8cc2632ec6abcbbbd79f6"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
