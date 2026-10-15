# Linux R3 `no_index` process API acceptance

Status: the Linux R3 contract is accepted at the current integrated candidate, `42c117e84669f4d105b5d76b5f0c07611622708b`, for the base `testing-environ,sys,no_index` profile. This closes the named Linux R3 behavior only; it does not close the release feature/platform/MSRV matrix or any A–F / Ticket03 process package.

The accepted behavior has two focused public Engine observations:

- `run("/bin/true")` works without an argument list. The returned map reports success, code 0, complete stdout and complete stderr.
- A real Rhai `Array`, injected through the host `Scope` because `no_index` disables array literal syntax, is passed as the second argument to `run`. The public Engine returns `ErrorFunctionNotFound` for `run(..., Vec<Dynamic>)`, proving that array-taking `run` overload is not registered. The prior scalar-process row also proves `run(program, options)` works and that `run_raw` is absent.

## Binding and results

The restored GREEN used Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, default profile and exactly `testing-environ,sys,no_index`. The source copy was built from integrated revision `42c117e8…`, with the working-tree test source copied into that source copy. `Cargo.lock` was reused from the accepted X35 Linux proof because its SHA-256 is identical: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. The production implementation hash is unchanged at `2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6`; the final test source hash is `9b031886eb3b4d365664a244e68ab574ef110e3cc7d41efe5f457d0d1fcb1dbe`.

The exact restored GREEN command was:

```sh
cargo test --locked --features testing-environ,sys,no_index --test sys_process run_without_arguments_works_and_array_overloads_are_absent -- --exact --nocapture --test-threads=1
```

Attempt 06 reports Cargo exit 0 and libtest `1 passed; 0 failed`. It emitted both explicit receipts: no-argument success/code/capture completeness and array-overload absence. Full environment, command, hashes, output and capacity snapshots are in `attempt-06/evidence/`.

The array-overload assertion control is attempt 05. It deliberately inverted the expected `ErrorFunctionNotFound` match. Cargo exited 101; libtest reported 0 passed / 1 failed; the panic included the exact unresolved signature `run (&str | ImmutableString | String, alloc::vec::Vec<rhai::types::dynamic::Dynamic>)`. The outer wrapper also returned 1 because its grep expected Rust's assertion formula while `assert!` emitted the custom diagnostic. This is a valid assertion RED, not a product failure or successful runner status. The original source hash, deterministic mutant hash and classification are recorded in `attempt-05/evidence/`.

The no-argument wrong-expectation control is retained in attempt 04: it reached the deliberately inverted success assertion after running `/bin/true` (Cargo 101, 0 passed / 1 failed). That attempt's restored command then hit a Rhai parser error because array literals are disabled under `no_index`; it is not accepted as the overload GREEN. The final host-Scope input correction and accepted GREEN are attempt 06. Attempt 03's missing lock-path preparation stop and all unsuccessful wrapper statuses are preserved rather than relabeled.

## Resource custody and remaining scope

Each actual Cargo invocation used the existing `tools/run_scoped.py`, an absent owned session scope under `/root/.local/share/agent-builds/rhai/`, explicit `TMPDIR`, one Cargo job, private `AGENT_RUNTIME_DIR/target` and `AGENT_RUNTIME_DIR/cargo-home`, and a source copy inside that runtime. Required evidence was exported outside the runtime. The runner removed its runtime; the caller retired only the exact empty owned session scope. No Rhai build remains active and no scope remains. Shared capacity and the unrelated Tauron build state are retained in per-attempt evidence; no foreign process was stopped or modified.

Attempt 02 remains valid and separately accepted for the named scalar `run(program, options)` behavior, child-file readback, cwd, captures, exit status, and absent `run_raw` under `testing-environ,sys,no_index,sync,unchecked`. It was not repeated. Its production-module hash and lock match this current candidate. This proof combines only those unchanged, applicable facts with the new default-profile no-argument and array-overload evidence.

Independent combined review: PASS for this named Linux base-profile R3 package; see `combined-review.md`.
