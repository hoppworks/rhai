# Collector emitter/consumer identity contract

**Verdict: the contract mismatch is understood and has a safe, narrow correction. Raw preservation remains verified; the frozen e537 collector remains CUSTODY/RETIREMENT NOT READY until that correction and fresh actual retirement checks pass. Repeated command labels and explicitly empty command strings are legitimate original emitter output. Accepting them does not require weakening exact process identity or cleanup gates.**

The applicable instruction repository is independently confirmed at `faba3db3bef6891ad2c0b20d434963bb8fe9572d`; global and root project instructions and the current roles table were read. This answer uses local source analysis, actual-parser/receiver pure probes and local byte rehashes only. No SSH, Cargo, native execution, stage mutation, retirement, source edit, Git mutation or external message occurred. Writing this requested answer is the sole deliverable mutation.

## Exact frozen emitter semantics

The original `run-examples.py` hash is `55c2a4a4c177f468757275a2691f73002a984a63b4c7cbba87314813a4b03d69`; original `launch.sh` is `2381ebb7dd8bb29bedb55f5dbcd9b1d12b732834c00f2fc747d439b0f6902d6d`. Both match the frozen collector's ten input pins.

`process_identity(pid)` reads `/proc/<pid>/stat`, then reads cmdline separately, replaces NUL bytes with spaces, decodes UTF-8 with replacement, and strips surrounding whitespace. It does not require a nonempty result and does not capture raw argv or atomic stat/cmdline provenance. A successfully read empty cmdline is retained as an empty string. Exit between reads is one possible explanation; the records do not establish the particular cause. Do not invent argv bytes or claim the command label proves an executable.

If either read raises NotFound/ProcessLookupError, the helper returns `None`. A command identity of `None` is omitted altogether. A required helper/supervisor identity of `None` produces an unavailable row and fails before commands. Permission/I/O/index/value failures raise; they are not evidence of absence. Therefore the TSV is the complete preserved set of identities the emitter successfully recorded, not a guaranteed census of every spawn or descendant.

`record_process_identity` appends a row for each successfully captured command. `sample_resources.capture` repeatedly spawns `du` and `ps` with unchanged labels. `run_command` uses `command:<name>` for its child. No sequence number or uniqueness promise exists for command labels. Each recorded row, including its empty last field, must remain available to absence checking; neither a dictionary keyed by command label nor a set of labels can represent the records.

The owner rows are different: exactly one helper and one scoped-supervisor are emitted before commands, and exactly one launcher and run-scoped are emitted by the launcher. The launcher command field is the prescribed launch-script path written by Bash; it is not read from its own `/proc/cmdline`. The other three owner fields come from proc reads. All four are nonempty in these originals.

The original observations are:

| Property | Actual preserved value |
|---|---|
| Helper TSV | 64 rows: helper 1, scoped-supervisor 1, command:du 29, command:ps 29, four other commands 1 each |
| Launcher TSV | 2 rows: launcher 1, run-scoped 1 |
| Exact recorded PIDs | 66 distinct positive PIDs |
| Empty command strings | command:du PID3061413; command:ps PID3061414; command:rustup-install PID3061415 |
| Owned groups | `[3061340, 3061410]` |
| Parent chain | launcher3061340 → run-scoped3061407 → supervisor3061410 → helper3061411 → every recorded command |
| Runtime marker | one original marker, ending `agent-build-rqtg34_b` |

Start ticks need not be globally unique: several separate PIDs share a tick. Identity is the positive `(pid, start_ticks)` pair; observations also carry the original label and PGID. Preserve the existing stronger unique-PID rule for this stage, which the actual originals satisfy. No PID-reuse support for duplicate recorded PIDs is needed in this repair.

## Minimal safe consumer correction

Correct only `collect-linux-sys-process-example.py` and its bounded local probe evidence. Keep the original emitter, all ten immutable pins, TSV bytes, failed663 stage/scope paths, archive and existing evidence untouched. The new60048 execution source/recipes remain separate and unrun.

