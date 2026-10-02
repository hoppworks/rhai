import ast
import importlib.util
import subprocess
import unittest
from pathlib import Path
p = Path(__file__).with_name("test-macos-process-overhead-source.py")
spec = importlib.util.spec_from_file_location("source_boundary_tests", p)
tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tests)
baseline = subprocess.check_output(["git", "show", "c3ac25738b76d304dc8c60c661a9a36a73704fa8:.scratch/all-tickets/macos-process-overhead.py"], text=True)
function = next(node for node in ast.parse(baseline).body if isinstance(node, ast.FunctionDef) and node.name == "validate_cargo_source_graph")
exec(compile(ast.Module(body=[function], type_ignores=[]), "frozen-c3ac-graph-validator", "exec"), tests.module.__dict__)
suite = unittest.TestSuite([tests.EnvironmentTests("test_stable_cargo_tree_and_metadata_preflight_cover_reviewed_candidate_superset")])
result = unittest.TextTestRunner(verbosity=2).run(suite)
if len(result.failures) != 1 or result.errors or "RuntimeError not raised" not in result.failures[0][1]:
    raise SystemExit("baseline must fail specifically for the missing-candidate expectation")
print("Expected baseline missing-candidate RED verified; candidate restored on disk.")
