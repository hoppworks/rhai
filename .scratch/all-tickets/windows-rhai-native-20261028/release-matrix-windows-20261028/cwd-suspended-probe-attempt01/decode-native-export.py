"""Reconstruct hash-bound original files from one bounded native COM1 export."""
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

root = Path(sys.argv[1]).resolve()
raw = (root / "serial-original.bin").read_bytes()
identity = 'rhai-native-c61eb47971c24dee985173da67278b42'
prefix = ("RHAI_BOOTSTRAP " + identity + " ").encode()
frames = []
for line in raw.splitlines():
    if not line.startswith(prefix):
        continue
    parts = line.split(b" ", 4)
    assert len(parts) == 5 and len(parts[4]) <= 3500
    frames.append((int(parts[2]), parts[3].decode("ascii"), json.loads(base64.b64decode(parts[4], validate=True))))
assert frames and [f[0] for f in frames] == list(range(len(frames)))
assert frames[0][1] == "BEGIN" and frames[-1][1] == "END"
begin, end = frames[0][2], frames[-1][2]
assert begin["id"] == end["id"] == identity
assert begin["accepted"] == end["accepted"]
assert begin["exit"] == end["exit"]
assert end["guest_evidence_retained"] is True
assert 0 <= end["files"] <= 64
out = root / "original-export"
if not out.exists():
    out.mkdir()
files = {}
current = None
content = bytearray()
total = 0
for _, kind, item in frames[1:-1]:
    if kind == "FILE":
        name = item["path"]
        path = PurePosixPath(name)
        assert current is None and not path.is_absolute() and ".." not in path.parts
        assert "\\" not in name and ":" not in name and name not in files
        assert 0 <= item["length"] <= 4 * 1024 * 1024
        current, content = item, bytearray()
    elif kind == "CHUNK":
        assert current is not None and item["path"] == current["path"] and item["offset"] == len(content)
        chunk = base64.b64decode(item["data"], validate=True)
        assert 0 < len(chunk) <= 1024
        content.extend(chunk)
        assert len(content) <= current["length"]
    elif kind == "FILE_END":
        assert current is not None and item == current and len(content) == item["length"]
        assert hashlib.sha256(content).hexdigest() == item["sha256"]
        destination = out / current["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            assert destination.read_bytes() == content
        else:
            destination.write_bytes(content)
        files[current["path"]] = current
        total += len(content)
        assert total <= 16 * 1024 * 1024
        current = None
    else:
        raise AssertionError("unexpected frame kind: " + kind)
assert current is None and len(files) == end["files"]
assert set(files) >= {"observer.json", "preflight.json", "source-manifest.json", "build-manifest.txt", "driver.stdout", "driver.stderr"}
assert sum(name.startswith("run/.scoped-run-") and name.endswith(".journal") for name in files) == 1
manifest_count = sum(name.startswith("run/.scoped-evidence-") and name.endswith("/manifest.txt") for name in files)
assert manifest_count == 1 if begin["accepted"] else manifest_count <= 1
record = {"id": identity, "frames": len(frames), "files": files, "begin": begin, "end": end, "bytes": total, "serial_sha256": hashlib.sha256(raw).hexdigest(), "serial_bytes": len(raw)}
(root / "original-export-readback.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"frames": len(frames), "files": len(files), "bytes": total, "accepted": begin["accepted"], "driver_exit": begin["exit"]}))
