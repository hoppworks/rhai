#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "a542a6b8cc9d4ed6b8bbda30beee4922"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "7f6fd0287b80ea5edae6a10a3c707d8e32fdcbe4bc1c3eda6c4e1852b77685bc"
assert digest(stage / "media-input" / "Start.ps1") == "50882a7b691f5ecfa66def66ab64b6db79deac53a12d3e6cff7fb3e71b2f03d1"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "ffbf55bf5774a81bb2e91fcd323283ba5b1e40bc1f1a07c3aa85d03b13e1897b"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "03161b01ed122386f69f758d9fd664656fc03c3a10f43bc9bc830206735ab522"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "a25e9858b0a46d0409c71b8d26cc31a3a1fb8619bc606275e94e15c817d580c9"
binding = json.loads((stage / "binding.json").read_text())
assert binding["source_commit"] == "7019821fc9d7814d0632fea06de50933aa9e35ee" and binding["source_manifest_sha256"] == "b829308ab356d7aaaf7bf8d3acc9f65aab8fb316192d9b1b69e3365d78c834fd" and binding["integrated_head_at_prepare"] == "2856055a56f621067cb0944830dcd6efaf250bdf" and binding["source_tree_matches_integrated_head"] is True and binding["test_overlay_sha256"] == "715af9df54ce68df64cbf4d29b5479ef8201dbc6802f515cc820749cb42fdeb7"
assert binding["profiles"] == ["testing-environ,net,no_object"] and binding["targets"] == {"net_no_object": ["registered_stream_functions_work_without_dot_syntax", "registered_listener_functions_work_with_explicit_handle_arguments", "registered_error_getters_are_callable_with_explicit_arguments"]} and binding["driver_deadline_seconds"] == 180 and binding["observer_deadline_seconds"] == 185
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "9225996b02ee11aff8c17c516399f4eec1fdfaba4bd31760bd55d51b58b05fb2"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
