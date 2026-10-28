#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "4a12b19a06a82e0422fd70c986713da7"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "195b9f49a02cbcfc4372a7ab8537a6bcc6287709b8fef7f562f421d0e789721a"
assert digest(stage / "media-input" / "Start.ps1") == "51bf8795c760bd74bcf6363f3c415aa515bf7fb36b39024e5b85b32911278a97"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "438f37ed4c6a8a1c9a7fab9f27160c03d0dac1ee72f658909c232d6bb01f7f3a"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "888de39f81168d11ad439b10ec63eddaaea49d1f0e99689d3ae80dfacf5dceae"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "2ebf757c08515e22504cf2a8d905e54afe082aa89cd597e25190513cda484dd4"
assert digest(stage / "dispatch-command.txt") == "5b400fcd497bf6e5ff21e25b4e749b6ea35495278a3d84b07dcd03436ae8599c"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
