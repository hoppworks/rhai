# Independent combined review - unsupported feature gates, attempt 01

Rules freshly loaded from lllm:
- agent-skills HEAD: `d6024420e9a829e97e1857ae3a853d832348c83f`
- central `AGENTS.md` SHA-256: `fa1c6e656d0f1d3e9c3c7596cf911203ae27094d38be5484d7a385ae11a3f65b`
- central common rules SHA-256: `989dcc707a9e561c5f3fab7a8a973bef3fd39a452a06476f928cf32885fe8c77`
- project `AGENTS.md` SHA-256: `37f95ff6a80be28bc21e9e523674f46f3ce6153a1923c708b86333bf21bba37c`
- `mattpocock-code-review/SKILL.md` SHA-256: `a9b6618b3c16759ddedf3e36b774cd0d76ee3fd122bbf3978c2166acad9df645`

## Standards

PASS for the four executed Linux host-target negative gates. The package binds to project revision `a98f5ce47c152900002904a45b060405ee722abb`, Cargo.toml SHA-256 `cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e`, and recorded `sys/mod.rs` / `net/mod.rs` hashes. Cargo.lock was copied from the named preserved source; its SHA-256 is `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, matching the package's expected value. The full package export manifest verifies.

The invocation records installed Rust/Cargo 1.77.2, target `x86_64-unknown-linux-gnu`, one Cargo job, and a private scoped runtime. The run-scoped command exited 0; cleanup readback says both runtime and owned scope were removed. No toolchain installation was attempted. The evidence marks the WASM target absent, so sys-only, net-only and combined sys+net WASM gates remain unverified.

## Spec / acceptance

PASS for these exact four Linux host-target feature combinations only:
- `sys,no_std`: exit 101 and the intended sys-requires-std diagnostic.
- `net,no_std`: exit 101 and the intended net-requires-std diagnostic.
- `sys,net,no_std`: exit 101 with both intended sys- and net-requires-std diagnostics present.
- `sys,no_object`: exit 101 and the intended sys-requires-object-maps diagnostic.

The matcher is fail-closed on the targeted sys/no_object diagnostic: a private source-copy control removes that single guard, and the control log lacks the diagnostic and is rejected by the matcher despite other compiler errors. The source is restored in the private copy, its recorded hash is checked against the original, and the restored sys/no_object run again produces the intended diagnostic. These records support the compile-time rejection gates, not broad platform or runtime acceptance.

WASM rejection gates are explicitly unverified because the target was not installed. No WASM result is inferred from the Linux checks.
