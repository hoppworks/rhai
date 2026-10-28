#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "a2acaef1e83f2b17389bb5b32034219d"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "46dfb517fbd57fd5301dbc8bb78bdeae47e50e4bd4276b6bb7fecf6e941a8514"
assert digest(stage / "media-input" / "Start.ps1") == "4983088a8983f508fa760817663d2127efd052a57d3c907756390d462a3bab9a"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "0bad82df89d3c5243f305a6321685e1b26eacd3880eaa170f7d6e87e3f8a4289"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "e70d99d6cdc3c8a3383b4ec1feeb7308720a098bc34a303b3b1651af89340319"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "a3ece7486432d013ab5e4e78a5b4dd1e4f30345bbda8c6f16790a77750f7173b"
assert digest(stage / "dispatch-command.txt") == "8babf2661d45e379efbf4186800249f100d09b2a4010798be878e1c39129ed32"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
