"""Retire this package's exact unmounted workhorse media and exported stage."""

import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


STAGE = Path("/var/roothome/.local/share/agent-builds/rhai/backend-failure-3cd277ed37eb4926b06e55c9c44279a4")
SOURCE = Path("/var/lib/libvirt/images/rhai-win11-quality/backend-failure-3cd277ed37eb4926b06e55c9c44279a4.iso")
CLEANUP = Path("/var/lib/libvirt/images/rhai-win11-quality/backend-failure-cleanup-3cd277ed37eb4926b06e55c9c44279a4.iso")
ORIGINAL_SDB = "/var/lib/libvirt/images/rhai-win11-quality/work-retirement-bounds-20261009-c18e85827e6f4404.iso"
ORIGINAL_SDC = "/var/lib/libvirt/images/rhai-win11-quality/acceptance-20261008T125846Z-b7f83433/monitor-fixture02.iso"
VM = "rhai-win11-quality"
VM_UUID = "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def command(*args):
    return subprocess.check_output(args, text=True)


def mounts():
    names = command("virsh", "list", "--all", "--name").splitlines()
    return {name: command("virsh", "domblklist", name, "--details") for name in names if name}


assert command("virsh", "domuuid", VM).strip() == VM_UUID
assert STAGE.is_dir() and not STAGE.is_symlink() and os.stat(STAGE).st_uid == 0
inventory = json.loads((STAGE / "host-staging-before.json").read_text())
assert inventory["stage"] == str(STAGE) and inventory["vm_uuid"] == VM_UUID
assert inventory["original_media_restored"] is True
assert inventory["source_medium"] == str(SOURCE) and inventory["cleanup_medium"] == str(CLEANUP)
assert sha(SOURCE) == inventory["source_medium_sha256"]
assert sha(CLEANUP) == inventory["cleanup_medium_sha256"]

actual = {}
for root, dirs, files in os.walk(STAGE, followlinks=False):
    for name in dirs + files:
        path = Path(root) / name
        assert not path.is_symlink(), path
    for name in files:
        path = Path(root) / name
        actual[str(path.relative_to(STAGE))] = path
assert set(actual) == set(inventory["files"]) | {"host-staging-before.json"}
for relative, item in inventory["files"].items():
    path = actual[relative]
    assert path.stat().st_size == item["bytes"] and sha(path) == item["sha256"], relative

before = mounts()
assert VM in before and ORIGINAL_SDB in before[VM] and ORIGINAL_SDC in before[VM]
assert str(SOURCE) not in "\n".join(before.values())
assert str(CLEANUP) not in "\n".join(before.values())

SOURCE.unlink()
CLEANUP.unlink()
shutil.rmtree(STAGE)

after = mounts()
assert VM in after and ORIGINAL_SDB in after[VM] and ORIGINAL_SDC in after[VM]
assert not SOURCE.exists() and not CLEANUP.exists() and not STAGE.exists()
print(json.dumps({
    "retired_host_utc": datetime.now(timezone.utc).isoformat(),
    "vm_uuid": VM_UUID,
    "stage": str(STAGE),
    "retired_media": {str(SOURCE): inventory["source_medium_sha256"], str(CLEANUP): inventory["cleanup_medium_sha256"]},
    "retired_stage_file_count": len(actual),
    "retired_stage_total_bytes": sum(path["bytes"] for path in inventory["files"].values()) + len((json.dumps(inventory, indent=2) + "\n").encode()),
    "original_media_restored": True,
    "vm_mounts_after": after[VM],
    "exact_resources_absent": True,
}, indent=2))
