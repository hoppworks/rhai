"""Independently verify the exported original Linux Sys run."""

import hashlib
import json
from pathlib import Path
import re

out = Path(__file__).resolve().parent
preflight = json.loads((out / "preflight.json").read_text())
result = json.loads((out / "result.json").read_text())
commands = json.loads((out / "commands.json").read_text())
targets = ["sys_policy", "sys_env", "sys_fs", "sys_process", "sys_process_report"]
assert preflight["source_files"] == 448 and not preflight["mismatches"]
assert result["accepted"] is True and result["features"] == "testing-environ,sys"
assert result["targets"] == targets and result["total_passed"] == 134
assert result["lock_sha256"] == preflight["lock_sha256"]
assert result["source_manifest_sha256"] == preflight["manifest_sha256"]
assert [item["label"] for item in commands] == [
    "cargo-version", "rustc-version", "compile", "wrong-host-readback",
    *["green-" + target for target in targets],
]
assert [item["exit"] for item in commands] == [0, 0, 0, 101, 0, 0, 0, 0, 0]
assert (out / "outer.status").read_text().strip() == "0"
assert (out / "cleanup-readback.txt").read_text().strip() == "exact-stage-and-scope-absent"

hashes = {}
for line in (out / "remote-export.sha256").read_text().splitlines():
    expected_hash, name = line.split("  ", 1)
    assert name not in hashes and "/" not in name and "\\" not in name
    assert hashlib.sha256((out / name).read_bytes()).hexdigest() == expected_hash
    hashes[name] = expected_hash
assert len(hashes) == 19

compile_log = (out / "compile.log").read_text()
compiled = {}
passed = {}
for target in targets:
    match = re.search(r"(?m)^\s*Executable tests/" + re.escape(target) + r"\.rs \(([^)]+)\)", compile_log)
    assert match, target
    compiled[target] = match.group(1)
    green = (out / ("green-" + target + ".log")).read_text()
    match = re.search(r"(?m)^\s*Running tests/" + re.escape(target) + r"\.rs \(([^)]+)\)", green)
    assert match and match.group(1) == compiled[target], target
    summaries = re.findall(r"(?m)^test result: ok\. (\d+) passed; 0 failed; (\d+) ignored; 0 measured; 0 filtered out;", green)
    assert len(summaries) == 1, target
    passed[target] = {"passed": int(summaries[0][0]), "ignored": int(summaries[0][1])}
    assert passed[target] == {key: result["passed"][target][key] for key in ("passed", "ignored")}

wrong = (out / "wrong-host-readback.log").read_text()
assert 'independent host readback: "original XYyload"' in wrong
assert "left: [111, 114, 105, 103, 105, 110, 97, 108, 32, 88, 89, 121, 108, 111, 97, 100]" in wrong
assert "right: [119, 114, 111, 110, 103, 32, 101, 120, 112, 101, 99, 116, 97, 116, 105, 111, 110]" in wrong
assert "test test_open_file_default_preserves_contents_and_shares_cursor ... FAILED" in wrong
assert "test result: FAILED. 0 passed; 1 failed;" in wrong
match = re.search(r"(?m)^\s*Running tests/sys_fs\.rs \(([^)]+)\)", wrong)
assert match and match.group(1) == compiled["sys_fs"]
green_fs = (out / "green-sys_fs.log").read_text()
assert re.search(
    r'test test_open_file_default_preserves_contents_and_shares_cursor \.\.\. independent host readback: "original XYyload"\s+ok',
    green_fs,
)
summary = {
    "accepted_original_results": True,
    "head": preflight["head"],
    "features": result["features"],
    "targets": targets,
    "wrong_exit": 101,
    "green_exits": [0] * len(targets),
    "passed": passed,
    "total_passed": sum(item["passed"] for item in passed.values()),
    "same_sys_fs_executable": compiled["sys_fs"],
    "export_file_count": len(hashes),
    "export_hashes_valid": True,
    "owned_stage_and_scope_absent": True,
}
(out / "readback.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
