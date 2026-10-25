"""Decode the two saved native COM1 exports without contacting the VM."""
import base64
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


root = Path(sys.argv[1]).resolve()
raw = (root / "serial-all-original.bin").read_bytes()
reconstruction = json.loads((root / "serial-reconstruction.json").read_text())
require(hashlib.sha256(raw).hexdigest() == reconstruction["sha256"], "saved COM1 bytes changed")
require(len(raw) == reconstruction["bytes"], "saved COM1 length changed")

cases = (
    ("hardlink", "rhai-backend-evidence-0e6872acee8647af927c9023af25d331"),
    ("readonly", "rhai-backend-cleanup-60e5e70f35564d85bf8f08f18e911f5d"),
)
for tag, identity in cases:
    prefix = ("RHAI_BOOTSTRAP " + identity + " ").encode()
    frames = []
    for line in raw.splitlines():
        if not line.startswith(prefix):
            continue
        parts = line.split(b" ", 4)
        require(len(parts) == 5 and len(parts[4]) <= 3500, "malformed serial frame")
        try:
            payload = json.loads(base64.b64decode(parts[4], validate=True))
            frames.append((int(parts[2]), parts[3].decode("ascii"), payload))
        except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("invalid serial frame payload") from exc
    require(frames and [row[0] for row in frames] == list(range(len(frames))), "frame gap or duplicate")
    require(frames[0][1] == "BEGIN" and frames[-1][1] == "END", "missing BEGIN or END")
    begin, end = frames[0][2], frames[-1][2]
    require(begin["id"] == end["id"] == identity, "wrong control identity")
    require(begin["accepted"] is True and end["accepted"] is True, "control export was not accepted")
    require(begin["exit"] == end["exit"] == 2, "wrong negative Driver exit")
    output = root / (tag + "-export")
    require(not output.exists(), "export destination already exists")
    output.mkdir()
    files = {}
    current = None
    content = bytearray()
    total = 0
    for _, kind, item in frames[1:-1]:
        if kind == "FILE":
            name = item["path"]
            path = PurePosixPath(name)
            require(current is None and not path.is_absolute() and ".." not in path.parts
                    and "\\" not in name and ":" not in name and name not in files,
                    "unsafe or duplicate export path")
            require(0 <= item["length"] <= 4 * 1024 * 1024, "file exceeds export cap")
            current = item
            content = bytearray()
        elif kind == "CHUNK":
            require(current is not None and item["path"] == current["path"]
                    and item["offset"] == len(content), "out-of-order chunk")
            chunk = base64.b64decode(item["data"], validate=True)
            require(0 < len(chunk) <= 1024, "chunk exceeds export cap")
            content.extend(chunk)
            require(len(content) <= current["length"], "chunk exceeds declared length")
        elif kind == "FILE_END":
            require(current is not None and item == current and len(content) == item["length"],
                    "incomplete export file")
            require(hashlib.sha256(content).hexdigest() == item["sha256"], "export hash differs")
            destination = output / current["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            files[current["path"]] = current
            total += len(content)
            require(len(files) <= 64 and total <= 16 * 1024 * 1024, "export aggregate cap exceeded")
            current = None
        else:
            raise RuntimeError("unexpected serial frame kind: " + kind)
    require(current is None and len(files) == end["files"], "export inventory incomplete")
    record = {"id": identity, "frames": len(frames), "files": files,
              "begin": begin, "end": end, "bytes": total}
    (root / (tag + "-export-readback.json")).write_text(json.dumps(record, indent=2) + "\n")
    print(tag, "frames", len(frames), "files", len(files), "bytes", total)
