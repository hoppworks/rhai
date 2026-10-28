#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "df708abd30fc2cc198ff04fe0bfddb8f"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "bf2b77e27f02e7021595e39edb46e7413a5b7f4af05af5265dfbf2b3829e4b95"
assert digest(stage / "media-input" / "Start.ps1") == "dcbea0b4419e0b6ade20688ede77ecd0b99303aadbbe9bae16d3422ce81dba7a"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "9c87709f0c8ba0ed560c0667b1c432b3111e6fc9bb517bdc98f8a0eb5e1e3232"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "c7ec59c24ee9fe300af0599784a934372dd70acad790fdc5542aad234f89d5a1"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "d0de54225ee1248909a4be838ccaa17238d80041499673fd9d6d0bd3ddc50391"
assert digest(stage / "dispatch-command.txt") == "20c9fe9acff28fe67ef244e7c9c2e4f16ac502a102a7962aaa0a06a972cbd921"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
