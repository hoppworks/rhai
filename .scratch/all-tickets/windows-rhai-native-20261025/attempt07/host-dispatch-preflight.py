#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "f0574ef3db2445e1826ac702a85126eb"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "eb1339b32a786569dbb5e49844a0d979d7a4d131f50540c11744894b86ca34bc"
assert digest(stage / "media-input" / "Start.ps1") == "f59d61a765c9a557d5fd57f4b07b62a9e3a52ccfbeac32e2c3c2e6332bedc30d"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "6f6b256a5aae40645d5cb4114f58050407cee67ce7b465a4f1aade87aae19bec"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "56556cc2e1c1e4920563d3114e264e54cbef089a4f9226734907cb1f365c36b0"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "a38540ec3d3e20daca4f41f54324178906cd3ed0fd0e563420ac98d6386b2a92"
assert digest(stage / "dispatch-command.txt") == "5839540d7f94ec67ef1c59b78de5afe4b80412f9458d13184d0b9ebaeb3556bf"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
