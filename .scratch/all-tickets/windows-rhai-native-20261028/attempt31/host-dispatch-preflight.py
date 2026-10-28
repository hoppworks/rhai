#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "37a7f14ee6a6d923591f92d5b67923d4"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "76584d6e26148086fa7129a00f55f29601b7d4186b1803d960673450acd5c107"
assert digest(stage / "media-input" / "Start.ps1") == "6940abdfab578761ce77a04ff9a5281fcdf32fa05baf57cc0c459f2072bd521b"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "bd2f89e8faff655b5981d001ba5ff4c8404cfc2f28579bc1910eb7b55b532739"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "f3ee1a951079fbc757a0103f24e5b04aa0e2c3977b45d3f1e22b0d40ea150059"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "3229e069f9968c389962f38f9f8cbb7274dcaadaedb59cd9b65934f3d8302956"
assert digest(stage / "dispatch-command.txt") == "437fc832ed4562d1edb63fd8f0237ce5c30804ebbc3bc49e4470ae6ac535a307"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
