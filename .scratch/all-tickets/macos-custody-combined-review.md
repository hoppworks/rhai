# Combined macOS custody source review

Result: **changes required; source readiness is not established**. Four material findings form one correction batch below. No native ABI, process interruption, cleanup, build, fixture, control or measurement acceptance is claimed.

## Reviewed baseline and coverage

The reviewed range is `878a5164c697311029138c511a58271496742240` (the original parent of `2f4be015`) through frozen `b2db6448af7c4c29fe6d6529910d4648e264739a`, including:

- `2f4be0150c694a14e7d4ca3cc45320abb5220162`
- `a7232f054d324779bab9afd43f5b6d52ca7c685e`
- `fdb9cf207158cff0635b500f26664a89bc2af5ab`
- `b2db6448af7c4c29fe6d6529910d4648e264739a`

Sources were read in `/Users/hoppworks/.codex/worktrees/macos-overhead-safeguards/rhai`. HEAD matched the frozen ref, and `git status --short` showed no tracked modifications; the unrelated untracked audit tree was preserved. OCR range preview identified exactly six changed files, with no exclusions. All six files and their changed behavior were reviewed:

| File relative to the frozen worktree | Status | Coverage |
|---|---|---|
| `.scratch/all-tickets/darwin-process-reader.py` | modified | reviewed |
| `.scratch/all-tickets/macos-process-overhead.py` | modified | reviewed |
| `.scratch/all-tickets/run-macos-process-overhead-scoped.py` | modified | reviewed |
| `.scratch/all-tickets/run-macos-process-overhead.sh` | modified | reviewed |
| `.scratch/all-tickets/test-darwin-process-reader.py` | modified | reviewed |
| `.scratch/all-tickets/test-macos-process-overhead-source.py` | modified | reviewed |

Coverage: `total_files=6`, `reviewed_files=6`, `skipped_files=0`, `coverage_rate=100%`. Applicable OCR Python and default rules were read. The review used direct source and diff reads; tests were inspected, not executed. Supporting parser context was read at `.scratch/managed-unix-scope-close/measure-process-overhead.py:24–44`.

The review also read the current global and project instructions, `ocr-delegate/SKILL.md`, the prior `macos-custodian-architecture-root-review.json`, the named `macos-selected-source-confinement-review.md`, and `macos-selected-graph-root-readback.json`. This is one independent review under the existing Expert09 cause/history/caps. It creates no escalation, repair allocation, launch allowance or cap reset. Work completed within the 30-minute active-work planning checkpoint. No source files were changed, and no commit or push was made.

## Material findings: one correction batch

### 1. High — successful measurement output changed from text to bytes

**File:** `.scratch/all-tickets/macos-process-overhead.py:256`, with consumers at lines 338–344. **Category:** bug.

`run_anchored_command()` returns `output.read_bytes()` (lines 225–227). The revised `run()` returns that `out` unchanged. After a successful Cargo command and candidate readback, `main()` passes the bytes to `Path.write_text(out, encoding='utf-8')` at line 340. That raises `TypeError` before `cargo.status`, raw samples and summary are completed. Even changing that write alone would leave the text regular expression in `parser.parse_samples(out)` incompatible with bytes. The pre-package `run()` returned `path.read_text(errors='replace')`, so this is a regression introduced by the custody refactor.

Restore an explicit text boundary in the measurement result path while keeping the raw log intact. Add a pure regression that supplies a successful byte response and exercises the measurement export/parser boundary, checking the resulting status, samples and summary. Current pure tests do not cover this boundary. A native measurement must not be consumed to discover this deterministic type error.

### 2. High — final acceptance omits the explicit incomplete-cleanup state

**File:** `.scratch/all-tickets/run-macos-process-overhead-scoped.py:652–660`, with the incomplete state produced at lines 330–339 and EOF handling at lines 499–501. **Category:** bug.

