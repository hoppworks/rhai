#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "4197aac65a57420ba09fa6855525c353"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "652177528360db10a099eb3635f4dffb432bd67e9f78dda81862a5b2c46ed0a6"
assert digest(stage / "media-input" / "Start.ps1") == "cf9bb98a30508c15f3e5cee3d381c69cdf963943a4c27e1fd1fb213de7e9c849"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "3b36866f1d0f5417957b7cdb839df0abb719a89df26c9cc569511ddab6893500"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "d046494e73556e3980af8d343ff09a6022958a5d22e0079bd8e55ea4b53cf10f"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "abf1d8b1927f5ec94de39b5ee7f6f5fa89ee704b14550fb7e669b216a3e27499"
binding = json.loads((stage / "binding.json").read_text())
assert binding["base_head"] == "421c4159de0ae47e9bfe05fc20a391b1f4da640b" and binding["overlay_sha256"] == "96ce7de544d63c535c8f0a8e6046d69c1ec6cfc15550c853f888a3b2f914d053"
assert binding["target"] == "sys_process_windows" and binding["features"] == "testing-environ,sys,net" and binding["test"] == "windows_spawn_retains_early_stdin_close_error"
assert binding["native_started"] is False
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "99f9c94baa9e8d02c5fee533e0e976116c273fbc6a36a3de9ed3f4f37a2a36c7"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
