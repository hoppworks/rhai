# Darwin split-stream coverage decision

## Decision and evidence boundary

Keep the corrected split-stream target/block association. Repair the coverage boundary by consuming coverage-affecting diagnostics as a separate input, with explicit source-grounded association. Do not feed arbitrary stderr lines back into the libtest structure parser. The acceptance goal is named assertion completion, not a successful Cargo process or a complete libtest summary.

This is source-only analysis of helper revision `4c4a81e0551f6e6d5c56112de7febda0101ce27f` and frozen test/source revision `2f795ecee8edd6ddf348f382e5397cc6e348ad37`. Current global instructions, project `AGENTS.md`, campaign instructions and `references/repair-package.md`, and `config/roles.toml` were read at instruction repository revision `958a4538b0191c53f2ccb2cd00d96c15045fbf68`. The Expert definition calls for independent hard reasoning, a file answer, and a reply of at most 15 lines. No descendants, source changes, native queries/APIs, Cargo, builds, controls, toolchain operations, push or merge occurred. Only this answer was written. No native acceptance follows.

The exact failure is helper lines 601–604: `parser_input` retains stderr diagnostics, but `positive_test_coverage(parser_core, ...)` does not consume them. `tests/sys_fs.rs:731` emits the frozen EILSEQ marker with `eprintln!` and immediately returns. Under the helper's `--nocapture --test-threads=1`, the test can therefore emit an ordinary named `ok` result on stdout while its assertion was never reached. Serial execution within a test executable does not merge the streams.

The original report, reproduction and receipts at `/tmp/current-darwin-sys-net-second-recheck.6h16fg12/` demonstrate exactly this boundary. Two complete stdout blocks correspond to stderr headers `net_reads, sys_fs`, while the requested tuple is `sys_fs, net_reads`. Appending EILSEQ only to stderr leaves derived coverage true and F19 completed. Running the existing classifier on the preserved full parser input instead marks only F19 uncovered. The raw model files were read; they contain real line feeds, not literal escaped newline separators. These are pure modeled streams from the actual producer shape, not a captured native run. I inspected the source and original reproduction; I did not rerun the review harness or claim a new GREEN.

There are three distinct kinds of evidence:

| Evidence | What it establishes | What it does not establish |
|---|---|---|
| Ordered stderr Cargo headers | Reported selected target order, checked exactly once | Chronology between stderr and stdout |
| Ordered stdout libtest blocks, checked against frozen inventories | Named outcomes and summary structure for the derived target association | That every assertion ran despite normal early return |
| Coverage-affecting diagnostics plus frozen producer identity | A reported normal return invalidated a particular assertion completion, or its association is unresolved | A synthetic position inside a stdout block |

The derived target association is acceptable for this fixed sequential Cargo invocation when headers, complete block count, inventories and summaries agree. Its label must continue to state that it is derived. This reasoning does not authorize a general parser for concurrent executables, arbitrary runners or merged chronology.

## Smallest sound source correction

Preserve the existing structural parsing and exact inventory checks. Add a small diagnostic-classification step to the existing coverage path, preferably an optional diagnostic input to `positive_test_coverage` or a shared pure classifier applied before that function finalizes completed names and flags. Pass the separate stderr diagnostic lines from `derive_target_order_parser_input`; retain their raw text and stream/line provenance in receipts. Keep `parser_input` as a labeled inspection artifact. Raw stdout and stderr remain authoritative originals.

The classifier needs only the frozen producer contract, not a new general logging protocol:

1. Recognize the exact marker `filesystem rejects non-UTF-8 fixture with EILSEQ:` wherever it occurs in the coverage inputs. Its source identity is the pair `sys_fs / test_non_utf8_file_name`, justified by the frozen test above. Require that target to be selected and that test to occur exactly once in its active inventory. Do not associate by the last synthetic header, the last stdout result, or an arbitrary target that happens to contain the same test name. A semantic source mapping is not a chronology claim.
2. For a uniquely resolved marker, record one skipped assertion for that pair and retain its diagnostic provenance. Remove only F19 from `completed_named_tests`; leave its observed libtest outcome `ok` intact. Put F19 in `uncovered_named_tests`. Preserve completed filesystem siblings and other targets. Deduplicate repeated reporting of the same producer without concealing diagnostic occurrences.
3. A recognized coverage-affecting marker with no valid producer in the active inventory is an unresolved diagnostic. Record it explicitly and force overall coverage false. Examples are EILSEQ in a no-index inventory or a selected set without `sys_fs`. Never silently ignore it, assign it to the final target, or fabricate a named skip. An ambiguous producer mapping is handled the same way.
4. Keep ordinary Cargo warnings as retained diagnostics with no coverage penalty. Do not invent a rule that every unknown stderr line is a skip; the frozen contract has one known early-return producer. Conversely, if another actual early-return producer is discovered, stop for an uncovered diagnostic contract rather than calling it a harmless warning. Free-form words such as “skip” are insufficient to identify assertion completion.
5. A recognized unresolved diagnostic must set `coverage_found=false`, `named_test_coverage_found=false` and the aggregate pass flag false. Preserve observed names/outcomes and provisional per-test completion lists, but label them as not certified while diagnostic association is unresolved. With unresolved evidence, those lists cannot certify any potentially affected assertion; do not describe every listed `ok` as accepted completion. This preserves partial observations without converting ambiguity into acceptance.

