# Specification transfer review in progress

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
