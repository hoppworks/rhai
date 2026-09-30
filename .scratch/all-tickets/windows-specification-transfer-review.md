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
