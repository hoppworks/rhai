#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "d4ece7b0690446ddb5853c2b8592e872"
stage = Path(f"/var/roothome/.local/share/agent-builds/rhai/windows-rhai-native-{nonce}")
medium = Path(f"/var/lib/libvirt/images/rhai-win11-quality/rhai-native-{nonce}.iso")
serial = Path("/var/log/libvirt/qemu/rhai-win11-quality-serial0.log")
expires = dt.datetime.fromisoformat("2026-10-25T21:16:54+00:00")
now = dt.datetime.now(dt.timezone.utc)
assert now + dt.timedelta(seconds=210) < expires, "retained public build has insufficient original lifetime"
assert subprocess.check_output(["virsh", "domuuid", "rhai-win11-quality"], text=True).strip() == "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19"
assert subprocess.check_output(["virsh", "domstate", "rhai-win11-quality"], text=True).strip() == "running"
devices = subprocess.check_output(["virsh", "domblklist", "rhai-win11-quality", "--details"], text=True)
assert any(line.split()[-2:] == ["sdc", str(medium)] for line in devices.splitlines() if len(line.split()) >= 4)
def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()
assert digest(medium) == digest(stage / "rhai-native.iso") == "55bfa15a67410c93673030d18d08bf3f6c9c06b6e4bb5ba5459841c03b34e71f"
assert digest(stage / "media-input" / "Start.ps1") == "1c1b5f66625fc8f568d9f7de2d38f1037b9184d97bdcec349e9c35f2a52ee595"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "82c80c1efb62f72d4c8b6e812e842c2f165273a6918189bb73fb186a91fcdef0"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "35e9384b983c0e634cf392093d3091178b11a85c828d216e689f980799d8583a"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "7d32d426218bb870bf6c913d5c5b2c1bd364bc3e5ea9eeaeadf9aa581b6d3c2e"
assert digest(stage / "dispatch-command.txt") == "b17bbe037ab504f0d52571011e47b2ccae2530db5a546ab09bf9346ce0ae1286"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
