"""Type the single reviewed, hash-guarded guest bootstrap command."""
import hashlib
from pathlib import Path
import subprocess
import sys

stage = Path(sys.argv[1]).resolve()
assert stage.name == "windows-msrv-bootstrap-a7e54f39104e47c7ad826b2b9938365f"
command = (stage / "attempt04-dispatch-command.txt").read_text().rstrip("\n")
expected = "6e1d484c88ccb74e9d805b4013b1e62ce9188e7acdae627782f62483a04dbae5"
helper_hash = "cee8cf1139b8f817e2b49e99013c7ce7f93a5b4319875fa7cb4f4c31a8367929"
assert command.count("\n") == 0 and command.startswith("if ((Get-FileHash E:\\Start.ps1).Hash -eq '")
assert expected.upper() in command
assert hashlib.sha256((stage / "media-input" / "Start.ps1").read_bytes()).hexdigest() == expected
assert hashlib.sha256((stage / "console-key-input.py").read_bytes()).hexdigest() == helper_hash
subprocess.run(["python3", "-B", str(stage / "console-key-input.py"), command], check=True)
