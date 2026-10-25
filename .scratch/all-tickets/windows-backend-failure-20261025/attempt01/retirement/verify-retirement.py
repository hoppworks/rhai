"""Verify the saved native cleanup receipt and its source-bound actor census."""
import base64
import hashlib
import json
import sys
from pathlib import Path


def check(value, message):
    if not value:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


root = Path(sys.argv[1]).resolve()
binding = json.loads((root / "binding.json").read_text())
manifest = json.loads((root / "cleanup-host-manifest.json").read_text())
medium = json.loads((root / "media-readback.json").read_text())
dispatch = json.loads((root / "dispatch.json").read_text())
mount = json.loads((root / "host-mount-readback.json").read_text())
check(digest(root / "cleanup.ps1") == binding["source_sha256"] == medium["files"]["cleanup.ps1"], "cleanup source pin")
check(digest(root / "cleanup-host-manifest.json") == binding["manifest_sha256"] == medium["files"]["cleanup-host-manifest.json"], "cleanup manifest pin")
check(len(medium["files"]) == 2 and manifest["accepted_for_cleanup"], "cleanup medium scope")
check(dispatch["enter_sent"] is True and dispatch["vm_uuid"] == mount["vm_uuid"] == binding["vm_uuid"], "VM dispatch")
check(dispatch["medium_sha256"] == mount["medium_sha256"] == medium["sha256"], "medium dispatch")
check(dispatch["source_sha256"] == binding["source_sha256"] and dispatch["manifest_sha256"] == binding["manifest_sha256"], "command dispatch")
check(manifest["host_readback_sha256"] == digest(root.parent / "host-accepted-readback.json"), "original host acceptance")
check(manifest["serial_original_sha256"] == digest(root.parent / "serial-all-original.bin"), "original native export")

raw = (root / "serial-original.bin").read_bytes()
collection = json.loads((root / "serial-collection.json").read_text())
check(len(raw) == collection["bytes"] and hashlib.sha256(raw).hexdigest() == collection["sha256"], "saved serial bytes")
actor_lines = [line.split(b" ", 1)[1] for line in raw.splitlines() if line.startswith(b"RHAI_BACKEND_ACTORS ")]
receipt_lines = [line.split(b" ", 1)[1] for line in raw.splitlines() if line.startswith(b"RHAI_BACKEND_CLEANUP ")]
check(len(actor_lines) == len(receipt_lines) == 1, "exact cleanup frame count")
actor_json = base64.b64decode(actor_lines[0], validate=True)
actors = json.loads(actor_json)
receipt = json.loads(base64.b64decode(receipt_lines[0], validate=True))
check(receipt["nonce"] == manifest["nonce"] == binding["nonce"], "cleanup identity")
check(receipt["manifest_sha256"] == binding["manifest_sha256"] and receipt["host_readback_sha256"] == manifest["host_readback_sha256"], "receipt provenance")
check(receipt["actor_count"] == len(actors) == 4 and receipt["actor_checks_sha256"] == hashlib.sha256(actor_json).hexdigest(), "actor census hash")
expected = {(pair["pid"], pair["creation"]) for scope in manifest["scopes"] for pair in scope["actors"]}
check(len(expected) == 4 and {(actor["pid"], actor["creation"]) for actor in actors} == expected, "actor generations")
for actor in actors:
    check(actor["original_alive"] is False and (actor["current_creation"] == 0 or abs(actor["current_creation"] - actor["creation"]) > 10_000_000), "original actor still present")
check(receipt["failure_sha256"] == "0" * 64 and receipt["all_scopes_absent"] is True and receipt["retained_builds_verified"] is True and receipt["foreign_resources_touched"] is False, "cleanup failed or touched foreign resources")
check(sorted(receipt["retired"]) == sorted(scope["scope"] for scope in manifest["scopes"]), "retired scope list")
check(sorted(manifest["preserved_build_scopes"]) == sorted(build["scope"].rsplit("\\", 1)[-1] for build in manifest["retained_builds"]), "retained build identity")
report = {"accepted": True, "removed_control_scopes": receipt["retired"], "stopped_actor_generations": len(actors), "retained_build_scopes": manifest["preserved_build_scopes"], "medium_sha256": medium["sha256"], "serial_sha256": collection["sha256"], "foreign_resources_touched": False}
(root / "host-cleanup-readback.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
