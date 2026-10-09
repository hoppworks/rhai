# Darwin X29 `unchecked` acceptance

**Accepted scope:** Ticket 03 X29, `shared_child_contract::script_throw_drops_and_reaps_a_live_child`, Darwin arm64/macOS 27.0.1, Rust/Cargo 1.77.2, `testing-environ,sys,unchecked`. This adds one feature/toolchain slice only.

Run metadata binds the exact source revision, test and fixture hashes, lock hash, toolchain, features and command in `run-info.txt`. The source/test SHA-256 is `a8fdc21e73b56bf12c82603c941b7c22b01c942a56d5f649ff2ec98b494c935c`; fixture SHA-256 is `1faf45c57a4fefeaa05683043e064d3485e892887986fef749bedc974230b217`; Cargo.lock SHA-256 is `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.

Cargo exited 0 and reported 1 passed. The real Rhai Engine threw while the child was live; the controller verified a fresh challenge response and `try_wait() == ()`. The wrong-message control was rejected. Independent output recorded controller PID 35507 and fixture PID 35508 absent with ESRCH, production cleanup verified, and the watchdog closure receipt succeeded. Raw output is `cargo.log`; its hash and all run metadata are in `SHA256SUMS`.

The invocation used the scoped runner and its private runtime is absent. The exact owned session scope was verified empty and removed with `rmdir`. The zsh wrapper failed after the test while assigning the read-only special variable `status`, so the outer runner exit code is unknown and is not inferred from Cargo's status; see `runner-status-classification.md`. This is retained as a harness bookkeeping cause, not a product failure. The initial direct invocation also stopped before entering the runner because `run_scoped.py` is not executable; the successful invocation used `python3` explicitly. Neither setup issue reran the test. No build cache or process was retained.

The combined independent Standards/Spec review passed for this exact partial row and confirmed the status limitation does not invalidate the Cargo result, raw behavioral evidence or scoped cleanup.
