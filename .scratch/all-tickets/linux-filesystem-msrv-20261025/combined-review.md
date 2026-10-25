# Combined source and acceptance review

## Verdict

The Linux filesystem MSRV package conforms to the scoped F19/F22 acceptance contract at the bound source and lock inputs. The saved evidence supports acceptance of this Linux/Rust 1.77.2 row only. It does not close the broader tickets, certify other operating systems, or establish release-matrix acceptance.

## Standards

No actionable standards finding. The package keeps proof code and artifacts under its scoped ticket directory, uses an owned scoped runtime for Cargo outputs, preserves original logs, records cumulative consumption, and reports cleanup read-back. No product source or test file was changed in this worktree; the test mutations were made in the disposable source copy and the final source pins match the original archive.

## Spec and correctness

- The source archive SHA256 is `d6a01eff9570209794d05bace0276da158a06560d1bbafa955d2bcba854e685c`; the lock SHA256 is `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. Both match `binding.json`. All six bound source pins match `result.json`; the prior archive inspection found every archived tracked file identical to base `fbb0af29e1a54922875e673bb27e17ed9b102bf0`.
- The evidence records Linux `x86_64-unknown-linux-gnu`, rustc/cargo 1.77.2, and successful locked metadata resolution. The non-UTF-8 filesystem prerequisite is true.
- All three assertion-only controls exit 101, print their distinct control marker, and show an independent `test result: FAILED. 0 passed; 1 failed` summary. The names are independently visible as failed test lines. These controls establish sensitivity for F19 and both F22 behaviors.
- The restored full `sys_fs`, `sys_policy`, and `sys_env` regression executables pass for all four profiles: base, `sync`, `unchecked`, and `sync+unchecked`. The named F19/F22 regressions pass in each `sys_fs` run; no non-UTF-8 fixture skip is recorded. Fresh artifact flags are false for these builds, and executable hashes are recorded.
- `result.json` reports cumulative totals of six Cargo builds (including the earlier pre-rustc source-resolution failure), two metadata queries, three RED tests, and twelve GREEN target executions. The count scope now names both preparation attempts.
- Cleanup read-back records the exact session scope absent and the runner runtime retired. The result records fixture temp absence and parent cwd/environment preservation.

## Acceptance limits

This evidence verifies the scoped native Linux/Rust 1.77.2 behavior for F19/F22 and the specified `sys_*` regression targets only. It does not verify macOS or Windows, other feature combinations, performance/release behavior, or broader ticket closure. Earlier preparation stops were dependency-resolution failures before rustc or assertions and are preserved separately; they do not count as product failures or acceptance.

## Final documentation and cleanup delta

The final `proof.md`, `contract.md`, and `docs/sys-package-plan.md` wording agrees with the reviewed result and keeps the claim limited to the native Linux/Rust 1.77.2 four-profile F19/F22 row. The record correctly distinguishes the two pre-rustc dependency-resolution stops from the passing assertion and regression evidence, and the cumulative totals are consistent.

The retirement manifest contains 108 host-staging file hashes, including the exact source archive and lock hashes. `input-retirement.json` reports all 108 host staging files retired, both local transfer inputs absent after hash verification, accepted evidence preserved, and all three exact session scopes absent. The runtime cleanup read-back independently records the final scoped runner runtime retired. No accuracy issue found in this documentation/cleanup delta.
