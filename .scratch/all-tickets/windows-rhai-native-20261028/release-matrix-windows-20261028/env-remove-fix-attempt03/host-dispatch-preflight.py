#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "7fdb1180cd7f40b48f389ef77d0e6aeb"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "b44ec2ea46bbd138804a51d8ee69acd5085a45f651ff08ec4528e018511214ae"
assert digest(stage / "media-input" / "Start.ps1") == "c8b8695878dd1c6b974fc74c20980dcae98e54135be91bfc412f072810536338"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "5a07a9393e18746eaff2c25b55e361f90b9812e5366b31038c32ee5e4b392110"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "4a1aaea11f94eb2dfc4c6e2df1e5ad9bd33a38d96d0bb5ac21528a7a54691a13"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "c6a6ca48d416c74feccc883fa479ad4f8bc8fa4e35714802a2a1fa3dff205d20"
binding = json.loads((stage / "binding.json").read_text())
assert binding["base_head"] == "9a03f2ce9a1800293bf09b98e5ee6bc1d23c8c4b" and binding["overlay_sha256"] == "12beff629244aafbb71dde6206c5052b49d972ff92a66bb64b5674dd9c4b0f1f"
assert binding["target"] == "sys_process_windows" and binding["features"] == "testing-environ,sys,net" and binding["test"] == "windows_env_remove_preserves_parent_and_applies_overrides"
assert binding["native_started"] is False
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "6a5ae8350183cba8bfb536c879471d28576b8933c616c9fa0e77d223c8a3f99b"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
