#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "5f7c712a24164bea996d8062417bd7a5"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "6feb43ed5f060dba9b29f57e2225e8935d4b273d8d0438f7bfcb5cbe1a45f8a4"
assert digest(stage / "media-input" / "Start.ps1") == "82227025c9a05922d8498a8f973f2ff0623ff19d34b4e0d5c9706c7a61ddfc94"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "1139c85a0a5762736c15862c133468f7ec960a35426054b19749828bc82e71d3"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "40bbe6cd078b3f94e4bdbbed368cef44721ff38fd50ffb8bd084a68b73fb658a"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "1836358c21f96f985bb1b284c0535b42f5c41cba67878317e384db9ad25f0a16"
binding = json.loads((stage / "binding.json").read_text())
assert binding["source_commit"] == "7019821fc9d7814d0632fea06de50933aa9e35ee" and binding["source_manifest_sha256"] == "254d021566408f44b2b645551e2598f7cf9db5fee63c5e34bcc7ea20012ec9ba"
assert binding["target"] == "combined_sys_net" and binding["features"] == "testing-environ,sys,net,no_index,sync,metadata" and binding["driver_deadline_seconds"] == 180 and binding["observer_deadline_seconds"] == 185
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "96dc146855a5c9e97e972a3fd700aa3df05ef92ac34315d5559b98da8a2d6be5"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
