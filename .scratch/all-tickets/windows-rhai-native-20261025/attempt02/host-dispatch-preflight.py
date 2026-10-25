#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "97a0dde027334ae09b0603240dc1bbda"
stage = Path(f"/var/roothome/.local/share/agent-builds/rhai/windows-rhai-native-{nonce}")
medium = Path(f"/var/lib/libvirt/images/rhai-win11-quality/rhai-native-{nonce}.iso")
serial = Path("/var/log/libvirt/qemu/rhai-win11-quality-serial0.log")
expires = dt.datetime.fromisoformat("2026-10-25T19:14:01.279906+00:00")
now = dt.datetime.now(dt.timezone.utc)
assert now + dt.timedelta(minutes=8) < expires, "retained public build has insufficient original lifetime"
assert subprocess.check_output(["virsh", "domuuid", "rhai-win11-quality"], text=True).strip() == "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19"
assert subprocess.check_output(["virsh", "domstate", "rhai-win11-quality"], text=True).strip() == "running"
devices = subprocess.check_output(["virsh", "domblklist", "rhai-win11-quality", "--details"], text=True)
assert any(line.split()[-2:] == ["sdc", str(medium)] for line in devices.splitlines() if len(line.split()) >= 4)
def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()
assert digest(medium) == digest(stage / "rhai-native.iso") == "c85083e7ad418e48c3b860a47c1a6cea59b0f00652bcc2853d8a0624890aa5a8"
assert digest(stage / "media-input" / "Start.ps1") == "113ac61dbc96e03af704a90c8dfeea2e776f5023f9da8d9f4c47f4864e4087ee"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "53934aedf39688b0e4ccc3b505d7db26ed12c14b8f5e043adde4fc094ad32a69"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "2600784687b66ff4a543ea8948d6d2c6e6d5867aa4df8e61ff14db9542d7f672"
assert digest(stage / "dispatch-command.txt") == "decba8553da4e34c7ccec12e68c5c8320c177c6445ad4dab209c688ee7935957"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
