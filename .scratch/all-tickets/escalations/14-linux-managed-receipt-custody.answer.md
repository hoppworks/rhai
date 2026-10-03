# Verdict

NOT READY. One bounded harness repair can resolve this cause without changing frozen source or acceptance. Add the missing success API suffix, bind the entire quoted prompt cleanup to that same receipt, and use the supplied closure prefix when exporting GREEN success closure. Then exercise the actual helper and collector paths with source-derived positives and targeted corruptions before refreshing pins. Do not stage or allocate native96 on the current files.

Loaded the project/global instructions, campaign and repair instructions, roles table and Expert template at agent-skills revision `faba3db3bef6891ad2c0b20d434963bb8fe9572d`. Diagnosis was read-only except this requested answer. No SSH, staging, build, native invocation, process restart, source edit or allocation occurred. Usage/cost is unknown. Prior correction history and Unix95 consumption remain unchanged.

## Frozen inputs preserved

| Input | SHA-256 |
|---|---|
| Proof | `4cdd64b3be763c317568abab15f763b17b03a4e629e9a27d47934d347bcb446a` |
| Collector | `2016e5406da01889fea1316c3b7286334193c84433dca6209a8835e94225ba9b` |
| Stage | `524836952857f3de84e15c1eb29fd9df0a4aa1601d0804338f6498ac1cdf9db4` |
| Launcher | `27e1ee59a936fefaab51172aa0b27d6b877f3eda1e37ca119a2967c6e5f6ff50` |
| Preparation | `1494a730cde3d303ea59dbb9dea928c9dc484cc393f2846ba2d38f9bf483d793` |
| Frozen test | `e0034cf3a69ccf6107a9dfbc0854c0147ec2d93fdda8acf5ed6b07e683e1dc14` |

All six match actual bytes. Source remains `003da06421fbd11c26e0c96ab5013416c0939a1d`. Archive, lock and contract pins remain unchanged.

## Source-derived receipt grammar

The following notation uses decimal positive PID/start values, named independently bound identities, and `LF` for an actual newline. `\\n` inside a quoted Rust Debug string means the literal backslash followed by n. Distinct processes may share start ticks. `G=L`; acquired parent/group relationships must be exactly the ones below. Numeric wait statuses are native waitpid status integers; do not require a particular signal status for descendants.

Success pre-assertion receipt (`tests/sys_process.rs:1843`):

```text
managed_prompt_reap_live_boundary reaper=R reaper_start=RS host=H host_start=HS leader=L leader_start=LS worker=W worker_start=WS leaf=F leaf_start=FS group=G sentinel=S sentinel_start=SS LF
```

Its six PIDs must be distinct. The acquired receipts emitted by `acquire_managed_pidfds` are:

```text
managed_pidfd_acquired pid=L start=LS ppid=H pgid=G LF
managed_pidfd_acquired pid=W start=WS ppid=L pgid=G LF
managed_pidfd_acquired pid=F start=FS ppid=W pgid=G LF
```

Each expected PID occurs exactly once. In a two-test command the global inventory remains six distinct receipts, exactly the disjoint union of both cases; filtering to a boundary does not waive that inventory check.

Full success record (`1621`, `1650`, `1893`), physically two lines:

```text
managed_prompt_reap_success host=H host_start=HS leader=L leader_start=LS leader_absent=true worker=W worker_start=WS worker_absent=true leaf=F leaf_start=FS leaf_absent=true sentinel=S sentinel_start=SS sentinel_live_at_return=true sentinel_reaped_after_return=true api_exit_zero_at_return=true captures_complete_at_return=true api=host=H host_start=HS api_success=true api_outcome=success_report code=0 exit=Some(0) stdout_complete=true stderr_complete=true cause=none diagnostic=none LF
 cleanup="worker=W start=WS pgid=G reaped=true wait_status=WK leaf=F start=FS pgid=G reaped=true wait_status=FK complete=true\\n" LF
```

The single space before cleanup comes from the final eprintln format after api_result's trailing actual newline. The quoted cleanup is Rust Debug output of the string produced at `1190` and `1213`, in worker-then-leaf order. It includes both wait_status fields, complete=true, and the escaped trailing newline. The API H/HS must equal the boundary H/HS; all boundary identities must equal the early receipt; cleanup W/WS/F/FS/G must equal those bound identities. Require the complete quoted cleanup, including its end, from this record, rather than searching arbitrary later text.

