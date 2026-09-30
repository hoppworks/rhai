# Complete streaming file documentation and runnable example

Role Worker, one bounded phase4 deliverable. Own assigned worktree
/Users/hoppworks/projects/rhai-file-handle-docs task/file-handle-docs at90c40989.
Read AGENTS.md, docs/sys-package-plan.md phase4, accepted file source/tests and
.scratch/all-tickets/file-handle-open-review.md + file-handle-reads-review.md.
Implement documentation only for completed streaming files: README section,
CHANGELOG entry and new examples/sys.rs. Familiar nine open modes, default w+
creates without truncation, read/write grants checked before mutation, clones
share cursor/drop state, no public close, positive reads actual up-to-N, omitted/
zero toward EOF under cap, negatives rejected, strict UTF-8 consumes captured
bytes before error, max_file_read default8MiB hostzeroempty, checked Engine caps,
unchecked hostcap and no_index omission. Whole-file APIs differ; do not conflate.
Keep platform/MSRV/release gates honest. Do not change production source/manifest
unless registering required-features=sys for the example is necessary to preserve
default compilation. Keep no_sys example fallback if that is project convention.

Example must use unique owned temporary directory, guard cleanup on failure,
real SysPackage registration and actual script open/write/seek/read with independent
host readback assertion. Runnable Cargo example proving final output, not a snippet
claim. Restrict to string APIs to remain no_index-compatible. No environment
mutation, processes, shared files or net behavior. Script construction/paths use
safe scope binding. English deliverables, configured human author, no attribution.

Record actual start and30-active-minute limit including coordinator review;
scoped runner python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py
--timeout900 -- <command>. Private source copy/CARGO_HOME/TARGET_DIR/TMP, jobs2,
<=2GiB build tree, serial <=4 owned fixturefiles/handles; record actual measurement
rather than peak inference. Reuse build within one invocation for applicable
sys and sys,no_index example runs and wrong host-payload assertion control if
new example verification needs it. No redundant full feature suite. Export proof,
commands and cleanup before exit; no installs/credentials/remote writes/merges.
Commit source/docs atomically; send exact ref and proof paths. Stop on hard bounds,
contradictions or2 consecutive launches without diagnosis/closed check.
