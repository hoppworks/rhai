#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "3af4a0ad2db94f06a1ed15f30f07cd7d"
stage = Path(f"/var/roothome/.local/share/agent-builds/rhai/windows-rhai-native-{nonce}")
medium = Path(f"/var/lib/libvirt/images/rhai-win11-quality/rhai-native-{nonce}-r1.iso")
serial = Path("/var/log/libvirt/qemu/rhai-win11-quality-serial0.log")
expires = dt.datetime.fromisoformat("2026-10-26T11:40:00+00:00")
now = dt.datetime.now(dt.timezone.utc)
assert now + dt.timedelta(seconds=210) < expires, "retained public build has insufficient original lifetime"
assert subprocess.check_output(["virsh", "domuuid", "rhai-win11-quality"], text=True).strip() == "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19"
assert subprocess.check_output(["virsh", "domstate", "rhai-win11-quality"], text=True).strip() == "running"
devices = subprocess.check_output(["virsh", "domblklist", "rhai-win11-quality", "--details"], text=True)
assert any(line.split()[-2:] == ["sdc", str(medium)] for line in devices.splitlines() if len(line.split()) >= 4)
def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()
assert digest(medium) == digest(stage / "rhai-native-r1.iso") == "fdba5153911dfd6412e3930945e95120370b837d04b9908b2ff8abc98b01443c"
assert digest(stage / "media-input" / "Start.ps1") == "718cca54738088f092e9466a998fea41653812eaac9bd8c721982f47750be13d"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "3137e93fd098e80fbdb4efa0947a92c2c315314260ba18166c29a0f73eea6185"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "60d8f88be2bb03174d45341d70637e0cc6c7bd6380b9df313e12bb423846301a"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "93fdf6add889907f23d0f837a326430d25ff9dad712e9416e072e19239cbe761"
assert digest(stage / "dispatch-command.txt") == "ef2b7c6f6902081de19b6374fc79b3b87e71235e75f98d6f58c27a290412d532"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
