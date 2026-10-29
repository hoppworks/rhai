"""Attach only this attempt's hash-checked ISO to live sdc."""

from pathlib import Path
import hashlib
import json
import shutil
import subprocess

nonce = "06d6577d5a724d6cb791686d5534d254"
stage = Path("/var/roothome/.local/share/agent-builds/rhai/windows-rhai-native-" + nonce)
medium = Path("/var/lib/libvirt/images/rhai-win11-quality/rhai-native-" + nonce + ".iso")
original = Path("/var/lib/libvirt/images/rhai-win11-quality/acceptance-20261008T125846Z-b7f83433/monitor-fixture02.iso")
foreign = Path("/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso")
expected = "74c4e39c1908cbd2d7e1349a6790ee18e861568e58a998fcc7209ac52b05f424"
assert stage.is_dir() and not stage.is_symlink() and not medium.exists() and not medium.is_symlink()
assert hashlib.sha256((stage / "rhai-native.iso").read_bytes()).hexdigest() == expected
assert subprocess.check_output(["virsh", "domuuid", "rhai-win11-quality"], text=True).strip() == "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19"
assert subprocess.check_output(["virsh", "domstate", "rhai-win11-quality"], text=True).strip() == "running"


def devices(inactive=False):
    command = ["virsh", "domblklist", "rhai-win11-quality", "--details"]
    if inactive:
        command.append("--inactive")
    return subprocess.check_output(command, text=True)


def attached(rows, device, path):
    return any(line.split()[-2:] == [device, str(path)] for line in rows.splitlines() if len(line.split()) >= 4)


live, inactive = devices(), devices(True)
assert attached(live, "sdc", original) and attached(inactive, "sdc", original)
assert attached(live, "sdb", foreign) and attached(inactive, "sdb", foreign)
shutil.copyfile(stage / "rhai-native.iso", medium)
medium.chmod(0o644)
assert medium.stat().st_nlink == 1 and hashlib.sha256(medium.read_bytes()).hexdigest() == expected
subprocess.run(["virsh", "change-media", "rhai-win11-quality", "sdc", str(medium), "--update", "--live"], check=True, capture_output=True, text=True)
live, inactive = devices(), devices(True)
assert attached(live, "sdc", medium) and attached(inactive, "sdc", original)
assert attached(live, "sdb", foreign) and attached(inactive, "sdb", foreign)
record = {"vm_uuid": "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19", "own_iso": str(medium), "iso_sha256": expected,
          "live_sdc_own": True, "inactive_sdc_original": True, "foreign_sdb_unchanged": True}
(stage / "host-attach.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
