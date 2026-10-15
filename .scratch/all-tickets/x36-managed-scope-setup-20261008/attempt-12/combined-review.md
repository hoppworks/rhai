# Combined independent review - X36 Linux unchecked (attempt 12)

## Standards

PASS. The one-line change gates only `Engine::set_max_string_size`, which is unavailable under `unchecked`, while keeping the process-output-cap test and its `SysConfig::max_output` assertion compiled. The selected X36 test uses the public Rhai Engine and registered sys package with real Linux children. Attempt 12 uses the scoped runner, bounded phases, a private runtime, independent PID/group readback after runner exit, and exact owned-scope retirement.

## Spec and acceptance

ACCEPT only `managed_scope_kernel_setpgid_denial_cleans_created_group` on lllm Linux x86_64, Rust/Cargo 1.77.2, features `testing-environ,sys,unchecked`, at project revision `ffeab7c7958e69ebada7064aa9d0ca31f84edb13`.

Attempt 11 stopped at compile with E0599 because the test helper called `Engine::set_max_string_size`, absent under unchecked. Its status 101 is not a product RED and is excluded from acceptance. Attempt 12 adds only the cfg gate shown in `source-delta.patch`. Its source manifest binds Cargo.toml SHA-256 `cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e`, lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, and restored Unix source SHA-256 `2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6`; mutation/restoration hashes and the exported evidence manifest verify.

The expected mutation disables only the test kernel-denial seam. RED exits 101 at the expected public setup-failure assertion when the command runs. Restored GREEN exits 0 and passes 1/1; both public `run` and `spawn` report the kernel denial, no marker execution, retired reservation, and exact child PID/process-group absence. In-run and post-run readbacks confirm PIDs 2031932/2031934 and their groups are absent. The outer runner exits 0; cleanup records runtime absence and empty session-scope removal.

No broader X36, other feature, OS, toolchain, or Ticket03 acceptance follows.

## Binding rules

Agent-skills HEAD `d6024420e9a829e97e1857ae3a853d832348c83f`; central AGENTS SHA-256 `fa1c6e656d0f1d3e9c3c7596cf911203ae27094d38be5484d7a385ae11a3f65b`; project AGENTS SHA-256 `37f95ff6a80be28bc21e9e523674f46f3ce6153a1923c708b86333bf21bba37c`.
