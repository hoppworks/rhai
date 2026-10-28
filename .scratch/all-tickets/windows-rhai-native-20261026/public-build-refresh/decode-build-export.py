"""Verify and reconstruct the one native public BuildOnly COM1 export."""
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath

root = Path(__file__).resolve().parent
identity = "rhai-public-refresh-47066f0d4e2a4f8bb45f1e62e8f7e5ad"
raw = (root / "serial-original.bin").read_bytes()
prefix = ("RHAI_BOOTSTRAP " + identity + " ").encode()
frames = []
for line in raw.splitlines():
    if line.startswith(prefix):
        fields = line.split(b" ", 4)
        assert len(fields) == 5 and len(fields[4]) <= 3500
        frames.append((int(fields[2]), fields[3].decode("ascii"), json.loads(base64.b64decode(fields[4], validate=True))))
assert frames and [item[0] for item in frames] == list(range(len(frames)))
assert frames[0][1] == "BEGIN" and frames[-1][1] == "END"
begin, end = frames[0][2], frames[-1][2]
assert begin["id"] == end["id"] == identity
assert begin["accepted"] is end["accepted"] is True
assert begin["exit"] == end["exit"] == 0
assert end["guest_evidence_retained"] is True and end["files"] == 6
output = root / "original-export"
output.mkdir(exist_ok=True)
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
        destination = output / current["path"]
        digest = hashlib.sha256(content).hexdigest()
        assert digest == item["sha256"]
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
assert current is None and len(files) == 6
assert set(files) == {"build-observer.json", "project-readback.json", "bootstrap.stdout", "bootstrap.stderr", "run/monitor-source-47066f0d4e2a4f8bb45f1e62e8f7e5ad/run-result.txt", "run/monitor-source-47066f0d4e2a4f8bb45f1e62e8f7e5ad/build-manifest.txt"}
receipt = json.loads((output / "project-readback.json").read_text())
observer = json.loads((output / "build-observer.json").read_text())
manifest = output / "run/monitor-source-47066f0d4e2a4f8bb45f1e62e8f7e5ad/build-manifest.txt"
assert receipt["id"] == identity and receipt["build_only_pass"] is True
assert receipt["build_manifest_sha256"] == hashlib.sha256(manifest.read_bytes()).hexdigest()
assert receipt["source_manifest_sha256"] == observer["input_manifest_sha256"] == "175fee88ce1625dcd9efca0fb904d5c7cfeb7b96a9a80e25bc90187099a8a276"
assert receipt["compiler_sha256"] == observer["compiler_sha256"] == "cf32cb7e8e5691b962e1b6f92b03d87409dd9e7afbed71c5bf77b8203cc56ee1"
assert observer["accepted"] is True and observer["exit"] == 0 and observer["selection"] == "-PublicToolsOnly"
assert set(receipt["binary_sha256"]) == {"ScopedRunner.exe", "MonitorAcceptanceDriver.exe"}
for name, digest in receipt["binary_sha256"].items():
    assert f"{digest}  build/{name}" in manifest.read_text().splitlines()
assert (output / "run/monitor-source-47066f0d4e2a4f8bb45f1e62e8f7e5ad/run-result.txt").read_text().startswith("BUILD_ONLY_PASS:")
record = {"id": identity, "frames": len(frames), "files": files, "bytes": total, "serial_sha256": hashlib.sha256(raw).hexdigest(), "serial_bytes": len(raw), "manifest_sha256": receipt["build_manifest_sha256"], "binary_sha256": receipt["binary_sha256"]}
(root / "original-export-readback.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"frames": len(frames), "files": len(files), "bytes": total, "manifest": receipt["build_manifest_sha256"]}))
