"""Bind the two completed memory-denial scopes to saved original exports."""
from pathlib import Path, PureWindowsPath
import hashlib
import json
import re
import zlib

packet = Path(__file__).resolve().parent.parent
out_dir = packet / "retirement"
read = lambda path: json.loads(path.read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

accepted = read(packet / "attempt03/host-accepted-readback.json")
assert accepted["accepted"] and accepted["fresh_census_at_cleanup"] == "pending"
control_root = packet / "attempt03/memory01-export"
control_readback = read(packet / "attempt03/memory01-export-readback.json")
control = read(control_root / "observer.json")
assert control_readback["complete"] and control_readback["end"]["accepted"]
assert control["accepted"] and control["contract"] == "job-memory"
assert control["exact_driver_exited"] and control["pipes_drained"]
assert control["process_disposed"] and control["owned_executables_stopped"]
assert control["memory_actors_stopped"] and not control["custody_pending"]
assert not control["retained_driver_handles"] and not control["parent_environment_changed"]
for name, entry in control_readback["files"].items():
    assert sha(control_root / name) == entry["sha256"]

journals = list((control_root / "run").glob(".scoped-run-*.journal"))
assert len(journals) == 1
rows = []
for line in journals[0].read_bytes().splitlines():
    length, crc, body = line.split(b":", 2)
    assert int(length, 16) == len(body) and zlib.crc32(body) == int(crc, 16)
    rows.append(body.decode().split("|"))
assert [row[0] for row in rows] == [
    "INTENT", "IDENTITY", "STAGED", "LIFECYCLE", "EVIDENCE", "OUTCOME",
    "REMOVE_INTENT", "REMOVED",
]
fields = lambda row: dict(item.split("=", 1) for item in row if "=" in item)
assert fields(rows[4])["proof"] == "EXACT"
assert fields(rows[5])["cleanup"] == "CONFIRMED"
runtime = rows[0][2]
assert PureWindowsPath(runtime).parent == PureWindowsPath(control["run"])
assert re.fullmatch(r"scoped-[0-9a-f]{32}", PureWindowsPath(runtime).name)
actors = {(control["driver_pid"], control["driver_creation"])}
for actor in control["job_memory_observed"].values():
    if isinstance(actor, dict) and "pid" in actor and "creation" in actor:
        actors.add((int(actor["pid"]), int(actor["creation"])))
assert len(actors) == 4
empty = []
for snapshot in (control_root / "run").glob(".scoped-evidence-*"):
    for line in (snapshot / "manifest.txt").read_text().splitlines():
        values = line.split("|")
        if values[1] == "D":
            empty.append(
                snapshot.relative_to(control_root).as_posix()
                + "/runtime"
                + ("/" + values[0].replace("\\", "/") if values[0] else "")
            )
control_scope = {
    "scope": control["scope"], "kind": "completed-control", "id": control["id"],
    "contract": control["contract"], "expected_accepted": True, "runtime": runtime,
    "actors": [{"pid": pid, "creation": creation} for pid, creation in sorted(actors)],
    "files": {name: entry["sha256"] for name, entry in control_readback["files"].items()},
    "empty_dirs": empty,
}

build_root = packet / "build-readback/build-export"
build_readback = read(packet / "build-readback/build-export-readback.json")
build = read(build_root / "build-observer.json")
begin = build_readback["begin"]
assert build_readback["complete"] and begin["readback_only"]
assert begin["build_accepted"] and not begin["native_reexecution"]
assert build["accepted"] and build["native_started"] and build["exit"] == 0
assert not build["custody_indeterminate"] and not build["driver_launched"]
assert begin["scope"] == build["session"]
for name, entry in build_readback["files"].items():
    assert sha(build_root / name) == entry["sha256"]
build_scope = {
    "scope": build["session"], "kind": "completed-build", "id": build["id"],
    "files": {name: entry["sha256"] for name, entry in build_readback["files"].items()},
    "empty_dirs": begin["directories"],
}

retained = read(packet.parent / "windows-process-quota-20261025/retained-default-build.json")
assert retained["scope"] not in (control_scope["scope"], build_scope["scope"])
retained_manifest = packet.parent / "windows-process-quota-20261025/quota01-export/build-readback/build-manifest.txt"
manifest = {
    "nonce": "197434e7a73dd8d7f20fd2f296895dce",
    "accepted_for_cleanup": True,
    "host_receipt_sha256": sha(packet / "attempt03/host-accepted-readback.json"),
    "build_readback_sha256": sha(packet / "build-readback/build-export-readback.json"),
    "scopes": [control_scope, build_scope],
    "retained": retained,
    "retained_manifest_sha256": sha(retained_manifest),
    "keep_other_resources": True,
}
(out_dir / "cleanup-host-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("Exact owned scope file counts", [len(scope["files"]) for scope in manifest["scopes"]])
