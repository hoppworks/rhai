#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "a90bb2797c791644886326e73e5f70c8"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "0bce3175cb5a0875861e86eb224d4f2ea104ce5c7b394e6876099d91823e3a26"
assert digest(stage / "media-input" / "Start.ps1") == "56f8e56ec14268b71f3207c2d2adc88c69626a2ebf5e266b1f876432c7e8e86d"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "0f166600dc93dbccc2c1c41ee7b76e3ec40876961ce14ca84f47a28e7231bd85"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "e2137024a3862b1c98208e51492d7e7c522b90cad742c6c928b1340b6f1279db"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "9fa92bfcc035f3141a01b9f0e46b9a1664d269aff7bae4429b94f140e71227ae"
assert digest(stage / "dispatch-command.txt") == "5480e0bb015418f9b18fb6055b3b05ea5a781bd39f2adfff187b01aba28c97f3"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