1. **Embedded `REMOTE_CUSTODY.parse` (e537 lines69–78):** retain exact header, six fields (`split('\t', 5)`), strict decoding, positive numeric PID/PPID/PGID/start, allowed owner labels and nonempty command suffix. Require cmdline only for required owners; command cmdline may be exactly `''`. Retain missing/unavailable/malformed rows as errors, rather than dropping them and declaring ready. Remove the all-label uniqueness rule; retain exactly-one required owner counts and unique PIDs. Commands may repeat only with distinct positive exact identities. After joining both files, reject any cross-file PID duplication as well.
2. **Owner lookup and provenance checks:** construct owner dictionaries from required owner rows only, after validating their count. Never collapse command rows. Preserve all recorded ancestry checks: command PPID=helper PID, helper PPID=supervisor PID, supervisor PPID=run-scoped PID, run-scoped PPID=launcher PID. The launcher PPID is positive but its external parent is not an owned chain member. Keep owner cmdline provenance bound to these pinned scripts and recorded relationships. At minimum retain the existing expected script checks; bind them to the prescribed stage script paths (allow the known logical `/root` and canonical `/var/roothome` path spellings), rather than accepting an arbitrary script with the same basename. Preserve original cmdline text; do not reconstruct argv with shell parsing. For this one retired invocation, exact owner strings from the verified copied TSV are an acceptable still narrower comparison if carried from independently preserved input, not newly invented constants.
3. **Local `validate_custody_receipt` (e537 lines170–189):** replace global label uniqueness with exact required-owner multiplicity; launcher must have exactly its two required rows. Validate positive PID/PPID/PGID/start using `type(value) is int`, excluding JSON booleans. Validate cmdline as a string, permit empty only on commands, and repeat the owner-parent/provenance predicates. The current receiver does not independently check PPID, cmdline or owner multiplicity beyond a global-label rule; simply deleting that rule would lose its accidental owner-duplicate protection. Retain global unique PIDs and complete `(label,pid,start_ticks,pgid)` observation equality with equal row count. Repeated labels cannot collapse those tuples because PIDs remain unique. Keep groups exactly the sorted union of every recorded PGID.
4. **Proc readback classification in the custody script and both retirement loops:** validate the observed stat framing/required field count and positive numeric start field before comparing it with recorded start ticks. Present matching start means `live`, even for a zombie. Only a successful well-formed different start means `pid-reused-original-absent`; only explicit NotFound means `absent`. Permission/I/O/short/malformed proc reads remain unknown and block. The current three loops treat a nonnumeric field19 as a differing start and thus absence; this directly conflicts with the stated unknown-read requirement and belongs in this same identity repair. Do not synthesize absent state for malformed stat data.
5. **Leave retirement safeguards intact:** preserve all66 row observations, exact independent group census, one direct runtime child grammar, scope/runtime absence checks, complete preserved tree/tar hash checks, fresh immutable inventory/input binding and fresh receipt equality. The embedded deletion script still rehashes exact original files and repeats immediate OS checks before deletion. Keep `sorted(groups)` and the explicit final stage/scope/runtime, all66 PID/start and group receipt checks. No raw status, modeled-ready flag or supplementary old cleanup receipt can substitute for them.

This is compatibility with known producer output, not a command provenance waiver: recorded cmdline can be unavailable as bytes while the positive identity, original TSV hash, verified emitter, helper parent and current absence observation remain independently required. Empty command text is not an unknown proc read during retirement.

## Executed local evidence and required probes

The actual e537 collector hash independently matches `694d327c4a20f6c0c4c28cadbe0417e6865b3e4dfaf4a91a727b6f51e2bea8c9`.

I AST-extracted and executed the actual `REMOTE_CUSTODY.parse` function against the original copied helper TSV, with no proc/ps/remote execution. It accepts only61 rows, reports three malformed empty-command rows and duplicate command labels. I AST-extracted the actual local validator and supplied all original64+2 rows with explicitly modeled absent observations: it returns false. These reproduce both concrete failures. A direct read of all original rows confirms all parent relationships and66 unique PIDs. This is consumer-model evidence, not fresh Linux absence proof.

For the one follow-up, retain original fixtures unchanged and use mutations of in-memory copies. Execute the corrected actual parser, complete actual embedded custody code with fake filesystem/proc/ps, actual local validator, and isolated actual final receipt expression/receiver. Any model must be labeled as a model and prevented from launching subprocesses or invoking deletion. These are the minimum cases:

