# Release API and documentation review

Verdict: the named additive Rust API compatibility requirement is source-ready. The documentation/metadata requirement is not ready: three material documentation gaps remain below. This review does not close ticket06 or any unproved behavior criterion.

## Reviewed baseline and rules

- Source HEAD: `ba3b14988d9db9d1cfab191b6cbe404ec3c8248b`, owned `task/all-tickets-environment-recovery` worktree. Only the report was written. Concurrent coordinator-state edits were left intact.
- Loaded current `/Users/hoppworks/.agents/AGENTS.md`, worktree `AGENTS.md`, OCR Delegate and E2E Proof skills, `config/roles.toml` and campaign escalation brief template. The instruction repository independently resolves to `6830c49ed962a3dc1937d72d0d182150bb4c935c`; no copied prior instruction revision was used. Existing unrelated dirty instruction-repository scratch files were observed, not changed.
- Accepted contracts: local tickets02–06, `release-proposal.md`, `tcp-proposal.md`, relevant `docs/sys-package-plan.md` contracts, and narrow current state goal/evidence sections. Strict proof remains required.
- OCR is already available at `/Users/hoppworks/.local/bin/ocr`. Origin is the user's `hoppworks/rhai` fork. Deterministic commit preview and rules were used; no install, configuration, agent-home mutation, LLM endpoint or native execution occurred.
- This is one coherent API/documentation review. No security, performance, native lifecycle or full matrix review was repeated. The concurrent unfrozen post-spawn recipe work and stopped stdin/native110/Darwin/Windows paths are excluded.
- Planning checkpoint: 30 minutes active work, no extended checkpoint requested or used. Exact active elapsed was not instrumented at entry and is unknown; command wall times are not an active-work total. Costs/token billing are unknown.

## Findings

### Medium — missing function documentation leaves the metadata release criterion unfulfilled

Locations: `src/packages/net/stream.rs:541`, `src/packages/net/listener.rs:226`, `src/packages/net/error.rs:132`, `src/packages/sys/process/unix.rs:1672`; verification gap in `tests/net_metadata.rs:8` and `tests/sys_policy.rs:522`.

All TCP exported stream functions (reads, writes, close, shutdown and address/state access), listener functions and error getters lack function doc attributes. The `Child` id/try_wait/wait/kill registrations have no `with_comments` call. The class/module Rustdocs and `docs/sys-process.md` describe some behavior, but do not populate those individual metadata entries. `codegen/src/module.rs:155` sources exported-function metadata comments from the function's doc attributes, so the absence is a source-level fact. Manual registration requires comments explicitly, as the report getters already demonstrate in `src/packages/sys/process.rs:213`.

The accepted plan's R6 requires doc-comments on every function to render; release-proposal also requires metadata/documentation and executable examples. `tests/net_metadata.rs` only checks function names and custom-type names. `test_function_metadata` only checks `read_file`, any `# Example`, and `SysError`. Both can pass while every newly added handle function has empty comments. Add accurate comments to the script registration boundaries, covering units, mandatory/optional parameters, return/unit/error behavior, transfer/read semantics and clone lifetime where applicable, then validate actual metadata comments for each promised public handle operation. A passing name inventory cannot close this criterion. No runtime metadata rendering was claimed here.

### Medium — process-error getter documentation contradicts the additive variant's classification

Locations: `src/packages/sys/error.rs:62`, `src/packages/sys/error.rs:94`, `src/packages/sys/error.rs:114`, `src/packages/sys/error.rs:137`, `src/packages/sys/error.rs:146`.

`kind` is documented as the variant name, although `SysError::Process` deliberately returns its primary cause category (`Io`, `Timeout` or `OutputLimit`), not `Process`. The `io_kind`, `op`, and `target` comments say they apply to `Io` errors and are unit for other kinds, while their actual match arms also expose these fields from `ProcessCause::Io`. A Rust reader identifying the variant as `Process` can therefore conclude the report-bearing error loses classification/context when it does not. Update the comments to distinguish Rust variants from script failure categories and explain process-cause delegation. Retain the existing behavior and constructor payloads. Include a report-bearing I/O example or metadata check so this extension stays explicit.

