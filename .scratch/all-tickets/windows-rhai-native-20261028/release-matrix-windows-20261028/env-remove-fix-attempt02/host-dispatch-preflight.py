#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "649d364d5e1244ffa522dea09490b2a0"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "7b061b88844006c5ed740f24109573165960ffb4a189ff10adaace4023bc4efd"
assert digest(stage / "media-input" / "Start.ps1") == "d61d9776bebbb7846be672119c1e9f8d9bbe1d2ab074ad383b51df1916095910"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "078aa06086199c6e567a927b403ba893f01d0cd5734a9f27a3383a5da289ec15"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "761792e035f03c61e9f6842764843b2552496d07f6810ef9a7a8aaf4e05fb86f"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "e40b9a4de52a6f07260fbfc196d15428eb3f2ad3c68e2db171712d1cbb2d6f3c"
binding = json.loads((stage / "binding.json").read_text())
assert binding["base_head"] == "9a03f2ce9a1800293bf09b98e5ee6bc1d23c8c4b" and binding["overlay_sha256"] == "ad610317341b6427d00e3bd8624927669c7d41b9b3e7035a4398ab784e16a297"
assert binding["target"] == "sys_process_windows" and binding["features"] == "testing-environ,sys,net" and binding["test"] == "windows_env_remove_preserves_parent_and_applies_overrides"
assert binding["native_started"] is False
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "314690d53b1f2b2272e983a00a5fd2bed0f708254cbe2606a0407c41ccfa62ff"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
