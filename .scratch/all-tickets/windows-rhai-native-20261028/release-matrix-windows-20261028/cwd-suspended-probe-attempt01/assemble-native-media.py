"""Build and read back only this attempt's immutable native control medium."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

stage = Path(sys.argv[1]).resolve()
nonce = "c61eb47971c24dee985173da67278b42"
assert stage.name == "windows-rhai-native-" + nonce
runtime = Path(os.environ["AGENT_RUNTIME_DIR"]).resolve()
source = stage / "media-input"
target = stage / "rhai-native.iso"
assert source.is_dir() and not target.exists()
expected = {
    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
    for path in source.iterdir() if path.is_file()
}
assert len(expected) == 8, expected
temporary = runtime / "rhai-native.iso"
subprocess.run(["genisoimage", "-quiet", "-J", "-R", "-V", "RHAINATIVE",
                "-o", str(temporary), str(source)], check=True)
verified = {}
for iso_path in subprocess.check_output(
        ["isoinfo", "-J", "-i", str(temporary), "-f"], text=True).splitlines():
    name = iso_path.lstrip("/").split(";")[0]
    if name in expected:
        actual = subprocess.check_output(["isoinfo", "-J", "-i", str(temporary), "-x", iso_path])
        assert hashlib.sha256(actual).hexdigest() == expected[name], name
        verified[name] = expected[name]
assert verified == expected, (verified, expected)
shutil.copyfile(temporary, target)
target.chmod(0o644)
print(json.dumps({"iso_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                  "files": verified, "bytes": target.stat().st_size}, indent=2))
