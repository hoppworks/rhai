#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "ed665e3968e2453db7cba4dd594abeb2"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "4a8ed02158d2710090446650f7535872b6aecd4c3e22c950f794f5a7c975e6bf"
assert digest(stage / "media-input" / "Start.ps1") == "7d0cb55fe1b19aa768c7b8114422a28aaee97c504fc001bc4aa6f3471d7cdabc"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "851eb47f491a40307f9f5c976394843bc7eab7e77f95f1a1f66c587e6627bc51"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "ee797ff3168ac32fdad4d4ab19fec3ace18ade33891c780397c04ca231665873"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "afb2351597ddc1e3e0f81af38fcc98434ba9738b0acaf626820cce731cc86c67"
binding = json.loads((stage / "binding.json").read_text())
assert binding["base_head"] == "e0ec6fae0161a743b1f7e8ede9892f4f89787c87" and binding["overlay_sha256"] == "c1a58015ab4704d5c34f7d3de70c51a00e4b47ab92109c0b07751eb99d7989f8"
assert binding["target"] == "sys_process_windows_scalar" and binding["features"] == "testing-environ,sys,net,no_index" and binding["test"] == "windows_scalar_run_reports_native_hostname"
assert binding["native_started"] is False
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "f9d98e0424c1174927d5e4fa37523851788cfe6c61e08ed47c4438e7bef4f97f"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
