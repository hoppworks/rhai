# Independent combined review - Linux X34 sync/unchecked, attempt 01

Freshly loaded lllm rules:
- agent-skills HEAD: `d6024420e9a829e97e1857ae3a853d832348c83f`
- central `AGENTS.md` SHA-256: `fa1c6e656d0f1d3e9c3c7596cf911203ae27094d38be5484d7a385ae11a3f65b`
- central common rules SHA-256: `989dcc707a9e561c5f3fab7a8a973bef3fd39a452a06476f928cf32885fe8c77`
- project `AGENTS.md` SHA-256: `37f95ff6a80be28bc21e9e523674f46f3ce6153a1923c708b86333bf21bba37c`
- `mattpocock-code-review/SKILL.md` SHA-256: `a9b6618b3c16759ddedf3e36b774cd0d76ee3fd122bbf3978c2166acad9df645`
- `build-efficiently/SKILL.md` SHA-256: `58f676b48691ea2ed476f67f13ef68aedcdb73cd4cabf13925db1927c9ccaf04`

## Standards

PASS for this bounded native Linux profile package. Inputs bind project revision `6af3cae30a233880eafc92c4f742534a926e6a88`, Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, default profile, and `testing-environ,sys,sync,unchecked`. Cargo.toml, Cargo.lock, Unix process source, and test source hashes match the recorded receipts; the lock hash is the preserved X35 lock SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. The package export manifest verifies.

Two pre-run snapshots ten seconds apart both report no active Cargo/rustc process. Memory and disk headroom are ample; swap is low (about 2.1 MiB free) but stable across the snapshots. The scoped runner exited 0, used one job and an owned runtime, and recorded the runtime and owned empty session scope removed. No unrelated process was touched.

## Spec / acceptance

PASS for these two X34 selectors under the exact profile/platform above. The deadline RED uses the private inverted `api_is_timed_out` expectation. Although nested fixture libtest output contains successful `running 1 test` blocks, the outer selected integration test reaches the named `RED_CONTROL` panic after recording `timed_out=true`, incomplete captures/partial output, exact managed leader/worker/leaf PIDFD identities, group ESRCH, host/reaper/sentinel live at the boundary, exact reaping, and explicit sentinel cleanup. Its outer result is 0 passed / 1 failed and Cargo exits 101, as expected.

Restored deadline GREEN and output-limit GREEN each exit 0 with 1 passed. Deadline records timeout-report semantics, incomplete stdout/stderr, markers, PIDFD exit and exact worker/leaf/reaper cleanup. Output-limit records typed output-limit failure, exact 4096-byte prefix, honest incomplete captures, PIDFD exit, host/reaper/sentinel live at the boundary, and exact worker/leaf/reaper cleanup. The post-run verification receipt confirms the required boundary fields for all three phases.

Acceptance is limited to `managed_run_deadline_reaps_group_under_fixture_reaper` and `managed_run_output_limit_reaps_group_under_fixture_reaper` in Linux x86_64/Bazzite 44 with Rust/Cargo 1.77.2 and `testing-environ,sys,sync,unchecked`. It does not close other X34 profiles, platforms, fault rows, or broader Ticket03 behavior.
