"""Current host-wide readback of VM mounts and process file/cwd references."""
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


nonce = "49243ecf52d64c609a876e3c52409500"
domains = [x for x in subprocess.check_output(
    ["virsh", "list", "--all", "--name"], text=True).splitlines() if x]
mounts = {name: subprocess.check_output(
    ["virsh", "domblklist", name], text=True) for name in domains}
references = []
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
        if nonce in target:
            references.append({"pid": int(process.name), "link": str(path), "target": target})
print(json.dumps({"observed_utc": datetime.now(timezone.utc).isoformat(),
                  "domains": domains, "mounts": mounts,
                  "mounted_own_media": [name for name, value in mounts.items() if nonce in value],
                  "open_own_paths": references}, sort_keys=True))
