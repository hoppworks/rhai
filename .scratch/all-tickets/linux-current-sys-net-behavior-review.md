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

## Corrected package narrow recheck — 519ad474

The intended control message and byte-vector findings are addressed in source. Three output-contract defects still block native dispatch: positive classification concatenates stdout then stderr although libtest results are stdout and Cargo target markers stderr, so summaries precede their boundaries; target order must be exact membership/once rather than caller order; modern Rust panic PID format in the original no_object record is `(51957959)`, not the invented `(pid 123)` pure fixture. Preserve Rust 1.77 no-PID support. Existing owner receives one coherent correction batch with chronological merged-output and original-format regression requirements. No native attempt consumed. Source commit attribution is Daniel Hopp; integration must use explicit lowercase author/committer and future owner commits corrected without rewriting published history.

## Narrow recheck closure — 33b4d676

Merged positive stdout/stderr uses one chronological descriptor, target equality uses exact membership plus count (duplicates/missing rejected), and named panic parsing accepts both actual numeric PID and old no-PID formats. Original byte-for-byte net-write/no-object output fixtures are retained. Exact selected panic/source, one failed test, assertion and wrong/actual values still required; removal of an unreliable standalone test-start line does not weaken this execution proof. No new blocking source finding. Independent integrated eight-requirement pure replay passed in linux-current-sys-net-behavior-root-pure.log; scoped runner zero, private runtime removed and exact empty scope retired. Original setup/error/correction history remains. Native behavior is still unexecuted. Existing finite limits and four runtime rows unchanged. Next stage exact reviewed inputs, independently compare all nine identities, then revalidate foreign heavy slot before one native dispatch.

## First native result

Exec5531 terminal1, 23.547 seconds at export. First three intended RED controls101 classify correctly. Combined exact named panic/source and custom assert! message show real intended RED101, but the generic assertion-prefix predicate falsely rejects it. Pure synthetic combined output contained a prefix the real assertion does not print. Existing owner receives original native bytes and precise classifier correction. First native infrastructure/classifier failure for this cause; production failure is not established and no positive runtime row has run. Original evidence/launcher receipts are retained. Reviewed helper bytes match. Fresh independent exact PID/start and runtime/scope absence readback passed; all cleanup statuses0. Limits/history remain, no process85. New stage/scope required for corrected finite follow-up; old original stage preserved.
