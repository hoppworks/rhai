#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "e0c7562105baad184aa60a7229106e95"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "abe5bf2179f5bdcc265d8e93e6ba7fb366d608c314a5be32ae2522ae9c722f0f"
assert digest(stage / "media-input" / "Start.ps1") == "e305f1a45087efa572a0dde5180456f146615dfb259e65b4f91c635724a1afbc"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "415787690d06d7f421fe74cb3a7cf5c13d2ed3aff4cf033dbd57a7d2a0f8e2fb"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "1f6503781d279f398e2060230f2708b16fe6740d087c27468ceb899cfd10c1cc"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "d9426e67efb9217f06f349553001832f79ad19c3a2b1eab1f993076dabfe2efa"
assert digest(stage / "dispatch-command.txt") == "30616a2373f65a82a0fc5b0b39a5eae8ac723c9ab939cb839b1755725e0bd74a"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
