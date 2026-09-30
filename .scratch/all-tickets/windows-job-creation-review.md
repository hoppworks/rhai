# Windows creation-time job source review

Reviewed candidate b596feba19ecc75e381403a87d6bc86b15c20172 on
task/windows-scoped-runner at /Users/hoppworks/projects/rhai-windows-scoped-runner.
This candidate remains separate from the integrated package source.

OCR delegate preview reported one reviewable source and three excluded files.
All four changed files were manually reviewed: ScopedRunner.cs, README.md,
fixtures/PayloadFixture.cs, fixtures/RunProcessCreationFixtures.ps1. Coverage:
4 reviewed, 0 skipped. OCR's default correctness/resource rules were applied.

Source replaces post-create assignment with STARTUPINFOEXW JOB_LIST association,
suspended creation, exact membership check and expected previous suspend count.
Two review findings were corrected in the responsible context before commit:
cleanup failures must not skip job/other resource release; failed attribute setup
must free both allocations and delete initialized native attributes. Fixture
review also removed unowned compilation, required intended diagnostics, restored
the prior environment value and retained failed artifacts.

No remaining blocker was identified for this narrow source change. This does
not certify ABI, compilation, Windows creation atomicity, actual job membership,
process-tree termination or cleanup. No compiler, fixture or native command ran;
TDD RED/GREEN and independent native readback remain unverified. The candidate's
own receipt and marker absence are not independent termination proof. The
PowerShell harness is not an accepted outer supervisor and must not run until
native custody/bootstrap gates pass. Successful harness cleanup is also unproven.

The broader monitor/client, lease, journal, safe handle-based filesystem and
transport-survival contract remains unimplemented. This is one intermediate
source commit within the existing custody correction, not an accepted correction
or a failed independent native attempt. Do not merge or launch package workloads
on the strength of this source review.
