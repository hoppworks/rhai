#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "60b79304df6f44f52cdd8c42dd536d29"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "1aa1c7d8f030a173a8040f654793c6e1f16680bc8758d5ee11a029fe8d292b88"
assert digest(stage / "media-input" / "Start.ps1") == "1dcf44e0f871383aa35eb2f29e32a34d0cc7edbcb0ecb6dff561d88de4688df7"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "b77e95864ce622d71018a3b6c1c0acaacb897b176936ed3a156623bb5c9de68a"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "93aff69a88e5471e82c80d465a30be3f2797bc21f36918ab5049e26d7f369f1e"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "6e3762c27e3fb7ca46f4aa892135010f41926602567317eb4a88bf5b6716fc35"
assert digest(stage / "dispatch-command.txt") == "d1d88a7c2a9d2d839bd3fefa4302fdc5fc1616987de66a559d7410b1118e736e"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