Success/control unwind also emits:

```text
managed-scope sentinel_cleanup pid=S status=Some(ExitStatus(unix_wait_status(SK))) esrch=true LF
```

The source additionally has an `already-exited` Drop branch. The reviewed success flow asserts the sentinel live immediately before dropping it and existing acceptance requires the Some(ExitStatus(...)) branch; retain that requirement here. This diagnosis does not authorize broadening it. Sentinel PID must match the early receipt.

Full held boundary (`1773`), also physically two lines:

```text
managed_held_zombie_boundary host_live_at_return=true leader=L leader_start=LS leader_reaped=true worker=W worker_start=WS worker_state=Z worker_pgid=G leaf=F leaf_start=FS leaf_state=Z leaf_pgid=G group=G kill_zero_result=KR kill_zero_errno=KE capture_complete=true host=H host_start=HS api_success=false api_outcome=typed_process_io cause_op=observe_process_group_closure cause_op_matches=true kind=TimedOut exit=Some(0) stdout_complete=true stderr_complete=true diagnostic=true cause_details=DIO cleanup_diagnostics=DD LF
 held="pid=R start=RS host_status=0 worker=Some(W) worker_start=Some(WS) leaf=Some(F) leaf_start=Some(FS) held_zombies=true\\n" reaper_status=ExitStatus(unix_wait_status(0)) LF
managed_held_zombie_cleanup worker=W reaped=true leaf=F reaped=true LF
```

`DIO` and `DD` are the single physical line Rust Debug representations supplied by the typed error and its diagnostic list; the actual95 original contains their full bodies. They include quoted text and nested structures, so do not flatten or invent an abbreviated positive. Preserve the exact typed op/kind/direct-exit/capture/diagnostic requirements independently of these variable debug bodies. Restrict their capture to the API line; they must not consume another receipt. KR is signed; KE is numeric. The source records kill-zero as evidence only, so do not introduce a success-only KR/KE restriction. Actual95 has KR=0/KE=0, shared start ticks, full bodies, an actual newline before held, and escaped newline inside held. Held H/R/L/W/F PIDs are distinct; G and acquired hierarchy bind as above. The reaper-held W/WS/F/FS and cleanup W/F must agree with this boundary. The collector already checks all five held identities are distinct through verify_absent; preserve that check.

For the repaired success grammar, require exactly one complete success boundary for the selected case, with line boundaries. Combined stderr contains both receipt types; a success predicate must never use held flags, diagnostics or cleanup to repair a malformed success record. Existing stdout segmentation handles outer libtest names and nested stdout; retain the last stdout-only outer summary logic.

## Confirmed defects and minimal changes

1. **Genuine success rejection.** `success_api_receipt` requires newline immediately after stderr_complete=true, omitting cause=none diagnostic=none. The actual loaded function rejects the complete source-format positive. An in-memory diagnostic replacement adding exactly those fields makes the same positive pass. This reproduces the known blocker without altering files.

2. **Cleanup matching is not confined to its record.** The current DOTALL `cleanup=.*?worker=...*?leaf=...` accepts complete=false and even accepts the required worker/leaf fields after `cleanup=""` has closed and a foreign line begins. Both were reproduced against the actual parser with only the missing suffix repaired in memory. Replace this wildcard with the full quoted cleanup grammar above. Keep wait-status captures syntactically numeric without imposing an unsupported particular status. Remove the redundant whole-text cleanup search in require_success, or bind it to the already validated match; it must not choose an unrelated earlier cleanup. This is a small same-cause receipt correction, not a new framework.

3. **Concrete dependent export blocker.** `identity_closure(text, prefix, h, label)` ignores prefix and writes `f'{label}-fixture-closure.json'`. GREEN calls it with prefix success-green-row-N and label green-row-N. The collector requires success-green-row-N-fixture-closure.json. A pure call through actual identity_closure with an in-memory suffix repair and stubbed absence/ps/write_json emitted `/no-write/green-row-1-fixture-closure.json`, confirming the mismatch. Change only the output filename to `f'{prefix}-fixture-closure.json'`. RED calls already supply identical prefix/label. This leaves seven success/control closure files and four held closure files, eleven total, as required by collector inventory.

