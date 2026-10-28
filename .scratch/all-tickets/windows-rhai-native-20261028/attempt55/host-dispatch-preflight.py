#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "721a05f238c3d0bea14df69d8a20cd72"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "8cf5482136bd96ccce5e227de8f8a92344db7118058a64dbb0568beb6fdc9788"
assert digest(stage / "media-input" / "Start.ps1") == "e0b7c0caaf40ab43c036ccf7620c8c983c73b762d788f2d0c26075ac8ca8c04b"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "e30f97003023cdb3e519fe7b4e4571d3f1e764f0593a19e35f9d1d42eadcb046"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "898802f5b3c7fa504ce49de2964d26bf35b5237e2e6239edeed0d05104fa63f3"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "982764ab5441c37507e8d76e1258fdb6c47f764709926dfaf7416c7afc9f9aba"
assert digest(stage / "dispatch-command.txt") == "66b9d563eac77a3cdbdd4a8bfc873e0ed4a5eb69c35e8472faea8c44c94aaee8"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
