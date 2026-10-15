# Independent combined review - X37 Linux sync/unchecked, attempt 01

Rules freshly loaded from lllm:
- agent-skills HEAD: `d6024420e9a829e97e1857ae3a853d832348c83f`
- central `AGENTS.md` SHA-256: `fa1c6e656d0f1d3e9c3c7596cf911203ae27094d38be5484d7a385ae11a3f65b`
- central common rules SHA-256: `989dcc707a9e561c5f3fab7a8a973bef3fd39a452a06476f928cf32885fe8c77`
- project `AGENTS.md` SHA-256: `37f95ff6a80be28bc21e9e523674f46f3ce6153a1923c708b86333bf21bba37c`
- `mattpocock-code-review/SKILL.md` SHA-256: `a9b6618b3c16759ddedf3e36b774cd0d76ee3fd122bbf3978c2166acad9df645`
- `build-efficiently/SKILL.md` SHA-256: `58f676b48691ea2ed476f67f13ef68aedcdb73cd4cabf13925db1927c9ccaf04`

## Standards

PASS for the named Linux X37 `sync,unchecked` evidence slice, with the recorded runner and capacity caveats below. The package binds to revision `c94a7a5f830e9589bb79297cebb1756c3a57e39f`, Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, default profile, and `testing-environ,sys,sync,unchecked`. Cargo.toml, Cargo.lock, Unix process source, and test source hashes match the recorded attempt inputs and RED/GREEN source receipts. The lock hash matches the preserved lock named in the evidence. The package export manifest verifies completely.

Cargo RED is 101 at the deliberately inverted final sentinel-live assertion; restored Cargo GREEN is 0 with 1 passed. Preserve the outer `run_scoped` status as **1**. The included original post-run parser requires PID and ESRCH fields to be adjacent, but the real cleanup line includes `status=...` between them. The corrected replay helper is now included and byte-for-byte matches the already-reviewed base-profile helper (SHA-256 b1402597985d4ae7016bed52397b4778efd6db34a13aed959a8a78a5ede71901). Its saved replay output exactly matches the recorded leader, worker, leaf, managed PGID, sentinel PID, and sentinel PGID absence; the updated package manifest verifies. The original run-scoped status remains 1 and is not called successful. The saved output records the leader, worker, leaf, managed PGID, sentinel PID, and sentinel PGID absent, while cleanup readback records the runtime and owned session scope removed. The runner's status remains 1 and is not called successful.

The pre-run snapshot shows an unrelated Tauron Cargo/rustc build active and only about 928 KiB of swap free. Rhai used one job and an isolated source, Cargo home, and target; both Cargo phases completed and their statuses/logs are present. This concurrent load does not invalidate the completed test result, but it is a capacity deviation and argues against another heavy run until the host is confirmed idle.

## Spec / acceptance

PASS for this single Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, default-profile `testing-environ,sys,sync,unchecked` X37 row. The logs show nonfinal clone drop preserving leader/worker/leaf, final clone drop removing all three while the unrelated sentinel remains live at the API boundary, and explicit sentinel cleanup. The saved corrected readback confirms absence of all exact recorded process and group identities. The intentional assertion-only RED establishes sensitivity to the false expectation.

This accepts only `managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not` for that named feature/profile/platform slice. It does not accept other X37 profiles, platforms, or broader Ticket03 behavior.
