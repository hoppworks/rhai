#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "262a54f73a7048ad915dfddf83af6b2f"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "74f8508731b243477b11d55be4cf077802defc8641e63e322fb9e9dc07e57b94"
assert digest(stage / "media-input" / "Start.ps1") == "efb87ff84cd283a100e87ac57955688530e96987b963c132dc5aa89b2ef5a181"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "5b4c7e16454b53c7aa9fd391c02f12bd700bd2d581d4409b6f8c49951cdb5a2a"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "895917a81656326c81a233569d8874be82f23f9440059e2940c581d4b6796542"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "c9c07e85f5b04474d46b2ccd80bfdfb30f8eb35ae5e9aae81bb048cf3c0f74fc"
binding = json.loads((stage / "binding.json").read_text())
assert binding["base_head"] == "6dc2565bebe137063c218cc90fa748d24559d1a5" and binding["overlay_sha256"] == "abf2f00b4023205160cb5da3422bc4372f367cbfd4a1bd57e0481847e76370a0"
assert binding["target"] == "sys_process_windows" and binding["features"] == "testing-environ,sys,net" and binding["test"] == "windows_cwd_uses_allowed_directory_without_mutating_parent"
assert binding["native_started"] is False
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "48b97ab621c431574bc9fd89473541a300faca01a2f90e53d8ea6feb621563d1"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
