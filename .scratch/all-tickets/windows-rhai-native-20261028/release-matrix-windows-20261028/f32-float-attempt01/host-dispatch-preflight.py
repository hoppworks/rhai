#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "6c165808b8d4457c996fa3f103ec7a86"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "767071d0efdf50dbec87c3b6c05766ab0fb7710ce7c2db5e01a49d30f91f6eed"
assert digest(stage / "media-input" / "Start.ps1") == "f16cff160ba3e1cfc3bebf3d13f8e63c2bb330f06096c00a39274ba061b50f10"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "77462aeaafad65ba927f5f77d468d889a9c9681ce2da675645b6644c65c543ce"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "23d22071263fe956eef1827d9801700a9a4209b4952c68dc95661d01517f9bc8"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "b6b0c2c901ce6f38dabddd14955558a04458f8423197c5d769a2a7414e0855d9"
binding = json.loads((stage / "binding.json").read_text())
assert binding["source_commit"] == "7019821fc9d7814d0632fea06de50933aa9e35ee" and binding["integrated_head_at_prepare"] == "eea5ef8b8cf34b3d60b7b4b34a6211e9927e5c7e" and binding["source_tree_matches_integrated_head"] is True
assert binding["planned_target_count"] == 12 and binding["planned_features"] == "testing-environ,sys,net,f32_float"
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "de4b51e5f5a3717f1d324bb6dbe0e66e540131ae01d7aebbf358c2bb5d174699"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
