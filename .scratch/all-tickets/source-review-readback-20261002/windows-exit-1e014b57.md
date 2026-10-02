Source disposition: the exit-status repair is reasonable and preserves the existing custody design. I found no material implementation regression in `1e014b57675b4b46add54973245ef20907f42972` against `9e0e84e8e531e0b64859f613bb4b1bc64f804d42`. Native acceptance remains incomplete, with one medium acceptance-coverage finding.

**Medium — the new native checks do not demonstrate failure of the exit-status assertion.**  
Category: test. Location: [RunSourceFixtures.ps1:385](/Users/hoppworks/.codex/worktrees/windows-source-exit-codes/rhai/tools/windows-scoped-runner/fixtures/RunSourceFixtures.ps1:385), lines 385–402.

The real children declare exits 0 and 17, and their distinct redirected markers are independently read. Those are useful positive checks. The injected `$null` check meaningfully tests unavailable-status rejection, but it does not exercise the real child-status comparison with a wrong expectation. The setup-failure control tests a different failure path. Consequently, neither the fixture nor the reported Python RED/GREEN supplies the project-required native failing control for this assertion.

Before acceptance, demonstrate that a real exit-17 child fails when expected to exit 0, with diagnostics containing observed 17 and expected 0; then demonstrate the correct expectation passes. This must fit a separately authorized finite native package without resetting consumed allocations. Removing handle caching alone is not a dependable failing control unless the defect is first shown to reproduce on this guest.

The source review supports these conclusions:

| Area | Assessment |
|---|---|
| Handle caching | Both waiting paths access the returned `Process.Handle` before waiting, at lines 368 and 420. This matches the workaround described in [PowerShell issue 5421](https://github.com/PowerShell/PowerShell/issues/5421); applicability to this guest remains unverified. |
| Status validation | `Get-RequiredExitCode` accepts an object, rejects null and non-`Int32` values before conversion, and therefore does not silently turn missing status into zero. |
| Single capture | Each affected path reads `ExitCode` once after its bounded wait and refresh. Subsequent validation and diagnostics use the captured value. |
| Expected status | Existing compiler and fixture calls retain expected-zero behavior. The new exit-17 case explicitly expects 17. |
| Nested setup failure | The control now rejects unavailable status while retaining nonzero enforcement, exception/PID marker checks, shared 30-second deadline, exact-job accounting and process disposal. |
| Custody and cleanup | Job assignment precedes child launches. No breakaway policy, job limits, timeout cleanup, watchdog ownership or final accounting was changed. New failures unwind through the existing encompassing cleanup. |
| Output read-back | Distinct stdout files are freshly read after the children exit. The markers establish child execution independently of the captured status; they do not independently establish the numerical status. |
| Python regression | Structural source evidence only. It cannot prove PowerShell parsing, handle lifetime, actual status, redirection or native cleanup. |

Caching an `IntPtr` is not itself a separate owning handle; the important operation is accessing `.Handle` on the retained `Process` before waiting. I found no replacement-by-PID lookup or premature disposal in either changed waiting path.

The prior blank compiler receipt remains unresolved historical evidence. Warning-only stdout, empty stderr and a 171,008-byte executable do not establish compiler success or subsequent fixture execution. The recorded absence of three PIDs proves only their absence at observation, not complete job closure.

All three changed files were reviewed in full:

| Path | Status | Coverage |
|---|---|---|
| `.scratch/all-tickets/windows-exit-code-repair-result.md` | Added | Claims, recorded checks and native limitations |
| `tools/windows-scoped-runner/fixtures/RunSourceFixtures.ps1` | Modified | Full file, including assignment, setup failure, waits, compiler callers, read-back and final disposition |
| `tools/windows-scoped-runner/fixtures/test_source_process_exit_contract.py` | Added | Full file and limits of its assertions |

`total_files=3`, `reviewed_files=3`, `skipped_files=0`, `coverage_rate=100%`. This is source-review coverage.

Loaded instructions repository revision, confirmed separately from Rhai: `958a4538b0191c53f2ccb2cd00d96c15045fbf68`. I read the current global/project instructions, ocr-delegate, `config/roles.toml`, and Expert templates. Rhai HEAD was independently read as the reviewed revision.

OCR preview reproduced the documented failure: sandbox-denied Apple Git cache diagnostics contaminated its revision argument. I made one attempt, with no retry or reinstall, then used the brief-authorized direct immutable diff and manual rule coverage. Automated OCR selection/rule resolution was unavailable. The repair result’s eight passing Python checks and `git diff --check` are reported prior evidence; I did not rerun them.

The exact remaining native paths are:

- Windows PowerShell 5.1 parsing and execution of this revision.
- Actual redirected child exits 0 and 17, plus independent marker read-back.
- Unavailable-status rejection and the meaningful failing control described above.
- Cached-handle behavior for the real compiler invocation.
- Nested setup-failure status, primary-exception preservation and owner-only job accounting.
- Timeout/interruption cleanup, final job disposition and watchdog drain.

Any native package still requires verified guest identity/environment, reviewed staged-source provenance, the existing compiler, approved private runtime, exact process-tree custody, bounded execution and independent cleanup read-back. The consumed fixture invocation, outer one-hour cap and nonrenewable real-client 30-minute limits remain unchanged.

No files were edited, no report was written, and no tests, builds, compiler, PowerShell, VM/SSH, guest input, descendants, installs, configuration changes or pushes were launched.