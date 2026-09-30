# File open and cursor acceptance

Candidate source 2626acc0a8a7280afd3fd8dfa3e8a8f9d1649766 and test correction
62f27ac31663bc68ca88a8f7d42b9113bf1f244e are integrated locally in 260ac238.
Both changed Rust files and the final four-line reopen assertion were independently
read in full. OCR deterministic selection resolved both files and their rules,
with zero skipped files. No remaining source finding in this slice.

The sole Expert source answer at
/Users/hoppworks/projects/rhai-file-handles/.scratch/file-handles/escalations/01-file-open-api.answer.md
confirms cap-std opening and conversion preserve authority without reopening paths.
Mode-specific read/write authority precedes OS access; clones share the locked
file and cursor. Source preserves final-owner drop, checked counts, negative seek
clamping and the no-index blob omission. No explicit close or reads are accepted.

Strict macOS proof and raw logs remain at
/Users/hoppworks/projects/rhai-file-handles/.scratch/file-handles/:
proof.md, full-sys-fs-final.log, full-sys-fs-sync-no-index-final.log,
false-green-final.log and storage-final-drop.txt. Final affected suites pass 27/27
with testing-environ,sys,metadata and 18/18 with additional sync,no_index.
Real Engine scripts exercise all modes, denial without mutation, shared cursor,
actual write counts and default create/no truncate. Independent host readback
checks byte content. After script handle drop, another evaluation reopens and
writes, followed by independent host readback. This proves reopen behavior,
not an independently measured kernel descriptor close. The wrong host payload
expectation fails. Final proof includes the final reopen test change.

The final runtime /var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-3wb1vvb4
was independently confirmed absent after scoped cleanup. Observed storage
306532 KiB is an end measurement, not peak. The full parallel suite's simultaneous
fixture count was not measured; do not claim proof of its sixteen-resource cap.
Functional acceptance does not imply historical resource-compliance measurement.
Future suites must serialize fixtures when using that cap.

The owned worktree is retained because its untracked private evidence is still
needed; only source/tests were merged. No remote publication. Streaming reads,
allocation, release feature coverage, minimum toolchains and native Linux/Windows
proof for this new API remain open.
