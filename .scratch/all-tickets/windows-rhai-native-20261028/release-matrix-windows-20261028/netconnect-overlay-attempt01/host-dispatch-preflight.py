#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "c3f78f6ab1234d9e83e70518c678aa2b"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "c1ee3edf819138062f7f2ab23cac6fbbce5ce34e247bfdddea8830696571a28e"
assert digest(stage / "media-input" / "Start.ps1") == "d22ef0046b6b842270fbaf5327722f7021da8167b9f8711c429893809d4a7dde"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "fef75b5a73891e81be327e623948d7512d50024f0366951cc3f40fb1b76fa0b5"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "22d64a5a3116f6d82d4cfcf1849e2ff1a81db1cedde071ddc7d3bb432798373a"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "16bfd8c8c4d1a52c74f9e01b40ea0ce1a15f8dcf7db79778cd0c996bd8542639"
binding = json.loads((stage / "binding.json").read_text())
assert binding["source_commit"] == "7019821fc9d7814d0632fea06de50933aa9e35ee" and binding["source_manifest_sha256"] == "b829308ab356d7aaaf7bf8d3acc9f65aab8fb316192d9b1b69e3365d78c834fd" and binding["integrated_head_at_prepare"] == "09cda9223ad2a739dd740997ecbcf639afe733a2" and binding["source_tree_matches_integrated_head"] is False and binding["test_overlay_sha256"] == "715af9df54ce68df64cbf4d29b5479ef8201dbc6802f515cc820749cb42fdeb7"
assert binding["profiles"] == ["testing-environ,sys", "testing-environ,net"] and binding["targets"] == {"sys": ["sys_policy", "sys_env", "sys_fs"], "net": ["net_connect", "net_listen", "net_reads", "net_writes"]} and binding["driver_deadline_seconds"] == 180 and binding["observer_deadline_seconds"] == 185
assert set(binding["media_files"]) == {path.name for path in (stage / "media-input").iterdir()}
for name, pin in binding["media_files"].items():
    file = stage / "media-input" / name
    assert file.is_file() and not file.is_symlink() and file.stat().st_size == pin["bytes"]
    assert digest(file) == pin["sha256"], name
assert any(line.split()[-2:] == ["sdb", "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"] for line in devices.splitlines() if len(line.split()) >= 4)
assert digest(stage / "dispatch-command.txt") == "586fc240f8437eae2f4c8b16c0eff5004582e134aa9b847860a858ca80f1118c"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
