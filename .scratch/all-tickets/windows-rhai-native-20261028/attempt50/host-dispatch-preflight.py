#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "40183259d0ce4fad840e953ca5bcf415"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "bfd516f4f04a30c9fa5e9f110d9c8b83a8f1739876ac6bdc3a9e855663659038"
assert digest(stage / "media-input" / "Start.ps1") == "761e5ab7c1b985302261ee89fba3bbc59997f0d915b1bad7ed7d9d70669c0997"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "48c01939a81254c51d3a3ebc4e71735a705a693edcda659253779e50b770f7ca"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "6a8eb62b984afe9c9aaa5aee685c0cf0e35c4a0b1c7f5413807ade2e4937f212"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "a33b8b6191d6417af21904ee48f0bb90990804f9ff11fc9eb1423f2e9ac3d75b"
assert digest(stage / "dispatch-command.txt") == "80389e769275f508bebb3d0b9c4cc0c2e4362ba232d4a09c30dee8309cbb5206"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
