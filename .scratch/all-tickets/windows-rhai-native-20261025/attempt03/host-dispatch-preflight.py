#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "88b0797744d34d97861d1b3e681069fb"
stage = Path(f"/var/roothome/.local/share/agent-builds/rhai/windows-rhai-native-{nonce}")
medium = Path(f"/var/lib/libvirt/images/rhai-win11-quality/rhai-native-{nonce}.iso")
serial = Path("/var/log/libvirt/qemu/rhai-win11-quality-serial0.log")
expires = dt.datetime.fromisoformat("2026-10-25T19:14:01.279906+00:00")
now = dt.datetime.now(dt.timezone.utc)
assert now + dt.timedelta(seconds=210) < expires, "retained public build has insufficient original lifetime"
assert subprocess.check_output(["virsh", "domuuid", "rhai-win11-quality"], text=True).strip() == "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19"
assert subprocess.check_output(["virsh", "domstate", "rhai-win11-quality"], text=True).strip() == "running"
devices = subprocess.check_output(["virsh", "domblklist", "rhai-win11-quality", "--details"], text=True)
assert any(line.split()[-2:] == ["sdc", str(medium)] for line in devices.splitlines() if len(line.split()) >= 4)
def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()
assert digest(medium) == digest(stage / "rhai-native.iso") == "c5d645a43707c44a597f970cf3a43a63b5e9ba1cbc3a99b73faeff71b3c12456"
assert digest(stage / "media-input" / "Start.ps1") == "9a15e23abecfcc5061b5d71c2d362fe4c0225ef84b25d0a98d4b87caab53cb83"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "80b49c51bd2f72a67c6668f9b71e8a55d9906ec6fe659173fa52144266c18a49"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "35e9384b983c0e634cf392093d3091178b11a85c828d216e689f980799d8583a"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "d7a2e034ebdccec0fd62c033096c88c992364d0665737d4b445c2e4f8a999c1a"
assert digest(stage / "dispatch-command.txt") == "d232ed260e760d62b6cb13e02fe4e2a707036f50466eac3855cbbcd0b2ffb488"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
