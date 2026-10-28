#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "879cb849992adcfeb8c0b059be9ae569"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "56d89fcccb40581daacac40c75a924a5235ab952806ecf54d41a826fa15c9c4a"
assert digest(stage / "media-input" / "Start.ps1") == "353b2d611a2fa6f2681a76bb49d9e3fc37b04824a50b465bbe0743493fc47d27"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "97110353920a976af3fbf0540af573332bdb80c5fef3f4e185ced8f1de8db247"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "dd6360e7b5d634551c13ec7f0e7ab2a5c1a297dc15f75279484cc921b3932bfd"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "b16c78f023affe14cae266902804fbfb0916c940ad26b8f1bb2700d9bb8b050e"
assert digest(stage / "dispatch-command.txt") == "7f34e45a1a6d53d2f9e1e1fb9dd33a54378ed7aa455a262353f7ba1205da89b2"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
