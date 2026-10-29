#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "30fd2b271e5c44b7bdf9c24ffe1bbc16"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "05e1ffbefa154e3fc5f181a66b929cc4e20bc30e52599f527968a05bee91d3a1"
assert digest(stage / "media-input" / "Start.ps1") == "18d1e828b2baf71095a3b2809fe607cfd4d5ec95470803ee8b52561651e7569b"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "f3d9ba25cded38f8443145108abccfe4a472f24c5c9c8cd1ad1c3652d8178bb5"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "877a45eacd53995e75fc4943c600def78205d8089c5d698b1a8fe84781e4ae53"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "3e9a9eaa8ec311444881a5dd5fb96f1eb168c1a967504c1f7b0e5c9794cf8c07"
binding = json.loads((stage / "binding.json").read_text())
assert binding["base_head"] == "9a03f2ce9a1800293bf09b98e5ee6bc1d23c8c4b" and binding["overlay_sha256"] == "cad724117a41f35322a7b43d4bf3c8fcc2e137d827d865c8337e3aae9b3367da"
assert binding["target"] == "sys_process_windows" and binding["features"] == "testing-environ,sys,net" and binding["test"] == "windows_env_remove_preserves_parent_and_applies_overrides"
assert binding["native_started"] is False
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "71f880a8575848e60d2f93a1de890928769a148fda5030dfdf810ea99c1d8b5f"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
