"""Source-only checks for the prepared Linux scalar process acceptance recipe."""
import ast
import importlib.util
import os
import tempfile
from unittest.mock import patch
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
PROOF = ROOT / "linux-scalar-process-proof.py"
BASE = ROOT / "check-linux-current-msrv-examples.py"
PUBLIC_TESTS = ROOT.parent.parent / "tests/sys_process.rs"


class RecipeSourceTests(unittest.TestCase):
    def test_proof_adapter_is_valid_python_and_pins_reviewed_base(self):
        source = PROOF.read_text()
        ast.parse(source)
        self.assertIn('BASE_SHA256 = "59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06"', source)
        self.assertEqual(__import__("hashlib").sha256(BASE.read_bytes()).hexdigest(),
                         "59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06")

    def test_two_feature_rows_and_narrow_test_are_explicit(self):
        tree = ast.parse(PROOF.read_text())
        values = [node.value for node in ast.walk(tree)
                  if isinstance(node, ast.Constant) and isinstance(node.value, str)]
        self.assertIn("scalar_run_with_cwd_works_without_collections", values)
        self.assertIn("testing-environ,sys,no_index", values)
        self.assertIn("testing-environ,sys,net,no_index,sync,metadata", values)
        self.assertIn("2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425", values)

    def test_controls_and_independent_child_receipts_are_required(self):
        source = PROOF.read_text()
        for token in ("expected_status=101", "left:", "right:", "1 passed; 0 failed;",
                      "child_pid=", "reap=ESRCH", "restore_example_sources()",
                      "manifest_hashes()", "source-lock-manifests.json",
                      "def export_evidence()", "resource-samples.json",
                      "source-restoration.json", "h.EVIDENCE.mkdir",
                      "signal.signal(signal.SIGTERM, h.on_signal)",
                      "check_deadline(during_export=True)"):
            self.assertIn(token, source)

    def test_public_test_and_production_sources_are_not_edited(self):
        self.assertTrue(PUBLIC_TESTS.is_file())
        public_source = PUBLIC_TESTS.read_text()
        assertion = ('    assert_eq!(result["stdout"].as_immutable_string_ref().unwrap().as_str(), '
                     'format!("{}\\n", expected.display()));')
        self.assertEqual(public_source.count(assertion), 1)
        for independent_check in ('std::fs::read_to_string(&record_path)',
                                  'std::fs::canonicalize(&child_dir)',
                                  'libc::kill(pid, 0)', 'Some(libc::ESRCH)'):
            self.assertIn(independent_check, public_source)
        # The adapter edits only the disposable archive and its single assertion.
        source = PROOF.read_text()
        self.assertIn('SOURCE = runtime / "source"', source)
        self.assertIn('test_path = h.SOURCE / "tests/sys_process.rs"', source)
        self.assertNotIn('write_bytes(', public_source)

    def test_stage_and_launch_are_absent_only_and_not_self_invoked(self):
        stage = (ROOT / "linux-scalar-process-stage.sh").read_text()
        launch = (ROOT / "linux-scalar-process-launch.sh").read_text()
        self.assertIn("test ! -e '$stage'", stage)
        self.assertIn("test ! -e '$scope'", stage)
        self.assertIn('if [[ -e "$scope" || -L "$scope" ]]; then', launch)
        self.assertIn('mkdir -m 700 "$scope"', launch)
        self.assertNotIn('bash "$script_dir/linux-scalar-process-stage.sh"', stage)
        self.assertNotIn('bash "$stage/launch.sh"', launch)


class VerifierFlowTests(unittest.TestCase):
    def setUp(self):
        self.scope = tempfile.TemporaryDirectory(prefix="rhai-scalar-source-test-")
        self.addCleanup(self.scope.cleanup)
        with patch.dict(os.environ, {"AGENT_RUNTIME_DIR": self.scope.name}):
            spec = importlib.util.spec_from_file_location("scalar_recipe", PROOF)
            self.recipe = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.recipe)
            spec = importlib.util.spec_from_file_location("reviewed_base", BASE)
            self.base = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.base)
        self.base.STAGE = Path(self.scope.name)
        self.output = ("no-index scalar child_pid=1234 reap=ESRCH\n"
                       "test scalar_run_with_cwd_works_without_collections ... ok\n"
                       "test result: ok. 1 passed; 0 failed; 0 ignored\n")

    def test_real_receipts_pass_reviewed_verifier(self):
        self.recipe.verify_positive_row(self.base, "row-green", 0, self.output)
        self.assertEqual(self.base.CONTROL_RESULTS[0]["expected_status"], 0)
        self.assertTrue((self.base.STAGE / "control-results.json").is_file())

    def test_missing_independent_receipt_and_nonzero_exit_fail(self):
        for output in (self.output.replace("reap=ESRCH", ""),
                       self.output.replace("1 passed; 0 failed;", "0 passed; 1 failed;")):
            with self.assertRaises(RuntimeError):
                self.recipe.verify_positive_row(self.base, "row-green", 0, output)
        with self.assertRaises(RuntimeError):
            self.recipe.verify_positive_row(self.base, "row-green", 101, self.output)
        self.assertEqual(self.base.CONTROL_RESULTS, [])

    def test_original_fabricated_green_summary_is_rejected(self):
        with self.assertRaises(RuntimeError):
            self.base.verify_pass("baseline", 0, self.output,
                "test scalar_run_with_cwd_works_without_collections ... ok; "
                "1 passed; 0 failed; child_pid receipt; reap=ESRCH")

    def test_launcher_is_exact_bounded_port_of_reviewed_flow(self):
        expected = (ROOT / "launch-linux-current-msrv-examples.sh").read_text()
        expected = expected.replace("rhai-linux-current-msrv-examples-1ca21e32-20261002",
            "rhai-linux-scalar-process-20261003-2a8fdc49")
        expected = expected.replace("linux-current-msrv-examples-1ca21e32-20261002",
            "linux-scalar-process-20261003-2a8fdc49")
        expected = expected.replace('helper="$stage/run-examples.py"',
            'helper="$stage/linux-scalar-process-proof.py"')
        expected = expected.replace("runner_timeout_seconds=600", "runner_timeout_seconds=585")
        expected = expected.replace('"$runner" --timeout 600', '"$runner" --timeout 585')
        expected = expected.replace('PROOF_STAGE="$stage" EXPECTED_PROOF_STAGE="$stage"',
            'PYTHONDONTWRITEBYTECODE=1 PROOF_STAGE="$stage" EXPECTED_PROOF_STAGE="$stage"')
        self.assertEqual((ROOT / "linux-scalar-process-launch.sh").read_text(), expected)
        for action in ('trap \'on_signal TERM\' TERM',
                       'INTERRUPT_REQUEST="$evidence/interrupt.request"',
                       'wait "$runner_pid"', 'pid-readback.status', 'rmdir "$scope"'):
            self.assertIn(action, expected)


if __name__ == "__main__":
    unittest.main()
