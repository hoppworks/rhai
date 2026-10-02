# Windows source-fixture exit-code repair result

## Revision and scope

- Frozen starting revision: `9e0e84e8e531e0b64859f613bb4b1bc64f804d42`.
- Instructions repository revision loaded separately: `958a4538b0191c53f2ccb2cd00d96c15045fbf68`.
- Role/config reference: Standard is configured in `config/roles.toml`; the active Codex template is `config/codex/config.toml.tmpl`.
- Changed implementation: `tools/windows-scoped-runner/fixtures/RunSourceFixtures.ps1`.
- Focused source regression: `tools/windows-scoped-runner/fixtures/test_source_process_exit_contract.py`.

## Repair

Both redirected `Start-Process` paths that wait for a child now access and retain that exact process handle before waiting: the common owned-process runner and nested setup-failure control. They refresh after the bounded wait, read `ExitCode` once, reject unavailable or non-`Int32` status explicitly, and report the captured value. The common runner checks an expected status, preserving zero-success behavior and making nonzero diagnostics include the observed and expected codes.

The fixture now includes native regression cases using real `powershell.exe` children under the already-assigned inherited job. They write distinct redirected output markers and exit 0 and 17; the parent checks both captured statuses and independently reads both output files. A third check requires explicit rejection of an unavailable status. Existing timeout bounds, job assignment, and job policy are unchanged.

## RED/GREEN and checks

- RED: before the implementation edit, the new Python source-contract test failed: no pre-wait cached handle, no single validated exit-code capture, no nested-control handling, and no native 0/17/unavailable regression declarations.
- GREEN: `PYTHONDONTWRITEBYTECODE=1 /Users/hoppworks/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest tools.windows-scoped-runner.fixtures.test_source_process_exit_contract tools.windows-scoped-runner.fixtures.test_real_client_driver_contract -v` passed all 8 tests after the repair.
- `git diff --check` passed.
- Static/source checks only. PowerShell parsing and the Windows native regression were not run in this source-only job.

## Native prerequisites and limits

The native proof remains pending review of this source change, followed by the separately authorized, bounded Windows guest run with Windows PowerShell 5.1, the existing compiler, the approved private run root, and exact job/process custody. The native run must demonstrate actual child statuses 0 and 17 plus unavailable-status rejection, and must independently read the redirected marker files. No Cargo command, compiler, VM/SSH command, guest input, install, service, or heavy/native launch was performed here.

This change does not establish that Windows PowerShell 5.1 exhibits the reported null status on the prior invocation, nor that the cached-handle workaround resolves it on the target guest. Source assertions do not certify process exit behavior, redirection, handle lifetime, or cleanup on Windows. The prior single guest source-fixture invocation remains consumed; no retry allocation was used or requested. Review is required before guest execution.
