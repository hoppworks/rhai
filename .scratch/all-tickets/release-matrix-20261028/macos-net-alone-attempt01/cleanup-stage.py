"""Retire only the exported, failed macOS net-only stage."""
import json
from pathlib import Path
import shutil

stage = Path("/Users/hoppworks/.local/share/agent-builds/rhai/macos-net-alone-4c76d812")
scope = Path("/Users/hoppworks/.local/share/agent-builds/rhai/macos-net-alone-4c76d812-scope")
assert stage.is_dir() and not stage.is_symlink() and not scope.exists() and not scope.is_symlink()
expected = {
    "binding.json", "cargo-clean.log", "Cargo.lock", "cargo-version.log",
    "commands.json", "compile.log", "launch.sh", "outer.log", "outer.status",
    "rhai-source.zip", "run.py", "rustc-version.log", "source-manifest.json",
    "suite.log", "wrong-peer-eof.log",
}
assert {item.name for item in stage.iterdir()} == expected
assert all(item.is_file() and not item.is_symlink() for item in stage.iterdir())
assert (stage / "outer.status").read_text().strip() == "1"
assert [item["exit"] for item in json.loads((stage / "commands.json").read_text())] == [0, 0, 0, 101, 101, 0]
shutil.rmtree(stage)
assert not stage.exists() and not scope.exists()
print(json.dumps({"stage": str(stage), "scope": str(scope),
                  "stage_absent": True, "scope_absent": True,
                  "owned_file_count": len(expected)}, indent=2))