`owned_command()` deliberately marks `record['cleanup_complete'] = False` when anchored cleanup is uncertain, even if exact-child fallback subsequently reaps gate and anchor. `records_closed` checks setup, the signal-attempt flag and the two exit statuses, but omits `cleanup_complete`. A group-signal syscall error after `signal_state['issued'] = True`, followed by successful exact-child fallback, produces a record with all those checked fields populated and cleanup explicitly false. If the client has exited by signal and EOF is observed, the server returns `client-eof` before classifying custody uncertainty; `clean_interruption` can then accept this record.

Later candidate/group/observed-identity absence checks are valuable, but do not establish that an uncertain group signal succeeded or cover every unobserved escaped external helper. The code's own retained-custody decision must remain binding. Otherwise the adapter can export `complete: true` and remove the runtime while a command record says cleanup was incomplete.

Require every accepted command record to have `cleanup_complete is True`, and preserve that requirement on the EOF/interruption path. Add a pure regression for group-signal failure, successful exact-child fallback, client EOF and a negative client status: the runtime and incomplete receipt must remain retained. Also retain the successful exact cleanup/EOF case as a positive control. This is an acceptance-predicate issue, not a request to weaken group identity checks or issue another numeric group signal.

### 3. Medium — client connection wait can consume the reserved closure/readback phases

**File:** `.scratch/all-tickets/run-macos-process-overhead-scoped.py:631–639`. **Category:** bug.

The initial client-connection loop checks the overall `deadline` (585 seconds for the wrapper invocation), rather than `work_deadline` (560 seconds). A client that remains alive without connecting can keep the adapter in this loop through both closure575 and readback580. On expiration, `finally` calls `terminate_and_reap_client(proc, closure_deadline)` with an already-expired deadline, so TERM and subsequent KILL have zero reserved reap time. This retains the runtime honestly if reaping fails, but violates the restored work-stop/closure reservation and makes the exact client cleanup unreliable on this startup boundary.

Bound connection establishment by `work_deadline`, preserving the remaining closure interval for exact client TERM/KILL/reap. Add a pure clock/client regression for a live nonconnecting client and verify that the loop exits at work stop and the cleanup call receives time remaining before closure. Cancellation is already checked in this loop; that does not repair the timeout boundary.

### 4. Medium — wrapper rejects the normal duplicated runtime record

**File:** `.scratch/all-tickets/run-macos-process-overhead.sh:21–24`; emitters at adapter line 577 and driver line 278. **Category:** bug.

The adapter and connected client both print `runtime_path=<same runtime>` to the wrapper's shared evidence stream. The wrapper collects every matching line and requires exactly one entry. Any successful path that reaches the client therefore reports `cleanup_readback=missing_or_ambiguous count=2`, sets `cleanup_rc=1`, and returns failure even when runtime removal and the custody receipt are otherwise correct. This defect is inherited from the original baseline, but remains material in this complete wrapper/custody package.

Use one authoritative adapter record, or accept repeated identical absolute paths while continuing to reject differing paths. Add a pure wrapper-record regression covering one path, two identical records, conflicting records and an absent record. Do not weaken the exact-path/symlink/absence checks.

## Prior findings and requirement trace

