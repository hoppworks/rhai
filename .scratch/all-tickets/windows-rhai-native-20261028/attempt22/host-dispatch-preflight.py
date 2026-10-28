#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "30f674c8f631d898ed0b3711b70bf30b"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "75f0a58e6d9972badcc2bb0fecca8b3b83a4d9a59292f766b48ccb13911c62cf"
assert digest(stage / "media-input" / "Start.ps1") == "4087515ef1a551da366252c2174600e0781f2a77685b285ea608c3d17fe19098"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "52a65d52f7059e2097fcb925ca1563217c85fe423574341835c44ed9fab3d51b"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "13e31c64529d0b7f7df4541f8e6f3ef6647ab40a0921e75eb1632cea83d8642e"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "57df40413643cd1da4ec725af50ede631fd954fccde41b8672067894968b4d10"
assert digest(stage / "dispatch-command.txt") == "21a87ab4237ae3354fec9ff56946464dc0ff8abf29bf05e4eb949ac05fefda24"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
