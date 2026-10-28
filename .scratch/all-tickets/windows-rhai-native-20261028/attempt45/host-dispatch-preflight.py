#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "113f2d02834996789b1ea5ba536e5703"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "051d74f41a799d6f5e28ca76607764011868ea99ea776946cc85f745ebed8a09"
assert digest(stage / "media-input" / "Start.ps1") == "fecc1cf6628e50697f4d006867cd394456a5d1d3e99d27379105fd3cae52bf5c"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "c6b61f2c9676e125b5a2a3f2d02eaf0059ada7db715ad5d4caed418c3f6dc91e"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "65c96be56b7c03a89b3505236a51cedb892742ec8b35e56897634f66fe04cca5"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "777b0889e55217ae97e72c89790cad63ba2142cb39573cb85d3d409ff5b70ada"
assert digest(stage / "dispatch-command.txt") == "ac28aea5cb0e02d456615cbf5ba0a5e306cd5591ee11e0cf22af3d84c3470ef2"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
