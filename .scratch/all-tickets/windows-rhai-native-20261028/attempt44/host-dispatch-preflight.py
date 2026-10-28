#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "3cbd910f81f7ed38c50015fd5347be5c"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "0c3c53e03ba6e5860b37210169a1b03a758e658f952a138844bac7a7d5a4058d"
assert digest(stage / "media-input" / "Start.ps1") == "3b3c4ba8014b4ff8459d1a3ab5b4205a7193e343e71c4be8be325553aee5e282"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "839e3c573a6b86220487479aa0a9b316cea19d74684932467f400266f929ecfd"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "0095c82f5a6b0ab380285fbdd7d782869cceeb3ed097bee50faaf27fb8394763"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "a60c7206af2388f0c6a0b7f27516fa86a5db89ce5044eee1e95857d9a1f64687"
assert digest(stage / "dispatch-command.txt") == "ebf1b0bc2cc95245b56070c78a83d05c2191e402da7a71c178337fb20bebda80"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
