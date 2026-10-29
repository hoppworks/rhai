# Independent combined review

Candidate: `src/tests.rs` test-only diff against `8d8bf84febebb182ca65f2307f96676f05858eb2`; Windows process work excluded.

**Standards: PASS.** No actionable repository-rule violation or relevant code smell in the scoped change.

**Spec/correctness: PASS for the named slice.** The old assertion failed at the intended 56-versus-48 mismatch on Rust 1.66/aarch64. The corrected maximum-size assertion passed at the same source and lock with overlay SHA-256 `3949a1ea368a1408ad9b410b0573194402146f5fd519f087728359ac62f942e2`. The independent layout probe reproduced 56 on 1.66 and 48 on stable. The comment's exact compiler-layout mechanism is an inference; the observed variation supports the test change.

**Coverage limit:** The GREEN tests only macOS default-feature core `--lib`. It does not certify the Windows sys work or remaining release matrix.
