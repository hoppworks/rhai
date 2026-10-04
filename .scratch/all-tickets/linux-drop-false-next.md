# `kill_on_drop(false)` final-drop criterion: next step

## Criterion and source coverage

Ticket 03 requires retained ownership after the last public client and Engine are dropped: captured output must continue draining, the child must remain alive until fixture release, then exit and be reaped; managed scope must also retire its owned group without harming unrelated processes.

Accepted source baseline `523608648dcae99bc0f6b46eaf2bb91fa4ecc752` already has two focused Unix public-Engine tests in `tests/sys_process.rs`:

- `direct_spawn_kill_on_drop_false_preserves_child_and_capture` runs an allowlisted self-executable fixture under `kill_on_drop(false)`, drops the only `Dynamic` handle and Engine, challenges the still-live child, confirms it has not completed, releases it to write 512 KiB to each captured stream, checks its completion record, waits for exact PID absence, and runs bounded fixture cleanup.
- `managed_spawn_kill_on_drop_false_preserves_group_until_leader_exit` likewise drops the client and Engine, checks leader/worker/leaf remain live and answer a challenge in the owned group while a distinct sentinel stays live, then releases the leader and checks all three exact PIDs disappear while the sentinel remains alive; it reaps the sentinel.

Both are gated by `all(unix, not(feature = "no_index"), not(feature = "no_float"))`. They are real self-executable process fixtures, not mocks. The direct test asserts the captured-byte counts through the fixture completion record; the managed test exercises retained group ownership and exact member cleanup but does not itself assert captured byte counts.

## Existing proof and applicability

The retained macOS process-refresh run executes both named tests and records their challenge, output, ESRCH, and fixture-cleanup receipts. Its test-file hash is `66131f8d5438ada49a309b2774f0f31144aba150146e2927f6da55c902d6bec2` (commit `e5b55460ff8f94dba5d35564ced640e6ac8ea3ee`); baseline 523's whole test-file hash is `5836af855f7410213367786e195c0b9b09c0da005cde37244cfa241baf59c4cb`. The file grew, but comparison shows the two test bodies are byte-identical between e5 and 523, as are their relevant direct-drop branch, managed leader fixture, script builder, process identity helpers, and sentinel helper. The production dependencies `src/packages/sys/process/unix.rs`, `process.rs`, `config.rs`, `mod.rs`, and `Cargo.toml` are byte-identical across the commits. Thus the macOS run remains applicable to those unchanged behaviors; the whole-file hash difference alone does not invalidate it.

The macOS log shows the direct child alive after final drop, both 524288-byte stream writes complete, and exact child ESRCH. The managed log shows leader/worker/leaf live and responsive after final drop, all three exact PIDs absent after leader release, and the unrelated sentinel still live until its explicit cleanup. Independent native81 host readback confirms direct child PID 53149 and sentinel PID/group 53168 absent, all recorded checked groups empty, and the runtime absent. That independent readback does not list managed PIDs 53169–53171 or their group 53169; those disappearances are asserted by the test log, not separately repeated in the host readback.

The retained Linux process IO89 and options90 evidence is for other named tests, and the final-drop102 evidence runs a different managed final-clone-drop test. A targeted search of retained output finds neither of these two test names in those Linux records. Native109 is exact baseline523 but does not list these cases. Existing evidence therefore closes the direct and managed behavior on macOS, while exact Linux OS execution and independent managed-member/group readback remain unproven.

## Narrow remaining check

Do not rerun macOS solely because the surrounding test file changed. For Linux-specific ticket coverage, reuse these exact tests and the accepted Linux bounded custody route at baseline523 (`--locked`, `testing-environ,sys`, neither `no_index` nor `no_float`). Capture original output and add independent host readback of the direct PID plus managed leader/worker/leaf PIDs, their owned group, and the sentinel, then confirm fixture/runtime/scope cleanup. No fixture or production change is indicated by this comparison. Windows remains a separate ticket03 platform criterion.

No build, remote action, or native run was performed for this diagnosis. Existing macOS evidence is reusable for its platform and unchanged source dependencies; Linux and Windows coverage remain separate.
