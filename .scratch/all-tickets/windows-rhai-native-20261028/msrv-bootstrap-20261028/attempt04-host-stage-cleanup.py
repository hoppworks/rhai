"""Retire the exact owned POSIX staging directory after evidence export."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

stage = Path("/var/roothome/.local/share/agent-builds/rhai/"
             "windows-msrv-bootstrap-a7e54f39104e47c7ad826b2b9938365f")
assert stage.is_dir() and not stage.is_symlink() and stage.stat().st_uid == os.getuid()
entries = sorted(stage.rglob("*"))
assert entries and all(not entry.is_symlink() for entry in entries)
files = [entry for entry in entries if entry.is_file()]
assert all(entry.is_file() or entry.is_dir() for entry in entries)
assert len(files) >= 50
tree = hashlib.sha256()
bytes_total = 0
for path in files:
    data = path.read_bytes()
    bytes_total += len(data)
    tree.update(path.relative_to(stage).as_posix().encode() + b"\0")
    tree.update(hashlib.sha256(data).digest())
    user = subprocess.run(["fuser", "-a", str(path)], capture_output=True, text=True)
    assert user.returncode == 1 and not user.stdout.strip(), (path, user)
shutil.rmtree(stage)
assert not stage.exists()
print(json.dumps({"stage": str(stage), "file_count": len(files),
                  "file_bytes": bytes_total, "pre_retirement_tree_sha256": tree.hexdigest(),
                  "no_symlinks_or_exact_file_users": True,
                  "stage_absent_after_retirement": True}, indent=2))
