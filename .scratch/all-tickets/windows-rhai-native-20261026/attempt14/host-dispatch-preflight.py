#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "125661064694d9b32879b4e665dff275"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "13de27c0dba744771a630760b23382ca3652f7a80fbd82aea4ca781c7f7d0359"
assert digest(stage / "media-input" / "Start.ps1") == "e7422f1a0f42fbb3c80014843f2c05bcb79154d326e2d481fd385258948e57a0"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "32ce1f4c2e0e9b5d6451e1bbb6e5ae420a62ba4f085db6128f8349611d13cf20"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "1b3fc43f2efed56f8d2fceb9e2c171f775c6101741d774652d7be2516374bd2e"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "2ebf757c08515e22504cf2a8d905e54afe082aa89cd597e25190513cda484dd4"
assert digest(stage / "dispatch-command.txt") == "0113da0fdcac99e7a51548157f06d89a67517cdab93aff01c06f456bad03f446"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
