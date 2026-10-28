#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "72a37db2a6d396199fc3f972181d8197"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "fdc8d4a27be0ba5000cdacbf833fbe99cb1b8d139435c000c40354c6c43854c4"
assert digest(stage / "media-input" / "Start.ps1") == "1474bf5a4aca3eab267cc660ee75d8c263d337b377e59a6bfa2b0dc6b263ad98"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "089eea3292b335bf931d5830b5c62d941d0cc80fe6b64fec6c1c4db4ca55f827"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "631c44c771f19243135b22bb8d6a65e99726249b2528b92b0368f5cc4fae8a1c"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "a8bbbcd46f4bbeacff90016dea40b99bb1b74fa8ef7c22e36741931c1be73638"
assert digest(stage / "dispatch-command.txt") == "86a34e135a5ec4abe45eb8f862d8ae328f69903278b07e2133fa7a074ec67686"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
