#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "cd94dc0b4a06cc6be7163edfc3c1bdee"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "288d82f7c8a040a62798700145ff712fd867b4b0067b9af8078fb76135f97f58"
assert digest(stage / "media-input" / "Start.ps1") == "6875bc2a5e9707de3351027f350efad66e9e04c1f131539cb8d2ec2c42ff4ba2"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "cc4e0b7168e71507dd2d037a54e5e9316f16839edb6234bf6c10639643ad45a6"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "256a5bf27123dcaf286cd9a9e9554b91bb00e02f26b4f57b9da72db7b500be92"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "4a4184b23384760bbd4926cb4c8a13d915bc072e7bb75a980572256ccfb336ff"
assert digest(stage / "dispatch-command.txt") == "463c67ced320ae94bc9204d4b8b62deeec3b28e8fd9b723fbd4df222035fa545"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
