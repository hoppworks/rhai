# Second affected recheck of the same Darwin package

Immutable helper/provenance revision: `4c4a81e0551f6e6d5c56112de7febda0101ce27f`, compared with `8b9740de8e4493c78320293d3a07599672f22484`. **F3 is corrected at source level. F4 has a material diagnostic regression and remains unaccepted.** A separate stage/scope contract mismatch also blocks following the prepared launch instructions.

Rules/roles revision remains `958a4538b0191c53f2ccb2cd00d96c15045fbf68`; unchanged applicable rules were reused. Owner was clean. No descendants, native APIs/fixtures, Cargo, toolchain setup, process queries, controls, measurement85, source edits, push or merge occurred. This is the same combined review's affected recheck; no broad review was repeated. OCR discovered seven changed files, four reviewable and three manually covered exclusions; all seven were covered, including the original RED JSON and eight-category GREEN receipt. The unchanged cleanup module was loaded only as a pure source-test dependency.

## Remaining material findings

| Finding | Severity | Exact location | Effect |
|---|---|---|---|
| F4 diagnostic loss invalidates F1 rejection in the new execution path | High | `.scratch/all-tickets/check-current-darwin-sys-net-behavior.py:601`–`604`; affected frozen producer `tests/sys_fs.rs:731` | The helper preserves non-header stderr diagnostics in `parser_input`, but computes coverage from `parser_core`, which excludes them. F19 uses `eprintln!` for EILSEQ and returns normally: libtest stdout contains its `ok` and a complete passing summary, while stderr contains the only skip marker. The new derived coverage accepts that output, reports no skips and counts `test_non_utf8_file_name` as completed. Aggregate acceptance can therefore falsely accept F19 and its affected rows. |
| Prepared stage/scope names disagree with helper validation | Medium | helper `SESSION_ID` at `.scratch/all-tickets/check-current-darwin-sys-net-behavior.py:27`, enforcement at `216`–`219`; contract stage/scope paragraph | The revised contract prescribes `current-darwin-sys-net-behavior-2f795ece-20261002` for stage and build scope. The helper still requires `current-darwin-sys-net-behavior-a2d7a8c2-20261002` for both. Following the new contract fails stage/runtime validation before native behavior. Actual source pins are updated; this is a naming-contract mismatch, not evidence of wrong archive contents. |

The F4 reproduction uses two successive complete stdout libtest blocks and stderr headers in `net_reads,sys_fs` order, deliberately different from the selected target tuple. Adding the exact EILSEQ diagnostic to stderr yields `coverage_found=true`, `skipped_tests=[]`, and F19 among completed named tests. Feeding the exact preserved `parser_input` to the existing `positive_test_coverage` instead rejects that same output and marks F19 uncovered. Thus the existing skip classifier still works, but the new execution path omits its required diagnostic input.

This explicitly invalidates the prior accepted F1 EILSEQ rejection **for the new derived-stream path**. Missing names, duplicate/incomplete blocks, exact named inventories and other F1 conclusions remain applicable where unchanged. The affected acceptance includes F19 in baseline, sync, i32/no-float, unchecked and f32 `sys_fs` rows; no-index rows exclude that test. Any status-zero EILSEQ row must retain its other completed tests, continue later independent rows as designed, and remain unaccepted. A file containing a skip diagnostic is insufficient if the coverage calculation does not consume it.

The owner GREEN's EILSEQ injection puts the marker inside stdout. That verifies a different shape from frozen `eprintln!`. Both the initial combined review and first affected review preserved this source fact; moving to separate streams needed an actual stderr regression. This is the second failed F4 correction. Retain both failures and require the instructed fresh single root-cause escalation; this review performs no next patch or new advisory chain.

## Valid corrections and preserved conclusions

F3 now obtains the two verified spellings of the exact owned `real` directory and configures `fs_root` with the `/var` spelling. Absolute first-form reads match `root.given`; second-form reads match `prefix_alias(root.given)`. Each relative suffix is `a.txt`, so it passes the relative escape check. The retained canonicalization assertions establish exact owned-host equivalence before Engine construction, strings are distinct, writes are denied, and host bytes are read back. The unchanged nested-prefix test likewise configures roots with supported prefix spellings. This closes the identified source policy mismatch; actual host canonicalization, capability opening, Engine behavior and readback remain unverified until native acceptance. No files are created outside the central runtime by this fixture.

F4 now correctly associates clean successive stdout blocks with stderr target headers, validates exact selected headers and named inventories, and truthfully labels derived target order rather than captured chronology. Independent pure checks accept a clean multi-target reversed-selection-order case and reject missing/duplicate headers, missing named tests, incomplete blocks and extra summaries. Separate raw originals are retained. These improvements stand, but they do not close the stderr skip regression.

F2 source conclusions from repair8b974 remain applicable: fail-closed unknown process/path queries, stable PID/start checks, sampled descendant identities, owned-group enumeration and exact absent-runtime/empty-real-scope checks. The eight owner categories pass independently in the immutable snapshot, including unchanged mocked cleanup categories. No claim about actual disappearance, resource peaks or native cleanup follows.

Status/coverage-derived summaries and intentional continuation of status-zero incomplete rows remain unchanged. Compiler/examples accepted proof retains its original applicability; existing Linux behavior proof remains Linux-only and unaffected by these macOS-gated test changes. No proof copies were made merely to change review sessions.

## Provenance and receipts

Source/test freeze: `2f795ecee8edd6ddf348f382e5397cc6e348ad37`. Independently recomputed source tar SHA-256: `43c8b8e43a2bcd3e74dd0be3d60a0dea2eab50eb5bfe65cc736684631523d52b`. No source/test/manifest changes exist between this freeze and helper4c4a. Helper/test/contract/prep pins agree on source and digest. Compatible lock pin remains `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. Staged bytes and all Darwin outcomes remain future dispatch checks.

New originals are retained once at `/tmp/current-darwin-sys-net-second-recheck.6h16fg12/`:

- `review.md`, `revision.json`, `affected.diff`, `snapshot/`, `ocr-preview.json`, `ocr-rules.json` record immutable source coverage and provenance.
- `affected-regressions.py`, `affected-regressions.stdout`, `affected-receipts.json` record independent eight-category readback, clean/negative split-stream cases, actual EILSEQ stderr false acceptance, the existing classifier's rejection of the full preserved parser input, lexical F3 routes and stage/scope mismatch.
- `eilseq-model.stdout`, `eilseq-model.stderr`, `eilseq-model.parser-input.txt` are the exact minimal actual-producer stream shape, with injected data and no native run.
- `prepared-source-tests.stdout` records eight passing source categories. The first local harness attempt omitted the unchanged cleanup dependency; it was added from immutable4c4a and rerun. This was review snapshot setup, not an implementation correction or native launch.

Original review/receipts remain unchanged at `/tmp/current-darwin-sys-net-source-review.CnOZQa/` and their one root-retained copy `/Users/hoppworks/.codex/worktrees/all-tickets-continuation/rhai/.scratch/all-tickets/current-darwin-sys-net-source-review/`. First affected review/receipts remain unchanged at `/tmp/current-darwin-sys-net-affected-recheck.vmrgou7y/`. No original artifacts were rewritten or copied into this recheck.

Next action belongs to root: preserve the two failed F4 corrections and prepare the required root-cause escalation, including actual stderr EILSEQ shape and stage/scope inconsistency. No native acceptance or dispatch readiness is granted.
