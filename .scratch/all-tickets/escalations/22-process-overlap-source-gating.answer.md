# Verdict

One bounded source follow-up can close the identified source-readiness cause. In immutable candidate `b83ffe431f76bd051312179e297e1dcc14a79ae4`, delete only the newly added `#[cfg(all(target_os = "linux", not(feature = "no_float")))]` immediately above `record_field_pid` in `src/packages/sys/process/unix.rs:4185`. Restore that helper's baseline availability inside the existing test module. Keep the Linux/no-float gates on the new `record_field_ticks`, overlap case helper, and both overlap test wrappers unchanged.

The current candidate remains NOT READY. This recommendation is a static source determination, not a corrected-source review result, a compilation result, or native acceptance. No additional material source defect was found in the scoped changed code and coupled callers.

## Inputs and verification

- Read current global instructions, root `AGENTS.md`, the current Expert template, campaign escalation and bounded-repair references, escalation 22, and the specified process-overlap review and acceptance brief.
- Confirmed the instruction repository HEAD with a read-only lookup: `6830c49ed962a3dc1937d72d0d182150bb4c935c`.
- Reviewed the immutable Rust diff from `8c0ee4634355aee4e841b455461a7dd5aac2aa18` to `b83ffe431f76bd051312179e297e1dcc14a79ae4`, the helper definitions, every live-source helper call, the overlap instrumentation and ordinary poll/read/timeout/cleanup paths. Independently confirmed the candidate Rust SHA-256: `d4e09a1ccde117e0d7d81ba9cfa252984316f891851d2664c3bdb09994341c8b`.
- OCR preview and Rust rule lookup succeeded without installation or configuration. Preview found two reviewable files: the Rust file was reviewed; `.scratch/all-tickets/run-process-overlap-controls.py` was explicitly skipped because this escalation concerns source gating and the concrete recipe remains a separate preparation/review requirement. Coverage of the preview's reviewable files is therefore 1/2 (50%); scoped Rust coverage is 1/1. The unsupported Markdown preparation file was excluded by OCR; its original contents are outside this narrow escalation, with applicable requirements supplied by the acceptance brief and combined review.
- No source fixes, builds, SSH, native launches, signals, cleanup, installation, or Git mutations were performed. The sole written artifact is this answer. Compilation and native behavior are unverified.

## Exact minimal correction

Apply this one-line deletion relative to the immutable candidate:

```diff
-    #[cfg(all(target_os = "linux", not(feature = "no_float")))]
     fn record_field_pid(path: &Path, field: &str) -> io::Result<i32> {
```

Do not replace it with another gate, duplicate the parser, add Linux gates to inherited tests, change the tests' expectations, or broaden the fixture to Darwin. The helper only reads a supplied record and parses a named integer field. It has no `/proc` dependency. Its complete body is unchanged from the baseline, where it had no item-level gate. Restoring that exact baseline definition is smaller and safer than narrowing inherited test coverage.

## Affected dependency check

All line numbers below refer to immutable `b83ffe431f76bd051312179e297e1dcc14a79ae4`. A repository lookup restricted to live `src` and `tests` found exactly these three `record_field_pid` calls; archived scratch copies are independent evidence and must remain untouched.

| Definition or caller | Existing gate and use | Required final state |
|---|---|---|
| `record_field_pid`, 4186 | Currently Linux plus no-float exclusion; portable text parser | Remove its new attribute; retain enclosing `#[cfg(test)]` module and enclosing Unix module availability |
| Overlap case helper, 4425; PID-field call, 4449 | Linux plus no-float exclusion; parses actual fixture PGID | Keep its gate; shared parser is available |
| `run_inner_inherited_pipe_holder_case`, 5164; call, 5267 | No-float exclusion only; parses portable `holder-pid` record | Preserve caller gate and behavior; restored parser is available on every Unix target where caller exists |
| `inherited_pipe_holder_is_alive_at_timeout_and_fixture_releases_it`, 5332; call, 5387 | No-float exclusion only; outer fixture parses the same portable record and invokes the inner case | Preserve caller gate, exact nested test name and behavior |
| `record_field_ticks`, 4199; sole call, 4451 | Linux plus no-float exclusion; positive start-tick parser used only by overlap case | Keep its gate unchanged |
| DirectChild and Managed overlap wrappers, 4521 and 4530 | Linux plus no-float exclusion | Keep both gates unchanged |

With float support enabled on non-Linux Unix, both inherited callers currently survive configuration while `record_field_pid` disappears. The resulting unresolved helper name is a test-compilation regression. The deletion restores the baseline relationship. With `no_float`, these callers and the overlap cases disappear; the portable parser can remain defined as it did in the baseline. Windows does not include the Unix module. None of these static observations proves native Darwin or Windows behavior or resumes their stopped work.

The newly added scheduling adapter and observation fields/methods/calls consistently use `cfg(test)`; the arming helper is inside the test module. They contain no Linux-specific syscall or `/proc` access. Their remaining availability in other Unix test configurations is safe and does not require another gating change. Production behavior and the public API remain unchanged.

## Preserved acceptance and other blockers

Retain the corrected required-bit check (`observed & 0b1011 == 0b1011`) before the cause assertion, the deferred public outcome, and clean-timeout map normalization. These let the specific timeout-before-read control reach the intended OutputLimit assertion after independently checking fixture PID absence, scheduling acknowledgment and closure. Retain the final `0b1111` observation requirement and exact OutputLimit report assertions. The real poll readiness, ordinary overflow read, and closure observations remain in their existing positions; this fix must not change them.

The child publishes its record after writing the two stdout bytes, and the adapter waits for the actual deadline before the ordinary poll/read step. Both scopes remain required. The source recommendation does not validate the native receipt, actual child identity/start/PGID or cleanup. Those need the later bounded real-OS proof.

The independently recorded recipe defects remain separate: module-qualified names are required with `--exact`, receipts must match those names and actual test execution, and command accounting/export custody must use the accepted bounded mechanism. This answer does not approve the current Python recipe or allocate a native invocation. Existing stdin/API21/Darwin09/12/Windows02/13 stops and the future native 600/585/540-second limits and resource caps remain intact.

## Concrete next action and stop criteria

1. Record this answer against the existing source-readiness cause: initial review rejection, failed correction 1 (`cc329` portability gate), failed correction 2 (`b83` shared-helper gate), this single fresh analysis, and one remaining bounded follow-up. Keep cumulative work; cost remains unknown.
2. Have the existing source owner perform only the one-line deletion above, within the recorded 30-minute active-work planning checkpoint. Permit narrow scratch documentation of the new immutable revision and its source hash; do not change unrelated source or native allocation. Freeze the corrected immutable candidate.
3. Independently review its delta against `b83`, confirming that the only Rust change is this deletion, the parser matches the original baseline, all three callers remain correctly covered, the four new Linux/no-float item gates remain intact, and earlier cause/receipt/cleanup assertions remain unchanged. Recheck the full intended Rust diff against the production baseline for scope drift. A successful static check may close this source-readiness cause; the integrated package still awaits concrete recipe readiness and strict native acceptance.
4. Stop this source path if the bounded follow-up fails independent review, changes acceptance or production semantics, encounters contradictory source evidence, or needs another source design decision. Do not renew the two-failure history, rename the cause, or open a second escalation chain. Report the blocker once and continue only independent authorized preparation. At the planning checkpoint, record actual progress and cumulative use; it is not permission to renew a failed correction.

This finite analysis completed before its 20-minute active-work planning checkpoint. Actual monetary cost and precise active-work duration are unknown.
