#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "f3ffd1ef5775e316afec9c05663523b0"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "50d8017f8aba30d1edf5da62096376403617723fc8a87d41f2f128c3535e0923"
assert digest(stage / "media-input" / "Start.ps1") == "be5b17bf39a0775be1b7b9cdf8597f56ad0c9c050fddf99b2e3aa05b7d97dfff"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "f0177653ea83f6f901f9ba4c9ae0f02174ac18e2e1cc26795f4f9c7f80747c2b"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "60d8f88be2bb03174d45341d70637e0cc6c7bd6380b9df313e12bb423846301a"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "e971710a16c81c8c635ab09a0be95719c89b9fbd8e7d2d92bd095df65db2d123"
assert digest(stage / "dispatch-command.txt") == "d8a5bc78261ae09cb2883d5f9fe25c8d74939f9c58c2c0fa14eb4aaf62b7e76f"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
