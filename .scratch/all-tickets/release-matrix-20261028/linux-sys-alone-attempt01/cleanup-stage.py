"""Retire only this exported Linux Sys proof stage."""

import hashlib
from pathlib import Path

stage = Path("/var/roothome/.local/share/agent-builds/rhai/linux-sys-alone-20261029-4d9bce21")
scope = Path("/var/roothome/.local/share/agent-builds/rhai/linux-sys-alone-20261029-4d9bce21-scope")
assert stage.is_dir() and not stage.is_symlink() and not scope.exists()
listed = {}
for line in (stage / "remote-export.sha256").read_text().splitlines():
    digest, name = line.split("  ", 1)
    assert name not in listed and "/" not in name and "\\" not in name
    listed[name] = digest
assert len(listed) == 19
expected = set(listed) | {"remote-export.sha256", "cleanup-stage.py"}
assert {path.name for path in stage.iterdir()} == expected
for name, expected_hash in listed.items():
    path = stage / name
    assert path.is_file() and not path.is_symlink()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash
for name in expected:
    (stage / name).unlink()
stage.rmdir()
assert not stage.exists() and not scope.exists()
print("exact owned stage and scope absent")
