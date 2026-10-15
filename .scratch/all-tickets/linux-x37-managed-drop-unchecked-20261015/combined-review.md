# Combined independent review - Linux X37 managed drop unchecked

## Standards

PASS. The test exercises public Rhai managed `spawn` and final/nonfinal handle drops with real Linux processes. It uses an exact separate sentinel process group, bounded liveness polling for the managed leader/worker/leaf, and explicit sentinel reap. No implementation or test-source edits were made by this review.

## Spec and acceptance

ACCEPT only this named Linux x86_64/Bazzite 44, Rust/Cargo 1.77.2, `testing-environ,sys,unchecked` X37 slice: `managed_spawn_final_clone_drop_stops_group_but_nonfinal_drop_does_not`.

Attempt 01 is not product evidence. Attempt 02 binds HEAD `68a6a83af3cced6a0215fa815efc7a79b348873b`, the current test source SHA-256 `ddd5a6259b80647528fc1640f77f2c9f69acd913a20bf84b2a0942d3aec09cbf`, Unix product `7abd009fcccf9ad81a5a60de4c5978177243c66c3a73118d44aa99b1bcdcc234`, and lock `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. The wrong-sentinel-expectation mutation exits 101 at the intended assertion after reporting nonfinal leader/worker/leaf live, final leader/worker/leaf ESRCH, sentinel live, and cleanup. Restored GREEN passes 1/1 with the same lifecycle readbacks. The sentinel's PGID equals its PID and differs from the managed group; it is live at the final-drop boundary and then explicitly reaped by its exact Child handle. Cargo statuses are RED 101 and GREEN 0; outer runner status is 0; the recorded session scope was empty and absent.

This accepts no other feature, OS, toolchain, or X37 behavior, and does not close Ticket03 or the process package generally. No proof.md was present when reviewed; this combined review records the accepted row and its exact bounds.

## Binding rules

Agent-skills HEAD `d6024420e9a829e97e1857ae3a853d832348c83f`; central AGENTS SHA-256 `fa1c6e656d0f1d3e9c3c7596cf911203ae27094d38be5484d7a385ae11a3f65b`; project AGENTS SHA-256 `37f95ff6a80be28bc21e9e523674f46f3ce6153a1923c708b86333bf21bba37c`.
