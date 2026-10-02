# Linux current sys/net behavior package review

Immutable preparation `38b07774d3d518885004bbd04f9d93ea290fec78`.
OCR selected four code files; all four reviewed under resolved Python/shell
rules, no skips. The excluded Markdown contract was also manually reviewed.
The custody/export wrapper follows the corrected accepted examples baseline;
the new runtime feature rows remain unexecuted.

## Blocking assertion-control findings

- The `net-no-object-wrong-peer` classifier requires the message from the
  restored ELSE assertion (`independent peer observed exact script bytes`).
  Its intended RED branch instead prints `deliberately wrong independent peer
  expectation`; the valid RED would be rejected.
- The write control accepts status 101 plus substring `254`. That is not proof
  of the intended assertion: compilation/setup errors can contain those digits.
  Require the exact intended test to have executed and failed with its assertion
  context and expected wrong data. Apply equivalent named-assertion validation
  to all controls; reject compile failures, zero tests, and unrelated panics.

The pure source-membership tests miss these output-contract defects. Add focused
output fixtures for intended assertion failures and misleading incidental errors.
One fix batch was sent to the existing owner, with no native launch authorized
by the source-only preparation task. Native count84/no85 remains unchanged.

An initial reviewer concern that the combined file control prints numeric bytes
was withdrawn after reading the complete assertion: its formatting arguments
use `String::from_utf8_lossy`, so the expected literal text does appear. No fix
is required for that diagnostic. This is a corrected review inference, not a
failed implementation attempt or a native run.

## Scope retained

The four positive rows cover combined baseline/no_index/metadata+serde and
net/no_object across real public Engine, filesystem/environment and TCP targets.
Accepted examples are reused. Combined sync, only_i32/no_float, unchecked,
no_index/sync/metadata and f32_float, other platforms and native process/release
acceptance remain open. The frozen source/archive/lock and finite
600/540/510+30 second budgets, jobs2, periodic RSS/storage caps and descendant16
limits are preserved. This review does not prove any runtime row.

## Independent original-evidence reproduction

Root read the retained original no-object RED log and the frozen draft control
constants in an own scoped pure run. The intended named assertion is present,
and the draft restored-branch diagnostic is absent. A compile-error-shaped
negative fixture containing 254 also matches the draft write classifier.
Receipt: `linux-current-sys-net-behavior-root-review-readback.json`, with original
proof path/hash and exact draft ref. Runner exited0; private runtime and exact
empty scope were retired. No native acceptance run or build occurred.

A direct frozen1ca-to-current diff confirms production, build/codegen/manifests
and all selected target sources are unchanged. The repaired package should use
serial test-harness scheduling to bound fixture child count; explicit concurrency
tests retain their own threads. Positive test accounting must distinguish nested
fixture summaries from outer target summaries. One Cargo invocation per row can
run several integration test executables.
