# Windows exit-code failing control fix result

## Immutable starting revision and scope

- Starting revision: `1e014b57675b4b46add54973245ef20907f42972` (confirmed with `git rev-parse HEAD`).
- The source-only change adds a real exit-17 child configured with expected status 0 to `Test-OwnedProcessExitCodes`.
- No process implementation, handle logic, job policy, timeout policy or native allocation changed.
- No descendants were started. No PowerShell, parser, guest/VM/SSH, Cargo, compiler, native or heavy launch was performed.

## Change

The negative control starts a distinct redirected PowerShell child that writes `EXIT_CODE_REGRESSION_17_WRONG_EXPECTED` and exits 17, while `Invoke-OwnedProcess` expects 0. It requires the mismatch diagnostic to identify the child and report actual 17 and expected 0. It then reads the child's fresh, uniquely named stdout file and checks the marker independently. The case has the existing 30-second bound.

The existing expected-0 and expected-17 children remain separate real child invocations with their own redirected output markers and 30-second bounds. The unavailable/null-status rejection remains intact. The new Python source regression requires the negative case, exact mismatch diagnostic pattern, and distinct stdout marker.

## RED/GREEN and source checks

- RED: ran the newly added focused test before modifying the PowerShell fixture. It failed because no wrong-expected exit-17 case existed.
- GREEN: `PYTHONDONTWRITEBYTECODE=1 /Users/hoppworks/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest tools.windows-scoped-runner.fixtures.test_source_process_exit_contract -v` passed all 4 tests after the change.
- `git diff --check` passed.
- These checks inspect source text only; they do not parse or execute PowerShell and do not prove native status, redirection, process custody or cleanup.

## Native distinction and remaining limitations

Native verification remains unperformed and required before guest execution review/acceptance. In particular, the changed PowerShell 5.1 fixture has not been parsed or run on Windows. The actual exit 17 versus expected 0 diagnostic, independent marker read-back, separate correct expected-17 and expected-0 children, unavailable-status rejection, cached-handle behavior and cleanup remain unverified on the guest.

The single previously consumed guest fixture invocation, shared outer one-hour policy and Expert02 nonrenewable real-client 30-minute limits are unchanged. No retry allocation or limit reset was used. Review is required before guest execution.
