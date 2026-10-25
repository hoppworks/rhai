"""Retire the exact completed read-only Windows OS-query host stage."""
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


stage = Path("/var/roothome/.local/share/agent-builds/rhai/os-readback-ad552d11876d43f59e8ffe6a2cf1618f")
assert stage.is_dir() and not stage.is_symlink()
files = {}
total = 0
for current, directories, names in os.walk(stage, followlinks=False):
    assert not any((Path(current) / name).is_symlink() for name in directories)
    for name in names:
        path = Path(current) / name
        assert path.is_file() and not path.is_symlink()
        size = path.stat().st_size
        files[path.relative_to(stage).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        total += size
assert len(files) == 7 and total <= 2 * 1024 * 1024
open_paths = []
for process in Path("/proc").iterdir():
    if not process.name.isdecimal():
        continue
    paths = [process / "cwd", process / "exe"]
    try:
        paths.extend((process / "fd").iterdir())
    except (FileNotFoundError, PermissionError, NotADirectoryError):
        continue
    for path in paths:
        try:
            target = os.readlink(path)
        except (FileNotFoundError, PermissionError, NotADirectoryError, OSError):
            continue
        if target.startswith(str(stage) + "/") or target == str(stage):
            open_paths.append({"pid": process.name, "target": target})
assert not open_paths, open_paths
shutil.rmtree(stage)
assert not stage.exists()
print(json.dumps({"retired_utc": datetime.now(timezone.utc).isoformat(),
                  "stage": str(stage), "files": files, "bytes": total,
                  "open_paths_before": open_paths, "stage_absent": True}, sort_keys=True))
