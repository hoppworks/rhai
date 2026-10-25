#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "cdfb68cc215f49ef80b96585aca5aae9"
stage = Path(f"/var/roothome/.local/share/agent-builds/rhai/windows-rhai-native-{nonce}")
medium = Path(f"/var/lib/libvirt/images/rhai-win11-quality/rhai-native-{nonce}.iso")
serial = Path("/var/log/libvirt/qemu/rhai-win11-quality-serial0.log")
expires = dt.datetime.fromisoformat("2026-10-25T21:16:54+00:00")
now = dt.datetime.now(dt.timezone.utc)
assert now + dt.timedelta(seconds=210) < expires, "retained public build has insufficient original lifetime"
assert subprocess.check_output(["virsh", "domuuid", "rhai-win11-quality"], text=True).strip() == "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19"
assert subprocess.check_output(["virsh", "domstate", "rhai-win11-quality"], text=True).strip() == "running"
devices = subprocess.check_output(["virsh", "domblklist", "rhai-win11-quality", "--details"], text=True)
assert any(line.split()[-2:] == ["sdc", str(medium)] for line in devices.splitlines() if len(line.split()) >= 4)
def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()
assert digest(medium) == digest(stage / "rhai-native.iso") == "0cc5d102ec91705b980878222affc52a3d879cc8ee45af045144f8556eb726c2"
assert digest(stage / "media-input" / "Start.ps1") == "dfdf713af43f5906f806830619e80d7814a147c801bdceac7eb5f322c17472d0"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "b5bbee7fcc766500a3394e2f7c2c0a4d6ec3010f128bea7db995d22f76240f78"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "f789f21ccbe350abc566edd67d289c7f17741141cfee4df2cfc1162f3dfe3b14"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "9c72edf9ca6528d9d3c56d371d7ba3dba849671384307b1070686108f52e7d8b"
assert digest(stage / "dispatch-command.txt") == "3ccefff47d1256e5c8cc7b1b530c04bee2f30f8c7943c29bdbed4a4654cb73d5"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
