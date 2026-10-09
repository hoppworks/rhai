# Independent pre-run review: Linux X35 attempt06

**Verdict:** Cleared for one bounded RED/GREEN attempt; static review only.

The corrected artifact validator reads `red-build.stdout` and `green-build.stdout`. The cleanup observer checks each start marker before reading any log. If no selector started in a phase, it records no test fixtures and can verify/retire an empty session scope; if a partial phase started, missing selectors keep the observer incomplete. The launcher still returns failure when the runner fails.

The launcher loads the expected scoped-runner SHA-256 from checksummed `inputs.json`, verifies the runner bytes before scope creation and again after creating the exact scope but before launch, and records the checked value. The attempt-input manifest verifies all inputs.

RED controls are anchored in the three named X35 functions and check their expected assertion diagnostics. GREEN restores the exact instrumented test-source SHA. All three selectors are checked in `--list` and run individually with `--exact`; the two builds are shared across the three selectors per source state. The observer binds temporary roots to this unique scope, validates PIDfd/fixture cleanup readbacks, rejects remaining or unreadable group members, and retires only the exact empty scope after the runner is reaped.

Attempt-input manifest SHA-256: `d5cfc75e69f46d8d6aef4feadf3b959b3f1224df818bc688e07646e935a67cd4`.
Scoped runner SHA-256 enforced by the launcher: `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`.
