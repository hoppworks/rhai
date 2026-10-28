"""Type the one hash-guarded guest command without submitting it."""
import hashlib
from pathlib import Path
import subprocess
import sys

stage = Path(sys.argv[1]).resolve()
assert stage.name == "windows-rhai-native-a08d2c17c8ec4567b0b4f2d2e7124b92"
path = stage / "dispatch-command.txt"
command = path.read_text().rstrip("\n")
assert "\n" not in command and command.startswith("if ((Get-FileHash E:\\Start.ps1).Hash -eq '")
expected = "7f8f1140a2eec0f68498eff843075394138f701377b4049ca422018ee3014f4a"
assert expected.upper() in command
assert hashlib.sha256((stage / "media-input" / "Start.ps1").read_bytes()).hexdigest() == expected
subprocess.run(["python3", "-B", str(stage / "console-key-input.py"), command], check=True)
