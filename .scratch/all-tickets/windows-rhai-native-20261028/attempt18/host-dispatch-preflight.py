#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "ef1eb288ec8fa709a119b125a488b67d"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "0adbcbbc92006d7fbada53b9a9adc52c9659fd3822dd314062ca7db30200c0e0"
assert digest(stage / "media-input" / "Start.ps1") == "5bd5dd2363116b6efbdfc63f7a290a57fca9b1e8b27979ac00d4a70a37b15c53"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "d24f9e073c4ef83dff31eac8bf4a76d9a58a12e2ebe4a0b1d5eaa448d334bcc6"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "88f1cfdcb2800f36179fcb234e629434856d82e4d4f7865e1b6027c5f96e2c88"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "9cd6b55094ce0023fb7023bad07fd651f71f9cec040174b5f6244d332da55962"
assert digest(stage / "dispatch-command.txt") == "4bd9bb68dd0b4c0fe05cd4c4fe788c62485d846f7a3aa8932aa3c931a7e3f2c5"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
