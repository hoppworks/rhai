"""Type the one hash-guarded guest command without submitting it."""
import hashlib
from pathlib import Path
import subprocess
import sys

stage = Path(sys.argv[1]).resolve()
assert stage.name == "windows-rhai-native-a90bb2797c791644886326e73e5f70c8"
path = stage / "dispatch-command.txt"
command = path.read_text().rstrip("\n")
assert "\n" not in command and command.startswith("if ((Get-FileHash E:\\Start.ps1).Hash -eq '")
expected = "56f8e56ec14268b71f3207c2d2adc88c69626a2ebf5e266b1f876432c7e8e86d"
assert expected.upper() in command
assert hashlib.sha256((stage / "media-input" / "Start.ps1").read_bytes()).hexdigest() == expected
subprocess.run(["python3", "-B", str(stage / "console-key-input.py"), command], check=True)
