# X38 no_float applicability probe (2026-10-15)

No acceptance evidence was produced. Both X38 selectors have an explicit
cfg(not(feature = "no_float")) gate, so Cargo with
testing-environ,sys,no_float selected zero matching tests. No RED or GREEN
occurred and this feature row remains open.

Preserved attempts:
- attempt 01: runner could not write evidence because the new attempt directory
  was root-owned while execution ran as Daniel; Cargo did not start.
- attempt 02: Cargo was absent from the non-login PATH; status 127 before compile.
- attempt 03: Cargo compiled the target in 39.76 seconds but ran zero tests (33
  filtered out); the exact test-selector guard rejected that false green and the
  scoped command stopped before any X38 assertion. The runner returned 1.

The recorded scopes/runtimes were confirmed absent. No product/test source was
changed. Do not retry this feature unless the acceptance contract is revised to
provide an applicable X38 test under no_float; the existing tests intentionally
use float timeouts and exclude the profile.