| Case | Required result |
|---|---|
| Unchanged original TSVs, modeled all66 absent, empty group census including unrelated `1 0`, original runtime marker and absent paths |64+2 rows retained; three empty strings unchanged; two groups; both producer and receiver ready |
| Well-formed changed proc start for one PID |original absent via PID reuse; matching observation retained |
| Original repeated du/ps labels with distinct identities |accepted; all58 sampling rows observed |
| Missing/duplicate owner, owner empty/wrong script text, wrong owner PPID or command PPID |rejected by producer and receiver independently |
| Duplicate PID within/across files; repeated exact row; zero/negative/unavailable/nonnumeric PID/PPID/PGID/start; boolean integer receipt field |rejected |
| Wrong header, missing sixth field, unreadable/undecodable identity input, empty command suffix or foreign owner label |rejected |
| Live matching PID/start (including zombie), permission/I/O/short stat, nonnumeric observed start |rejected; unknown never becomes reuse/absence |
| Group member present, malformed census or ps failure; runtime traversal/duplicate marker/present/symlink path; present/symlink scope |rejected |
| Missing observation or substitution of one repeated-label command's observation with another; live/unknown final state; wrong final groups/truncated final receipt |rejected by actual receivers |
| Corrupted input manifest/source hash/tree/tar or changed fresh inventory/custody |retirement blocked before deletion; unaffected e537 input-binding guards still exercised |

Source-defined command omission does not justify deleting one row from the preserved TSV or a receipt: frozen inventory equality catches TSV edits; count-plus-tuple observation equality catches receipt omission. Do not require an expected count of spawns from command names; use the exact independently preserved row set for this invocation.

## One bounded follow-up for the existing Standard

Use the same responsible Standard and existing collector branch/worktree. Record cause `collector-emitter-identity-contract`, first escalation19, zero prior correction attempts for this cause, the already consumed unknown elapsed collector work, and this answer. Plan one20-minute active-work source/pure-probe checkpoint, as an estimate rather than a new launch allowance. No Cargo/SSH/native/staging/retirement/push or changes to example source, original emitters, preserved originals or new60048 recipes in this follow-up.

First add the original-shaped regression assertions and reproduce RED against e537. Implement the single consolidated consumer batch above. Run finite pure probes, Python syntax/AST checks, and actual final producer/receiver expression probes; freeze the correction and report file hash/revision, original fixture hashes, complete case results and actual elapsed use. Expected RED is not a failed repair. Stop on contradictory evidence, no progress or exhausted authorized capacity; preserve cause history. Return the frozen result to the existing combined affected reviewer for one focused recheck against e537 and original TSV/source evidence. No second broad review pipeline. A passing source/pure recheck permits preparation of actual retirement checks; it does not itself retire or accept behavior.

## Evidence applicability and remaining actual checks

Local independent rehash in this analysis confirms all49 preserved regular-file hashes equal the original inventory and the retained tar hash remains `3851968501ddfe01c5adcd96c64c239a72a3abb218defe87d903915a270e0672`. The original identity hashes are helper `f7949153ace6ecfc2b7a4b491308f6e1cd72d01b3c7d2fbab0a422a24a3a9aaf` and launcher `a3ef24e9092e530e7e41dc7d147bea70fe216769a321bcf2d49abd339d60de81`. Original preservation and immutable input binding remain valid narrowly. Retain existing raw tar, initial/fresh inventories, failed custody receipt, compiler diagnostics and collection status as historical originals. Do not rewrite the old failed receipt to ready.

The earlier e537 scope-decoupling and sorted final-group serialization conclusions remain valid. Its modeled actual receipt-expression checks remain useful for those unchanged portions; repeat affected identity coverage checks with all66 originals. The prepared60048 public API/source review remains applicable independently and compilation/native acceptance remains unverified. The failed663 build supplies compiler diagnostics only, no behavioral acceptance.

The earlier supplementary independent Linux receipt records66 identities absent, two empty groups, exact runtime/scope absent, and matching identity-input hashes. That is valid historical observation at its own time, not a current absence assertion, retirement receipt or replacement collector validation.

After corrected source readiness, the owner must obtain a new explicitly named custody readback for the unchanged original stage, preserving the old one separately. Revalidate all copied49-file inventory/tar and ten-input pins; obtain fresh remote exact stage inventory and current66 PID/start, both groups, original runtime and scope observations. Retirement requires the collector's immediate fresh inventory/custody equality and on-host pre-deletion checks, followed by the explicit post-deletion receipt and independent readback of exact stage/scope/runtime and66 PID/start/group absence. If any read is unknown, changed inventory or unmatched receipt appears, retain the stage and report the genuine blocker. A PID-reuse state transition between receipts may require refreshing custody; it must not be coerced into equality. Do not recollect into the existing destination or rerun native examples to acquire retirement evidence.

This answer allocates no actual remote retirement or build run. Original663 remains retained. New60048 remains independently prepared and unrun. Exhausted stdin/Windows/macOS paths remain stopped, native110 remains unallocated, and the all-tickets goal remains open. Costs and earlier unavailable elapsed use remain unknown.
