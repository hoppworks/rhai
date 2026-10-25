"""Source contract for trustworthy Windows PowerShell child exit handling."""

from pathlib import Path
import re
import unittest


FIXTURE = Path(__file__).with_name("RunSourceFixtures.ps1")


class SourceProcessExitContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = FIXTURE.read_text(encoding="utf-8")

    def test_owned_wait_captures_the_handle_before_waiting_and_status_once(self):
        helper = re.search(r"(?ms)^function Invoke-OwnedProcess\b.*?(?=^function |^if \(!\$SetupFailureControl\))", self.source).group(0)
        self.assertRegex(helper, r"(?s)\$process\s*=\s*Start-Process.*?\$processHandle\s*=\s*\$process\.Handle.*?WaitForExit")
        self.assertIn("Get-RequiredExitCode", self.source)
        self.assertRegex(helper, r"(?s)\$exitCode\s*=\s*\$process\.ExitCode.*?Get-RequiredExitCode\s+\$exitCode")
        self.assertEqual(len(re.findall(r"\$process\.ExitCode", helper)), 1)

    def test_nested_setup_failure_wait_also_caches_handle_and_rejects_missing_status(self):
        self.assertRegex(self.source, r"(?s)\$controlProcess\s*=\s*Start-Process.*?\$controlProcessHandle\s*=\s*\$controlProcess\.Handle.*?WaitForExit")
        self.assertIn("Get-RequiredExitCode $controlExitCode", self.source)

    def test_native_contract_runs_real_zero_and_seventeen_children_and_rejects_unavailable_status(self):
        for marker in (
            "exit-code-regression-zero.stdout.txt",
            "exit-code-regression-17.stdout.txt",
            "EXIT_CODE_REGRESSION_ZERO",
            "EXIT_CODE_REGRESSION_17",
            "Get-RequiredExitCode $null",
            "unavailable exit status",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.source)

    def test_native_contract_demonstrates_real_wrong_expected_exit_status(self):
        helper = re.search(r"(?ms)^function Test-OwnedProcessExitCodes\b.*?(?=^if \(!\$SetupFailureControl\))", self.source).group(0)
        self.assertRegex(helper, r"(?s)Invoke-OwnedProcess\s+\$PowerShellPath.*?exit 17.*?['\"]exit-code-regression-17-wrong-expected['\"]\s+30\s+0")
        self.assertRegex(helper, r"(?s)catch\s*\{.*?Exception\.Message\s*-match.*?exit-code-regression-17-wrong-expected exited 17 \\\(expected 0\\\).*")
        self.assertIn("EXIT_CODE_REGRESSION_17_WRONG_EXPECTED", helper)
        self.assertIn("exit-code-regression-17-wrong-expected.stdout.txt", helper)


if __name__ == "__main__":
    unittest.main()
