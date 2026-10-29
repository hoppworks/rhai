#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "8edc9965d4f64647b6e86849167df542"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "ea42811388e165c729644713d7124e6e53ba14c3c5a754377daf2564adbf1982"
assert digest(stage / "media-input" / "Start.ps1") == "59791f882f529f6bc922cc9469e0ec86df8d0d476d7e3749269dd4d0a4aea2ef"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "684e8d07f592de8042e535ec7f237ea36e7b341a685b47ab7a8ab521673c8403"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "8efdd8b029ff3075bc0910574a582812efac3d77ee30eb24e71f235099c01c66"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "6884ac4d19b271db01169d9277fc3e373fcc97666f8f2021e66d1aed267c7d42"
binding = json.loads((stage / "binding.json").read_text())
assert binding["base_head"] == "6dc2565bebe137063c218cc90fa748d24559d1a5" and binding["overlay_sha256"] == "0039528cba8117ca93e488d8f093880b6974c9afd63ee95b03c63c3939216838"
assert binding["target"] == "sys_process_windows_streams" and binding["features"] == "testing-environ,sys,net" and binding["test"] == "windows_stream_direct_run"
assert binding["native_started"] is False
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "7d645912ec1ce38ff56600160585c7301769bb3d61fd02b609676963e65b805f"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
