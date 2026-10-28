#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "c645f6f1bb21397c5d5d87d618b7c955"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "8ce6be18fdb96399b39761c837911f20c9f55aa8cbbbdee04887f9ebb44ca3c4"
assert digest(stage / "media-input" / "Start.ps1") == "5d216307f358b102cf09d5d1f2f36105c8af04edfbd66f6f6488748f2a018a23"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "f4df5f97848213ceed6bd72f0311cba01bba69bbc3589e216740e93c32f70584"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "e675c1030116e790a8f0d176693e0f0948f64285866a78be4aa1ec45729c9a0e"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "0c5ebcdeec554f3594215d6db0b1c345b85d4cb85c51d702d224614dde5f3eb4"
assert digest(stage / "dispatch-command.txt") == "066499327a3e67e7ad1ad40ca6dfa0d39741fcb140a812df79ff494c33998c9b"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
