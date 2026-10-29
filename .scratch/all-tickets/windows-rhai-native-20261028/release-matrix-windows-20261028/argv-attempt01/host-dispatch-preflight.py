#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "eebf1576031e4604bf85943c7b3b177a"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "37eb6560544083ffc8dd15dbb7dff4609c85fc698b13303fad079e5b89481d36"
assert digest(stage / "media-input" / "Start.ps1") == "8c381569c2e5d3b626b494d91a582a049897f8548198b95818edbb224e67572b"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "c1da19ad12bd942fc5af83238c55457b0f9210bc150cc5423a9f974e32633686"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "eca96e2b2f60203743c4726cfcd31c14bbfd02a79f0c596cf8914fcda7ae341c"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "98bbac581bff5aed0dad5f5c54f6112dba617699779be6ed9a527db74e9a81f8"
binding = json.loads((stage / "binding.json").read_text())
assert binding["base_head"] == "87d838e0ecae5de9a05cf0e29115506c58a780ed" and binding["overlay_sha256"] == "bb05e1168776c17e5b1480796a5f2d39317dd45a698800f2bbeb5af1b6426f14"
assert binding["target"] == "sys_process_windows_argv" and binding["features"] == "testing-environ,sys,net" and binding["test"] == "windows_process_arguments_reach_the_child_without_shell_interpretation"
assert binding["native_started"] is False
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "0de92a179d94ead3c598fdc0d0154d1803e54b9e7a8c421c28e9f4e48eb9022e"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
