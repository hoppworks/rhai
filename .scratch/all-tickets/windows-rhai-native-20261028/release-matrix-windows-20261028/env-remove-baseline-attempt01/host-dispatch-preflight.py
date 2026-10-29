#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "73dd74e3b0844a6795e144f663e0579e"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "489314cc2ed21c4628ad56d057b914c76a01fefc8469744f504d921174b1f27d"
assert digest(stage / "media-input" / "Start.ps1") == "f1352111a8a4184b39f6e9c1ca273234cc32859ebc9f36446ee6dadaa845819f"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "13b799b5b631ec107cbb911071080662d8fe2618274e73d4b8fc071547e82d51"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "321de4d2bb1edc12268243b5eebf508d2134c8af218d6a38d6f994e4046e30ab"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "19bd7ed6aca611109825f9a564ec74ac0e5d8fe971dc5052ff95367444d2c64f"
binding = json.loads((stage / "binding.json").read_text())
assert binding["base_head"] == "9a03f2ce9a1800293bf09b98e5ee6bc1d23c8c4b" and binding["overlay_sha256"] == "48921eaff6cbeef2e56b64644eb048513bc1bf7d0db90b28a29f7a582268e922"
assert binding["target"] == "sys_process_windows" and binding["features"] == "testing-environ,sys,net" and binding["test"] == "windows_env_remove_preserves_parent_and_applies_overrides"
assert binding["native_started"] is False
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "798657f9df9c5d3d25cd8675f37dae567f29776d857fd30eb635ba9d3e2d6bb4"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
