#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "71fb632adc42011e72eba4902ef0b516"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "3621e7c553ed4c4a7541569de25f5716d71ee53b5a6363e1e42eb983cc8f7033"
assert digest(stage / "media-input" / "Start.ps1") == "b9eb9c78d7610c595473a1a062b784dceb46aabf112c2fc12aab2da2ddb5c6da"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "9429b8e6b6dd54580f82a426ace3c4364979388e80144d349ab16af5a9f6a454"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "cbfb2db042d55c393f862d3b51b238730a321d4af1d7e85ad3ee74df9680c972"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "a84f434c7e459177bab9006a6965c7453c52b91feb11dc5e45872e6faf78b054"
assert digest(stage / "dispatch-command.txt") == "d454fd07f42b86a7a93a2379c60b0df8399f712d69f479f9f24eadf68ca1b513"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
