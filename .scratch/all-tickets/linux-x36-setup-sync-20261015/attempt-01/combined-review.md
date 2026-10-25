# Combined independent review: X36 Linux setup sync profiles

**Result: PASS** for the four named setup-failure selectors on lllm Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, under `testing-environ,sys,sync` and `testing-environ,sys,sync,unchecked`.

All eight targeted GREENs and the scoped runner exited 0. The evidence records 16 exact PID/group absence readbacks; the exact session scope and runtime were retired. `SHA256SUMS` verifies; revision, Cargo files, Unix source and runner are bound. The four failure points are exercised through public `run` and `spawn`, with no marker execution, retired reservations, and exact cleanup.

Prior RED controls are reusable at the selector/assertion level: test bodies are byte-identical, and existing evidence covers pre-`setpgid`, post-`setpgid`, `fchdir`, and kernel-denial cases. The kernel-denial control also has a reviewed Rust 1.77.2 checked-sync RED. The other three controls ran in earlier profiles; no fresh sync-profile mutation was performed for those, so the transfer does not claim new sync-specific RED execution.

Standards: PASS. Spec: PASS for only these eight rows. X36 overall and other platform/profile rows remain open.
