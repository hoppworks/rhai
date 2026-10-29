"""Type the one hash-guarded guest command without submitting it."""
import hashlib
from pathlib import Path
import subprocess
import sys

stage = Path(sys.argv[1]).resolve()
assert stage.name == "windows-rhai-native-4197aac65a57420ba09fa6855525c353"
path = stage / "dispatch-command.txt"
command = path.read_text().rstrip("\n")
assert "\n" not in command and command.startswith("if ((Get-FileHash E:\\Start.ps1).Hash -eq '")
expected = "cf9bb98a30508c15f3e5cee3d381c69cdf963943a4c27e1fd1fb213de7e9c849"
assert expected.upper() in command
assert hashlib.sha256((stage / "media-input" / "Start.ps1").read_bytes()).hexdigest() == expected
helper = stage / "console-key-input.py"
assert helper.is_file() and not helper.is_symlink()
assert hashlib.sha256(helper.read_bytes()).hexdigest() == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
subprocess.run(["python3", "-B", str(stage / "console-key-input.py"), command], check=True)
