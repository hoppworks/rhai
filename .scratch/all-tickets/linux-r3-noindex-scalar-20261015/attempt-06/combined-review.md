# Independent combined review - Linux R3 no_index contract at 42c117e8

Rules loaded from lllm:
- agent-skills HEAD: `d6024420e9a829e97e1857ae3a853d832348c83f`
- central `AGENTS.md` SHA-256: `fa1c6e656d0f1d3e9c3c7596cf911203ae27094d38be5484d7a385ae11a3f65b`
- project `AGENTS.md` SHA-256: `37f95ff6a80be28bc21e9e523674f46f3ce6153a1923c708b86333bf21bba37c`
- `mattpocock-code-review/SKILL.md` SHA-256: `a9b6618b3c16759ddedf3e36b774cd0d76ee3fd122bbf3978c2166acad9df645`

## Correctness

PASS. The working-tree change adds one focused test under `cfg(feature = "no_index")`; no production source changes are present. It calls public Engine `run("/bin/true")` without arguments and checks success, code 0 and complete captures. It injects a real Rhai Array through host `Scope` (avoiding disabled array-literal syntax) and verifies the public Engine returns `ErrorFunctionNotFound` for the array-taking `run` signature. This is directly sensitive to accidental registration of that overload.

## Standards

PASS. The completed package export manifest verifies, includes attempts 03-06 and this review, and the current revision-binding document leads with attempts 05/06 at revision 42c117e8 while explicitly separating attempts 01/02 as historical. Attempt 05/06 receipts bind revision `42c117e84669f4d105b5d76b5f0c07611622708b`, Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, default `testing-environ,sys,no_index`, lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, product source SHA-256 `2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6`, and restored working-tree test SHA-256 `9b031886eb3b4d365664a244e68ab574ef110e3cc7d41efe5f457d0d1fcb1dbe`. The test-only mutation is separately hashed. Attempt 06 records GREEN 0/1 passed and runtime/scope retirement.

Attempts 03-06 retain preparation, test-input, expected-RED, and restored-GREEN history with their receipts. The new current binding makes the accepted base-profile evidence unambiguous.

Attempt 03 is a pre-Cargo lock-path preparation failure. Attempt 04 proves no-argument RED but its corrected GREEN was blocked by using an array literal under `no_index`; this is test-design/setup failure, not product failure. Attempt 05 is the deliberate array-overload RED (Cargo 101 at the intended absent-overload assertion); its wrapper status 1 is the documented custom-diagnostic matcher mismatch, not a product failure. Attempt 06 is the restored-source GREEN (Cargo and runner 0, 1/1). The prior foreign Tauron process was not touched; its appearance is preserved in post-run evidence.

## Spec

PASS for the Linux base-profile R3 behavior only. Attempt 04 supplies a no-argument wrong-expectation control at the same candidate; attempt 05 supplies the array-overload assertion RED; attempt 06 restores the source and passes both assertions. The previous attempt-02 evidence remains a separate, explicitly narrower `sync,unchecked` row for scalar `run(program, options)`, cwd, independent child PID/ESRCH, complete captures, exit status, and absent `run_raw`.

The plan row preserves the five-column schema and scopes the accepted behavior to Linux. The coordinator and proof keep other release targets open. No evidence here accepts other platforms, feature/MSRV combinations, or broader A-F/Ticket03 behavior.

## Acceptance

PASS for the named Linux base-profile R3 behavior. The reviewed logs support acceptance only for Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, default `testing-environ,sys,no_index`: no-argument `run(program)` works and the array-taking `run(program, args)` overload is absent.
