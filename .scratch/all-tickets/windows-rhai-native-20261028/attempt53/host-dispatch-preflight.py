#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "e9e999be7cd8d2da60ff263814f0230a"
stage = Path(f"/var/roothome/.local/share/agent-builds/rhai/windows-rhai-native-{nonce}")
medium = Path(f"/var/lib/libvirt/images/rhai-win11-quality/rhai-native-{nonce}.iso")
serial = Path("/var/log/libvirt/qemu/rhai-win11-quality-serial0.log")
expires = dt.datetime.fromisoformat("2026-10-30T12:00:00+00:00")
now = dt.datetime.now(dt.timezone.utc)
assert now + dt.timedelta(seconds=270) < expires, "retained public build has insufficient original lifetime"
assert subprocess.check_output(["virsh", "domuuid", "rhai-win11-quality"], text=True).strip() == "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19"
assert subprocess.check_output(["virsh", "domstate", "rhai-win11-quality"], text=True).strip() == "running"
devices = subprocess.check_output(["virsh", "domblklist", "rhai-win11-quality", "--details"], text=True)
assert any(line.split()[-2:] == ["sdc", str(medium)] for line in devices.splitlines() if len(line.split()) >= 4)
def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()
assert digest(medium) == digest(stage / "rhai-native.iso") == "cf1d5df26a4d70aea87595c3bc1944f3e4251d9a60957ece55db1c54ffcae15c"
assert digest(stage / "media-input" / "Start.ps1") == "157246f8894acc4fa7c7ae479333a1700d1a476a683fe068b53cc253f3fc8f58"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "2f55022f6a58312b4ba9254dcfbe4727873414aa2e1e7bd05aa43642d3d4992b"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "014ca30c827a79d860da76d97c706dfdc61bb0fb4373a3ae191bff3d6ffc8788"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "94d02bb9394bc04926fe8388041ff9e659dfbd7f780185bf7dc50c8d88f55822"
assert digest(stage / "dispatch-command.txt") == "98d5843f00b4fbf4a05be37e20845156e5e7728faa32d216fd260a849cc3e184"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
