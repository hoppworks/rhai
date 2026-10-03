# Linux shared Child preparation combined review

Status: ready for the single recorded bounded native invocation after the two preparation defects below were corrected. This is source readiness, not native acceptance. No build, SSH, native execution, Git mutation, or descendant review was performed.

## Loaded rules and scope

Loaded current `~/.agents/AGENTS.md`, project `AGENTS.md`, campaign, e2e-proof, ocr-delegate, and `config/roles.toml` from `/Users/hoppworks/projects/agent-skills`; its observed HEAD is `faba3db`. Strict verification applies. Reviewed the three new scripts against accepted scalar equivalents and frozen `tests/fixtures/sys_process_shared_child_contract.rs`; checked the relevant command/environment/restoration functions of the unchanged accepted base helper. Source remains `2a8fdc49a37b780c63e5c30b141c345321a876d0`, archive `4da36cb9603354ce35dccb89a6d5e59da6da3d734414e46e79f9571b20d5fd1a`, lock `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`, root `0fca4e88fbcbada2c9934feee6c6f53fb29fa644`.

OCR deterministic workspace preview selected exactly the three new scripts (all added). All three reviewed: total_files=3, reviewed_files=3, skipped_files=0, coverage_rate=100%. Its 15 excluded entries were the brief and unrelated unsupported log files. Rule resolution supplied Python and default correctness/resource/test rules. The initial commit preview selected accepted scalar artifacts; these were context, not a renewed broad review. The explicit foreign-repo empty rule override was used conservatively; observed origin is the owner's fork.

## Findings and affected-delta recheck

1. **High, resolved — missing fixture runtime environment.** Initial proof helper lines 107–114 omitted `AGENT_RUNTIME_DIR` from the explicit Cargo environment. Accepted `run_command` passes that environment directly into `subprocess.Popen`; it does not merge the helper environment. Every real scenario reaches `FixtureDir::new`, whose frozen line 459 requires this variable. The intended wrong-exit assertion would therefore be unreachable. The coordinator added `AGENT_RUNTIME_DIR: str(runtime)` to that exact environment. Independently read back the changed source: the variable now reaches Cargo/test and is forwarded by the bounded scenario controller into its clear environment. No fixture/source change needed.

2. **High, resolved — impossible positive log receipt.** Initial `verify_positive_row` required `bytes=8388608 valid=true`. Frozen fixture writes this to `child.consumed` and reads/asserts the full PID/byte-count/validity record at lines 216–218, but never prints it; successful fixture cleanup removes the file. A fully green native run would consequently fail the helper verifier. The coordinator removed only this impossible stdout/stderr requirement. Independently read back the changed verifier and frozen contract: the real independent persisted-record assertion remains mandatory in the named passing test. The remaining required receipts are emitted by the contract. No source or acceptance weakening is implied; the persisted record is checked by the controller rather than exported as a separate log file.

No unresolved material findings in the reviewed package. The coordinator reports lightweight syntax and normal/sync verifier flow checks, including all nine missing receipts, nonzero status and missing-sync rejection; those checks are supporting preparation evidence, not native proof reviewed here.

## Correctness and proof applicability

The filter runs every shared_child_contract test serially, with seven tests in normal and eight with sync; both include no-op helper entry tests, so counts alone are insufficient. The verifier additionally requires the named substantive tests and real final-drop/stable-wait/reaping receipts, plus sync cancellation for sync rows. The three explicit feature rows cover normal, sync, and sync+no_float. No no_index or no_object shared-Child claim follows.

The sole negative overlay changes the unique first exit-code assertion from 17 to 19 in the disposable source copy. The child still exits 17 through the real Engine spawn/wait path. Cargo status 101 plus left:17/right:19, the intended test name and FAILED diagnoses distinguish expected assertion RED from unrelated infrastructure failure. A finally restores original bytes; a hash check precedes each GREEN; restoration evidence and post-run lock/manifests are exported. The restored assertion, snapshot mutation check, independent fixture-record read, repeated post-completion kill, and ESRCH observations remain in frozen source. The panic regression also checks the intended payload and production-reap receipt, while its own success/unrelated-panic controls reject false success.

The sync signal is sent before the public wait call, so this proves the recorded bounded concurrent cancel/wait behavior, not observed blocking condvar entry. Preserve that limitation. Shared Child correctness does not establish externally forced controller custody, managed process-group functionality, or Windows/macOS behavior.

## Custody, limits and required native readback

