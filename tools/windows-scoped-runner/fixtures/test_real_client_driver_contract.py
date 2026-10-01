"""Static scaffolding only; these checks do not execute or prove C# behavior."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "MonitorAcceptanceDriver.cs"
FIXTURE = ROOT / "fixtures" / "MonitorAcceptanceDriverFixture.cs"
README = ROOT / "README.md"


class RealClientDriverSourceScaffolding(unittest.TestCase):
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
