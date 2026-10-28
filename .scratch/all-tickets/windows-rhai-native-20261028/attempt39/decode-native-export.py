"""Reconstruct hash-bound original files from one bounded native COM1 export."""
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

root = Path(sys.argv[1]).resolve()
raw = (root / "serial-original.bin").read_bytes()
identity = "rhai-native-" + {"attempt01": "3e02fab1e0f047538d581fa4c9a52c85", "attempt02": "97a0dde027334ae09b0603240dc1bbda", "attempt03": "88b0797744d34d97861d1b3e681069fb", "attempt04": "d4ece7b0690446ddb5853c2b8592e872", "attempt05": "cdfb68cc215f49ef80b96585aca5aae9", "attempt06": "5b0ec646505e4e9bac799a1810bfad94", "attempt07": "f0574ef3db2445e1826ac702a85126eb", "attempt08": "e1644d91699d48e39fc2d5a2cbe90371", "attempt09": "9655c547808242c482b9212e0d5451e3", "attempt10": "9f3636e89a7447e49cdce5e81ad00f2c", "attempt11": "3af4a0ad2db94f06a1ed15f30f07cd7d", "attempt12": "ee369f78f6c44ca8a5a7c9abe3a9ba99", "attempt13": "f3ffd1ef5775e316afec9c05663523b0", "attempt14": "125661064694d9b32879b4e665dff275", "attempt15": "4a12b19a06a82e0422fd70c986713da7", "attempt16": "414156c57f5bd17a93bb70c05c54d5c1", "attempt17": "938153339eb2af49cb69654e866305e8", "attempt18": "ef1eb288ec8fa709a119b125a488b67d", "attempt19": "5cac6ebc2209265ceb215920655aaf60", "attempt20": "e0c7562105baad184aa60a7229106e95", "attempt21": "11793de1ce8b3f39329a8068dacec880", "attempt22": "30f674c8f631d898ed0b3711b70bf30b", "attempt23": "baccbb8a78b49adab4017d4c3a37103a", "attempt24": "57dff682c59e6cf0526f7640f64aa14c", "attempt25": "9415bf24d8e92c551480f13b2ed45742", "attempt26": "60b79304df6f44f52cdd8c42dd536d29", "attempt27": "cd94dc0b4a06cc6be7163edfc3c1bdee", "attempt28": "4a7fd1930ec5db86067fdd3ed06fa69f", "attempt29": "c1edb3295b7adca388523d436a6d2443", "attempt30": "df708abd30fc2cc198ff04fe0bfddb8f", "attempt31": "37a7f14ee6a6d923591f92d5b67923d4", "attempt33": "72a37db2a6d396199fc3f972181d8197", "attempt34": "18ebda9895886380691b77e134a6d309", "attempt35": "c645f6f1bb21397c5d5d87d618b7c955", "attempt36": "2d1976a3c2af801780941d3085b6db40", "attempt37": "f604ca66e3b2866b43d6691edc0c731d", "attempt38": "3c96a0b66285128f0ceef7306660cd8c", "attempt39": "2cb45485c2606bf8824397e2a2aed6a4"}[root.name]
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
