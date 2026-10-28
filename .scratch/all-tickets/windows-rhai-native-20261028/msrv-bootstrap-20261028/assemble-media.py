"""Build one hash-checked owned read-only Windows bootstrap control medium."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

stage = Path(sys.argv[1]).resolve()
runtime = Path(os.environ["AGENT_RUNTIME_DIR"]).resolve()
source = stage / "media-input"
output = stage / "msrv-bootstrap.iso"
expected_names = {
    "Start.ps1",
    "Check.ps1",
    "InstallAndVerify.cmd",
    "rhai-msrv-bootstrap-a7e54f39104e47c7ad826b2b9938365f.bundle",
}
assert stage.name == "windows-msrv-bootstrap-a7e54f39104e47c7ad826b2b9938365f"
assert source.is_dir() and not output.exists()
assert {p.name for p in source.iterdir()} == expected_names
assert all(p.is_file() and not p.is_symlink() for p in source.iterdir())
digest = lambda data: hashlib.sha256(data).hexdigest()
expected = {p.name: digest(p.read_bytes()) for p in source.iterdir()}
temporary = runtime / "msrv-bootstrap.iso"
subprocess.run(["genisoimage", "-quiet", "-J", "-R", "-V", "RHAIMSRV",
                "-o", str(temporary), str(source)], check=True, timeout=60)
found = {}
for entry in subprocess.check_output(
        ["isoinfo", "-J", "-i", str(temporary), "-f"], text=True, timeout=30).splitlines():
    name = entry.lstrip("/").split(";")[0]
    if name in expected:
        data = subprocess.check_output(
            ["isoinfo", "-J", "-i", str(temporary), "-x", entry], timeout=30)
        found[name] = digest(data)
assert found == expected, (found, expected)
shutil.copyfile(temporary, output)
output.chmod(0o644)
record = {"iso_sha256": digest(output.read_bytes()), "iso_bytes": output.stat().st_size,
          "files": expected}
(stage / "media-readback.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
