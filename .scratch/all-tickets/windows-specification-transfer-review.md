# Specification transfer source review

Source baseline: source-reviewed `73020670`; contract:
`briefs/windows-specification-transfer.md`. The same responsible Windows agent
is independently confirmed running. Candidate now contains an untracked
`fixtures/SpecificationTransferFixture.cs`, authored before the transfer model.
No compilation or fixture/native execution occurred.

## Intermediate fixture review

The complete current fixture source was read. It constructs an exact 8192-byte
valid specification using bounded base64 arithmetic, models BEGIN/DATA/END and
one pending frame, checks generated frame/ack limits and the existing byte queue,
and describes terminal receivers, deadline equality, immutable results and
acknowledgement separation from lease/create authority.

Related findings delivered to the responsible context before commit review:

- Bound the main transfer loop explicitly by the fixed maximum frame count plus
  an overrun failure slot. A buggy sender must not make a future fixture hang.
- Add sender wrong-token, out-of-order and replayed acknowledgement diagnostics
  and terminality; receiver DATA replay alone does not cover sender pacing.
- Cover a 513-byte incoming frame, decimal overflow, short nonfinal chunk, and
  complete assembled bytes rejected by LaunchSpecification.Parse at END.
- Correct the existing README's stale statement that Running renewal remains
  absent. The model supports it since 43d2f067; actual native workload integration
  and transport proof remain unverified.

These are source/coverage findings within the existing incomplete Windows
custody correction. They are not executed RED/GREEN or completed failed
full-custody corrections. Await the exact source/model commit, review all changed
files including OCR-excluded fixture/README, and retain workload/exact-job gates.

## Intermediate model review

The complete dirty SpecificationTransfer.cs was independently read when it
appeared. Fixed 324-byte chunks give 26 DATA frames at 8192 bytes, plus BEGIN/END;
maximum DATA representation is 486 bytes including LF, DATA ACK is 57. A
receiver allocates only after token/total/chunk-count checks and END parses
LaunchSpecification. Single pending sender frame and supplied deadline preserve
the intended pure source boundary; transport remains unconnected.

Further related findings delivered before commit:
- Private Sender.PendingKind is referenced by the enclosing AckFields/parser.
  Move it to the enclosing private scope. This is inferred from the official
  [C# accessibility-domain reference](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/keywords/accessibility-domain),
  which explicitly demonstrates inaccessible private nested-class members; no
  compiler was run.
- Active sender invalid-state ACK/duplicate Start paths bypass Fail, so an
  invalid transfer may remain startable. Fail active invalid events, preserving
  stable terminal Completed/Failed rejection, and test the intended state.
- ParseFrame's control scan precedes delimiter diagnostics, and the fixture's
  trailing-space base64 value is a framing defect. Align error precedence and
  use a genuine malformed/noncanonical base64 case.
- CountChunks must avoid signed overflow on arbitrary internal input.
- Future MonitorTransport dispatch strips LF/optional CR today; an adapter must
  preserve/validate original canonical delimiters and byte accounting instead
  of claiming canonical input after normalization. Document the boundary while
  keeping existing lease dispatch unchanged.

These change the pre-commit review/correction action; no executed behavioral
evidence, compiler result or completed full-custody correction is claimed.

## Final immutable commit review

Reviewed commit `53140bcf` in the separate owned Windows worktree. All three
changed files were read in full, including the README and fixture excluded by
OCR. The default OCR rule was read for SpecificationTransfer.cs. Coverage is
three of three files, zero skips. The source was reread after the final commit;
`git diff --check` passed and the candidate was clean.

The bounded fixture loop, sender acknowledgement terminality and replay/token
cases, oversized frame/decimal overflow/short chunk/invalid assembled document
cases are present. PendingKind now lives in the enclosing internal scope;
CountChunks uses widened arithmetic. Delimiter diagnostics precede the ASCII
scan. Invalid active Start/ACK paths fail permanently while completed/failed
states remain stable. README records Running renewal and the original-framing
boundary. The intermediate findings are closed in source.

Transfer DATA is at most 486 bytes including LF, ACK at most 57. Exact 8192-byte
input requires 26 DATA plus BEGIN/END and one outstanding sender frame; queue
pressure cannot authorize advancement. Receiver allocation follows token/size/
chunk-count validation and END parses the immutable specification. The supplied
fixed deadline is checked for every active event; transfer acknowledgements do
not operate the lease protocol or create/resume capability.

This is source review only. No compiler, fixture, native Windows process, build,
runtime allocation, transport dispatch, workload start or exact-job proof was
executed. No full-custody attempt is complete and no product ticket is accepted.
The candidate remains isolated. Next source requirement is real monitor dispatch
with original framing preserved and workload authority still closed.