### Medium — Rust host lifetime documentation implies cancellation on every cloned-handle drop

Location: `src/packages/sys/config.rs:235`.

The builder is documented as whether a child is killed when the script drops its handle. In the shared `Child` API, ordinary copies retain a shared `Arc<ClientLease>` (`src/packages/sys/process/unix.rs:187`); cancellation is requested by `ClientLease::drop` only when its final client lease is released (`:196`). Dropping one clone is not cancellation, and requesting cancellation does not synchronously prove reaping. `docs/sys-process.md:94` now documents the final-client and asynchronous semantics correctly. Align the public host builder Rustdoc with that contract, including the false setting's retained cleanup service and final-drop qualifier. This is a documentation correction, not a proposed lifecycle change.

### Low — incorrect whole-file Blob function name in the user-facing compatibility section

Location: `README.md:101`.

The section lists `read_blob` as a whole-file function. The actual whole-file registration is `read_file_blob` (`src/packages/sys/fs.rs:757`); `read_blob` is the handle operation. A user following this distinction can call the wrong overload with a string path. Change that name to `read_file_blob`. The surrounding shared cursor, no explicit close, strict streaming UTF-8, negative-length rejection and host/Engine cap descriptions agree with the source.

## Additive Rust compatibility evidence

The pre-process public sys boundary at `de9a97a41` was compared directly with current source (`git diff de9a97a41..HEAD` over config/error/mod). The following source compatibility conclusions are supported; no new compile check was run.

| Boundary | Evidence and conclusion |
| --- | --- |
| Existing `SysError` constructors | `Denied(String)`, `Io { op: &'static str, target: String, kind: io::ErrorKind, message: String }`, `Timeout(String)`, `OutputLimit(String)`, and `NotUtf8(String)` retain their names and exact payload types. Existing Display branches, traits and conversion into ErrorRuntime remain. |
| New process variant | Existing enum was already `#[non_exhaustive]`; `Process { cause: ProcessCause, report: ProcessReport }` is additive. External matches already require a wildcard. Proposal explicitly permits new process failures to use this new Rust variant; no prior process API exists in that baseline. |
| Host configuration | Existing fields are crate-private. Existing builders/signatures remain. Added `ProcessScope`, default `DirectChild`, `process_scope`, `process_scope_value`, and `max_file_read` do not invalidate external struct literals because those were unavailable. No script scope setter exists. |
| Report access | Public cause variants and public immutable report/diagnostic constructors and getters are re-exported. Rust can match `Process` for both cause and report; script `error.process` clones the report snapshot or returns unit. Report fields are private and script getters expose no mutation. Cause helper methods being crate-private do not prevent public variant matching. |
| Process registration | `Child` and execution adapter are Unix-gated; report/error types remain available across sys targets. The current docs correctly say Unix implementation and Windows production work remain open. Do not promote Windows to supported process behavior from package compilation. |
| Net boundary | Separate feature/config/error types, no sys dependency, separate exact connect/listen grants, positive host deadlines, integer milliseconds for script stream/accept requests, shared clone state and no-index Blob omission agree with the accepted TCP contract. Net handles are script-visible Rust wrapper types; their operational methods are private Rust implementation, not newly promised public Rust methods. |

The existing `SysError::kind` signature and existing constructors are unchanged. Adding variants to new public ProcessCause/ProcessExit is a future compatibility consideration because those new enums are exhaustive; there is no current baseline break requiring a change in this review.

## Documentation and registration checks

