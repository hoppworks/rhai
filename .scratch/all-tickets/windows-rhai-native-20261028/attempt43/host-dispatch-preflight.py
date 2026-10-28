#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "623f36c773dc8f478681f5fd66d60c9b"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "bdc4c136df989a8bdefe4b79a2e8830e7a827dfcba94eeeb0238c2070ac400c9"
assert digest(stage / "media-input" / "Start.ps1") == "a084d3a00bc3afb4fb44ebebd59db7de7f0d467f18dbea0d81dd068397a719a4"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "513e9eb38120cec14f7e9e6544c1f037c4f8678ae14039ecf14a0c9b1d490f94"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "c79cec7fbb8e8010147d0c6723c1399711b8519e2682ea9e23e511798b25021a"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "57b54614c7796b39383ed1703c07755a47ec1f8636d6a702c306d9bee93705e8"
assert digest(stage / "dispatch-command.txt") == "ec9b207c55b0a91db1369025479e895bd18d5415c7c809aff8553ed4875c2dc8"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
