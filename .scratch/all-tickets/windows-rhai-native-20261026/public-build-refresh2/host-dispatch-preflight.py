#!/usr/bin/env python3
"""Read-only host binding immediately before one native public BuildOnly entry."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "e2047d40e48afb4426d07e2a1e881f19"
stage = Path(f"/var/roothome/.local/share/agent-builds/rhai/windows-public-refresh-{nonce}")
medium = Path(f"/var/lib/libvirt/images/rhai-win11-quality/public-refresh-{nonce}.iso")
serial = Path("/var/log/libvirt/qemu/rhai-win11-quality-serial0.log")
expires = dt.datetime.fromisoformat("2026-10-30T12:00:00+00:00")
now = dt.datetime.now(dt.timezone.utc)
assert now + dt.timedelta(minutes=15) < expires, "owned public-build window too short"
assert subprocess.check_output(["virsh", "domuuid", "rhai-win11-quality"], text=True).strip() == "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19"
assert subprocess.check_output(["virsh", "domstate", "rhai-win11-quality"], text=True).strip() == "running"
devices = subprocess.check_output(["virsh", "domblklist", "rhai-win11-quality", "--details"], text=True)
assert any(line.split()[-2:] == ["sdc", str(medium)] for line in devices.splitlines() if len(line.split()) >= 4)

def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()

assert digest(medium) == digest(stage / "public-refresh.iso") == "a53108b8d69e4c86a3a4ec81dc91808610d06fe7fcc75e8066e730e70d78bee8"
assert digest(stage / "media-input" / "Start.ps1") == "aa73bad6324f786629eb6c45533b70bf58291797eb202c39d4e523c91e17484a"
assert digest(stage / "media-input" / "input-manifest.json") == "175fee88ce1625dcd9efca0fb904d5c7cfeb7b96a9a80e25bc90187099a8a276"
assert digest(stage / "dispatch-command.txt") == "ad3f9e274288277870bf825de6305af13ad2ac3e1024490ddf0b3313c6c72498"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
