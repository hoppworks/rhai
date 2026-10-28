#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "57dff682c59e6cf0526f7640f64aa14c"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "f5130233fc7c4467a9748d02d0f5b9ab4f9a9bc5d5a7ca307ffc359306d91c14"
assert digest(stage / "media-input" / "Start.ps1") == "972d80d1c5b9d26b220a0045ab19d73e460ec1fd884368501fc68146b049be43"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "325781d6f4dea13f25e405bfe7b3f6e3c77c4a17e1ffb76993d63206d3d23d78"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "583ef8002e7071d5b10a65c0c41ac85f8ca5b7eedec6a899184a9a3eaa18edc2"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "d6a0f9f15d38bd62c74b1b22bab374c6012f949a7e1f9eac69efde7aa4276cad"
assert digest(stage / "dispatch-command.txt") == "585397f994b8d9156e339a2a34cf97bb2ba02b360fcfad99205a49b2b4658821"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