- `src/packages/mod.rs` gates sys and net separately; StandardPackage does not register either. Sys intentionally rejects no_object; both packages explicitly reject no_std and wasm. Core Cargo rust-version remains1.66.0; the optional1.77.2 contract remains documented, not inferred from the core manifest.
- Sys no_index omits run_raw, argument-array overloads, Blob input and array env_remove. String/map-based calls and indexed diagnostic method remain. Normal timed Child wait takes FLOAT; no_float takes INT seconds. The documented pending-unit versus completed-map/error distinction matches registration.
- Current process docs distinguish program-string allow-list/PATH authority from a sandbox; default run deadline, spawn timeout rejection, synchronous unbounded OS creation, overflow precedence, immutable partial report and honest incomplete managed cleanup are present. The source's actual adapter and option/result registrations match these descriptions at the boundary reviewed.
- TCP Rustdocs distinguish short reads/EOF, lossy per-call decoding, write count versus full transfer, clone-wide close/half-close and potentially interleaving cloned writes. File handle README explains its different zero/omitted read behavior, shared cursor and strict UTF-8. These divergences are explicit enough at the user-facing boundary after the low finding above.
- `NetError::partial_bytes` Rustdoc (`error.rs:120`) calls the count bytes captured; writes actually report bytes accepted by socket writes. This is a minor wording correction to include with the metadata comment batch: describe operation-specific received/accepted progress, without implying peer acknowledgement. Its implementation is bounded by the1MiB caps, so the INT conversion is compatible with accepted integer modes.

## Existing proof applicability and remaining criteria

No source test, Cargo, build, E2E, SSH or live process operation was executed. This is read-only source/evidence review, not new behavior acceptance.

`linux-process-example3-proof.md` and the completed acceptance section of `linux-process-example-review.md` retain scoped Linux Rust1.77.2 runnable sys/net/sys_process evidence: real Engine/OS effects, independent file/peer/child-record readback, meaningful wrong-expectation controls and exact cleanup. Direct Git comparison from frozen `20d25ad8` to this HEAD shows **no differences in src, Cargo.toml or examples**. Only the process document's host-policy clarification changed, matching the implementation. Thus those example inputs retain applicability, without rebuilding or copying evidence. This report did not re-audit all71 raw originals or reinterpret its proof as a matrix closure.

Earlier accepted filesystem/TCP/process slices and compiler rows remain retained at their recorded scope in ticket06 and current state. Their validity was not broadly re-certified here; no relevant source mutation was made by this review. The reviewed current top-level state explicitly leaves final current-source matrix and full release open.

Unresolved API/documentation/release criteria:

1. Correct the material comments and metadata gap above, then execute/render/read back the documented metadata surface. No current passing metadata names test proves per-function comments.
2. Execute actual Rustdoc/example checks appropriate to required supported feature combinations; existing no_run/Rhai fenced snippets are not automatically executable behavior proof. Current Linux runnable examples close only their documented Unix/default-float selected-feature slice; net no_object and non-Unix message claims retain their separately recorded evidence/coverage limitations.
3. Windows production process adapter, managed jobs, required native platforms, remaining lifecycle/error cases, feature/MSRV behavior and performance remain open per existing tickets/state. This report supplies no waiver or fresh acceptance. The concurrent post-spawn preparation is not frozen and not reviewed here.
4. No breaking constructor/payload change was found in the named existing Rust API. Compile-consumer compatibility was not newly executed; conclusions above are structural source evidence.

Concrete next action: one consolidated documentation/metadata correction package, preserving source behavior and previously valid proof; recheck only the changed comments/registrations and actual metadata output, then return to all approved tickets. Do not mark ticket06 complete from this report.

## Coverage

Primary bounded input coverage: all15 primary files reviewed: six sys files (mod/config/error/fs/process/process-unix), five net files (mod/config/error/stream/listener), process docs and three runnable examples. Supporting README, CHANGELOG, Cargo/package gates, codegen comment sourcing and existing metadata tests inspected where necessary. Proposals/ticket02–06 contract sections reviewed. No primary input skipped.

OCR's HEAD commit preview concerns proof/infrastructure files from the latest integration, not the requested API source set. Preview total_files162; reviewable_files60; excluded_files102 (OCR's own extension/binary exclusions). All60 previewed reviewable entries are explicitly skipped from code review below because this brief prohibits repeated recipe/native/custody review and their changes do not define the API/documentation boundary. Preview reviewed0/skipped60/coverage0%; **this is not a full HEAD commit review**. Rules were resolved for the primary source/docs inputs and used for the manually selected bounded API review. The per-entry accounting prevents those infrastructure files being silently treated as reviewed.

