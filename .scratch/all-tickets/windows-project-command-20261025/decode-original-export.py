"""Reconstruct one saved native project-command export from COM1 bytes."""
import base64
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath


def need(ok, why):
    if not ok:
        raise RuntimeError(why)


root = Path(sys.argv[1]).resolve()
raw = (root / "serial-original.bin").read_bytes()
identity = "rhai-project-export-49243ecf52d64c609a876e3c52409500"
prefix = ("RHAI_BOOTSTRAP " + identity + " ").encode()
frames = []
for line in raw.splitlines():
    if not line.startswith(prefix):
        continue
    parts = line.split(b" ", 4)
    need(len(parts) == 5 and len(parts[4]) <= 3500, "malformed serial frame")
    payload = json.loads(base64.b64decode(parts[4], validate=True))
    frames.append((int(parts[2]), parts[3].decode("ascii"), payload))
need(frames and [x[0] for x in frames] == list(range(len(frames))), "frame gap or duplicate")
need(frames[0][1] == "BEGIN" and frames[-1][1] == "END", "missing export boundary")
begin, end = frames[0][2], frames[-1][2]
need(begin["id"] == end["id"] == identity, "wrong export identity")
need(begin["accepted"] is True and end["accepted"] is True, "guest rejected original")
need(begin["driver_exit"] == 0 and begin["runtime_absent"] is True
     and end["runtime_absent"] is True and end["guest_originals_retained"] is True,
     "native result or cleanup state differs")
need(begin["original_files"] == end["files"] == 10, "selected count differs")
need(0 <= begin["original_bytes"] == end["bytes"] <= 16 * 1024 * 1024,
     "selected byte count differs")
out = root / "original-export"
need(not out.exists(), "destination already exists")
out.mkdir()
files = {}
current = None
content = bytearray()
total = 0
for _, kind, item in frames[1:-1]:
    if kind == "FILE":
        name = item["path"]
        path = PurePosixPath(name)
        need(current is None and not path.is_absolute() and ".." not in path.parts
             and "\\" not in name and ":" not in name and name not in files,
             "unsafe or duplicate export path")
        need(0 <= item["length"] <= 4 * 1024 * 1024, "file exceeds cap")
        current = item
        content = bytearray()
    elif kind == "CHUNK":
        need(current is not None and item["path"] == current["path"]
             and item["offset"] == len(content), "out-of-order chunk")
        chunk = base64.b64decode(item["data"], validate=True)
        need(0 < len(chunk) <= 1024, "chunk exceeds cap")
        content.extend(chunk)
        need(len(content) <= current["length"], "chunk exceeds length")
    elif kind == "FILE_END":
        need(current is not None and item == current and len(content) == item["length"],
             "incomplete original file")
        need(hashlib.sha256(content).hexdigest() == item["sha256"], "original hash differs")
        dst = out / current["path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(content)
        files[current["path"]] = current
        total += len(content)
        need(len(files) <= 10 and total <= 16 * 1024 * 1024, "aggregate cap exceeded")
        current = None
    else:
        raise RuntimeError("unexpected serial kind " + kind)
need(current is None and len(files) == 10 and total == end["bytes"], "export incomplete")
need(set(files) >= {"observer.json", "preflight.json", "source-manifest.json",
                    "build-manifest.txt", "driver.stdout", "driver.stderr"},
     "missing top-level originals")
need(sum(name.startswith("run/.scoped-run-") and name.endswith(".journal") for name in files) == 1,
     "missing exact journal")
need(sum(name.startswith("run/.scoped-evidence-") and name.endswith("/stdout.log") for name in files) == 1,
     "missing evidence stdout")
need(sum(name.startswith("run/.scoped-evidence-") and name.endswith("/stderr.log") for name in files) == 1,
     "missing evidence stderr")
need(sum(name.startswith("run/.scoped-evidence-") and name.endswith("/manifest.txt") for name in files) == 1,
     "missing evidence manifest")
record = {"id": identity, "frames": len(frames), "files": files,
          "begin": begin, "end": end, "bytes": total,
          "serial_sha256": hashlib.sha256(raw).hexdigest(), "serial_bytes": len(raw)}
(root / "original-export-readback.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"frames": len(frames), "files": len(files), "bytes": total}))
