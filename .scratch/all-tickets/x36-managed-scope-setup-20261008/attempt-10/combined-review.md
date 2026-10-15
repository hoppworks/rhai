# Combined independent review - Darwin X36 kernel setpgid denial (attempt 10)

## Standards

PASS. Attempt 10 uses the real Darwin kernel and a public Rhai Engine with the registered sys package; the run/spawn operations execute real child processes. The RED verifies assertion sensitivity by disabling only the test denial seam, allowing the command to run and reaching the intended public error assertion. Restored GREEN records exact run/spawn PID cleanup, group absence, retired reservation, and no marker. Independent post-run readback confirms the same PIDs and groups absent after runner exit; export hashes validate, runner status is 0, and the owned runtime and scope were removed.

## Spec and acceptance

ACCEPT only `managed_scope_kernel_setpgid_denial_cleans_created_group` on Darwin arm64/macOS 27.0.1, Rust/Cargo 1.93.0, `testing-environ,sys`. The evidence binds attempt 10's source archive, Cargo.toml, Cargo.lock, test selector, script, toolchain, host, and features through `inputs.json`, environment, mutation/restoration hashes, logs, and the verified 16-entry export manifest. RED is 101 at the expected public setup-failure assertion when the test-only denial seam is disabled; restored source GREEN is 0. Run and spawn both show `pid=ESRCH`, `group=ESRCH`, `reservation=retired`, and `marker=absent`; independent after-run readback confirms exact PIDs 71596 and 71597 and their groups are absent.

Whole-file source identity has changed: attempt 10's restored `unix.rs` is SHA-256 `55dc5ad528ad2b4fd56d3fcdd42f92af0b30bf3f96db37c476ee31320dcba713`, while current `unix.rs` is `7abd009fcccf9ad81a5a60de4c5978177243c66c3a73118d44aa99b1bcdcc234`. The delta is not comment-only: it adds the stdin WriteZero/BrokenPipe pump behavior and its helper/unit test. It is outside this selector's path: the byte-identical setup-failure helper/test span from `fn assert_managed_scope_setup_failure` up to `fn run_inner_inherited_pipe_holder_case` is 10,141 bytes with SHA-256 `69a7585b5e98cd41ffe0df76a810aaa18db05399498d4358a9678060e62a647e` in both files. The test options set no stdin, and setup failure occurs before the child enters the input-pump path. The product diff has no other hunks. Thus this source change does not invalidate the named evidence.

Other Darwin setup-failure points, platforms, features/toolchains, and X36 overall remain open. This does not close Ticket03 or imply a broader process-package acceptance.

## Binding rules

Agent-skills HEAD `d6024420e9a829e97e1857ae3a853d832348c83f`; central AGENTS SHA-256 `fa1c6e656d0f1d3e9c3c7596cf911203ae27094d38be5484d7a385ae11a3f65b`; project AGENTS SHA-256 `37f95ff6a80be28bc21e9e523674f46f3ce6153a1923c708b86333bf21bba37c`.
