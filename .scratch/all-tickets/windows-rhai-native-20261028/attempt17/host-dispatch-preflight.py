#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "938153339eb2af49cb69654e866305e8"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "2a1c1b9c3d1617645aa539cb9f940ede80fcb7707ff2798071419af399996a16"
assert digest(stage / "media-input" / "Start.ps1") == "8486e586958310e62fda4a60c340d2a3995de7613223e04d1bbf758c6fc60212"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "bc0456072cb8e8edfe4b593b2813f529fa720f9ff4195b4217b5bed208949ed9"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "888de39f81168d11ad439b10ec63eddaaea49d1f0e99689d3ae80dfacf5dceae"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "1920de6164fefedf24c63610ee00b114340827dac868a142697497f6db9a4c99"
assert digest(stage / "dispatch-command.txt") == "e46a46b984847f7e6dbc17a0b5382afa3ad45e86533ccdc0002be24d9086d415"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
