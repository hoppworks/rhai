# Independent combined review - X37 Linux base profile, attempt 01

Rules loaded for this review: agent-skills HEAD `d6024420e9a829e97e1857ae3a853d832348c83f`; central `AGENTS.md` SHA-256 `fa1c6e656d0f1d3e9c3c7596cf911203ae27094d38be5484d7a385ae11a3f65b`; project `AGENTS.md` SHA-256 `37f95ff6a80be28bc21e9e523674f46f3ce6153a1923c708b86333bf21bba37c`; `mattpocock-code-review/SKILL.md` SHA-256 `a9b6618b3c16759ddedf3e36b774cd0d76ee3fd122bbf3978c2166acad9df645`.

## Standards

PASS for the narrowly scoped evidence package. The recorded invocation is Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, default profile, `testing-environ,sys`, and the named integration test. Recorded source hashes match the input manifest. The preserved lock at `.scratch/all-tickets/linux-x35-direct-managed-20261015/attempt-02/source-Cargo.lock` hashes to `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, matching both the expected and actual lock readback in this package. The evidence records the owned runtime and session scope as absent after export.

The outer `run_scoped` status is **1**, and the script status is **1**. They are not represented as successful. The saved runner log attributes this to the old post-run parser's overly strict cleanup-line pattern. The actual log places `status=...` between the sentinel PID and `esrch=true`; the corrected replay parser accepts that intervening status field. Its saved output confirms the exact leader, worker, leaf, managed PGID, sentinel PID, and sentinel PGID absent. The original outer-runner status remains 1.

## Spec / acceptance

PASS for this named X37 Linux base-profile slice only. The RED log exits 101 at the deliberately inverted final sentinel-live assertion after independently recording all managed members absent and the unrelated sentinel live. The restored GREEN Cargo status is 0 and reports 1 passed, 0 failed. Its readbacks show the nonfinal drop leaves leader/worker/leaf live; final drop removes all three while the separate sentinel remains live at the API boundary; teardown then records sentinel cleanup and ESRCH. The corrected saved post-run replay confirms absence of the exact recorded process and process-group identities.

This supports acceptance of `managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not` under the recorded Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, default-profile `testing-environ,sys` configuration. It does not convert the original runner status to green, nor accept other X37 profiles, platforms, or broader Ticket03 behavior.
