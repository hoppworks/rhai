#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "1c02c386a9eff2b69dc6c7cceefe2d26"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "ec8ed75865842bce13c81974b81d1cc059b7cc0ba2e1000020fd7c7b0d36b811"
assert digest(stage / "media-input" / "Start.ps1") == "769f103a6c7977e15cbefb8b3736ce5f39e4701c7b079a390363774d865c7614"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "bbca880a1152c95e996f28edfcb7a7ea351fc8f9e219b1de50f63865dc838dfd"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "e70d99d6cdc3c8a3383b4ec1feeb7308720a098bc34a303b3b1651af89340319"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "60c2ef4cf3e6dcf377e766d567c1b69c582d0dcfe7d378148f2968a70718f1c9"
assert digest(stage / "dispatch-command.txt") == "ce45dcc0a1385ac14309f273550c9d3e60e44df4ebbbe5e684d5560665487637"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
