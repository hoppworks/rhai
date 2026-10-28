#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "f604ca66e3b2866b43d6691edc0c731d"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "fde32f1ac1cd1ed92529cda23eb29991072a2063ae12dd13382c8051eb7f702a"
assert digest(stage / "media-input" / "Start.ps1") == "dcbe863fd597d64026195c5d01e9fa50abea1f7bedfacdb5644f4c47d2c0de27"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "6db25169ce66265a71e10b47eacb00423fdbafcf1806f855f8fe6da351c8cb7a"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "aaa6d46c9b7c495f23eca31b9b5cf33a9be55050f88220a697b060b36fbfb757"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "2c2d57923dd40164b8e34d96bb0fd4324e66ca56290a827296189e9c926ba9ea"
assert digest(stage / "dispatch-command.txt") == "dcbd9787ffe658fbb3d80d58cbcf87ebf952a874825c13eca3f520e68ed4b22b"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
