"""Retire only this completed workhorse control's stage and unmounted ISOs."""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


nonce = "49243ecf52d64c609a876e3c52409500"
stage = Path("/var/roothome/.local/share/agent-builds/rhai/project-command-" + nonce)
iso_root = Path("/var/lib/libvirt/images/rhai-win11-quality")
names = ["project-command-" + nonce + "-v2.iso", "project-export-" + nonce + ".iso"]
names += ["project-retire-" + nonce + suffix + ".iso"
          for suffix in ("", "-v2", "-v3", "-v4", "-v5", "-v6")]
isos = [iso_root / name for name in names]
original_sdb = iso_root / "work-retirement-bounds-20261009-c18e85827e6f4404.iso"
original_sdc = iso_root / "acceptance-20261008T125846Z-b7f83433/monitor-fixture02.iso"


def need(ok, why):
    if not ok:
        raise RuntimeError(why)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mounts():
    output = subprocess.check_output(["virsh", "domblklist", "rhai-win11-quality"], text=True)
    rows = {row.split()[0]: row.split()[1] for row in output.splitlines()
            if row.strip().startswith(("sda ", "sdb ", "sdc "))}
    need(rows.get("sdb") == str(original_sdb) and rows.get("sdc") == str(original_sdc),
         "original VM media not restored")
    need(all(str(path) not in output for path in isos), "own medium still attached")
    return rows


before = mounts()
need(stage.is_dir() and not stage.is_symlink() and stage.name == "project-command-" + nonce,
     "exact own host stage missing")
for parent in (stage, *stage.parents):
    need(not parent.is_symlink(), "symlink host stage ancestor")
files = {}
total = 0
for current, directories, filenames in os.walk(stage, followlinks=False):
    for name in directories:
        need(not (Path(current) / name).is_symlink(), "symlink host stage directory")
    for name in filenames:
        path = Path(current) / name
        need(path.is_file() and not path.is_symlink(), "unexpected host stage entry")
        relative = path.relative_to(stage).as_posix()
        size = path.stat().st_size
        total += size
        files[relative] = {"bytes": size, "sha256": sha(path)}
        need(len(files) <= 128 and total <= 20 * 1024 * 1024,
             "host stage inventory exceeds owned bound")
need(len(files) >= 50, "host stage inventory unexpectedly short")
media = {}
for path in isos:
    need(path.is_file() and not path.is_symlink() and path.parent == iso_root,
         "exact own ISO missing or changed type")
    size = path.stat().st_size
    need(0 < size <= 2 * 1024 * 1024, "own ISO outside size bound")
    media[path.name] = {"bytes": size, "sha256": sha(path)}

for path in isos:
    path.unlink()
shutil.rmtree(stage)
need(not stage.exists() and all(not path.exists() for path in isos),
     "owned host resources remain")
after = mounts()
print(json.dumps({"owner": "this Rhai project-command control", "nonce": nonce,
                  "host_stage": str(stage), "stage_files": files, "stage_bytes": total,
                  "retired_media": media, "media_before": before, "media_after": after,
                  "stage_absent": True, "media_absent": True,
                  "foreign_resources_touched": False}, sort_keys=True))