| Preview path | Status | Disposition |
| --- | --- | --- |
| `.scratch/all-tickets/check-linux-current-msrv-examples.py` | modified | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-523-evidence/collect-originals.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-523-evidence/drop-false-observer.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-523-evidence/launch.sh` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-523-evidence/linux-drop-false-proof.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-523-evidence/recipe-probes.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-523-evidence/stage.sh` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/collection-recovery.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/export-manifest.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/failed-run-inspect-readback.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/failed-run-retire-readback.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/independent-readback.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/root-independent-retirement-readback.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/stage-originals/archive-build-source.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/stage-originals/check-linux-current-msrv-examples.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/stage-originals/drop-false-launch1-allocation.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/stage-originals/drop-false-observer.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/stage-originals/launch.sh` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/stage-originals/linux-drop-false-proof.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/stage-originals/proof-evidence/commands.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/stage-originals/proof-evidence/early-runtime-identity.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/stage-originals/proof-evidence/export.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/stage-originals/proof-evidence/package-result.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/stage-originals/proof-evidence/source-restoration.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/stage-originals/runner/tools/agentskills/__init__.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/stage-originals/runner/tools/agentskills/pyguard.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-originals/stage-originals/runner/tools/run_scoped.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native1-retire.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/export-manifest.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/fresh-custody-before-retirement.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/fresh-custody-readback.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/independent-readback.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/provisional-read-only-diagnosis3.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/root-independent-retirement-readback.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/archive-build-source.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/check-linux-current-msrv-examples.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/drop-false-launch2-allocation.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/drop-false-observer.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/launch.sh` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/linux-drop-false-proof.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/proof-evidence/commands.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/proof-evidence/control-results.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/proof-evidence/direct-observer-live.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/proof-evidence/direct-observer-partial.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/proof-evidence/direct-observer-readback.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/proof-evidence/direct-red-terminal.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/proof-evidence/early-runtime-identity.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/proof-evidence/export.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/proof-evidence/managed-observer-live.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/proof-evidence/managed-observer-partial.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/proof-evidence/managed-observer-readback.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/proof-evidence/managed-red-terminal.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/proof-evidence/package-result.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/proof-evidence/source-inputs.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/proof-evidence/source-restoration.json` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/runner/tools/agentskills/__init__.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/runner/tools/agentskills/pyguard.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-native2-originals/stage-originals/runner/tools/run_scoped.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-preflight.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |
| `.scratch/all-tickets/linux-drop-false-slot-launch-wrapper.py` | added | Skipped: outside named API/docs scope; previously reviewed infrastructure/proof excluded by brief. |


## Affected follow-up review: frozen metadata candidate 8bf8bad

Reviewed candidate `8bf8bad611cb4496c63062081bb0a4451c61b9eb` in `/Users/hoppworks/projects/rhai/.worktrees/stdlib-api-metadata`, relative to original reviewed baseline `ba3b14988d9db9d1cfab191b6cbe404ec3c8248b`. Live instruction revision remains `6830c49ed962a3dc1937d72d0d182150bb4c935c`; no instruction reload was needed. This is an affected-delta continuation of the same combined review, not a new behavioral acceptance review. The working-tree Child comment changes in `src/packages/sys/process/unix.rs` are dirty, unfrozen and excluded.

**Verdict: correction batch required; native metadata acceptance pending.** The schema correction is valid, but the frozen TCP metadata assertions have deterministic comment mismatches. No Cargo, native execution, SSH, fixture creation or cleanup was performed. This source assessment does not claim a test execution result.

### Material findings in this candidate

1. **Medium — new TCP metadata test cannot pass its own literal assertions.** `tests/net_metadata.rs:60–68` requires `direction` for both shutdown methods, `clones` for every `close` overload, `peer` for `peer_addr`, `kind` for `kind`, and `message` for `message`. The per-function assertion at line 84 searches only each exported function's `docComments`; function names and enclosing type comments do not supply the missing words. The actual comments are:

   | Function | Frozen comment location | Mismatch |
   |---|---|---|
   | `shutdown_read` / `shutdown_write` | `src/packages/net/stream.rs:549`, `:556` | receiving/sending, but no `direction` |
   | stream/listener `close` | `src/packages/net/stream.rs:543`, `src/packages/net/listener.rs:228` | singular `clone`, but no `clones` |
   | `peer_addr` | `src/packages/net/stream.rs:569` | `remote`, but no `peer` |
   | `kind` | `src/packages/net/error.rs:135` | `category`, but no `kind` |
   | `message` | `src/packages/net/error.rs:141` | `explanation`, but no `message` |

   Align the assertions with their intended semantic requirement or make the comments use the required terms while preserving their accurate meaning. Keep checking every overload. The schema fix alone cannot make these checks GREEN; allocating a native run before correcting them would not resolve this known source mismatch.

2. **Medium — new read metadata incorrectly equates every empty result with EOF.** `src/packages/net/stream.rs:700`, `:717`, `:766` and `:781` make this assertion for the four `read_blob`/`read_string` timeout forms. The unchanged shared implementation returns an empty result immediately for a zero request at `stream.rs:405–406`, without observing the socket. The accepted contract and existing type rustdoc distinguish positive-length EOF from zero-length reads. State that zero returns immediately and that an empty result for a positive request indicates EOF. This is a documentation correction, not a newly discovered runtime defect.

3. **Low — process kind metadata retains the misleading original lead sentence.** `src/packages/sys/error.rs:99` still says “Name of the error variant,” although a `SysError::Process` value reports its primary cause category. The added qualification at lines 110–111 correctly explains the Process case but does not make the lead sentence accurate. Change the lead to error/cause category. This is the remaining portion of initial finding 2, not a separate API compatibility regression.

4. **Low — read-to-end metadata omits the effective cap.** `src/packages/net/stream.rs:733`, `:749`, `:796` and `:811` describe stopping at EOF or requested `max_bytes`. The unchanged implementation at lines 431–435 also bounds the result by host and applicable Engine limits; it can return before either named condition. Say “effective byte cap” and identify the requested, host and Engine bounds. This makes generated per-function metadata useful without requiring readers to find enclosing module comments.

### Corrected source criteria and remaining acceptance

- `src/serde/metadata.rs:72` uses `rename_all = "camelCase"`, with `doc_comments` at line 94. Thus `docComments` in both new tests is the correct serialized key. The earlier `doc_comments` test key was invalid evidence; its correction is confirmed by source, not by a new execution here.
- All changed TCP exported methods now have function-level documentation, including timeout overloads. The new write and `partial_bytes` metadata correctly describe socket acceptance rather than peer acknowledgement. Public Rust `NetError::partial_bytes` rustdoc at `net/error.rs:120` still uses the earlier “captured” wording; the initial minor recommendation remains applicable to that public host-facing documentation.
- The changed plain `SysError` documentation for I/O cause delegation is consistent with the unchanged getters. `SysConfig::kill_on_drop` now describes final shared-client drop and asynchronous cancellation, matching the original reviewed source. README now names `read_file_blob`, matching registration. These source corrections address their respective initial findings subject to the residual kind lead sentence above.
- The new Sys metadata check deliberately requires Child method comments. It is not ready for acceptance until the separately prepared Child delta is frozen and reviewed; missing frozen Child comments are a known planned dependency, not an additional finding against this candidate. Neither TCP nor Sys metadata has accepted native proof at this revision.
- Parent-supplied run history is preserved as status, not independently re-reviewed proof: native1 RED/GREEN used invalid `doc_comments`; native2 was terminated with status 143 during setup before an assertion because of admission error; native3 was waiting on the heavy-run gate. None closes corrected-schema metadata acceptance. Preserve the raw records and use a corrected candidate for actual public Engine metadata read-back.
- Original additive Rust API compatibility conclusions and accepted Linux example proof applicability are retained. This delta changes documentation/metadata and its tests, not operational runtime bodies, so it does not justify repeating the unchanged example build or broad security, lifecycle, performance or platform matrix reviews. Runtime/platform criteria already open remain open.

### Delta selection and scope

OCR deterministic range preview selected seven reviewable Rust files: `src/packages/net/{stream,listener,error}.rs`, `src/packages/sys/{config,error}.rs`, `tests/net_metadata.rs`, and `tests/sys_policy.rs`. All seven were reviewed; zero selected Rust files skipped. `README.md` was excluded by OCR as unsupported extension and reviewed manually. Actual range contains eight changed files, 149 insertions and eight deletions. `git diff --check` for the frozen range is clean. The metadata serializer and unchanged bounded-read implementation were consulted only as affected dependencies. No dirty Child source, unrelated proof history, or foreign work was reviewed or modified.

The 30-minute active-work checkpoint remains a planning estimate. Exact cumulative active elapsed and usage/cost remain unknown; this continuation does not reset earlier consumption or imply an extended hard cap. Only this report was appended.


## Affected correction review: 07862c3a8 and Linux metadata helper

**Verdict: NOT READY for the proposed metadata acceptance run.** Reviewed frozen `07862c3a8ed3707956aba16f1d4bd9f66cd57cbb` against `8bf8bad611cb4496c63062081bb0a4451c61b9eb`, plus root's source-only `.scratch/all-tickets/api-metadata-evidence/linux-metadata.py`. Instructions remain revision `6830c49ed962a3dc1937d72d0d182150bb4c935c`. Dirty `sys/process/unix.rs` Child comments remain excluded. No build, Cargo, SSH, native process or source modification occurred. Native metadata acceptance remains pending; previous raw run histories and initial additive API/source-proof conclusions are retained.

### Consolidated remaining findings

1. **Medium — TCP GREEN still has a deterministic incidental-wording mismatch.** `tests/net_metadata.rs:105` requires `underlying io error kind`, but the unchanged function-level getter comment at `src/packages/net/error.rs:147` says `Underlying I/O error kind`. The lowercasing/joining at test lines 59–61 does not remove the slash. The actual documented meaning is correct, but this comparison cannot pass. Match the accepted spelling or normalize the I/O concept deliberately; do not alter correct documentation merely to satisfy accidental punctuation assumptions. The earlier shutdown/clone/peer/category/message mismatches are otherwise corrected by the revised assertions.

2. **Medium — revised timeout helper lost the proof that both timeout forms exist.** `tests/net_metadata.rs:113–121` finds one function with a `timeout_ms` parameter. It never requires an untimed form or expected arities/counts. The former explicit two-`write_string`-overload assertion was removed. Removing an untimed read/write overload would still pass the new name-presence, comment and timeout checks, even though the accepted surface promises both forms. Require the expected timed and untimed parameter signatures for each paired read/write name, and retain the single timed accept form separately. This is an acceptance-test gap; the current source still registers both promised forms. Meaningful semantic checks should constrain promised API concepts and signatures, rather than incidental prose punctuation.

3. **Medium — metadata helper GREEN and SYS RED checks are too weak to establish the intended controls.** `linux-metadata.py:38` checks the process status via the existing `run_command`, but only RED branches inspect output at lines 41–46. For `tcp-green`, `sys-green` and `integrated-tcp-green`, status 0 with zero matching tests would be recorded indistinguishably from the intended named test passing. Require the named tests' success records and expected nonzero test counts, plus the appropriate `TCP_METADATA_JSON=`/`SYS_METADATA_JSON=` record for later independent JSON read-back. For SYS RED, the generic `metadata comments should mention` diagnostic is not specific to missing Child comments: any required SysError comment failure has the same text. Bind the negative control to the expected missing Child function/requirement (currently the first required missing Child getter), rather than accept an unrelated metadata assertion failure. This is source review, not an observed zero-test or wrong-cause native run.

4. **Medium — helper's fix handshake lacks reviewed assertion/source binding and early provenance export.** `linux-metadata.py:26` compares archive bytes with the supplied manifest hash; line 61 accepts a replacement `sys-fix` entry from `sys-fix-ready.json` without requiring the reviewed revision, unchanged TCP/Sys metadata assertion bytes or a bounded Child-only change. A valid archive hash alone cannot show that SYS GREEN kept the RED assertion intact. `results` records the supplied source entry only after a case succeeds (line 47); a failed compile/assertion before that point exports command logs without that attempted input binding. Before each command, persist/export the source revision, archive hash, lock hash, relevant source/test hashes and assertion identity. At the handshake, verify the frozen reviewed metadata test bytes remain unchanged and identify the exact Child correction revision; preserve the ready record outside the private runtime. The TCP RED archive likewise must bind the accepted baseline plus exactly the reviewed new test. Root may construct this provenance deterministically when freezing/staging, but the present helper/absent staging manifest does not yet establish it.

These are one correction batch for the already authorized metadata requirement. No additional broad framework, example, lifecycle or native matrix review is implied.

### Corrected documentation and retained conclusions

- All four newly documented length-based reads now distinguish immediate zero-length return from positive-request EOF, matching `stream.rs:405–406`. Initial follow-up finding 2 is source-corrected.
- All four read-to-end metadata comments describe the effective minimum of requested, host and applicable Engine caps, matching `stream.rs:431–435`. Initial follow-up finding 4 is source-corrected. Checked string decoding may separately reject expanded lossy output beyond the Engine string limit (`stream.rs:372–384`); the new comments do not remove that existing bound.
- SysError kind's lead now says script failure category, with the Process primary-cause qualification preserved. Initial follow-up finding 3 is source-corrected.
- Newly expanded connect/listen port ranges, ephemeral listen port, host deadlines, accept timeout cap, write input bounds and local-address failure after close match their unchanged affected implementations. No operational runtime bodies changed in this range.
- The public metadata serializer still uses `docComments`, and `params` entries expose `name`; the revised timeout lookup is schema-correct. TCP documentation is now present for every observed overload. Dirty Child metadata remains a planned separate freeze/review dependency, not a new missing-source finding.
- Initial Rust API additive compatibility conclusions, previous unaffected Linux example proof applicability and open platform/release criteria remain unchanged. This correction does not close ticket06 or the full campaign.

### Targeted helper readiness assessment

The helper imports the unchanged sampler/run-command implementation, which enforces 540-second helper / 510-second work limits, two jobs, 16 descendants, 1.5 GiB preemptive storage and 2 GiB hard RSS/storage limits. It uses the cached native Linux 1.93.0 Cargo/rustc directly, private Cargo home/target outputs, accepted lock copy and one extracted private source tree. It clears inherited Rust flags/wrappers and performs bounded command execution. This proposed check is metadata acceptance on Linux 1.93.0, not optional-package MSRV proof.

Per-case original command files are copied after successful cases; the `finally` copies partial logs on later command/assertion failures and checks the export deadline. The SYS fix wait checks the unchanged work deadline every second, so it does not authorize extending the 540-second budget. The 585-second runner/600-second outer bounds are parent-provided launch prerequisites; no new launcher has been executed or reviewed here. The `try/finally` starts after initialization, so the helper does not promise partial export for failures before entering that block. `resource-maxima.json` contains sampled maxima, not a continuous peak measurement; preserve the runner's stdout sample records (or export the raw `b.SAMPLES`) with original evidence. The original runtime and custody/retirement acceptance rules remain applicable.

The helper compiles as Python source (AST/syntax check only). Neither intended RED nor GREEN was executed by this review. Review of immutable archive/manifests and the updated handshake/control assertions remains necessary before native readiness, followed by actual public metadata read-back after execution. The old invalid-key native1 and setup-terminated native2 evidence do not close these corrected checks.

### Scope and measurement

OCR deterministic range preview selected exactly five Rust files, all reviewed, zero excluded/skipped: `net/listener.rs`, `net/mod.rs`, `net/stream.rs`, `sys/error.rs`, and `tests/net_metadata.rs`. Frozen range is 98 insertions/54 deletions; `git diff --check` is clean. Existing rule selections remain applicable; dependencies read were the metadata serializer, unchanged affected networking bodies, current Sys metadata assertion and the existing bounded sampler/run-command. Root helper was separately reviewed because explicitly named in the brief. No unrelated history or dirty Child implementation was reviewed. Only this report was appended.

The 30-minute active-work checkpoint remains a planning estimate; exact cumulative active elapsed and cost remain unknown. No previous resource/cause consumption was reset. The next coherent action is the small consolidated source/test/helper correction, its affected readiness recheck, then the already authorized shared TCP baseline RED / corrected GREEN and specific Child metadata RED / frozen Child GREEN with independent JSON read-back.


## Affected contract review: 09ebce31f and root metadata helper

**Verdict: NOT READY. Native launches by this review: 0.** Reviewed immutable `09ebce31f` against `07862c3a8`; only stream.rs and net_metadata.rs changed (68 insertions/21 deletions). Dirty Child comments remain excluded. Current loaded instruction revision is independently confirmed `6830c49ed962a3dc1937d72d0d182150bb4c935c`. Read escalation21 diagnosis and its saved source-preflight output; preserve the same exhausted `api-metadata-contract-assertions` cause and ONE bounded follow-up history. No additional correction or native allocation is authorized on this path.

**Material frozen assertion defect:** `tests/net_metadata.rs:136–139` routes only `accept` to NetListener and all otherwise unmatched names to NetStream. `require_comments("local_addr", ...)` at line102 consequently excludes its sole TCP export: `src/packages/net/listener.rs:242` receives `&mut NetListener`. The helper returns an empty list, and line55 fails with `metadata omitted TCP function local_addr` even for the correct exported metadata. This receiver-selection defect invalidates candidate GREEN. The saved source preflight checks source comment concepts and available signatures, not this new filtering logic; its PASS does not close the defect.

The prior I/O spelling mismatch is corrected; timed write_blob now accurately documents short results. The new signature assertions require exact counts, ordered parameter names and numParams consistency for the eight timed/untimed pairs, plus timed-only accept; both forms retain common semantics and every timed form retains positive-millisecond units. Receiver filtering is appropriate for the other reviewed names. Schema `params[].type`, `docComments` and `numParams` matches current src/serde/metadata.rs. Additive Rust API/source conclusions and unchanged behavior proofs retain their previous applicability.

**Root helper finding:** `api-metadata-evidence/linux-metadata.py:71,75` requires contiguous `test <name> ... ok`, but both named tests print their JSON under `--nocapture` before completion. Existing raw green.stdout already shows `test metadata_documents_tcp_handle_operations_and_overloads ... TCP_METADATA_JSON={`. The harness completion `ok` follows the captured JSON, so successful intended tests need not contain either required contiguous success string. Preserve named-test attribution and exact nonzero counts while accepting the actual nocapture record structure; do not drop the JSON output requirement. Helper source SHA-256 reviewed: `bbe73fbe794a7ba3c79325fde7375767e2591b342b2109e9454653b637b66ddd`.

Other requested helper corrections are present at source level: exact intended SYS id/identifier RED; named TCP RED reason; nonzero expected GREEN counts and public JSON markers; complete source file maps/extracted hash equality; pre-command provenance export; Child-only differing-file handshake with reviewed Child hash; raw sampler export and finally export of partial command evidence. Their package binding remains pending. The local old linux-sources.json intentionally records unlaunched 078 preparation and is not the new candidate: do not classify its obsolete revision/missing files maps as a failed Expert21 correction. A new immutable manifest/archive binding to the reviewed assertion source would still be required before execution, and cannot rescue this rejected frozen assertion candidate.

OCR range selection and applicable rules were resolved deterministically: two files, both reviewed, none skipped. git diff --check is clean. No build, Cargo, SSH, native action, deletion, source edit or new fixture occurred. Source-ready is not generated metadata acceptance; ticket06/overall campaign and SYS missing Child documentation remain open. Prior raw histories, elapsed consumption and proof limitations remain intact; cumulative active elapsed and costs are unknown.
