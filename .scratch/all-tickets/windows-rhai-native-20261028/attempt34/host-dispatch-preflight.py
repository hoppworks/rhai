#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "18ebda9895886380691b77e134a6d309"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "e724ec8052b78d03e62659f2394d5e6520b8dbc5058e53327d9f07ee4395444c"
assert digest(stage / "media-input" / "Start.ps1") == "df3854b1824b0a94e5ebeba086cb0f3363e6e84e42b4e431456508cf5558eda1"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "5180d05c1b25f0a893001c4da79022d2aa71d5ede945e4e427bea898f39f4fdb"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "4a1878048d4b3edabd03c84ea5dd65a40c9535dc617d988421cf24acd85bae9a"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "9b41809eaf4da387963fd8a271840b7b4270dbf76cd43c92b76793b265f7d019"
assert digest(stage / "dispatch-command.txt") == "a6a6e1f83f910640dec8624b8675d7cd2e349b847437f2e2e863866c91be1b55"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
