"""Independently check saved native Cargo project-command originals."""
import glob
import hashlib
import json
import ntpath
import sys
import zlib
from pathlib import Path


def need(ok, why):
    if not ok:
        raise RuntimeError(why)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


root = Path(sys.argv[1]).resolve()
saved = root / "original-export"
observer = json.loads((saved / "observer.json").read_text())
preflight = json.loads((saved / "preflight.json").read_text())
source = json.loads((saved / "source-manifest.json").read_text())
readback = json.loads((root / "original-export-readback.json").read_text())
nonce = "49243ecf52d64c609a876e3c52409500"
session = rf"C:\Users\RhaiTest\.local\share\agent-builds\rhai\project-control-{nonce}"
expected_runtime = ntpath.join(session, "run", "scoped-dd99b5329e6f42bca82b03f0c5a816e8")
need(observer["id"] == preflight["id"] == "rhai-project-command-" + nonce,
     "original run identity differs")
need(observer["accepted"] is True and observer["wrong_expectation_rejected"] is True
     and observer["product_test_run"] is False and observer["driver_exit"] == 0
     and observer["driver_exited"] is True and observer["pipes_drained"] is True
     and observer["process_disposed"] is True and observer["custody_pending"] is False
     and observer["observer_kill_used"] is False and observer["owned_executables_stopped"] is True
     and observer["failure"] == "", "native observer contract differs")
need(ntpath.normcase(observer["scope"]) == ntpath.normcase(session)
     and ntpath.normcase(observer["runtime"]) == ntpath.normcase(expected_runtime),
     "original scope/runtime differs")
need(preflight["source_commit"] == source["source_commit"]
     == "25e78217dc75f4ccda64a16710ac1f53bee521cb", "source commit differs")
need(preflight["source_files"] == source["file_count"] == 437, "source file count differs")
need(preflight["archive_sha256"] == source["archive_sha256"]
     == "422507c89fef8094387a82e6af18d80453af1c56579ee12a55b332aaff30be93",
     "source archive pin differs")
need(sha(saved / "source-manifest.json") == observer["source_manifest_sha256"]
     == preflight["source_manifest_sha256"]
     == "1ed2dc76e988d82654f588e2c9e7c32c8526f2d888c44fbbaee9b996f7c847a1",
     "original source manifest hash differs")
need(sha(saved / "build-manifest.txt") == observer["public_build_manifest_sha256"]
     == preflight["public_build_manifest_sha256"]
     == "613361eba54c1edfaa0da576ccece3a6cb0009cfc4e35af582d46f967e1a320a",
     "original public build hash differs")
need(preflight["cargo_version"] == "cargo 1.93.0 (083ac5135 2025-12-15)"
     and preflight["rustc_version"] == "rustc 1.93.0 (254b59607 2026-01-19)",
     "native toolchain differs")
need(preflight["cargo_sha256"] == observer["cargo_proxy_sha256"]
     == "6f4bef66261261fcb43131be8720bab817d403a09edec7455c371974b90bdb7e",
     "native Cargo proxy differs")
driver = (saved / "driver.stdout").read_text()
need((saved / "driver.stderr").read_bytes() == b"", "Driver stderr differs")
for line in ("CLIENT_EXIT=0x0000004E", "MODE=success;ACTION_CONFIRMED=True;",
             "PAYLOAD_EXIT=00000000", "SUPERVISION=PayloadExited",
             "CLEANUP_CONFIRMED=True", "RUNTIME_REMOVED=True", "HOST_EXPORTED=False"):
    need(line in driver, "Driver result missing: " + line)
need("RUNTIME=" + expected_runtime in driver, "Driver runtime differs")
journals = list((saved / "run").glob(".scoped-run-*.journal"))
need(len(journals) == 1, "original journal count differs")
rows = []
for line in journals[0].read_bytes().splitlines():
    length, checksum, body = line.split(b":", 2)
    need(int(length, 16) == len(body) and zlib.crc32(body) == int(checksum, 16),
         "native journal CRC differs")
    rows.append(body.decode().split("|"))
need([x[0] for x in rows] == ["INTENT", "IDENTITY", "STAGED", "LIFECYCLE",
                                "EVIDENCE", "OUTCOME", "REMOVE_INTENT", "REMOVED"],
     "native journal transition differs")
evidence = next((saved / "run").glob(".scoped-evidence-*"))
stdout = evidence / "stdout.log"
stderr = evidence / "stderr.log"
manifest = evidence / "manifest.txt"
evidence_row = "|".join(rows[4])
need(sha(stdout).upper() in evidence_row
     and sha(stderr).upper() in evidence_row
     and sha(manifest).upper() in evidence_row, "journal/evidence hash binding differs")
metadata = json.loads(stdout.read_text())
packages = [(x["name"], x["version"]) for x in metadata["packages"]]
need(packages == [("rhai", "1.26.1"), ("rhai_codegen", "3.2.0"),
                  ("custom_root", "0.1.0")], "actual native workspace packages differ")
need(len(metadata["workspace_members"]) == 3, "actual native workspace members differ")
rhai = next(x for x in metadata["packages"] if x["name"] == "rhai")
need(ntpath.normcase(rhai["manifest_path"]) == ntpath.normcase(ntpath.join(expected_runtime, "Cargo.toml")),
     "actual Cargo manifest escaped owned runtime")
need(ntpath.normcase(metadata["target_directory"]) == ntpath.normcase(ntpath.join(expected_runtime, "work", "target")),
     "actual Cargo target escaped owned runtime")
need(readback["end"]["runtime_absent"] is True
     and readback["end"]["guest_originals_retained"] is True,
     "fresh guest export closure differs")
result = {"accepted": True, "source_commit": preflight["source_commit"],
          "native_driver_exit": observer["driver_exit"],
          "driver_seconds": observer["driver_elapsed_seconds"],
          "wrong_expectation_rejected": observer["wrong_expectation_rejected"],
          "cargo_metadata_packages": packages, "journal_crc_records": len(rows),
          "export_files": len(readback["files"]), "export_bytes": readback["bytes"],
          "serial_sha256": readback["serial_sha256"],
          "scope_runtime_removed": readback["end"]["runtime_absent"],
          "product_test_run": observer["product_test_run"]}
(root / "independent-verification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
