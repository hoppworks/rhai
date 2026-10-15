# Linux X36 sync-feature kernel-denial slice (2026-10-15)

## Scope

Exact selector: `managed_scope_kernel_setpgid_denial_cleans_created_group` in `src/packages/sys/process/unix.rs`. Platform: lllm Linux x86_64/Bazzite 44. Toolchain: Rust/Cargo 1.77.2. Profiles: checked `testing-environ,sys,sync`; unchecked `testing-environ,sys,sync,unchecked`. Integrated source revision: `0981631785e9e2c2d485544b24d165a3bc21ab0c`.

## Results

The checked-sync expected RED was preserved from invocation 2 and is bound to the current checked GREEN by exact revision, source SHA-256 `2eee89d216ab1edfab6e56b0e6f056195a3708b888395b9429c367412add25f6`, canonical lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, selector and mutation recipe. Cargo exited 101 at the intended public “must not run the program” assertion after the test-only kernel-denial seam was disabled. No mutated-source hash was captured for that invocation; this provenance limitation is retained in the combined review.

The corrected bounded scoped run produced checked-sync GREEN 1/1, unchecked-sync RED 101 at the same assertion, and restored unchecked-sync GREEN 1/1. Both GREENs prove both public `run` and `spawn` fail closed on actual kernel `setpgid` EPERM, marker files remain absent, setup reservations retire, and exact child PID and group are independently absent after the runner. Outer runner status is 0. Source restoration hash matches the archived revision. The private runtime was removed, all three exact owned session scopes are absent, and the foreign Tauron build was preserved.

## Preparation history and limits

`attempt-01/preparation-stops.md` records two earlier failures: invocation 1 stopped before Cargo because the checkout has no tracked Cargo.lock; invocation 2 produced valid checked-sync RED but failed to restore because `git show` was invoked inside a `git archive` copy without `.git`. Independent read-only diagnosis found the complete path defect. The corrected invocation saves the archived source privately and restores by copying that backup; no preparation wrapper was added.

Combined independent review: `attempt-01/combined-review.md` (PASS). Acceptance is limited to this selector and the two named Linux sync profiles. Other setup failure points, platforms, toolchains, feature combinations and Ticket03 remain open.