The positive coverage invariant becomes: exact selected target association AND complete exact named structure AND passing unignored/unfiltered outcomes AND no mapped early returns AND no unresolved coverage-affecting diagnostics. Only then can completion and aggregate acceptance be certified. Structural validity and observed outcomes remain separately useful even when coverage fails.

The existing inline-stdout EILSEQ case must still be rejected. Its attribution should use the same frozen producer mapping; a conflicting inline test name is unresolved evidence, not permission to skip an unrelated test. The broad current fallback that searches the full output and attaches the marker to every target inventory containing `test_non_utf8_file_name` should not become a second, inconsistent attribution policy.

A one-line switch from `parser_core` to `parser_input` would close the supplied EILSEQ example, but is insufficient as the complete repair. Arbitrary stderr lines would then enter the structural parser under the final synthetic target. A stderr line looking like a libtest result, summary or target header could mutate that target's structure, and the current global EILSEQ fallback silently accepts the marker when F19 is absent from all active inventories. Separate diagnostic consumption avoids both problems with a small local change.

Do not throw away a well-formed row merely because it contains a known EILSEQ return. Return an incomplete coverage receipt so the current status-zero continuation path records the row and proceeds to independent rows. Preserve existing fail-closed structural exceptions for malformed streams; broad recovery from malformed libtest blocks is not required by this repair.

## Required realistic RED/GREEN cases

Add assertions against the production entry point `derive_target_order_parser_input`, not only against `positive_test_coverage`. Use two complete stdout blocks and independent stderr headers. Use inventories and target order that differ from the requested tuple. Keep the reviewer model files by reference rather than overwriting or duplicating them as new native evidence.

| Case | Expected result after repair | Meaningful control |
|---|---|---|
| Existing exact two-target model plus marker only on stderr | Coverage false; F19 skipped/uncovered; filesystem sibling and net test retained; original `ok` preserved | Fails against immutable4c4a because it falsely certifies F19 |
| Same streams without marker; ordinary Cargo warning present | Coverage true; no skipped or unresolved diagnostics | Removing a named outcome or duplicating a header must reject |
| Put `sys_fs` first and another target last, with EILSEQ in stderr after the `sys_fs` header and before the next header | Only F19 uncovered; final target unaffected | Exposes attribution by last synthetic target |
| Marker position moved without any claimed cross-stream timing | Semantic F19 association unchanged when its frozen producer is uniquely active | Exposes invented interpolation into stdout chronology |
| EILSEQ marker present but F19 excluded by no-index, or `sys_fs` absent | Coverage false; explicit unresolved diagnostic; no invented F19 completion/skip | Fails against immutable4c4a; full-text fallback alone also fails this requirement |
| Same named test string in another target's inventory | Marker maps only to frozen `sys_fs` producer when active; no extra skip | Exposes mapping by unqualified function name across inventories |
| Marker conflicts with an inline stdout test name | Coverage false; conflict recorded, unrelated name not falsely marked skipped | Exposes trusting incidental surrounding result text |
| Marker supplied through legacy inline stdout shape | F19 uncovered, preserving previous diagnostic rejection | Existing source test remains applicable |
| Ordinary stderr diagnostic text shaped like `test x ... ok` or `test result: ...` | Cannot add named completion or alter libtest summaries; retained as diagnostic text | Exposes reparsing the entire appended stderr section |
| Missing/duplicate/extra headers; incomplete/extra blocks or summaries; missing/duplicate named outcomes; ignored/filtered/measured/failed results | Fail closed using existing structural/coverage rules | Retain prior meaningful negatives, including an extra summary outside a block |

For the unresolved cases, assert each public acceptance flag and receipt field, not only a single final boolean. For the known skip cases, assert exact retained and uncovered name sets for every target. Also assert raw stdout/stderr references and the derived-order label survive. The command-level receipt/summary check should use the helper's existing pure testing technique to prove that a status-zero incomplete row is retained, later independent rows remain eligible to run, and the final successful-row count/acceptance marker never becomes all-passed. Do not add a native run to test these source contracts.

Record the actual RED outcomes on the immutable baseline, then the repaired GREEN outcomes. Expected TDD REDs are not failed implementation corrections. A baseline assertion that is already satisfied is a regression check, not a newly demonstrated RED. Pure regression success establishes parser behavior only; it cannot prove Darwin filesystem/TCP execution or cleanup.

