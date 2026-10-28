#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "2d1976a3c2af801780941d3085b6db40"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "26a58accba1b3194bfc52caeecee9d85c95569341388af458d7b827e8d0064ad"
assert digest(stage / "media-input" / "Start.ps1") == "e90480a3ea322e2e0be74e6198b04904022c5f32a65b98b60fdca89151f02d4f"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "8cb843bb264c7809494dd4af71e99cc79ca872462fd0a0a6b52acda255ddcf4d"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "bbbaeb3e8763ff8c8c6e897c8d095685d20e3b1f85a5cdd9689b542d212bb277"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "2cb0656a505ab788391853f713033ce3e51e03694f391b586258786905cd9410"
assert digest(stage / "dispatch-command.txt") == "91f929cbc3dd6f2b7a3d4f858a7371cf69d47a428727420a8dc533744eda99b6"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
