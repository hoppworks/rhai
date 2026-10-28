#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "e1fb33fd0b43a60173b05dd591fe39de"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "a69ae4f67b47b5a9e57fbedcadf00ebc2a585b5f5849660b6e024dbe29a92bf8"
assert digest(stage / "media-input" / "Start.ps1") == "873a35ee9b965a2afdb91c0963e07b89cd10767a63418376f9fce664715128e0"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "77defa9e95c042ab57f994c0418cd58403fc8a4f92b161aa590f3a1006bf8b1c"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "cbfb2db042d55c393f862d3b51b238730a321d4af1d7e85ad3ee74df9680c972"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "adbd3ef0fa8842479a87a80a09ecb0551fbc2dcf2de8b0aa41449b80a2d765e4"
assert digest(stage / "dispatch-command.txt") == "5a30814c73c34e51ff2e3fd9f3761be38b52ec57c06dc4bc6d364dac4aaf6fc4"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
