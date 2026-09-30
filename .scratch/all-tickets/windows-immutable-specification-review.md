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
