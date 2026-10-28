#!/usr/bin/env python3
"""Read-only binding immediately before the one native Rhai dispatch."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

nonce = "9415bf24d8e92c551480f13b2ed45742"
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
assert digest(medium) == digest(stage / "rhai-native.iso") == "a6247aa684fd315d216d24389864c9ea647885d47898b7e08d51c066219419a8"
assert digest(stage / "media-input" / "Start.ps1") == "9df3ae13f010e41b2bf37e5b83ce94c7257b25877cd1682e9aa291b42fdc334a"
assert digest(stage / "media-input" / "RunRhaiContractControl.ps1") == "47d3ad122698687b86f90410ada120ebbf5a858c7e49835106b55fc880af7a84"
assert digest(stage / "media-input" / "RunRhaiContract.cmd") == "31820afd16768ddcdc112f9ab9674d9ead11b37880e44956ba32e1a1ceda831a"
assert digest(stage / "media-input" / "ClearOwnedWorkReadOnly.ps1") == "a41956730d570c0f564461c680099f9c8b791245c9365e5bf8aa007d446d34d1"
assert digest(stage / "dispatch-command.txt") == "82385d7a8a2385de80c2caef12d76b9510d316493f60b1ee1abf7719239dc446"
fs = os.statvfs("/var")
assert fs.f_bavail * fs.f_frsize >= 4 * 1024**3
stat = serial.stat()
print(json.dumps({"host_utc_before_enter": now.isoformat(), "original_expiry_utc": expires.isoformat(), "vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "medium_sha256": digest(medium), "start_sha256": digest(stage / "media-input" / "Start.ps1"), "serial_path": str(serial), "serial_inode": stat.st_ino, "serial_offset": stat.st_size, "host_free_var_bytes": fs.f_bavail * fs.f_frsize, "source_review": "READY", "native_started": False}, indent=2))
