#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "dee8dccda0d9d086858b8878c2e5f6ab"
stage = Path(f"/var/roothome/.local/share/agent-builds/rhai/windows-rhai-native-{nonce}")
medium = Path(f"/var/lib/libvirt/images/rhai-win11-quality/rhai-native-{nonce}.iso")
serial = Path("/var/log/libvirt/qemu/rhai-win11-quality-serial0.log")
expires = dt.datetime.fromisoformat("2026-10-30T12:00:00+00:00")
now = dt.datetime.now(dt.timezone.utc)
assert now + dt.timedelta(seconds=270) < expires, "retained public build has insufficient original lifetime"
assert subprocess.check_output(["virsh", "domuuid", "rhai-win11-quality"], text=True).strip() == "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19"
assert subprocess.check_output(["virsh", "domstate", "rhai-win11-quality"], text=True).strip() == "running"
devices = subprocess.check_output(["virsh", "domblklist", "rhai-win11-quality", "--details"], text=True)
assert any(line.split()[-2:] == ["sdc", str(medium)] for line in devices.splitlines() if len(line.split()) >= 4)
def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()
assert digest(medium) == digest(stage / "rhai-native.iso") == "56306945612cbe8fc99d5745a84ef3e42759407b8798e3e6427e85205ba668dc"
assert digest(stage / "media-input" / "Start.ps1") == "84502c97780a5d027ef2f9a6ec053874c261ca8315c8ce7fc7eac8a71d152b6d"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "f151c91a622950d6d0d11d448d117f3ce1fc3a4887dbf73e771c5734591d2657"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "95eb1327d504ca10f02244e0cb50587a4bbd0e7a47c87226a8a63514da150099"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "ae2a6d7e5372d66f385b2f46ced34da1ef33e7d6b667ddbe57459a4b991de23a"
assert digest(stage / "dispatch-command.txt") == "4c96efabaf0ece1c47c873f1226cae489a664571ac3be6cd45f3fd6a9f7c22ee"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
