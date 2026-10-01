"""Static scaffolding only; these checks do not execute or prove C# behavior."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "MonitorAcceptanceDriver.cs"
FIXTURE = ROOT / "fixtures" / "MonitorAcceptanceDriverFixture.cs"
README = ROOT / "README.md"
COMPILE_WRAPPER = ROOT / "fixtures" / "CompileMonitorAcceptanceDriver.ps1"


class RealClientDriverSourceScaffolding(unittest.TestCase):
    def test_compile_wrapper_is_separate_pinned_and_bounded(self):
        source = COMPILE_WRAPPER.read_text(encoding="utf-8")
        for marker in (
            "monitor-driver-[0-9a-f]{32}", "ReparsePoint", "AvailableFreeSpace",
            "6e1516897be40b66585b25163bac51f9f283cc8b6b2b8ea3218338cc2d4bf019",
            "33581ea00e1dc536bf4afdd8842c0a9cc3fdd028514e228c8b1ca776d40e1db0",
            "PSObject]::AsPSObject", "[object[]]::new(2)", "SetValue",
            "AssignProcessToJobObject", "0x2308", "3600000", "Dispose($drained)",
            "MaximumLogBytes", "compile-driver", "compile-fixture",
            "expected-compiler-failure", "MonitorAcceptanceDriverFixture assertions=15",
            "ReadInt32($accounting, 40) -ne 1", "SCOPED_RUNNER_TESTING",
            "ExpectedRunnerSha256", "runnerSourceHash", "runnerHash -cne $ExpectedRunnerSha256",
            "FailFast(\"Job disposition failed", "TerminateJobObject",
            "preserving watchdog and owner through controller teardown",
        ):
            self.assertIn(marker, source)
        self.assertNotIn("RunSourceFixtures.ps1", source)
        self.assertNotIn("Invoke-OwnedProcess (Join-Path $buildRoot 'MonitorAcceptanceDriver.exe')", source)

    def test_runner_provenance_and_failed_disposition_keep_watchdog_owner(self):
        source = COMPILE_WRAPPER.read_text(encoding="utf-8")
        self.assertLess(source.index("if ($runnerSourceHash -cne $ExpectedRunnerSha256)"), source.index("New-Item -ItemType Directory -Path $run"))
        self.assertLess(source.index("if ($runnerHash -cne $ExpectedRunnerSha256"), source.index("$manifest ="))
        cleanup = source[source.index("} finally {\n    if ($script:jobHandle"):]
        failure = cleanup.index("Job disposition failed")
        dispose = cleanup.index("$script:wallTimer.Dispose($drained)")
        release = cleanup.index("$drained.Dispose(); $currentProcess.Dispose()")
        self.assertLess(failure, dispose)
        self.assertLess(failure, release)
        self.assertIn("recovery TerminateJobObject failed", cleanup)

    def test_source_declares_bounded_native_route_and_separate_fixture_seam(self):
        source = DRIVER.read_text(encoding="utf-8")
        fixture = FIXTURE.read_text(encoding="utf-8")
        for marker in ("--lease-client", "RHAI-LAUNCH/1", "SPEC-XFER/1 BEGIN",
                       "SPEC-XFER/1 DATA", "SPEC-XFER/1 END", "ParseFreshChallenge",
                       "expectedAck", "input.NewLine=\"\\n\"", "Deadline(180000)"):
            self.assertIn(marker, source)
        self.assertIn("ParseJournalForFixture", fixture)
        self.assertIn("ValidateModeForFixture", fixture)

    def test_source_has_bounded_io_journal_and_job_disposition_paths(self):
        source = DRIVER.read_text(encoding="utf-8")
        for marker in ("BoundedPipes", "MaximumRecordBytes", "DecodeJournalFrames",
                       "QueryInformationJobObject", "accounting.ActiveProcesses!=1",
                       "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE", "WatchDeadline", "RejectReparse"):
            self.assertIn(marker, source)
        self.assertNotIn("Task.Factory.StartNew", source)
        self.assertNotIn("reader.ReadLine()", source)

    def test_documentation_describes_bounded_route_without_exclusivity_claim(self):
        readme = README.read_text(encoding="utf-8")
        self.assertIn("180-second whole-driver monotonic deadline", readme)
        self.assertIn("grants breakaway\ncapability to eligible children", readme)
        self.assertIn("Python source-presence checks are scaffolding only", readme)
        self.assertIn("EOF or disconnect does not count", readme)


if __name__ == "__main__":
    unittest.main()
