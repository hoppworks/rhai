"""Type the one hash-guarded guest command without submitting it."""
import hashlib
from pathlib import Path
import subprocess
import sys

stage = Path(sys.argv[1]).resolve()
assert stage.name == "windows-rhai-native-3d6e4701fab4530e3c3e8d68af3c882f"
path = stage / "dispatch-command.txt"
command = path.read_text().rstrip("\n")
assert "\n" not in command and command.startswith("if ((Get-FileHash E:\\Start.ps1).Hash -eq '")
expected = "a951df1c5a54e509722b22e1e32526043e1310288aafe62a4c98004e8e2decd5"
assert expected.upper() in command
assert hashlib.sha256((stage / "media-input" / "Start.ps1").read_bytes()).hexdigest() == expected
subprocess.run(["python3", "-B", str(stage / "console-key-input.py"), command], check=True)
