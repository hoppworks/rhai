"""Read-only exact binding immediately before one native Windows bootstrap dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "a7e54f39104e47c7ad826b2b9938365f"
stage = Path(f"/var/roothome/.local/share/agent-builds/rhai/windows-msrv-bootstrap-{nonce}")
medium = Path(f"/var/lib/libvirt/images/rhai-win11-quality/rhai-msrv-bootstrap-a04-{nonce}.iso")
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
assert digest(medium) == digest(stage / "msrv-bootstrap.iso") == "6a5278548109fa6e3dfeee6245c20785f1c0d6b6ec596ed4f966b329a4100582"
assert digest(stage / "media-input" / "Start.ps1") == "6e1d484c88ccb74e9d805b4013b1e62ce9188e7acdae627782f62483a04dbae5"
assert digest(stage / "media-input" / "InstallAndVerify.cmd") == "ad351600c96d10253a0be97aa8ca7aa810664064dec48fe18e19fbe50355b4d1"
assert digest(stage / "attempt04-dispatch-command.txt") == "2253fdd45ecccc1841ce9e43521c320950d0d862f8336fa22617b3c2ea71e28b"
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
