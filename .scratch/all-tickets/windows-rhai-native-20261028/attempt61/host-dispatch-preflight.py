#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "f289af7361c080794e4688723f5dd0b1"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "5224ce9cd9be7a697ae702b4204ef2f94132e0772499c74a385b0e2b48821b26"
assert digest(stage / "media-input" / "Start.ps1") == "4f402f11959b00459d8724d693d0b00782a16e06cec331a9e4d53613b32211c7"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "522689350e56beeec588325ac4b33ec664435037a532cbe22924a6373ebfb87d"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "647333f370daf4e0df7cae351bf0dc27b04f6abe1598258f718ee13b9eacf5f0"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "d1090f9e6001d61d25eca7e363eeb65b3e844cdc36ae0cd41b446bdafe6d91ca"
assert digest(stage / "dispatch-command.txt") == "117f17b0f268bdd08c005fe208b844da159519a70beeff02c5419d0eda9c5b2f"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