## Stage and scope correction

The prepared contract prescribes `current-darwin-sys-net-behavior-2f795ece-20261002`; helper `SESSION_ID` still prescribes `current-darwin-sys-net-behavior-a2d7a8c2-20261002`. `validate_stage_inputs` compares both runtime parent and stage basename to that old identifier. Resolve this by changing the helper identifier to the already prescribed contract identifier and deriving its expected scope from it. Keep validation strict. Do not accept both names, bypass validation or rename an existing foreign/staged resource.

Add a source/pure validation regression proving the contract's exact stage basename and scope suffix agree with the helper and source pin, and that a wrong basename/wrong scope still fails. Check the source-prep instructions and future dispatch command use the same identifier. The source/test archive digest and lock digest remain unchanged if only helper/tests/contract wording change. Helper freeze and staged-helper verification must refer to the new helper revision. No stage/runtime directory was created or inspected here; dispatch must still prove an absent owned scope and exact staged bytes under its original safeguards.

## Evidence applicability

| Conclusion or proof | Disposition |
|---|---|
| F1 EILSEQ rejection on the new derived-stream execution path | Invalidated by the actual stderr-only counterexample; remains unaccepted until repaired and independently rechecked |
| F4 closure and eight GREEN categories as evidence of stderr diagnostic rejection | Invalid; the owner test injects EILSEQ into stdout and misses the producer's actual stream |
| Stage/scope dispatch readiness | Invalid until the helper/contract mismatch is corrected and frozen/read back |
| F4 clean target association, exact inventory and malformed-stream checks | Reusable at source level; recheck affected dependencies after modifying coverage |
| F1 other exact-name/summary requirements and assertion-control classification | Reusable where unchanged; preserve controls and their independent evidence |
| F2 conservative identity/group/path cleanup logic | Unchanged source conclusions reusable; pure/mock proof remains distinct from actual native disappearance |
| F3 corrected root configuration, distinct alias assertions and lexical routing | Source conclusion reusable; actual canonicalization, Engine access and host readback remain unverified |
| Nine-row matrix and no-index exclusion of F19 | Unchanged; never waive F19 in rows that include it |
| Existing Linux behavior, compiler/example proof | Preserve original applicable evidence; Linux remains Linux-only and compiler/examples do not certify Darwin sys/net behavior |
| Any future native receipt evaluated with old coverage logic | Cannot certify EILSEQ-sensitive rows; authoritative separate originals would need corrected coverage readback and all remaining native criteria |

The brief and original review report no native launch during these F4 corrections. There is therefore no new native acceptance to salvage or invalidate. Production source and accepted unrelated proof must remain untouched.

## One bounded follow-up repair contract

The responsible owner may perform one follow-up source-only repair package for cause11 using this answer. Record it in the existing coordinator state before work: requirement, answer path, two failed implemented corrections (`8b9740de`, `4c4a81e`), one Expert analysis, cumulative active use, permitted files, checkpoint and stop conditions. This is not a new budget or review chain.

Permitted work: helper diagnostic consumption/association and strict session-name correction, meaningful pure tests, necessary contract/source-prep wording and receipts. Freeze the resulting helper/test/contract revision. Preserve the frozen production/test source, archive/lock pins, wrong controls, nine rows, cleanup obligations and all original evidence. No native process query, API/control/build/Cargo/toolchain launch, measurement85, resource allocation revision, push or merge is part of this package.

Use the 30-minute active-work planning checkpoint from the brief. At that checkpoint, record cumulative use and a concrete closed check or new diagnosis before any justified continuation; it is a planning estimate, not an automatic permission gate. Preserve all actual time/resource caps and historical failures. Record pure test invocations and setup failures without counting an expected RED as a failed correction. Permit at most two consecutive invocations without a new diagnosis or closed check; do not repeat identical failing checks or extend a hard cap.

After the source assertions pass, the same combined independent reviewer should perform one affected recheck of diagnostic association, partial receipts/aggregate flags and session-name validation against the frozen repair. Reuse unchanged review conclusions. No fresh broad scan, second Expert chain, new review pipeline or native dispatch is needed to close this source boundary.

Source acceptance requires realistic stderr-only EILSEQ rejection, clean multi-target acceptance, unresolved association rejection, exact preservation of valid partial evidence, unchanged structural negatives, and matching strict stage/scope naming, confirmed independently at the new freeze. This closes source dispatch prerequisites only. Strict native acceptance still requires the previously specified real Darwin rows, controls, independent readbacks and cleanup under the existing separately recorded allocation.

Stop dependent work on acceptance, an explicit stop/hard limit, repeated failure without progress, contradictory remaining evidence, or discovery of a diagnostic/execution contract the ticket does not cover. In that event retain the receipts and report the specific remaining requirement once. Do not launch another Expert chain or native run to bypass the unresolved source boundary. Independent authorized work may continue.
