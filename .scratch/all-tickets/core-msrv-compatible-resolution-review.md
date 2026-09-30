# Core minimum-toolchain evidence acceptance

Candidate20452caba4c39d4d640312d93db1175bea35d301 is integrated locally.
This is evidence-only: no production source or manifest changed. The proof archives
c4646230's entire source/workspace and uses a private complete v3-compatible lock.
Coordinator read the122-line helper fully with deterministic OCR Python rules;
one reviewable source file, zero skipped. Logs and lock/proof artifacts were
assessed separately, including the final lock missed by OCR automatic selection.

Actual Cargo1.66 check --lib --locked --target aarch64-apple-darwin completes.
Real Engine example using that compiler runs40+2 and independently expects42;
wrong43 assertion panics at the actual42/43 comparison. Source manifest remains
unchanged, no optional target pruning. Precise js-sys0.3.91/wasm-bindgen0.2.114
selection resolves inactive dependency syntax that old Cargo could not parse.
Final lock selects thin-vec0.2.19. Original thin-vec0.2.20/edition2024 and solver
boundaries are retained as diagnostics, not core-source failures.

Final exact lock is tracked at ../core-msrv-compatible-resolution/Cargo.lock.
Proof and raw core-check/Engine logs are in the same directory. Independently
confirmed final runtime absent:
/var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-5yr5quw3.
Sampled post-command private storage maximum1317696KiB is not continuous peak.
CARGO_BUILD_JOBS was inherited without captured value: two-job compliance is
unverified. This does not invalidate observed compiler/Engine behavior or certify
all resource instructions. Do not rebuild just to infer missing historical data.

Evidence applies to current default core: only optional sys/fs.rs production code
changed since archived c4646230. No relevant default-core manifest or code changed.
This accepts native macOS default core1.66 compilation and smoke evaluation only.
Optional sys/net1.77.2, feature/platform/release gates remain open. No remote writes.
