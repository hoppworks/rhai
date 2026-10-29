"""Reclassify preserved original Cargo results after a parser-only failure."""

import hashlib
import json
from pathlib import Path
import re

out = Path(__file__).resolve().parent
preflight = json.loads((out / "preflight.json").read_text())
commands = json.loads((out / "commands.json").read_text())
targets = ["sys_policy", "sys_env", "sys_fs", "sys_process", "sys_process_report"]
assert preflight["source_files"] == 448 and not preflight["mismatches"]
assert (out / "outer.status").read_text().strip() == "1"
assert "AssertionError" in (out / "outer.log").read_text()
assert "green-sys_fs.log" in (out / "outer.log").read_text()
assert [item["label"] for item in commands] == [
    "cargo-version", "rustc-version", "compile", "wrong-host-readback",
    *["green-" + target for target in targets],
]
assert [item["exit"] for item in commands] == [0, 0, 0, 101, 0, 0, 0, 0, 0]
compile_log = (out / "compile.log").read_text()
compiled = {}
for target in targets:
    match = re.search(r"(?m)^\s*Executable tests/" + re.escape(target) + r"\.rs \(([^)]+)\)", compile_log)
    assert match, target
    compiled[target] = match.group(1)

wrong = (out / "wrong-host-readback.log").read_text()
assert 'independent host readback: "original XYyload"' in wrong
assert "left: [111, 114, 105, 103, 105, 110, 97, 108, 32, 88, 89, 121, 108, 111, 97, 100]" in wrong
assert "right: [119, 114, 111, 110, 103, 32, 101, 120, 112, 101, 99, 116, 97, 116, 105, 111, 110]" in wrong
assert "test test_open_file_default_preserves_contents_and_shares_cursor ... FAILED" in wrong
assert "test result: FAILED. 0 passed; 1 failed;" in wrong
match = re.search(r"(?m)^\s*Running tests/sys_fs\.rs \(([^)]+)\)", wrong)
assert match and match.group(1) == compiled["sys_fs"]

passed = {}
hashes = {}
for target in targets:
    path = out / ("green-" + target + ".log")
    log = path.read_text()
    match = re.search(r"(?m)^\s*Running tests/" + re.escape(target) + r"\.rs \(([^)]+)\)", log)
    assert match and match.group(1) == compiled[target], target
    summaries = re.findall(r"(?m)^test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;", log)
    assert len(summaries) == 1 and int(summaries[0][0]) > 0, target
    passed[target] = {"passed": int(summaries[0][0]), "ignored": int(summaries[0][1])}
    hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
green_fs = (out / "green-sys_fs.log").read_text()
assert re.search(
    r'test test_open_file_default_preserves_contents_and_shares_cursor \.\.\. independent host readback: "original XYyload"\s+ok',
    green_fs,
)
assert not Path("/Users/hoppworks/.local/share/agent-builds/rhai/macos-sys-alone-20261029-c9f8ab62").exists()
for name in ["compile.log", "wrong-host-readback.log", "commands.json", "outer.log", "outer.status"]:
    path = out / name
    hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
result = {
    "accepted_original_cargo_results": True,
    "outer_status": 1,
    "outer_failure": "parser required the green test name and ok on one line despite --nocapture readback",
    "preflight": preflight,
    "features": "testing-environ,sys",
    "targets": targets,
    "wrong_exit": 101,
    "green_exits": [0] * len(targets),
    "passed": passed,
    "total_passed": sum(item["passed"] for item in passed.values()),
    "source_manifest_sha256": preflight["manifest_sha256"],
    "lock_sha256": preflight["lock_sha256"],
    "same_sys_fs_executable": compiled["sys_fs"],
    "owned_scope_absent": True,
    "original_hashes": hashes,
}
(out / "readback.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
