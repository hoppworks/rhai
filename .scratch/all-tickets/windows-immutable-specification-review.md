# Immutable launch specification review in progress

Baseline source-reviewed `43d2f067`; implementation brief at
briefs/windows-immutable-specification.md. The same responsible agent is confirmed
running. Fixture source was authored first; no compilation or execution occurred.

## Intermediate fixture findings

- An exact-wire-bound fixture initially searches pairs of argument lengths with
  nested loops and repeated string allocations. Replace this with deterministic
  base64 length arithmetic or a small explicit finite adjustment count.
- Do not add unused runtime/evidence/policy model properties just to assert they
  return null. The accepted model contains only source/executable/arguments;
  rejecting unknown forbidden input fields is the meaningful boundary.
- A command-line overflow fixture using one huge argument can fail the smaller
  per-argument byte limit first. Build command-bound cases from multiple valid
  fields and assert the intended diagnostic.

Delivered for related source correction before final commit review. These do not
represent completed failed custody corrections or executed test evidence.

## Commit review: 91e474d7

All four changed files independently read, zero skipped. OCR preview selected
LaunchSpecification.cs and WindowsCustodyBackend.cs; README and fixture were
excluded by extension/path and manually reviewed in full. Default correctness,
security, performance and coverage rules inspected for both source files.

The model has only source/executable/arguments and defensive copies. Wire parsing
is bounded to 8192 bytes, canonical version/field/index/base64 framing, strict UTF8
and fixed argument/field/command limits. Pure path helpers do not perform I/O.
Exact argument-count, field-byte, encoded-wire and conservative command-line
boundary fixture source is present. Earlier fixture findings are closed in source.

Related findings sent to the responsible context before accepting this slice:
- Create clones the caller array before rejecting count >32, and scans caller
  strings before enforcing their field bound. Check count before cloning and
  cheap character-length bounds before scanning/UTF8 byte counts.
- BuildQuotedCommandLine scans a caller path before its 248-character bound and
  accepts empty/relative/device forms. Bound first and apply pure absolute-path
  syntax validation; this remains distinct from source identity/authority.
- Quoting fixtures check only a substring; add exact expected empty/quote/
  backslash cases and parser-input mutation coverage.
- Clarify that the codec allocates managed buffers but no runtime directory.

No compiler, fixture execution, native operation, created runtime or accepted
RED/GREEN occurred. These are intermediate source corrections within the
existing Windows custody chain, not completed failed full-custody attempts.
Workload entry and exact-job proof remain disabled. Await correction commit.
