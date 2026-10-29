#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "c29b127635c74048968d96923412b618"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "88590942dddea340f77d0e7b797d8b30ccafe241748efa9bd5e4b6b15f771aa0"
assert digest(stage / "media-input" / "Start.ps1") == "79383d711d50f74833ed30bf47aacfd6397b0a0c50a296b6933b451baffbb04f"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "da3f1f5255c7a6b209f378ff07d71d49a126865a22da24195377292c2a8505ea"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "44dd0655e0ef1f36d61f16e12e2bc5b6f59ec8a6cef62a0db4e66a54abf27a6d"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "a4a85abc73e9bfd813e3e84e3047688eb63bce374a678004fa79292a7ac734de"
binding = json.loads((stage / "binding.json").read_text())
assert binding["base_head"] == "b2608fc7c0682c760a4e9599e2616318ad680563" and binding["overlay_sha256"] == "4ea6490e9cda633221238e5a91c08c96369300698a646275947d4a33293d26fe"
assert binding["target"] == "sys_windows_reparse_probe" and binding["features"] == "testing-environ,sys,net" and binding["test"] == "pinned_directory_can_become_a_junction_before_child_start"
assert binding["native_started"] is False
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "56ec036076372853bb212bb411e9eb7a947ae9e8b3c0af7740a296acee8cf478"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
