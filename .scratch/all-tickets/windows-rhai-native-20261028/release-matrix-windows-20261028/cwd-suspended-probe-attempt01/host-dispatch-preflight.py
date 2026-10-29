#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "c61eb47971c24dee985173da67278b42"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "e030a40c157d319967661ed030fec6c5ec56a32fd6eb752a7394be6d09d03ddb"
assert digest(stage / "media-input" / "Start.ps1") == "09579fd8ebd88da991cf87fa7a4e0a273527869a999f4f7bb3cee10adcd7ae19"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "49c3fed21ebb92919eeddfece6a9c5a561122debace67e3a981a2d5eab9f680b"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "9b7d1184a4d12384306a67621a0cb137d7468c7c65bab578e7a3f8148916c8c0"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "c99f7ae9be700e8c32aea3e14344696ca1e4377ef6ea5e5ebdbec1658231f60d"
binding = json.loads((stage / "binding.json").read_text())
assert binding["base_head"] == "b2608fc7c0682c760a4e9599e2616318ad680563" and binding["overlay_sha256"] == "993bf902270fdc6de68144e043973339435e8fd235c6ad520ce04b1b7cf4b3eb"
assert binding["target"] == "sys_windows_reparse_probe" and binding["features"] == "testing-environ,sys,net" and binding["test"] == "suspended_cwd_candidate_identity_and_reparse"
assert binding["native_started"] is False
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "1c620708bb83357821fe36eca59a6ceda10418d8bd4ab3955ad0f9f06d806913"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