| Prior concern / requested check | Source assessment at frozen ref |
|---|---|
| Child INT/TERM masks and exec vector | Gate, anchor and client bootstrap explicitly restore the saved pre-block mask. The client exec vector runs the driver through `sys.executable`; gate arguments preserve the requested executable and argv. Pure tests inspect and mock-execute both client and gate vectors. Actual native inherited masks and interrupt delivery remain unverified. |
| Accumulated observed-identity ledger | Adapter initializes the ledger and accumulates PID/start-second/start-microsecond tuples before RSS/cap rejection. Empty observations do not erase earlier tuples; the driver no longer writes completion. Complete-census observations are covered, not unsampled descendants. Final closure has finding 2. |
| Original work deadline | Main restores work560, closure575 and readback580 beneath cleanup585, with Cargo540 retained. Normal RPC deadlines are clamped to work stop. The client connection boundary remains finding 3. |
| Reserved final readback | Final adapter identity readback uses the reserved native-reader phase and launches no readback subprocess. It marks completion only after a complete listing without matching observed identities. Native calls are synchronous and only detect deadline overrun after return. |
| Cancelled dispatch | Pending/delivered cancellation and deadline are checked before gate spawn, anchor spawn and release. RPC errors stop normal dispatch; there is no ordinary post-error command retry loop. Startup timeout and final uncertainty acceptance remain findings 3 and 2 respectively. |
| RSS census identity | Resource sampling now obtains topology, PID/start identities and resident bytes from the same native listing, avoiding a PID-only join with `ps`. TASKINFO is bracketed by BSD identity reads including start microseconds, UID, parent and group. Failed lengths/inaccessible rows fail closed; KiB totals round up. This is a per-process consistent sampled census, not an atomic whole-system snapshot or continuous cap. |
| Conservative launch guard | `CUSTODY_IMPLEMENTATION_FROZEN = False` remains, and readiness is checked before native waitid/reader setup or client/command launches. This review does not authorize changing the guard. |

The pure tests provide useful coverage for exact vectors, masks, cancellation before setup, signal-once child reaping, native identity/RSS sampling, ledger union and deadline-aware readback. Their mocks, structure assertions and transcribed ctypes sizes cannot establish native ABI or lifecycle behavior. They currently omit the four integration boundaries above. This reviewer did not execute tests. The separately supplied root replay receipt at `/Users/hoppworks/projects/rhai-all-tickets/.scratch/all-tickets/macos-native-sampling-root-evidence/receipt.json` was read back and identifies the same frozen `b2db6448` source: positive and restored reader/adapter statuses are 0, wrong RSS rounding and removed identity-microseconds equality statuses are 1, and native/build/fixture/control/measurement launches are 0. The restored logs report 19 reader and 25 adapter tests passing; the two wrong-source logs report the intended assertion failures. That pure evidence supports those sampling regressions only and does not cover the material boundaries reported here. The coordinator reports native slots84 remain unchanged; this review consumed no native slot.

## Build-helper risk and remaining native proof

The named confinement review covers the conservative selected metadata candidates and identifies synchronously waited rustc probes plus wrapper/configuration/PATH and toolchain helper assumptions, including libc's `emcc` resolution. The root receipt describes locked metadata discovery, not an exact executed Cargo unit graph. The closed adapter environment removes inherited wrapper/flag variables and selects explicit Cargo/rustc/rustdoc paths, but does not turn those source inputs into runtime confinement proof. This review neither broadens their accepted coverage nor certifies the SDK/linker/xcrun/dsymutil behavior.

After correcting the combined material batch, source readiness must be reconciled at the corrected immutable revision. Separate existing prerequisites remain: installed Darwin BSD/TASKINFO/waitid ABI validation, bounded native interruption controls across registration/release/client EOF/timeouts, exact direct-child reap and retained-runtime error paths, accumulated identity and escaped-leaf readback, and independent receipt/runtime/scope cleanup readback. Permissions or inaccessible process rows must continue to fail closed; zombies under foreign parents must remain an honest incomplete-cleanup result under the owner's accepted contract.

In particular, `_identity()` now requires a full TASKINFO result for every enumerated PID, including foreign-UID/system processes, before it can return a complete listing. The fake API tests do not establish that the installed macOS permits those reads, or that zombie/taskless entries expose that structure. Native validation must establish whether this fail-closed whole-system census is operational on the actual machine without treating denied rows as absent or zero-RSS. BSD start identity bracketing also does not prove executable-image stability: a process can exec without changing PID/start time, and this revision reads its path only once. Repeated candidate absence remains conservative sampling rather than a universal certificate against arbitrary exec/path changes. The named build/toolchain confinement assumptions and escaped-leaf native controls must bound that gap before readiness is asserted.

No Cargo, build, fixture, native API, interruption control, measurement or tool install was run for this review. No native launch or resumed measurement is authorized by this document. The current false guard, existing cause09 history and original hard limits remain in force.