Launcher differs from accepted scalar launcher only in exact package paths/helper name. Staging preserves the frozen source/archive/lock pins and uses the absent exact stage/scope `linux-shared-child-20261003-2a8fdc49`. Accepted base primitives remain pinned `59ac8b7b9c71ab2331c13196b36d8d2794931e07138741c43d4a8c3d1d754b06`. Outer600/scoped585/helper540 including30 export, jobs2, descendants16, 2GiB policy and sampled storage stop1572864KiB remain unchanged. Sampling is honestly labelled periodic rather than a continuous peak. No prior stopped cause is renewed. State retains native count85; 86 is consumed only on actual dispatch.

Native acceptance remains pending six intended RED/GREEN controls, actual command statuses and toolchain/feature receipts, restored test hash and unchanged manifest/lock receipts, process identities and exact PID/start/group closure readback, runtime absence and exact empty-scope retirement, resource/export receipts and independent root readback of the exported evidence. Package `acceptance_claim=false` is appropriate until that review. Missing or inconsistent receipts block the affected claim; runner exit or helper aggregate booleans alone do not close acceptance.

## Reviewed identities after correction

- `linux-shared-child-proof.py`: `eed5ca414da18e15e666cf70c241c1f5693f9d49fb502413e8cc532d7b2abab0`
- `linux-shared-child-stage.sh`: `799de1faf641406762b908f441e5b9e8355b39ba6d573ea0530463577c5908f9`
- `linux-shared-child-launch.sh`: `7604d4542a949e60309d7a42492fa71737ba101eb6c0c7ecf88570dc9bc65ab0`

Retain this responsible context for an affected delta or native evidence review. No further broad review is needed solely because native receipts arrive.

## Invocation 86 compiler outcome and bounded recovery review

This addendum supersedes the earlier source/archive/stage identities for the next invocation. Current rules remain `faba3db`; no broader review, native execution, SSH or build was performed.

Read invocation86's original `row-0-wrong-status.stderr`: E0308 at frozen fixture line52 passed a `String` to `closure_receipt`'s `&str` argument. Read outer-status and run-scoped.status: both1. No intended RED assertion executed. This is an infrastructure/compiler outcome and the first recovery for this cause, not expected RED or failed product acceptance. The initial source-readiness review missed this compiler defect in the inherited fixture; its readiness statement did not establish compilation.

Independently reviewed committed diff `0fca4e88..4bb0848f`: exactly one fixture line now calls `closure_receipt(&root, &scenario, ...)`. The shared borrow deref-coerces String to str, lives through the synchronous formatting call, and preserves scenario/receipt content, ownership and panic cleanup behavior. It changes no product behavior, assertion or required acceptance criterion. Commit author/committer are both hoppworks. Deterministic OCR commit preview excluded this test fixture by default_path; explicitly read and reviewed the delta anyway, with resolved Rust ownership/lifetime rules. Affected fixture coverage: one reviewed, none skipped.

Read back the updated recipe pins and exact new stage/scope consistently across helper, stage script and launcher. Independently computed the frozen Git archive hash. New source is `4bb0848f8731df5896c789e9ec4f18c57891d00c`; archive is `80203d948788f0f356b9a23f2bbd3d1c811d8b79f9208aaaa8c6f994c34e246d`; exact stage/scope suffix is `linux-shared-child-20261003-4bb0848f`. Existing base and compatible-lock hashes remain unchanged. The earlier consumed stage is not reused. Coordinator reports its exact cleanup/readback separately; no remote cleanup claim was independently established in this source review.

Current scripts independently hashed:

- proof: `faa7c1667921df0749fb121c1237e4b5f143c45cf57fe96acd8766c7b06b3073`
- stage: `c2738092cb6aae6d1f993f07e27594d2e5acddf70fe639e16b848fd6b794ac08`
- launch: `9db008814a191585fd0bf74989f0005b1f995955b9779eebd8da1b3e724f97e2`

Readiness: no remaining material blocker identified in this affected delta. Ready for the recorded bounded recovery invocation with unchanged three-row RED/restored-GREEN requirements and unchanged resource/time limits. Compilation and native behavioral acceptance remain unverified until that invocation and independent evidence review succeed. Invocation86 remains consumed in cumulative history; the next dispatch spends its next native count rather than resetting history.

## Invocation 87 native acceptance evidence review

Status: accept the bounded native Linux shared Child correctness package at source `4bb0848f8731df5896c789e9ec4f18c57891d00c`, for the three explicitly recorded feature rows and criteria below. This supersedes preparation-only status for those criteria. Rules `faba3db` remain loaded. This review read exported native evidence and the coordinator's independently collected root readback; it did not launch tests, use SSH or execute native commands.

