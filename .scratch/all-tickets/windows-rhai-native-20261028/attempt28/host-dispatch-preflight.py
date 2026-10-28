#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "4a7fd1930ec5db86067fdd3ed06fa69f"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "48c136a732dbf9832d3813f9f8945ee86a2e7deb633e055002d553cdb23b5090"
assert digest(stage / "media-input" / "Start.ps1") == "8f66157a5c641d97af6245e8c34676b4a068084766b885aa6a65c53ea10bcf53"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "f671323a6a8d61ffc8f31b344233b4a0c1df00f9fc5d5740b615be9002ae0472"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "c7ec59c24ee9fe300af0599784a934372dd70acad790fdc5542aad234f89d5a1"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "f8db54894e6d09bbb02ff0d77100a085b230907f52775e41d3239e8e4926880d"
assert digest(stage / "dispatch-command.txt") == "a9c52610f90f703142a9c8d17f168be9aed2b5fd2559f00de8ee405bb9e8f609"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
