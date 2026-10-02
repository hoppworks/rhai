The workspace is read-only, so I couldn’t write the requested report. Here is the complete report for the coordinator to retain.

# Windows source-fixture allowance reconciliation

## Finding

The **one-hour limit is an invocation watchdog**, not evidence of a one-hour cumulative work budget: `RunSourceFixtures.ps1` starts its overall timer at launch and throws when the remaining time reaches zero (lines 307–365; especially line 363). That does not renew the separately recorded authorization for a **single source-fixture invocation**. The coordinator state records that invocation as consumed and says there was no retry allocation (lines 196–205, 291–299, 328–353). Preserve that history; the blank compiler exit status is an infrastructure failure or unknown outcome, not proof that the fixtures passed.

The recorded authorization authorizes the single bounded invocation after its prerequisites; it does not clearly authorize a second invocation. The one-hour timer therefore must not be treated as a fresh cumulative allowance. The Expert02 real-client limit is a separate, nonrenewable 30-minute bound (`.scratch/all-tickets/escalations/02-windows-runtime-custody.answer.md`, around line 449), and does not apply to source fixtures.

## Human limits and workflow rules

The brief records the owner’s standing instruction to accept concrete recommendations for open questions and to pursue maximum quality, plus authorization for a further bounded process attempt and two bounded Linux/combined follow-ups. It also says no numeric Windows cumulative-hour cap was given. Per the loaded global workflow instructions, a standing acceptance of recommendations can cover a concrete, finite follow-up package; it does not erase consumed work or raise hard limits.

The available records do not establish that the separately mentioned bounded process attempt covers another **source-fixture** invocation. I therefore cannot recommend relaunching the fixture under the existing single-invocation authorization. Reconcile that attempt’s scope against the exact owner instruction before any new fixture launch. A stored `PENDING` label alone is not a blocker.

## Consumed history and evidence

- One source-fixture invocation was launched and is consumed. The retained readback shows the compiler step reported a blank exit code; `ScopedRunner.exe` existed at 171,008 bytes, but this does not prove compiler success, fixture execution, or job closure (`coordinator-state.md`, lines 289–299; `windows-staging-9e0-root-evidence/closure-readback/readback.md`).
- The prior compiler log had 2,817 bytes of stdout and no stderr; no “error” or “failed” matches were found. These observations do not recover the lost live `Process.ExitCode` (`windows-compiler-exit-diagnosis.md`).
- Source repair and independent coverage repair were completed without another guest invocation. The source repairs add cached process-handle/status capture and a real exit-17-versus-expected-0 control; they remain source-only (`windows-exit-code-repair-result.md`; `windows-exit-code-control-fix-result.md`).
- No reliable elapsed duration for the consumed fixture invocation is present in the retained records reviewed here. Do not invent one or subtract a guessed amount from the one-hour watchdog.
- Recent guest actions were staging/readback, not fixture launches. The corrected script was staged at `C:\Users\RhaiTest\.local\share\agent-builds\rhai\w2c9-20261002-cfe0128fbd4b\fixtures.ps1`; its native SHA-256 is `37dac20385ce3251c671960add4e43a5cde18ac5d52a42eae6827ffd2921543a`, with `Parser.ParseFile` reporting zero errors (`windows-exit-corrected-staging-20261002/root-readback.json`). The 17 C# pins match integrated source locally; the receipt explicitly says this is not a fresh guest pin readback (`coordinator-state.md`, lines 455–468).

## Source, compiler and run-root readiness

- The pinned source archive from revision `9e0e84e8e531e0b64859f613bb4b1bc64f804d42` is retained at `C:\Users\RhaiTest\.local\share\agent-builds\rhai\w9e0-20261002-6f804a9c4c4a4e78\rhai-source.zip`, 13,380,569 bytes, SHA-256 `8291e58652a7dc8494513d910460e6dae39a716f5dfca937bda40fafcfa0caa4` (`windows-staging-9e0-root-evidence/root-readback.json`).
- The retained ancestor receipt says an attempted extraction command was cancelled and does not establish extraction. Although coordinator history later references the fixture invocation, the reviewed retained receipts do **not identify an exact immutable extracted `SourceRoot`** or independently attest its current contents. Do not guess a source path or substitute an unverified fresh extraction.
- The existing compiler was observed at `C:\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe`, 59,720 bytes, SHA-256 `cf32c7b8e5691b962f1b6e92b03d87409dd9f7aebfd71c5bf778203cc56ee1` (`parser-compiler-root-readback.json`). Compiler identity should be freshly read back before any future invocation.
- The corrected harness scope `w2c9-20261002-cfe0128fbd4b` is retained and was explicitly staged without running fixtures (`windows-exit-corrected-staging-20261002/staging-state.md`). It is not a fresh `RunRoot`. Any future authorized run needs a fresh unique run root, verified non-reparse ancestors, sufficient free storage, fresh guest source pins, available heavy-run slot, and exact process/job custody, while preserving the existing per-compiler and fixture bounds. The runner README specifies 180-second per-compiler ceilings (`tools/windows-scoped-runner/README.md`, lines 55–76).

## Recommended next action and stop condition

First, resolve the existing invocation’s exact `SourceRoot` and provenance from retained native receipts or a permitted read-only guest inspection; also verify the current guest pins, compiler identity, run-root conditions, and heavy-run slot. Do not launch a fixture as part of that inspection.

Before any second fixture invocation, establish that the owner’s bounded process-attempt authorization covers this source-fixture route. If it does, record a concrete finite follow-up allocation that preserves the one-hour **per-invocation watchdog**, all existing resource and child-process caps, and the consumed first invocation. Stop on any prerequisite mismatch, custody uncertainty, compile or fixture failure, or time/resource limit; no rerun within that package.

## Still unverified

PowerShell fixture compilation and execution on Windows; actual child statuses 0 and 17, the wrong-expected-status control and unavailable-status rejection; marker-file readback; job accounting, forced-controller closure, and cleanup. These remain native acceptance requirements.