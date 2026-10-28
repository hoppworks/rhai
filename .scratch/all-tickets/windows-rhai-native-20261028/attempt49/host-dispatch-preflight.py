#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "f49ac23989d4bc5c53f38ad8fbf06b11"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "06e11b6b42ddda0c034780198af2afbdcf31b9bb637ad79f62ccb0da346fc6f0"
assert digest(stage / "media-input" / "Start.ps1") == "fe06512f6bb50c6cb2f86beef8e2eddf2b41d04c00c0e83e039dfb8904fd7afb"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "fc078b75f64cf520648a9ee199ac9a31c6036d0023c360202a1a264f344001b9"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "b4ecc72d19d5c24d415abff18acb6aaf0062d2ec4a80e5af1f5b7627319a7ecb"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "757b9bee69574b3b9e8980c68b298e17a13e9318b12f78179dc6fe1884a4b94c"
assert digest(stage / "dispatch-command.txt") == "aa92b10282526aa144a9a9d901f40f3e55d4b6e245f921e30f17fe5a936672e5"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
