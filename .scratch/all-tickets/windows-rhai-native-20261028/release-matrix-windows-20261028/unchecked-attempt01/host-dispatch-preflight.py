#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "46e22a229fb0090d9fb61902ab09a359"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "66127269402fd9fd8f27114d8f01d7ede8ebc743919df3f0e3a1affb11119c8a"
assert digest(stage / "media-input" / "Start.ps1") == "4d1fd12124fc22202e3816844551df64348397da917fe722007c2f4aa75c0745"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "911c466ec7d4ca460ee98db05c81f776b026b75d97c0a49ec62c3288cd58fb22"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "321be04800b8c6ce522e1767572b660a1299300ad8894562788604cebdaccee6"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "ac01c1ba6cf3ae116131dcb595ea190830e5c221a8bda3aebf638aa05dc891f6"
binding = json.loads((stage / "binding.json").read_text())
assert binding["source_commit"] == "7019821fc9d7814d0632fea06de50933aa9e35ee" and binding["integrated_head_at_prepare"] == "26bf9ef3a971cd752dec20bb4cad105fb0cff3e3" and binding["source_tree_matches_integrated_head"] is True
assert binding["planned_target_count"] == 12 and binding["planned_features"] == "testing-environ,sys,net,unchecked"
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "b1757913cdfffc07f3b720d7bb6b6e456814ea62df54305e15c576511ffb00fc"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
