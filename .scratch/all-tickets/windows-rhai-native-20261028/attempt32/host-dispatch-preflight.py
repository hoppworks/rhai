#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "94914036ac778e12246ea198233eae01"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "c119e0716c71f97cc720cbc17cfc4d9befefa887175cfb40d10a77b0e164fa11"
assert digest(stage / "media-input" / "Start.ps1") == "36cb461186f463b8cff8790da334b7796fd0391ddcb91f477ed1e6f9b4d50f01"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "65a00f2e9f98f1c206088f8b77bb4f7c217fc305ab90f3558f19feb82aa119f7"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "631c44c771f19243135b22bb8d6a65e99726249b2528b92b0368f5cc4fae8a1c"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "a75991cf6e400ef840b88b553985483f3d56211f21157643b41b7e90c9447ff1"
assert digest(stage / "dispatch-command.txt") == "2b925fb67c733abe6235d0be34d4bb988c48e474bc1b1bdf4cc5b7a388fa9f98"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
