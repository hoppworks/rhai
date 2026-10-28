#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "8743857428e410e845bd818740923a6d"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "27b62827983ec31d521c84734d6aedecdc71286b14eccf31e830037ccacab412"
assert digest(stage / "media-input" / "Start.ps1") == "8ea42e7cb2e5a2f78aca3679abb5637afb0957a9f436bf43db25e5032fcbb793"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "ae38fc31f8939cca3984d73d8f0702ca7a90d40f63feb2b3da5b38d1b2925272"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "06ac3df1d02fca02e913699845220f3c5b9bd30373acd21d7c42efaa295a2be6"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "d38ff59705d7c2db03c51491ec90ec4def07f4f75a8d865a13f27c61cd9a9b96"
assert digest(stage / "dispatch-command.txt") == "e651a8bb7a28e7b518bdc67bc4c66a27d59ef140028ea0ca72b0afb8f58b16a4"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
