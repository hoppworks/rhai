"""Type the one hash-guarded guest command without submitting it."""
import hashlib
from pathlib import Path
import subprocess
import sys

stage = Path(sys.argv[1]).resolve()
assert stage.name == "windows-rhai-native-e1534746c0394e61a2defda7c3a79c08"
path = stage / "dispatch-command.txt"
command = path.read_text().rstrip("\n")
assert "\n" not in command and command.startswith("if ((Get-FileHash E:\\Start.ps1).Hash -eq '")
expected = "8dc4404639f74c025c893f7d9b5dcbc293fe9b35d3f29053ae5ad309763ac087"
assert expected.upper() in command
assert hashlib.sha256((stage / "media-input" / "Start.ps1").read_bytes()).hexdigest() == expected
helper = stage / "console-key-input.py"
assert helper.is_file() and not helper.is_symlink()
assert hashlib.sha256(helper.read_bytes()).hexdigest() == "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
subprocess.run(["python3", "-B", str(stage / "console-key-input.py"), command], check=True)
