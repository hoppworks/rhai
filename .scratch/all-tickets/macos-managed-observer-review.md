# Managed capture observer review

Reviewed immutable increment c2829b1e148a54d6225b2a821835feb5061dd64f.
OCR preview and rule receipts are retained alongside this file. All six selected
code files were reviewed; the excluded pure-suite log was read as evidence.

## Blocking findings

1. The companion invokes `run_raw`, routed through `run_map` and `supervise`.
   The observer is attached only to `pump_spawned_record` and `ChildSnapshot`.
   The actual synchronous control path therefore cannot publish the receipt.
2. `run_control_only` extracts SOURCE_REF 00bed4 and copies only the companion.
   That frozen Cargo manifest and Unix source contain neither the new feature
   nor observer. Building this source with the new feature cannot succeed.

Correct these together using an explicitly pinned separate control source and
the actual synchronous read path. Preserve the frozen measurement source and
timer. Source checks must verify actual assembled control inputs and call-path
applicability, rather than only finding strings in current working files.
The stale missing-progress comment should reflect the repaired control wiring.

## Evidence and acceptance

Owner pure66 is source evidence only. No compilation or native observation was
performed. Launch guard remains false, native allocation count remains84.
No claim of live dual-stream read progress or Darwin identity binding is accepted.
Fix batch returned to the responsible owner; independent affected-path recheck
and native prerequisites remain required before control execution.

## Corrected increment and independent replay

Rechecked immutable c3ac25738b76d304dc8c60c661a9a36a73704fa8 against c2829b1e.
All six OCR-selected files reviewed, plus the two excluded RED/GREEN logs and
the earlier receipt-binding/companion callers. Correction preview and rules are
`macos-managed-observer-correction-{preview,rules}.json`; coverage is 6/6 (100%).
Both blocking findings are resolved in source. The pinned private manifest and
Unix overlay are assembled separately; successful synchronous `supervise` reads
publish positive counts for both streams. Atomic no-overwrite publication binds
the host/fixture PIDs to the existing complete native identity census. Publication
errors take the existing bounded failure/cleanup path. The observer is absent
from production and the frozen measurement command/source. Production manifest
and Unix source exactly equal the 00bed4 baseline; no rollback is integrated.
The overlay also retains two harmless read-result local bindings in the unused
spawn capture path, without observer calls there.

Root independently replayed the integrated pure suite: 68/68 pass, scoped exit0,
runtime removed and exact empty scope retired. Original output is
`macos-managed-observer-correction-root-pure.log`. This checks real private-source
assembly/nonmutation and rejects altered frozen input, alongside protocol and
counter controls. No material source finding remains. No Cargo/native fixture,
interruption control or measurement ran; ABI, actual confinement and live-capture
acceptance remain open. Native process allocation84 and false guard unchanged.
