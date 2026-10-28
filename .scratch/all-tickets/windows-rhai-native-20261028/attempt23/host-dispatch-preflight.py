#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "baccbb8a78b49adab4017d4c3a37103a"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "4b34243b1e3a20035ad3a4cfe290560e68869f4203c0c51b82bfd08b482f167f"
assert digest(stage / "media-input" / "Start.ps1") == "6e700161807153cd4deaa5565b73471b1b7ee3df406cccfe73d5fe5a65fa5735"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "e3ee5d88ed3a6e01e7c1f2b424dc07963923081dd521a07c68b5573f84397009"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "363a6aa0b919bc1af441619f9aedd0cb2178f0651925fcb420d7935569558203"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "d099998da6567e039076d2224e123609d17da2eb857b7b0fcddb154feb3a723c"
assert digest(stage / "dispatch-command.txt") == "12a5551f58a7dcc327acf6263ed92c8f7bbce072887802718783f1dc727b6e0e"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