The held parser accepts actual95 original bytes now; no suffix repair is needed there. Existing acquisition inventory, PIDFD list comparison, process custody, fresh /proc/group reads, statuses, restoration and export guards remain in force. No broad changes to unchanged held/custody logic are required for the smallest route. Keep source-defined held positives in the affected end-to-end collector purecheck so the success correction cannot accidentally regress this dependent path.

## One bounded follow-up repair and check sequence

The responsible implementation context should apply the three local changes above as one repair, preserving the two rejected checkpoints and this answer. No source/launcher change is needed. This is the single post-escalation follow-up for linux-managed-receipt-custody, not a renewed retry chain.

1. Start with the current complete source-format success positive failing for the suffix omission; preserve its exact two-line/quoted-cleanup layout. Use all six distinct success PIDs with shared start ticks. Pair it with the unmodified actual95 held stderr, including warnings/full debug body and its own disjoint three PIDFD receipts. Add realistic exact outer prefixes and nested stdout. Do not use the old abbreviated positive as acceptance.
2. After correction, execute actual require_success, exact_boundary, identity_closure and require_held under bytecode suppression. For source-only export-path tests, stub only /proc absence, ps and write_json, clearly recording that these are harness tests, not native proof. Assert exact output filenames and serialized expected identity/PIDFD rows. Assert all eleven expected closure files are consumed by the collector.
3. Execute the actual embedded collector REMOTE locally with a fully populated temporary synthetic stage, mock only external OS/readback operations and fixed hashes as necessary, and exercise its real command loop for held-mode RED, both post-success assertion controls and four combined GREEN rows. Keep the mock boundaries explicit. Exercise actual local-export validation separately. These source-only executions do not establish native96 acceptance.
4. Run the negative cases below individually against their actual consuming functions/paths; each must fail for the mutated requirement. Preserve the complete opposite case when mutating only success. No additional native launch is needed for these checks.
5. Run Python AST/compile checks without bytecode and bash -n for recipes. Freeze proof SHA; update stage expected_proof; freeze stage SHA; update every collector PROOF/REMOTE/fixed-input and stage pin; freeze collector; update preparation with exact results/hashes. Keep archive/source/lock/contract and launcher hashes unchanged. Read back the final hash chain independently; do not merely repeat documented hashes.
6. The existing combined reviewer rechecks only this repair and pins against the frozen rejected baseline. After READY, the Coordinator may proceed to the already authorized bounded native procedure with a fresh slot/preflight. No native budget is consumed by this diagnosis or purechecks. Native96 and strict success/held OS acceptance remain unverified until original outputs, restored source, fresh fixture/helper/launcher custody and verified export/cleanup establish them.

| Negative mutation | Required rejection |
|---|---|
| Remove cause=none or diagnostic=none; change either to a failure value | Complete success API grammar |
| Change only success API host/start, code/exit, success/outcome or either capture flag; retain held flags unchanged | Same-receipt success identity/outcome binding |
| Remove the actual API newline; flatten it; replace cleanup escaped newline with a physical newline | Source-format receipt structure |
| Change cleanup W/WS/F/FS/G, reaped flag, complete flag; remove either wait_status | Exact quoted reaper cleanup |
| Close cleanup quote early and place valid worker/leaf fields on a foreign line or later receipt | No cross-record wildcard completion |
| Duplicate the full success boundary | Unique repaired success receipt |
| Duplicate/remove acquired row, alter ppid/group/start, or overlap the two case PID sets | Exact per-case inventory and disjoint six-row union |
| Corrupt held direct exit, typed op/kind/captures, held identity/start, host_status, reaper status or cleanup identity | Held receipt and reaper binding |
| Missing/wrong/old-name GREEN success closure; missing held closure; extra closure file | Exact eleven-file inventory |
| Missing closure identity row; alive=true; altered PIDFD row | Existing custody representation guards |
| Missing required helper/launcher/supervisor custody row or unreadable PID/start | Existing independent custody guard |
| Changed/deleted exported original byte, directory inventory, or added symlink before cleanup | Existing local export guard; remote copy preserved |

Stop this failing path if the bounded follow-up still fails its intended independent check or evidence contradicts this route. Preserve outputs and the stable cause history; do not rename the cause or allocate a native run to diagnose a known parser failure. Native limits remain 600/585/540 seconds including 30 seconds export, jobs2, descendants16, preemptive storage1572864KiB, hard RSS/storage2097152KiB. No changes to stopped macOS/Windows causes or broader acceptance claims are recommended.
