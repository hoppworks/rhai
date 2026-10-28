#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "1da2f15ec840d2311ebd1769ddac14db"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "17563cdaeb1a2c71ed81de34f103e10158651218d5eed27c282bdb453963eb55"
assert digest(stage / "media-input" / "Start.ps1") == "9ae31e22caa6a9607666528824d0e80eb37fd3fa354a3c68b069a95a7e3d9401"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "90bda9046a1e7998caa919e59a054b052ebfd534835f28e2e4e6a126bd7c787f"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "3d83a2b5f22990fe675c82e7a8f016ed7967d048c5501b13369a8bb79009e114"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "537351c81e87961179b83cae01769d64bae801b3690df493b3c41e7b74b75c71"
assert digest(stage / "dispatch-command.txt") == "a3ce6c77f2648b9fbb24f1856cc9f348ed815c81f617a9512db1d5a494de8123"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
