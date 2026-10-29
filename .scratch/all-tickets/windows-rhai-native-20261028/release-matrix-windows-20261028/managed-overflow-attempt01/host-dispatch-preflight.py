#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "996bad1b0372473bb01b3a7c2c770535"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "08e6aea9be8d50833888258584a85aef963398c3aea72617f14babd52694f659"
assert digest(stage / "media-input" / "Start.ps1") == "9311cdbb28aba465cabd22ceafa3f63ca5e4c58a45ee3f5d6114bec7c6dd3458"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "e1467e05f9402a76d7331f4c50d08eadb44c1a7ab1b272111618de8b710545ef"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "2a8e2ec76f9216c9e3454e194b32b25024835e543978a64eae38985405ff2c17"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "648c5a07899fb58b4eae434dc5bb26d36af2b96ee9cdfb3a292dff13c5947579"
binding = json.loads((stage / "binding.json").read_text())
assert binding["base_head"] == "f7c42546fc62d3082422be7877619719884bbd70" and binding["overlay_sha256"] == "a4f13e031461651f5dcceeebee4f447ccd85edb8c228f1f99a8bebb16af028a5"
assert binding["target"] == "sys_process_windows" and binding["features"] == "testing-environ,sys,net" and binding["test"] == "windows_managed_output_limit_closes_descendant_and_preserves_sentinel"
assert binding["native_started"] is False
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "77d4fced04c39305ea421265ce802b4dac4e4472d1a4e8bdc9dc3eea14b4e155"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
