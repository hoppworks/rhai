#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "feb4ba1d87f14ddfb33d6f113e3964b6"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "8adafcfe69a9cddae171f0ab9b49ef33953cc2b08052265de377c3f69d092181"
assert digest(stage / "media-input" / "Start.ps1") == "87c999e4b8d438a9654e8c0dfff2a5dd19acf886e6331a58b62218258198dde1"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "85c649e2553f5764bd8db1ba42f3e59006c74479a3302fdcbaf8cc4f1ae5b37c"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "54921e0d75ecbfc9e21d780bd7470054f175f5679a353406211d31d0745b547f"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "b42737023e744a9d9634d560db0887247f93780da912b858048492722594acbe"
binding = json.loads((stage / "binding.json").read_text())
assert binding["base_head"] == "e0ec6fae0161a743b1f7e8ede9892f4f89787c87" and binding["overlay_sha256"] == "3b07ca627b2d5dd2f5e033d4a1a6a5797fb62f2cd021ae61fdf32b93c01163e2"
assert binding["target"] == "sys_process_windows" and binding["features"] == "testing-environ,sys,net" and binding["test"] == "windows_cwd_uses_allowed_directory_without_mutating_parent"
assert binding["native_started"] is False
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "9390907bca67258a510e218d0d779be0beb4a084942d332774dcb716cee515db"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
