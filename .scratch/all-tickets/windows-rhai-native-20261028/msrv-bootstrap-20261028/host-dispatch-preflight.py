"""Read-only exact binding immediately before one native Windows bootstrap dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "a7e54f39104e47c7ad826b2b9938365f"
stage = Path(f"/var/roothome/.local/share/agent-builds/rhai/windows-msrv-bootstrap-{nonce}")
medium = Path(f"/var/lib/libvirt/images/rhai-win11-quality/rhai-msrv-bootstrap-{nonce}.iso")
serial = Path("/var/log/libvirt/qemu/rhai-win11-quality-serial0.log")
now = dt.datetime.now(dt.timezone.utc)
expiry = dt.datetime.fromisoformat("2026-10-30T12:00:00+00:00")
assert now + dt.timedelta(minutes=8) < expiry
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert subprocess.check_output(["virsh", "domuuid", "rhai-win11-quality"], text=True).strip() == "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19"
assert subprocess.check_output(["virsh", "domstate", "rhai-win11-quality"], text=True).strip() == "running"
devices = subprocess.check_output(["virsh", "domblklist", "rhai-win11-quality"], text=True)
assert any(line.split()[-2:] == ["sdc", str(medium)] for line in devices.splitlines() if len(line.split()) >= 2)
assert any("sdb" in line and "work-retirement-bounds-20261009-c18e85827e6f4404.iso" in line for line in devices.splitlines())
assert digest(medium) == digest(stage / "msrv-bootstrap.iso") == "e16c3f6122cb8a28c5ba24cc4ba5b6423fa8f989094e3922d5e6f1841e34c0b6"
assert digest(stage / "media-input" / "Start.ps1") == "b18feb739936e50aa53a780328980804beeb8a359a19e19120c70bee4dcbf80c"
assert digest(stage / "media-input" / "InstallAndVerify.cmd") == "48ba32cf6e1ee2a71603ad86992313084a4e60b4f91c8d5a2ee6e30d6be23717"
assert digest(stage / "dispatch-command.txt") == "878aa502ee46326856f210fe502973a92387d3725cc5cc46e43d47cb6309fd54"
assert digest(stage / "console-key-input.py") == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
fs = os.statvfs("/var")
free = fs.f_bavail * fs.f_frsize
assert free >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "public_build_expiry_utc": expiry.isoformat(),
                  "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium),
                  "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_inode": stat.st_ino,
                  "serial_offset": stat.st_size, "host_free_var_bytes": free,
                  "source_review": "READY", "native_started": False}, indent=2))
