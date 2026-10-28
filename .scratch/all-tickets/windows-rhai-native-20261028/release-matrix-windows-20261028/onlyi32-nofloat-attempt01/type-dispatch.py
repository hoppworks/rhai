"""Type the one hash-guarded guest command without submitting it."""
import hashlib
from pathlib import Path
import subprocess
import sys

stage = Path(sys.argv[1]).resolve()
assert stage.name == "windows-rhai-native-174569010c83bd99aa10db76dc6fe7fa"
path = stage / "dispatch-command.txt"
command = path.read_text().rstrip("\n")
assert "\n" not in command and command.startswith("if ((Get-FileHash E:\\Start.ps1).Hash -eq '")
expected = "ed5ec78fe9a302e16792bb68ca6ce74b6fbabbbc80e813c7e277fde9671ae312"
assert expected.upper() in command
assert hashlib.sha256((stage / "media-input" / "Start.ps1").read_bytes()).hexdigest() == expected
subprocess.run(["python3", "-B", str(stage / "console-key-input.py"), command], check=True)
