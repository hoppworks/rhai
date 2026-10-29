"""Verify original native Windows Managed RED/GREEN and custody evidence."""

import hashlib
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parent
binding = json.loads((root / "binding.json").read_text())
preflight = json.loads((root / "host-dispatch-preflight-final.json").read_text())
capture = json.loads((root / "serial-capture-binding.json").read_text())
export = json.loads((root / "original-export-readback.json").read_text())
journal = json.loads((root / "journal-readback.json").read_text())
original = root / "original-export"
observer = json.loads((original / "observer.json").read_text())
guest = list((original / "run").glob(".scoped-evidence-*/runtime"))
assert len(guest) == 1
runtime = guest[0]
assert binding["integrated_head_at_prepare"] == "7dacf2ae09ef657cfbb53d3a0b35b9bb7dc2f4ac"
assert binding["source_tree_matches_integrated_head"] and not binding["source_mismatches"]
assert binding["planned_features"] == "testing-environ,sys,net"
assert binding["planned_targets"] == ["sys_process_windows"]
assert binding["lock_sha256"] == observer["lock_sha256"] == hashlib.sha256((root / "media-input/Cargo.lock").read_bytes()).hexdigest()
assert binding["source_manifest_sha256"] == observer["source_manifest_sha256"] == hashlib.sha256((root / "media-input/source-manifest.json").read_bytes()).hexdigest()
assert binding["archive_sha256"] == hashlib.sha256((root / "media-input/rhai-source.zip").read_bytes()).hexdigest()
assert binding["iso_sha256"] == preflight["medium_sha256"]
assert preflight["serial_inode"] == capture["inode"] and preflight["serial_offset"] == capture["offset_start"]
raw = (root / "serial-original.bin").read_bytes()
assert len(raw) == capture["bytes"] == capture["offset_end"] - capture["offset_start"]
assert hashlib.sha256(raw).hexdigest() == capture["sha256"] == export["serial_sha256"]
assert export["begin"]["accepted"] is True and export["end"]["accepted"] is True
assert export["begin"]["exit"] == export["end"]["exit"] == 0
assert len(export["files"]) == 19 and len(export["files"]) == export["end"]["files"]
for name, record in export["files"].items():
    path = original / name
    assert path.is_file() and path.stat().st_size == record["length"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
assert journal["records"] == 8 and journal["terminal_removed"] and journal["crc32_and_length_valid"]
assert journal["payload_exit"] == "00000000"
for key in ["driver_exited", "pipes_drained", "process_disposed", "owned_executables_stopped", "wrong_expectation_rejected", "target_suite_complete", "accepted", "product_test_run"]:
    assert observer[key] is True, key
for key in ["custody_pending", "observer_kill_used", "product_acceptance"]:
    assert observer[key] is False, key
assert observer["driver_exit"] == 0 and observer["failure"] == ""
assert observer["driver_elapsed_seconds"] < binding["observer_deadline_seconds"]
assert "cargo 1.77.2" in (runtime / "cargo-version.txt").read_text()
assert "rustc 1.77.2" in (runtime / "rustc-version.txt").read_text()

compile_log = (runtime / "compile.log").read_text()
match = re.search(r"Executable tests\\sys_process_windows\.rs \(([^)]+)\)", compile_log)
assert match
executable = match.group(1)
cases = {
    "managed-kill-wrong.log": ("windows_managed_spawn_kill_closes_descendant_and_preserves_sentinel", "windows_managed_kill_os_readback", "deliberately wrong managed kill closure expectation"),
    "managed-timeout-wrong.log": ("windows_managed_timeout_closes_descendant_and_preserves_sentinel", "windows_managed_timeout_os_readback", "deliberately wrong managed timeout closure expectation"),
    "managed-drop-kill-wrong.log": ("windows_managed_spawn_final_drop_follows_host_policy", "windows_managed_drop_os_readback mode=kill", "deliberately wrong managed kill drop termination expectation"),
    "managed-drop-retain-wrong.log": ("windows_managed_spawn_final_drop_follows_host_policy", "windows_managed_drop_os_readback mode=retain", "deliberately wrong managed retain drop survival expectation"),
}
for name, tokens in cases.items():
    log = (runtime / name).read_text()
    assert all(token in log for token in tokens), name
    assert "test result: FAILED. 0 passed; 1 failed;" in log, name
    match = re.search(r"Running tests\\sys_process_windows\.rs \(([^)]+)\)", log)
    assert match and match.group(1) == executable, name
suite = (runtime / "suite.log").read_text()
match = re.search(r"Running tests\\sys_process_windows\.rs \(([^)]+)\)", suite)
assert match and match.group(1) == executable
assert "test result: ok. 32 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;" in suite
for name in ["windows_managed_spawn_kill_closes_descendant_and_preserves_sentinel", "windows_managed_timeout_closes_descendant_and_preserves_sentinel", "windows_managed_spawn_final_drop_follows_host_policy"]:
    assert "test " + name + " ... " in suite
for observation in ["windows_managed_kill_os_readback", "windows_managed_timeout_os_readback", "windows_managed_drop_os_readback mode=kill", "windows_managed_drop_os_readback mode=retain"]:
    assert observation in suite and "sentinel_alive=true" in suite
stdout = (original / "run" / guest[0].parent.name / "stdout.log").read_text()
for marker in ["RHAI_MANAGED_COMPILE_EXIT=0", "RHAI_MANAGED_KILL_WRONG_EXIT=101", "RHAI_MANAGED_TIMEOUT_WRONG_EXIT=101", "RHAI_MANAGED_DROP_KILL_WRONG_EXIT=101", "RHAI_MANAGED_DROP_RETAIN_WRONG_EXIT=101", "RHAI_MANAGED_SUITE_EXIT=0", "RHAI_MANAGED_CONTROLS_PASS", "RHAI_CARGO_CLEAN_EXIT=0"]:
    assert marker in stdout, marker
result = {
    "accepted_original_native_slice": True,
    "source_head": binding["integrated_head_at_prepare"],
    "features": binding["planned_features"],
    "target": "sys_process_windows",
    "compile_exit": 0,
    "four_wrong_exits": [101] * 4,
    "green_exit": 0,
    "green_passed": 32,
    "same_compiled_executable": executable,
    "driver_exit": 0,
    "driver_elapsed_seconds": observer["driver_elapsed_seconds"],
    "original_frame_count": export["frames"],
    "original_file_count": len(export["files"]),
    "journal_records": journal["records"],
    "inner_runtime_removed": True,
    "guest_outer_scope_retired": False,
    "host_iso_stage_retired": False,
}
(root / "readback.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
