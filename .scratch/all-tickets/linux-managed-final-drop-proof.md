# Linux managed final-clone drop — native102 evidence

Status: native run and collection complete; final combined independent acceptance is pending. This is a partial criterion record, not closure of tickets 03 or 06.

## Frozen inputs

- Source: `61b3739a785503d6a74d769b30c218b82f5dd249`; source archive SHA-256 `47361b26246a615e74d6d5d774729acd4380f136ac553723f028ac6605274c24`.
- `tests/sys_process.rs` SHA-256 `d0a8842cc6be749a98ab7786ae66fdeca4a0488ad48aacfc88b24d48bdc660d8`; test `managed_spawn_final_clone_drop_closes_group_under_fixture_reaper`.
- Compatible `Cargo.lock` SHA-256 `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`; process contract SHA-256 `1d8a61b5dffefc4f5891d12ed2b19b438637e4e752607e68c6495f96eb553d41`.
- Recipe inputs: proof helper `b94913dd6e7baaf8140c24d1a609086ae0367a62f1c2c30277ccff5393031e99`; stage `68dcc9ba2e98d5234901701e1e2d5061dbcf14c7ad0faeee869a6fd8ff28b869`; launcher `bc6641e8ccb33fae2fb86468656ef418f0ba893effe0c6f831006fa04b0371ee`; collector `c76a4cec9de2233e311230a26d91c58cf4a0869003c5839e8cd8195b05c0f442`.
- Rust/Cargo 1.77.2, `x86_64-unknown-linux-gnu`, Linux (toolchain reports Linux 44). Selected features were `testing-environ,sys`, with additional `sync,metadata`, `f32_float`, and `unchecked` rows.

## Observable result

The real fixture first cloned the public managed `Child`; dropping the nonfinal clone preserved the leader, worker, and leaf. The final clone drop was separately recorded. A bounded PIDFD observation then saw all three exact identities exit and become absent while the Engine host, fixture reaper, and unrelated sentinel remained live. The fixture independently reaped worker and leaf with wait status 9; its reaper exited successfully. The boundary receipt binds PID/start values and process-group relations, says `exceptional_cleanup_not_started=true`, and records `final_members_live=false`; after the boundary, cleanup verified the host absent, sentinel reaped, and group empty. No public `Child.kill`, wait, or deadline operation substitutes for the final-drop action.

All four exact final-drop invocations passed. The one post-cleanup wrong-control (`require-member-live-control`) exited 101 at the named `managed-final-drop-control require-member-live assertion`, demonstrating sensitivity to the observed closure. Three base-row regressions also passed: managed `Child.kill`, prompt-reaped ordinary success, and the held-zombie boundary. The package therefore contains eight exact test invocations total (seven passing, one intended assertion control).

## Custody and limits

The original native export is preserved at `/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/.scratch/all-tickets/linux-managed-final-drop102-evidence/`. It contains 73 files and five directories, including eight original case-closure records. The collector validated originals read-only, exported the complete package, and recorded source restoration. Fresh independent readback found stage and scope absent and both recorded process groups empty; runner, runtime cleanup, scope cleanup, and outer statuses were 0. The sampled maxima were RSS 973,476 KiB and runtime storage 968,332 KiB, with at most 7 sampled descendants. These are one-second samples, not continuous peaks. Helper elapsed time was 46.78 seconds; limits remained 600 seconds outer, 585 seconds runner, 540 seconds helper including the 30-second export reserve, two Cargo jobs, 16 descendants, and 2 GiB RSS/storage hard bounds.

The proof recipe, launch, stage, and collector inputs are preserved with the originals. Native execution is evidence; the combined independent acceptance review is still pending. Ticket 03's remaining managed deadline/overflow and other lifecycle cases, ticket 06's wider feature/platform/release matrix, and the stopped Darwin/Windows routes remain open.
