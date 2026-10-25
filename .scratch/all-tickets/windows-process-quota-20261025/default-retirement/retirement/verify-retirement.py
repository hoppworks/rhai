"""Verify saved default-build retirement serial frames offline."""
from pathlib import Path
import base64
import datetime
import hashlib
import json
import re

p = Path(__file__).resolve().parent
read = lambda file: json.loads((p / file).read_text())
sha = lambda file: hashlib.sha256((p / file).read_bytes()).hexdigest()
manifest = read("cleanup-host-manifest.json")
dispatch = read("dispatch.json")
export = read("../default-export-readback.json")
assert sha("cleanup-host-manifest.json") == dispatch["manifest_sha256"]
assert sha("cleanup.ps1") == dispatch["source_sha256"]
assert sha("retirement.iso") == dispatch["medium_sha256"]
assert manifest["accepted_for_cleanup"] and manifest["originals_exported"]
assert export["complete"] and len(export["files"]) == 53
assert manifest["host_receipt_sha256"] == sha("../default-export-readback.json")
assert len(manifest["scopes"]) == 1

actor_chunks, receipts = {}, []
for line in (p / "serial-original.bin").read_bytes().splitlines():
    if line.startswith(b"RHAI_DEFAULT_BUILD_ACTOR_CHECKS "):
        _, index, total, encoded = line.split(b" ", 3)
        index, total = int(index), int(total)
        assert 0 <= index < total <= 32 and len(encoded) <= 3000
        assert index not in actor_chunks
        actor_chunks[index] = (total, encoded)
    elif line.startswith(b"RHAI_DEFAULT_BUILD_CLEANUP "):
        receipts.append(line.split(b" ", 1)[1])
assert len(receipts) == 1 and len(actor_chunks) == 1
assert actor_chunks[0][0] == 1
actor_bytes = base64.b64decode(actor_chunks[0][1], validate=True)
actor = json.loads(actor_bytes)
if isinstance(actor, dict):
    actor = [actor]
receipt = json.loads(base64.b64decode(receipts[0], validate=True))
assert receipt["nonce"] == manifest["nonce"]
assert receipt["manifest_sha256"] == dispatch["manifest_sha256"]
assert receipt["host_receipt_sha256"] == manifest["host_receipt_sha256"]
assert receipt["actor_check_count"] == len(actor) == 1
assert receipt["actor_checks_sha256"] == hashlib.sha256(actor_bytes).hexdigest()
assert receipt["failure_sha256"] == "0" * 64
assert receipt["all_scopes_absent"] and receipt["original_build_retired"]
assert not receipt["foreign_resources_touched"]
assert receipt["retired"] == [manifest["scopes"][0]["scope"]]

observer = read("../default-export/build-observer.json")
match = re.fullmatch(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)\.(\d{7})Z", observer["process_start_utc"])
assert match
instant = datetime.datetime.fromisoformat(match[1]).replace(tzinfo=datetime.timezone.utc)
epoch = datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc)
delta = instant - epoch
creation = (delta.days * 86400 + delta.seconds) * 10_000_000 + int(match[2])
assert actor[0]["pid"] == observer["process_id"] and actor[0]["creation"] == creation
assert actor[0]["original_alive"] is False
assert actor[0]["source"] == "Win32_Process current census"
assert actor[0]["observed_creation"] == 0 or abs(actor[0]["observed_creation"] - creation) > 10_000_000

(p / "guest-cleanup-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
(p / "actor-checks-original.json").write_text(json.dumps(actor, indent=2) + "\n")
result = {"accepted": True, "single_own_scope_removed": receipt["retired"][0],
          "original_build_actor_absent": True, "serial_sha256": sha("serial-original.bin"),
          "manifest_sha256": dispatch["manifest_sha256"]}
(p / "host-cleanup-readback.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
