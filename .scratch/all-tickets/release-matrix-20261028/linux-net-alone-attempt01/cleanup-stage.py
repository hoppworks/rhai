"""Retire only the exported, completed Linux net-only host staging directory."""
import json
from pathlib import Path
import shutil

stage = Path("/var/roothome/.local/share/agent-builds/rhai/linux-net-alone-b1f047c8")
scope = Path("/var/roothome/.local/share/agent-builds/rhai/linux-net-alone-b1f047c8-scope")
assert stage.is_dir() and not stage.is_symlink() and not scope.exists() and not scope.is_symlink()
expected = {
    "binding.json", "cargo-clean.log", "Cargo.lock", "cargo-version.log",
    "commands.json", "compile.log", "launch.sh", "outer.log", "outer.status",
    "result.json", "rhai-source.zip", "run.py", "rustc-version.log",
    "source-manifest.json", "suite.log", "wrong-peer-eof.log",
}
assert {item.name for item in stage.iterdir()} == expected
assert all(item.is_file() and not item.is_symlink() for item in stage.iterdir())
assert (stage / "outer.status").read_text().strip() == "0"
assert json.loads((stage / "result.json").read_text())["accepted"] is True
shutil.rmtree(stage)
assert not stage.exists() and not scope.exists()
print(json.dumps({"stage": str(stage), "scope": str(scope),
                  "stage_absent": True, "scope_absent": True,
                  "owned_file_count": len(expected)}, indent=2))
