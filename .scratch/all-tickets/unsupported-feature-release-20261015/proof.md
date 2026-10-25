# Unsupported feature gates: Linux host-target proof (2026-10-15)

## Accepted slice

The combined independent review accepts four compile-time rejection checks on lllm Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, target `x86_64-unknown-linux-gnu`, at project revision `a98f5ce47c152900002904a45b060405ee722abb`. The checks used the recorded Cargo.toml and Cargo.lock hashes in `attempt-01/inputs.json`, one Cargo job, and one scoped runtime. Review: `attempt-01/combined-review.md`; its post-review toolchain-install statement is corrected by `attempt-01/evidence/review-context-correction.txt`.

Accepted gates:

- `sys,no_std`: exit 101 with the intentional sys-requires-std diagnostic.
- `net,no_std`: exit 101 with the intentional net-requires-std diagnostic.
- `sys,net,no_std`: exit 101 with both intentional diagnostics.
- `sys,no_object`: exit 101 with the intentional sys-requires-object-maps diagnostic.

The private-source control removed only the sys/no_object guard; the fail-closed matcher rejected the resulting compile failure because the intended diagnostic was absent. Restored source hash matched and the restored check emitted the intended diagnostic. The scoped runner exited 0; runtime and owned session scope were removed after exporting evidence.

## Unverified scope and incident

WASM target checks (sys-only, net-only, and combined sys+net) remain unverified because the existing Rust installation had no WASM target. No target was installed and no WASM result is inferred from host-target checks.

A post-review toolchain inspection accidentally caused two root-owned Rust 1.77.2 installations, each removed after identifying it as this session's own resource. The project toolchain at `/home/Daniel/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu` was already present, remained intact, and was used directly by the accepted run. See the correction evidence. The root installation was not used for project compilation.

This proof closes only the four named Linux host-target negative gates. WASM, release matrix, platform/MSRV rows, and the wider Ticket06/A-F package remain open.

## Later WASM result — 2026-10-25

The historical missing-target condition above no longer blocks the three named compiler cases: an existing workhorse Rust1.97.1 target was used without installation, with a minimal cfg repair after a meaningful sys/import-error RED. See [the source-bound compiler proof](../wasm-rejection-20261025/proof.md). The old1.77.2 host negative results remain at their original scope; no1.77.2 WASM execution or complete release acceptance is inferred.
