# Accepted Unix Child.wait decoded-output regression

Accepted 2026-10-08 after a combined independent review. This closes the named
no-primary decoded-expansion and committed-primary-cause cached-report scenarios
on native Darwin arm64 and Linux x86_64, Rust 1.77.2, in each of `sys`, `sys,sync`,
`sys,no_float`, and `sys,sync,no_float`. Verification adds `testing-environ`.

Public `Engine` runs `spawn` and bounded `Child.wait` against a real finite child.
For no-primary expansion, raw capture is below the Engine string limit, decoded
lossy text exceeds it, and the typed process error retains normal exit zero,
complete streams and exact raw bytes. For an already committed stdout overflow,
that primary cause survives later decoding. Cloned/repeated wait reports match.
Independent child-record readback and ESRCH establish reaping in every GREEN.

Each native/profile row has an intended assertion RED (exit 101, Some(0) versus
Some(1)) and freshly compiled restored GREEN (exit 0, selected test passed).
Separate same-line libtest status parsing is not required. Source, lock, profile,
compiler artifact and native environment bindings are in each `inputs.json`,
compiler/test logs and `result.json`. Darwin attempt03 and Linux use identical
archive, owned patch, test and lock hashes. Only the committed shared fixture is
included; the foreign dirty fixture is preserved outside the build.

See [combined review](attempt03/review.md), [Darwin results](attempt03/result.json),
[Linux results](linux/result.json) and their manifests/cleanup receipts. Runtime,
target/cache and exact owned empty outer scopes are absent on both machines;
original evidence was exported and independently hash-verified before retirement.

The historical three package-B preparation failures remain preserved. This turn's
attempt01 supplied a prohibited spawn timeout; attempt02 chose the wrong timed
wait overload. Neither reached the intended assertion or proves a product defect.
Their raw evidence and failure analyses remain beside accepted attempt03.

No production backend changed. Unchecked/no_index, Windows, other process
lifecycle criteria and overall A–F release acceptance remain open as mapped in
the canonical implementation plan. No unchanged accepted row needs a rerun.
