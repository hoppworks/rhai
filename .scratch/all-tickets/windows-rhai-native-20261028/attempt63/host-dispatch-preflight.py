#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "c50a944f97a48f2aa1fb39ec232b546c"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "491b964e3526a7e8a1b25ec478b92346626cabed9fe4f3c6e7d623da92ffd54c"
assert digest(stage / "media-input" / "Start.ps1") == "d70825b731293360568225e44463a016ea737694c6bc5c368541b2931c82c438"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "908f0c338301c71e641606e681a8c3b8c0f992d0d3b4f54383d6e9f2d25af564"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "06ac3df1d02fca02e913699845220f3c5b9bd30373acd21d7c42efaa295a2be6"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "eb2d926ccfc6974dfa549bf10fdb00635b913c46ef3479810152a2085bb3a0ab"
assert digest(stage / "dispatch-command.txt") == "aace72e1f27b7b395868818da86aae857ec093985c7b4dcc6da4679c164af670"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
