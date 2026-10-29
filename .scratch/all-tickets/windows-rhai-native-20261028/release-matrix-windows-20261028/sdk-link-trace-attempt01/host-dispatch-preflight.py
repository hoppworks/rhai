#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "7e51e9f298df4665810426dcaaa288d9"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "239325edf5de193323faf43ec2d140c82a60395fcc72b51a8eb630a7fcfcf8b7"
assert digest(stage / "media-input" / "Start.ps1") == "0d2a27dd07ef6670231db8573043261a833118a1ebc188f1cc720c51f8db7191"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "02a25d717f90350ae4d3b406fe1fe5a9ba9d2831465f3e75fe9a832d59ea8f55"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "a02f1203f158583962b2cd312e29a8526719ddbd9b5eede1509c3e3e3775b317"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "234d5794fae97a2f2d009305cd7718fc225de4c31d47ecab9da3ce8cab18c36a"
binding = json.loads((stage / "binding.json").read_text())
assert binding["source_commit"] == "7019821fc9d7814d0632fea06de50933aa9e35ee" and binding["integrated_head_at_prepare"] == "9ff5dea4208fcf15370a8141bb8ce7bf80236583" and binding["source_tree_matches_integrated_head"] is True
assert binding["planned_target_count"] == 1 and binding["planned_features"] == "testing-environ,sys,net"
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "6e62c86da4348822c5ff2f8e444356cf169784120315d12c80fd7b1013efc1f6"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
