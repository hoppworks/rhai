"""Verify saved, bounded guest retirement frames without running the guest."""
from pathlib import Path
import base64
import datetime
import hashlib
import json
import re

p = Path(__file__).resolve().parent
read = lambda name: json.loads((p / name).read_text())
sha = lambda name: hashlib.sha256((p / name).read_bytes()).hexdigest()
binding, manifest = read("binding.json"), read("cleanup-host-manifest.json")
assert sha("cleanup.ps1") == binding["source_sha256"]
assert sha("cleanup-host-manifest.json") == binding["manifest_sha256"]
assert sha("../media/retirement.iso") == binding["media_sha256"]
assert manifest["accepted_for_cleanup"] and len(manifest["scopes"]) == 2

lines = (p / "serial-original.bin").read_bytes().splitlines()
actor_parts, receipt_lines = {}, []
for line in lines:
    if line.startswith(b"RHAI_MEMORY_ACTOR_CHECKS "):
        _, index, total, encoded = line.split(b" ", 3)
        index, total = int(index), int(total)
        assert 0 <= index < total <= 32 and len(encoded) <= 3000
        assert index not in actor_parts
        actor_parts[index] = (total, encoded)
    elif line.startswith(b"RHAI_MEMORY_CLEANUP "):
        receipt_lines.append(line.split(b" ", 1)[1])
assert len(receipt_lines) == 1 and actor_parts
totals = {item[0] for item in actor_parts.values()}
assert len(totals) == 1
total = totals.pop()
assert list(sorted(actor_parts)) == list(range(total))
actor_json = base64.b64decode(b"".join(actor_parts[i][1] for i in range(total)), validate=True)
actors = json.loads(actor_json)
receipt = json.loads(base64.b64decode(receipt_lines[0], validate=True))
assert receipt["nonce"] == binding["nonce"] == manifest["nonce"]
assert receipt["manifest_sha256"] == binding["manifest_sha256"]
assert receipt["host_receipt_sha256"] == manifest["host_receipt_sha256"]
assert receipt["actor_check_count"] == len(actors) == 5
assert receipt["actor_checks_sha256"] == hashlib.sha256(actor_json).hexdigest()
assert receipt["failure_sha256"] == "0" * 64
assert receipt["all_scopes_absent"] and receipt["retained_verified"]
assert not receipt["foreign_resources_touched"]
assert sorted(receipt["retired"]) == sorted(scope["scope"] for scope in manifest["scopes"])
assert receipt["retained_scope_leaf"] == manifest["retained"]["scope"].rsplit("\\", 1)[-1]
assert receipt["retained_manifest_sha256"] == manifest["retained_manifest_sha256"]

expected = {(item["pid"], item["creation"]) for item in manifest["scopes"][0]["actors"]}
build = read("../build-readback/build-export/build-observer.json")
timestamp = build["process_start_utc"]
match = re.fullmatch(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)\.(\d{7})Z", timestamp)
assert match
instant = datetime.datetime.fromisoformat(match[1]).replace(tzinfo=datetime.timezone.utc)
epoch = datetime.datetime(1601, 1, 1, tzinfo=datetime.timezone.utc)
filetime = int((instant - epoch).total_seconds()) * 10_000_000 + int(match[2])
expected.add((build["process_id"], filetime))
assert {(item["pid"], item["creation"]) for item in actors} == expected
for actor in actors:
    assert actor["source"] == "Win32_Process current census"
    assert actor["original_alive"] is False
    assert actor["observed_creation"] == 0 or abs(actor["observed_creation"] - actor["creation"]) > 10_000_000

result = {
    "accepted": True,
    "own_scopes_removed": sorted(receipt["retired"]),
    "actor_count": len(actors),
    "retained_default_verified": True,
    "foreign_resources_touched": False,
    "serial_sha256": sha("serial-original.bin"),
    "manifest_sha256": binding["manifest_sha256"],
    "media_sha256": binding["media_sha256"],
}
(p / "guest-cleanup-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
(p / "actor-checks-original.json").write_text(json.dumps(actors, indent=2) + "\n")
(p / "host-cleanup-readback.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
