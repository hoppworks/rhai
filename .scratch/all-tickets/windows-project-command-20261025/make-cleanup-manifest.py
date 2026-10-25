"""Bind exact owned guest cleanup to exported originals and frozen sources."""
import hashlib
import json
import sys
from pathlib import Path


root = Path(sys.argv[1]).resolve()
export = json.loads((root / "original-export-readback.json").read_text())
verification_path = root / "independent-verification.json"
readback_path = root / "original-export-readback.json"
verification = json.loads(verification_path.read_text())
source = json.loads((root / "original-export/source-manifest.json").read_text())
observer = json.loads((root / "original-export/observer.json").read_text())
preflight = json.loads((root / "original-export/preflight.json").read_text())
assert observer["accepted"] is True and observer["driver_exit"] == 0
assert export["end"]["runtime_absent"] is True
assert len(source["files"]) == 437 and len(export["files"]) == 10
assert verification["accepted"] is True
assert verification["source_commit"] == preflight["source_commit"] == source["source_commit"]
assert verification["serial_sha256"] == export["serial_sha256"]
assert verification["native_driver_exit"] == 0
assert verification["wrong_expectation_rejected"] is True
assert verification["journal_crc_records"] == 8
assert verification["export_files"] == 10 and verification["export_bytes"] == export["bytes"] == 201438
assert verification["scope_runtime_removed"] is True and verification["product_test_run"] is False
assert verification["cargo_metadata_packages"] == [["rhai", "1.26.1"], ["rhai_codegen", "3.2.0"], ["custom_root", "0.1.0"]]
assert preflight["source_manifest_sha256"] == observer["source_manifest_sha256"] == hashlib.sha256((root / "original-export/source-manifest.json").read_bytes()).hexdigest()
assert preflight["public_build_manifest_sha256"] == observer["public_build_manifest_sha256"] == hashlib.sha256((root / "original-export/build-manifest.txt").read_bytes()).hexdigest()
assert preflight["cargo_sha256"] == observer["cargo_proxy_sha256"]
assert preflight["cargo_version"] == "cargo 1.93.0 (083ac5135 2025-12-15)"
assert preflight["rustc_version"] == "rustc 1.93.0 (254b59607 2026-01-19)"
files = {"source/" + name: value["sha256"] for name, value in source["files"].items()}
files["source/cargo.exe"] = preflight["cargo_sha256"]
files["bin/ScopedRunner.exe"] = observer["public_binary_pins"]["ScopedRunner.exe"]
files["bin/MonitorAcceptanceDriver.exe"] = observer["public_binary_pins"]["MonitorAcceptanceDriver.exe"]
files.update({name: value["sha256"] for name, value in export["files"].items()})
assert len(files) == 450
evidence_manifests = [name for name in export["files"] if name.startswith("run/.scoped-evidence-") and name.endswith("/manifest.txt")]
assert len(evidence_manifests) == 1
evidence_manifest_name = evidence_manifests[0]
evidence_root = evidence_manifest_name.removesuffix("/manifest.txt")
evidence_manifest = root / "original-export" / evidence_manifest_name
assert hashlib.sha256(evidence_manifest.read_bytes()).hexdigest() == export["files"][evidence_manifest_name]["sha256"]
entries = evidence_manifest.read_text().splitlines()
assert len(entries) == 482
snapshot_files = 0
snapshot_bytes = 0
for line in entries:
    row = line.split("|")
    assert len(row) == 7 and row[1] in ("D", "F")
    if row[1] == "D":
        continue
    relative = row[0].replace("\\", "/")
    assert relative and not relative.startswith("/") and ":" not in relative and ".." not in relative.split("/")
    assert len(row[6]) == 64 and all(ch in "0123456789ABCDEF" for ch in row[6])
    name = evidence_root + "/runtime/" + relative
    assert name not in files
    files[name] = row[6].lower()
    snapshot_files += 1
    snapshot_bytes += int(row[3])
assert snapshot_files == 438 and snapshot_bytes == 17810498
assert len(files) == 888
derived_directories = {"/".join(name.split("/")[:index])
                       for name in files for index in range(1, len(name.split("/")))}
assert len(derived_directories) == 91
manifest = {
    "id": observer["id"], "nonce": "49243ecf52d64c609a876e3c52409500",
    "scope": observer["scope"], "runtime": observer["runtime"],
    "driver_pid": observer["driver_pid"], "driver_creation": observer["driver_creation"],
    "observer_sha256": hashlib.sha256((root / "original-export/observer.json").read_bytes()).hexdigest(),
    "source_manifest_sha256": observer["source_manifest_sha256"],
    "serial_sha256": export["serial_sha256"], "accepted_for_cleanup": True,
    "independent_verification_sha256": hashlib.sha256(verification_path.read_bytes()).hexdigest(),
    "export_readback_sha256": hashlib.sha256(readback_path.read_bytes()).hexdigest(),
    "evidence_manifest_sha256": hashlib.sha256(evidence_manifest.read_bytes()).hexdigest(),
    "evidence_snapshot_files": snapshot_files,
    "max_files": 888, "max_entries": 1100, "max_bytes": 67108864,
    "files": dict(sorted(files.items())),
}
out = root / "cleanup-host-manifest.json"
assert not out.exists()
out.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
print(json.dumps({"manifest_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
                  "files": len(files), "bytes": out.stat().st_size}))
