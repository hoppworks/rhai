"""Type the one hash-guarded guest command without submitting it."""
import hashlib
from pathlib import Path
import subprocess
import sys

stage = Path(sys.argv[1]).resolve()
assert stage.name == "windows-rhai-native-6c165808b8d4457c996fa3f103ec7a86"
path = stage / "dispatch-command.txt"
command = path.read_text().rstrip("\n")
assert "\n" not in command and command.startswith("if ((Get-FileHash E:\\Start.ps1).Hash -eq '")
expected = "f16cff160ba3e1cfc3bebf3d13f8e63c2bb330f06096c00a39274ba061b50f10"
assert expected.upper() in command
assert hashlib.sha256((stage / "media-input" / "Start.ps1").read_bytes()).hexdigest() == expected
helper = stage / "console-key-input.py"
assert helper.is_file() and not helper.is_symlink()
assert hashlib.sha256(helper.read_bytes()).hexdigest() == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
subprocess.run(["python3", "-B", str(stage / "console-key-input.py"), command], check=True)
