#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "3c96a0b66285128f0ceef7306660cd8c"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "36084d9fbad0e09b8a8cc4084a36bf35dc6c2d752aeba4a03dcf5cea57a35ae6"
assert digest(stage / "media-input" / "Start.ps1") == "f4db41b826268f349f3e402c1c8e5f8475356132cdf431541e9ccd8f2728e473"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "fe51bb8af8ae98915c0160c9f6571f7b59b53d0bd4346d717d74fa61a06de199"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "b9059d502ff27c8998597cf246bc0c6c860ee7be8d57f1e91c140a5d5048c88d"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "c21adcc1c0eb231351f4c97c336a8b7b2f9311bf2ceb7eea7cac0d532df2fa8c"
assert digest(stage / "dispatch-command.txt") == "914a18a502d69baa493397f90420076807e7d671a955e50ec14dbd3b64962594"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
