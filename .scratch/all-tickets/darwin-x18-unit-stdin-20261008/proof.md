# Ticket 03 X18 — Darwin partial acceptance

## Scope

This proof closes only the named Darwin X18 row: arm64, macOS 27.0.1
(Build 26A434), Rust/Cargo 1.93.0, features testing-environ,sys, source
revision bcb524b866103f9a684b8da41725c802a00d2458. Other operating systems,
features, MSRVs and Ticket 03 rows remain open.

The acceptance test is tests/sys_process.rs::unit_stdin_means_immediate_eof,
SHA-256 7ddc87f6e4b57d61d077445a81f1c3ef2f2e54cb35ac8c90a7ed328245d14017.
It calls a Rhai script through the public Engine and run_raw with stdin: (),
launches the real test executable as a child, and checks exact stdout ending in
stdin-eof. The child independently writes its PID and exit code to a file;
assert_child_record rereads that file and verifies exit 0 plus direct-child
absence through kill(pid, 0) == -1 and ESRCH.

The accepted Cargo.lock SHA-256 is
2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425.

## Real run and assertion sensitivity

The command was run from a clean archive of the identified commit:

cargo +1.93.0 test --locked --features testing-environ,sys --test sys_process unit_stdin_means_immediate_eof -- --exact --nocapture --test-threads=1

Attempt02 changed only the expected byte string from stdin-eof to stdin-not-eof.
Its raw log shows the child returned the actual stdin-eof bytes, the mutant
expected stdin-not-eof, and the equality assertion failed: 0 passed, 1 failed,
exit 101. A wrapper check initially missed this because --nocapture interleaves
the panic before libtest's terminal FAILED marker. The raw log was independently
checked; this is the intended RED, not a product or infrastructure failure.
The restored baseline source hash matches the committed source exactly.
Attempt02/post-run-analysis.md and its check digest record this correction.

Attempt03 ran the restored source with the same commit, feature set, lock,
platform and toolchain. Its log reports the named test passed, 1 passed, 0
failed, exit 0. No second RED was run; attempt02 supplies the valid sensitivity
control.

## Resource and cleanup record

Each invocation used the central tools/run_scoped.py with a unique owned scope
under ~/.local/share/agent-builds/rhai/<session-id>, TMPDIR set to that scope,
and CARGO_HOME/CARGO_TARGET_DIR inside AGENT_RUNTIME_DIR. Cargo used one build
job. Build, test and evidence export were bounded to 600 seconds. The runner
removed each private runtime; host readback confirmed the exact attempt02 and
attempt03 scopes were empty and removed. Test TempDir guards own the child
record directory, and the test verifies direct-child reaping.

Attempt01 preserves a separate pre-assertion cwd setup failure and its cleanup
receipt. Attempt02 and attempt03 retain run scripts, raw logs, statuses, source
and lock hashes, metadata, outcomes and SHA-256 manifests. All three attempts
are preserved without treating infrastructure or wrapper errors as product
failures.

## Review state

The combined independent review returned READY on 2026-10-08. It verified the
source behavior, stated scope, rules, expected RED and restored GREEN, child
readback/reaping, manifests, and cleanup. It requested only the corrected
analysis-file reference above and this review-state update; the underlying
test evidence was accepted without rerunning it.
