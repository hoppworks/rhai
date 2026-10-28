#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "11793de1ce8b3f39329a8068dacec880"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "cb14bf69c857d081e43430b1ac832ec9f9fe247f924be8106b18b06e336b2b03"
assert digest(stage / "media-input" / "Start.ps1") == "67105eac610bdaa5f7a34269b0558d57be8ff607133432908824d9c65df51b7b"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "104da29f297c19660ca59abf9552a4a78c892a7327d0893baead85e9e4bfed9e"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "bf978bf28018ea6b644b9c3c559707eef69b692102aa61b6e6acac13890fba06"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "a062842b50d416e9d70b35237f3a89612d045e7f4947ed87e69ef0a6e5dd3889"
assert digest(stage / "dispatch-command.txt") == "7853e8512748d9ac7f59bc38c147886b5530da394e2bfeac4e66341b7986cad6"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
