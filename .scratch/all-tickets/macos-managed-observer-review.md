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
