# Native macOS net feature acceptance

Accepted 2026-09-30 15:33 UTC within original 15:03:10–15:33:10 UTC package. Tested source 9005d769fee70a62ef47749747d39488299fb0dd; documentation-only follow-up ba89d1770934c5c1c86202cb7868a2fac52f1bb7. All nine source/test files independently reviewed through OCR delegate; scratch artifacts reviewed as evidence separately. No blocking finding.

Additive getter free-function registration fixes the observed Engine RED under no_object while preserving existing properties. Socket and parser semantics are unchanged. Dedicated real-peer explicit API tests pass 3/3; four legacy dot-syntax targets run zero tests and contribute no runtime proof. This does not duplicate every legacy assertion.

Final logs independently inspected: only_i32+no_float 28 passes; no_index+sync+metadata 30 passes; f32_float final-duration 29 passes (4/7/8/10). Fractional, NaN and infinite timeout inputs are rejected without consuming buffered data; extreme integer timeout remains host-bounded. Host Duration::MAX rejected for all four settings. Both wrong peer-byte controls fail at actual byte assertions and corrected controls pass. Combined no_object guarded log status101 is the intentional second-command control, after green3/3.

All fourteen exact private runtime paths found in retained logs independently read back absent. Sampled private storage maximum 1,258,436 KiB; actual peak storage and memory unmeasured. Source formatting checks passed; raw retained logs contain blank EOF lines reported by whole-artifact diff check, with no source whitespace finding. Proof summary predates the final f32 duration row; final-duration log is authoritative.

Native macOS Rust1.93 only. Combined sys, Linux, Windows, optional MSRV and complete release acceptance remain open. Proof retained under ../net-feature-proof/. No further build required for this accepted slice.
