#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "73bbed61f32a48679390d099b4c3a9f5"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "628f5daaad1d6ec668f5632eb093f4ab4b3fe82a1e141eaf8db9baada99b1cbc"
assert digest(stage / "media-input" / "Start.ps1") == "c574625f7c8b385c881d02c313c55e589f1a4d2aa4ac7c2bd36728a45df49e41"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "4c3c7ad0bb0ec0c714ee3aa2671b81577bd2f1300fe23f763c122b8593804409"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "34470cc6d296c9e02aba5a5779f7f3dccafc9577ada280ddad4f74b09aca41f5"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "3a0766ec64f83135d1fd8a6dbae443dea07023c0aec94b6ee3130860de38440f"
binding = json.loads((stage / "binding.json").read_text())
assert binding["source_commit"] == "7019821fc9d7814d0632fea06de50933aa9e35ee" and binding["integrated_head_at_prepare"] == "7dacf2ae09ef657cfbb53d3a0b35b9bb7dc2f4ac" and binding["source_tree_matches_integrated_head"] is True
assert binding["planned_target_count"] == 1 and binding["planned_targets"] == ["sys_process_windows"] and binding["planned_features"] == "testing-environ,sys,net"
assert binding["planned_controls"] == ["managed-kill-wrong", "managed-timeout-wrong", "managed-drop-kill-wrong", "managed-drop-retain-wrong"]
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "c39f110b6dd104b4be94f5300f05764c9fd69d86322e0df7353865c0c89652b8"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
