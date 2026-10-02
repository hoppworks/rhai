#!/usr/bin/env python3
"""Exercise the exact runner-ledger predicate embedded in the launcher."""

import ast
import contextlib
import io
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
LAUNCHER = ROOT / "remote-overhead-launch.sh"

source = LAUNCHER.read_text(encoding="utf-8")
marker = 'python3 - "$evidence" <<\'PY\'\n'
block = source.split(marker, 1)[1].split("\nPY\n", 1)[0]
module = ast.parse(block)
function = next(node for node in module.body
                if isinstance(node, ast.FunctionDef)
                and node.name == "valid_runner_identity_row")
namespace = {}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(LAUNCHER), "exec"), namespace)
valid = namespace["valid_runner_identity_row"]

assert valid("1790919308.077\t3601690\t5590782\t3600516\t3600464\tpython3 short-lived")
assert valid("1790919308.077\t3601690\t5590782\t3600516\t3600464\t")
assert not valid("1790919308.077\t3601690\t\t3600516\t3600464\t")
assert not valid("not-time\t3601690\t5590782\t3600516\t3600464\t")
assert not valid("1790919308.077\t3601690\t5590782\t3600516\t\t")
assert not valid("1790919308.077\t3601690\t5590782\t3600516\t3600464")

ledger = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
if ledger is not None:
    rows = ledger.read_text(encoding="utf-8").splitlines()
    assert rows[0] == "utc_epoch\tpid\tstart_ticks\tppid\tpgid\tcmdline"
    invalid = [number for number, row in enumerate(rows[1:], 2) if not valid(row)]
    assert not invalid, f"exact launch-83 ledger rows rejected: {invalid}"
    print(f"launch83_identity_rows_valid={len(rows) - 1}")
print("identity row controls: empty descriptive cmdline accepted; missing/non-numeric identity fields rejected")

proof_source = (ROOT / "process-overhead-proof.py").read_text(encoding="utf-8")
proof_tree = ast.parse(proof_source)
main_guard = next(
    node for node in proof_tree.body
    if isinstance(node, ast.If)
    and isinstance(node.test, ast.Compare)
    and isinstance(node.test.left, ast.Name)
    and node.test.left.id == "__name__"
)
namespace = {"sys": sys, "main": lambda: 0}
stderr = io.StringIO()
try:
    with contextlib.redirect_stderr(stderr):
        exec(compile(ast.Module(body=main_guard.body, type_ignores=[]),
                     "process-overhead-proof.py", "exec"), namespace)
except SystemExit as exit_error:
    assert exit_error.code == 0
else:
    raise AssertionError("successful driver result must exit with status zero")
assert "MEASUREMENT_PACKAGE_FAILURE" not in stderr.getvalue()

def failing_main():
    raise RuntimeError("synthetic driver failure")

namespace = {"sys": sys, "main": failing_main}
stderr = io.StringIO()
try:
    with contextlib.redirect_stderr(stderr):
        exec(compile(ast.Module(body=main_guard.body, type_ignores=[]),
                     "process-overhead-proof.py", "exec"), namespace)
except RuntimeError as error:
    assert str(error) == "synthetic driver failure"
else:
    raise AssertionError("driver error must propagate")
assert "MEASUREMENT_PACKAGE_FAILURE RuntimeError: synthetic driver failure" in stderr.getvalue()
print("driver exit controls: success is quiet; real exception remains diagnosed")