Evidence references are `.scratch/all-tickets/linux-shared-child-evidence-87/`, `linux-shared-child-outer-evidence-87/`, and `linux-shared-child-root-readback-87.json`. Independently hashed saved `executed-proof.py` and `executed-launch.sh`: they match reviewed hashes `faa7c1667921df0749fb121c1237e4b5f143c45cf57fe96acd8766c7b06b3073` and `9db008814a191585fd0bf74989f0005b1f995955b9779eebd8da1b3e724f97e2`. Source-inputs records the reviewed archive/base/compatible-lock pins. Version output confirms Rust/Cargo1.77.2, x86_64-unknown-linux-gnu, native Linux. Commands identify private toolchain executables, `--locked`, the shared_child_contract filter and `--test-threads=1`.

| Features | Wrong first exit code17→19 | Restored complete contract |
|---|---|---|
| testing-environ,sys | Cargo101; intended named test FAILED with left17/right19 | Cargo0;7 passed,0 failed,0 ignored |
| testing-environ,sys,sync | Cargo101; same intended assertion diagnostics | Cargo0;8 passed,0 failed,0 ignored |
| testing-environ,sys,sync,no_float | Cargo101; same intended assertion diagnostics | Cargo0;8 passed,0 failed,0 ignored |

These observations were read from original row stdout/stderr/status and commands, not inferred from the helper aggregate alone. All restored rows contain stable-wait/try-wait, final-drop true/false and production-reap receipts; the sync rows contain actual waiter_returned/final_wait/reap receipts. The expected success-rejection and unrelated-panic rejection diagnostics are present in passing control-test output. The panic regression includes the intended payload, independent fixture exit-record read and production-reap verification. The borrowed scenario receipt path therefore compiled and executed successfully in native coverage.

Covered criteria through the real public Engine and actual OS child fixtures:

- Spawn returns while the 8MiB stdin fixture remains held; public finite wait returns unit. After explicit release, the controller independently reads and exactly asserts the fixture-written consumed record (PID,8MiB,valid input); that record is asserted in the frozen test rather than separately printed/exported.
- Final wait returns code17, exact stdout/stderr and completeness; repeated wait/try_wait snapshots survive caller mutation; two post-completion kills preserve cached status/output and completion flags.
- Nonfinal shared-handle release preserves operational child access, verified by a child-written challenge reply. Final release with kill_on_drop=true reaps; kill_on_drop=false permits another operational probe, then explicit release and eventual reap.
- Intentional scenario panic releases its live fixture, preserves the worker's production reap, and independently validates the identity-bound receipt and persisted exit record. Successful and unrelated-panicking controllers are rejected by the panic expectation.
- With sync (including no_float), another shared handle cancels the bounded concurrent waiter, followed by successful final wait and fixture absence.
- The wrong exit expectation fails at its intended assertion in each native feature row; restored exact source passes afterward. This validates the exit/status assertion's sensitivity, alongside the frozen panic-expectation controls.

Restoration evidence's original fixture hash `e293076113feba1708bc45cb5ff5a3c811c1b3d4c049752505cddf616ad40427` independently matches current frozen fixture bytes. Private overlay hash is `2dd4849bca7d5ac587e89c0a2f19529d69377239bdd2b053951f6fef68f17110`; restored_test_matches_original=true, restoration_error=null. Before/after manifest maps match exactly; compatible lock remains `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.

Outer and scoped statuses are both0. Launcher cleanup receipts report runtime absence and empty-scope retirement. Independently collected root-readback records127 PID/start identities all absent,80 controller/fixture PID receipts all absent, empty live_scoped_groups, runtime_absent=true and scope_absent=true. The exact identities and absence arrays were inspected, not just counts. These establish successful-run closure; they do not establish externally forced-controller custody.

Resource receipts record export entry at43.682s; sampled maxima RSS893368KiB, storage930176KiB and descendants7 remain below declared limits. Measurements are periodic sampled maxima, not continuous peaks. Invocation86's compiler failure remains preserved and consumed; invocation87 is the successful first compiler recovery, without resetting history. Exact staged-input cleanup follows the coordinator's hash-guarded lifecycle and is separate from the verified disposable runtime/scope closure.

Limitations remain unchanged: sync evidence does not prove observed blocking condvar entry; no externally forced controller termination/custody, managed process-group behavior, Windows/macOS, collection-disabled shared-Child feature rows or entire release matrix is claimed. No claim beyond this frozen shared Child contract follows from7/8/8 test totals. Within the named Linux correctness criteria, no remaining material acceptance finding was identified.
