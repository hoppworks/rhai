# Process example combined independent review

## Verdict

**NOT READY for native execution preparation** at `012e20f70dbef81fe08954af96459e59a03d1caf`, compared with `2518238beae7ade7e59f5abd7edf1ce209a4c2e3`. Consolidate the two material findings below into one repair. This is a distinct example package; the stopped stdin classifier and its consumed Expert18 follow-up remain stopped, with no reset, allocation, or acceptance.

Applicable agent-skills revision independently confirmed unchanged: `faba3db3bef6891ad2c0b20d434963bb8fe9572d`. Named Expert review; campaign, e2e-proof and ocr-delegate instructions retained. No Cargo, native run, SSH, staging, push, source edits or runtime cleanup occurred. Preparation review is not compilation or OS acceptance.

## Material findings

1. **Readiness publication races the host reader** — `examples/sys_process.rs:64`, `:214`. The child uses `fs::write(spawn-ready.txt, ...)`, which creates/truncates the final path before writing the PID. The parent treats `is_file()` as complete publication and immediately reads/parses it once. A legitimate schedule lets the host read an empty or partial record, so a correct API run can fail before the intended pending-wait/RED assertion. Publish a complete record atomically (write a separate owned path, then rename), or poll complete validated content under the existing deadline with explicit I/O handling. Preserve exact child-ID validation, the release gate, and the meaningful pending-wait assertion. A lightweight local filesystem model independently observed `is_file() == true` with empty contents while the writer had opened the file but had not written its bytes; this is a model of the actual ordering, not native reproduction.

2. **Scoped runner has the wrong bound and races the outer deadline** — `launch-linux-current-msrv-examples.sh:59`, `:81` versus contract's 585-second scoped bound. The launcher prints `runner_timeout_seconds=600` and passes `run_scoped.py --timeout 600`, while its own wait limit is also 600 seconds measured before runner startup. At the outer limit it explicitly leaves the runner and scope for later readback. The contract instead requires 600 outer / 585 scoped / 540 helper including restoration/export/cleanup. Use the promised 585-second runner bound and leave finite outer time for exit, group/readback and scope cleanup; preserve failure/partial evidence if that margin is exhausted. The helper's 540-second deadline is cooperative: export checks between files, not during a `copy2`/`copytree` operation. Do not describe that as an independently enforced per-copy hard limit; retain the enclosing runner limit and honest partial-export failure handling.

## Coverage and reasoning

All seven changed files reviewed. OCR deterministic preview selected five code/manifest/script files and excluded the two Markdown files as `unsupported_ext`; both Markdown files were explicitly included in rule resolution and manually reviewed. Reviewable coverage is 7/7 (100%), skipped 0. `OCR_NO_UPDATE=1` used; no installation/update. Preview/rules covered correctness, manifest/feature compatibility, ownership/error handling, concurrency, resources, boundary checks and testing. No extra specialist pipeline was created.

The production public API was read only where needed: Unix `run` returns the text map; `spawn` returns `Child`; `child.id` is a property; floating-point `wait(0.0)` returns UNIT while pending and a text map when terminal; cloned handles share the lease/cache. Default scope is DirectChild and kill-on-drop is enabled. No production or test change occurs in this package. The example intentionally launches only its own absolute executable through `ProgramPolicy::AllowList`, clears the child environment to the two fixture values, uses finite release/wait deadlines, checks nonzero exit as data, success/completion/timeout flags and captured text, compares repeated maps, and reads child-created records through host filesystem calls.

The cleanup guard is installed immediately after successful spawn and inexpensive clone/path operations. Unwind writes release, requests kill and polls bounded wait; the fixture independently stops waiting after five seconds, and package-owned lease/service cleanup remains responsible for reap on error. Its `Err(_) => return` is not proof of terminal success; the example does not emit such a claim. Happy-path terminal waits precede setting `finished`. Temp-directory removal errors are ignored by the example but the helper explicitly rejects matching leftover directories in its private TMPDIR. Launcher readback checks recorded helper/supervisor/command PID-start identities and scoped groups, then removes only the empty exact scope. These are preparation safeguards, not observed child/host cleanup receipts. Actual failure and happy paths remain unverified.

Cargo's `sys` example requirement matches the package feature gate; `sys` requires std/object-map support and is incompatible with no_std/no_object/WASM. The docs honestly limit this runnable example to Unix with floating-point support. The non-Unix main only prints an unsupported message; its successful exit cannot satisfy process acceptance. The recipe's supported profile `testing-environ,sys,net` on Linux x86_64/private Rust 1.77.2 excludes no_float. No Darwin, Windows or all-feature acceptance is claimed.

The new stage/scope/proof destination are distinct from historical sys/net locations. Their old evidence is not written by these scripts or asserted to cover the process example. Source/archive/lock/helper pins are consistent with the reviewed package and source `c0d0afd63383065783794337749289ffd5831722`. The stage script hashes transferred files into its manifest and validates source/lock/runner/helper fixed pins; independent prelaunch comparison of every recipe byte to this frozen review is still required, because a self-generated manifest alone does not bind edited working-tree recipes to this commit.

The helper builds all three binaries once with locked Cargo/private toolchain/homes, jobs=2 and explicit runtime target/output paths. Sys/net assertion instrumentation is confined to the private source copy, unique anchors and original byte hashes are checked, and those files are restored before runs and again in finally. Process source remains unmodified. Six result rows distinguish intended status101 assertion controls from status0 positives. For process RED, changing only expected exit8 retains all earlier real behavior assertions before the named failure; GREEN omits that override. Provided the two blockers are fixed and actual receipts validate, this same-build pair plus host record readbacks can prove the exact example criterion. It cannot prove strict release acceptance or unrelated lifecycle guarantees.

Resources are sampled at one-second intervals during commands: descendants16, storage preempt1572864KiB/hard2097152KiB, RSS2097152KiB. Samples are honestly labelled sampled maxima. Setup/build commands use the work deadline510 and export reserve30. Finally records failures/restoration and attempts original stage export to the separate proof destination; an existing/partial proof destination is preserved, not overwritten. Export errors fail the invocation. The recipe does not itself perform local independent custody export or delete its retained stage; a later independent collector must preserve originals, compare inventory/hashes, read back exact process/group/runtime/scope absence and only then retire owned stage resources. Such readback remains an acceptance obligation, not evidence supplied here.

## Lightweight checks (modeled/structural only)

Python AST parsing and both Bash syntax checks passed. Independently executed the actual `verify_pass`/`verify_control` function bodies with bounded in-memory inputs: source-shaped process GREEN marker strings passed, nonzero GREEN and missing output rejected; intended101/named/left7/right8 passed, wrong status and missing diagnostics rejected. The Rust Debug newline spelling used by the helper matches the source-shaped stdout model. These checks do not compile Rust or establish OS behavior, toolchain installation, command custody or cleanup.

## Frozen identities

Accepted source archive SHA256: `d75e7b83289081ad95c097763ac93c55520815bb5ea20a2079834ad137fecd7e`; lock SHA256: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`. Parent independently reproduced archive identity; this review does not convert that into executable evidence.

| Frozen file | SHA256 |
|---|---|
| Cargo.toml | cd6177f4aa38a6953c5907846a15edd6a4952bddcb663bb2dc34b3b9ed18970e |
| docs/sys-process.md | bb26ebc50169a06b01fbe6ddc7f03560eb4c3b8c3a3924cae71dcd889af079f7 |
| examples/sys_process.rs | 520aefeef3857c7f6763b752438d9c3ea6db495f369178bd7dcbd4d85afd2640 |
| check-linux-current-msrv-examples.py | c0c80653674feda4d3834a202d5f23585d46b461cdccc9f517c3f6febe7d2544 |
| launch-linux-current-msrv-examples.sh | a2892f29e42ee456c4d2ca6e88944e0da1f69d8dbdff2a5512fe220401c4456a |
| stage-linux-current-msrv-examples.sh | 570af5413b0f2d6faf56e655a89bbfc8e886e20139868053bad86fbebcf487e5 |
| linux-sys-process-example-contract.md | 410055e2de6d9b856ab1a53f0fd07153c87369849bca11291f8753402d4c993c |


---

## Affected correction recheck — fa0d91d56ecb48c066a314ba9699f473204d954f

**READY for bounded execution preparation; compilation/native acceptance unverified.** Compared only with the reviewed `012e20f70dbef81fe08954af96459e59a03d1caf` package and affected dependencies. Both original findings are resolved. No new material blocker found. This verdict supersedes the original preparation NOT READY while preserving its findings and evidence. Stdin Expert18 STOP, native110 unallocated, earlier limits/history and unaffected example-review conclusions remain unchanged.

Applicable rules revision independently reconfirmed `faba3db3bef6891ad2c0b20d434963bb8fe9572d`; existing named Expert/ocr-delegate context retained. OCR preview identified six changed files, four selected and two Markdown exclusions (`unsupported_ext`). Explicit rule resolution included all six; both Markdown files manually reviewed. Coverage 6/6, skipped0. No Cargo/src/tests changes or unrelated proof re-review. No build, native run, SSH, staging, source/recipe edits, install, push or runtime cleanup.

### Resolved findings and affected dependencies

- The child now writes the entire PID/readiness record to `spawn-ready.tmp` and, only after successful `fs::write`, renames that sibling to `spawn-ready.txt`. Same-directory Unix rename publishes the finished record atomically to the existing parent `is_file`/read sequence. The directory is unique and owned; no second fixture writer or old ready file exists in this invocation. Write/rename errors propagate and the existing fixture/host cleanup owns failure. Exact `child.id` comparison, pending UNIT assertion before release, finite release wait, final result equality and independent host effects remain intact. Docs reflect this ordering. No compilation/runtime result is inferred.
- Launcher passes the computed `runner_timeout_seconds` to `run_scoped.py`; the old 600-second runner argument is removed. It uses `min(585, 600 - elapsed - 15 - 1)`, rejects nonpositive budget before creating the scope, records the chosen bound, and reserves the one-second Bash rounding guard. The actual Bash arithmetic fragment independently returned584/583/564/484/1 for elapsed0/1/20/100/583, and refused elapsed584/600. These are local arithmetic models, not native launcher execution.
- At elapsed595, an outstanding non-zombie runner is signalled only after its recorded numeric PID/start identity matches a fresh `/proc` read. A changed/unreadable identity stops dependent cleanup and preserves the scope. An already absent/zombie runner follows normal status collection. The reviewed pinned runner handles TERM by returning a nonzero signal status and cleaning its own supervised group. `runner_stop_requested` is retained and forces outer failure even if a later status could otherwise look successful. No broad process match or foreign group kill is introduced. The normal bounded wait ends at600; failure can preserve an outstanding runner/scope for exact later readback. This is an honest failure path, not proof of successful cleanup. The contract now correctly calls600 an outer wait bound; filesystem operations and the subsequent finite readback are not a hard wall-clock timer supplied by this script.
- Cooperative helper deadlines remain work510/export540, with deadline checks between copied items. Checker export receipt and contract explicitly state that individual copies are not preemptible and partial original evidence may remain on failure. Existing refusal to overwrite evidence, finally restoration/export attempts, nonzero export failures, exact launcher readback and empty-scope removal are preserved. An incomplete/terminated invocation cannot satisfy acceptance. Independent host collection/hash comparison and fresh exact cleanup/readback remain required before accepting or retiring its retained stage, as recorded in the original review.

Source freeze/pin consumers consistently name `66379d3012ae606e278a0aaba8498846e1bd24cb`, archive `0ab9ec63c8f4b5d603be0bbcd0f4d582d8ef0a3e08ceb188841ed961828c884b`, and the new `66379d30` stage/scope. The lock and pinned runner/helpers are unchanged. Parent independently reproduced accepted-helper archive identity and source/docs/example byte equality; no execution proof is supplied by that identity check. Source restoration records, same-build six controls, API/platform/no_float limitations and historical sys/net proof separation retain their earlier applicability. The new stage/scope are unallocated.

Python AST and both Bash syntax checks passed. New termination wiring was reviewed structurally against the immutable pinned runner; no signal/proc behavior was modeled as OS proof. Real Rust1.77.2 compilation, process RED/GREEN, original output/status/resource receipts, complete export and independent host custody/cleanup are still required.

### Independently checked frozen SHA256 values

| File | SHA256 |
|---|---|
| examples/sys_process.rs | 3364188251bc581402398416a2b5ea8f3a16fdda35cb302d5f3260069de4d091 |
| docs/sys-process.md | 494e600eaec6398675e0347ab1f7b83cb8ad87a13dc004c31fca18a21e699b78 |
| check-linux-current-msrv-examples.py | 55c2a4a4c177f468757275a2691f73002a984a63b4c7cbba87314813a4b03d69 |
| launch-linux-current-msrv-examples.sh | 2381ebb7dd8bb29bedb55f5dbcd9b1d12b732834c00f2fc747d439b0f6902d6d |
| stage-linux-current-msrv-examples.sh | d80d5f8e353a160a400a0b3f851e65abe9eb314b771d5004524d51c54e0dd415 |
| linux-sys-process-example-contract.md | cba45561b10b29689bbd712c7cc8b601647c71fd0c8f99d686f879a27abcbc4a |


---

## Collector affected delta — 2dc12ce3ad6fa0b9fc5e3300a5c6145659c0e933

**NOT READY: consolidate three collector preparation findings below.** The accepted `fa0d91d56ecb48c066a314ba9699f473204d954f` example/source/runner preparation remains READY within its recorded scope; this collector-only finding does not invalidate those unaffected conclusions. Source `66379d3012ae606e278a0aaba8498846e1bd24cb` and staged recipes are unchanged. No native/compiler acceptance or allocation is claimed, and stdin Expert18 STOP/native110-unallocated history remains preserved. No counter/reset or new review pipeline is introduced.

Applicable agent-skills revision independently reconfirmed unchanged `faba3db3bef6891ad2c0b20d434963bb8fe9572d`. Existing Expert/ocr-delegate context retained. OCR preview/rules covered the sole new Python collector (1/1, skipped0); root preflight was inspected only for guard applicability. Complete collector blob SHA256 independently checked: `cd1efdec3eeecc7b283ff072b2f0c1b2b21d5f14c850bedef13955d0f9cb86dd`. AST parsing of the collector and embedded REMOTE passed. No SSH, remote code, Cargo, staging, native launch, push, source edits or cleanup ran.

### Consolidated material findings

1. **No immutable input/source gate in collection or retirement** (`collect-linux-sys-process-example.py:21–27`, `:105–127`, `:153`). The collector hashes whatever currently occupies the stage, compares that inventory to local copies and later fresh copies, and permits retirement if it remains stable. It never compares the ten staged input files to the independently fixed accepted hashes, and does not bind the copied source archive, lock, checker, launcher, stage script, contract or runner helpers to the reviewed package. The root preflight does check those ten exact pins and the original manifest before launch, which is a valid launch guard; it is not consumed here and does not establish post-run immutable binding. Add the frozen expected input map and manifest validation to the independent copied-original/fresh-remote retirement gates. Preserve unexpected/missing-input originals and mark binding failure separately; do not reject raw preservation merely because the inputs are wrong. An actual-REMOTE in-memory model with a wrong `source.tar` and all other staged inputs missing still returned `custody_ready=true`, proving this collector does not enforce those bindings.

2. **Custody predicates are not exact/fail-closed for recorded identities and runtime** (`:35–62`, `:131–140`). Numeric checks accept PID/PGID/start zero and only require label-set inclusion; required labels can be duplicated. No TSV header schema or complete row/provenance validation is performed. Runtime validation accepts any lexical string beginning with the scope's `agent-build-` prefix, including additional path components/traversal; the deletion boundary only checks `.exists()`. It must validate a single owned runtime child name against the prescribed canonical physical scope and distinguish actual absence from symlink/unknown state. Validate required original identity rows uniquely, positive IDs/groups and start values, expected emitter relationships/provenance, and fail on malformed group census instead of skipping non-two-column rows. Repeat the same conservative predicates at deletion and record the fresh observations in the retirement receipt. The actual embedded REMOTE, executed only with an in-memory fake filesystem/proc/ps, accepted four required zero-valued identity rows, group0 and an absent `.../agent-build-/../../foreign` runtime with `custody_errors=[]` and `custody_ready=true`. This is a corruption model, not an OS observation.

3. **Custody analysis failure can prevent preservation of otherwise readable originals** (`:35`, `:51`, `:57`, `:96–98`). `collect()` runs the combined remote inventory/custody script before opening the original tar. A group-query timeout/nonzero result or strict decoding error in an original identity/runtime receipt raises out of that script, so no raw archive is acquired and only a local error/status file remains. This conflicts with preserving all originals for partial/infrastructure failures. Separate raw inventory/export from custody classification, or return explicit unknown/error observations for these cases so the original tar and local inventory can still be completed and retained. Retirement must remain blocked for unknown custody. Never turn a timeout/decode error into absence or successful acceptance.

### Valid unaffected collector properties and acceptance boundary

The collector uses exact prescribed logical/physical stage paths, rejects stage symlinks/unexpected objects, refuses an existing local destination, streams a retained partial tar, rejects absolute/traversal/link/special tar members before extraction, and compares complete file hashes and directory inventories. Missing or structurally malformed identity rows already become custody errors that can coexist with preserved originals. It explicitly writes `acceptance=false`; collection must not be mistaken for native acceptance. Local copied trees, raw tar hash and canonical JSON readback hash are rechecked before retirement; a fresh remote inventory must match, and deletion rehashes the stage before unlinking exact inventoried files/directories and removing only the empty stage. Scope absence is rechecked. These gates are useful and should be retained with the fixes above.

Retirement currently emits only stage/scope boolean absence, leaving its immediate PID/group/runtime observations implicit in a successful exit. Preserve explicit final exact readback observations in the receipt when correcting the custody predicates; the existing local independent-readback is pre-deletion, not that final observation. Local copies are closed and hash-verified; no crash-durability/fsync guarantee is demonstrated, and no such native/storage claim is made here.

Root preflight binds the reviewed ten input hashes, canonical physical stage, absent scope/terminal/evidence state, idle heavy-run inventory and minimum16GiB available RAM/disk. This collector addition does not change those guard inputs. Fresh guard execution and independently read-back original six controls, restoration, bounds, cleanup and source applicability remain necessary for real example acceptance. This review ran only AST/immutable blob and bounded actual-consumer corruption models; no remote custody, deletion or native acceptance was simulated as proof.


---

## Combined affected correction — source60048ec4 / recipes4358af92

**Prepared execution: READY (source review only; compilation/native acceptance unverified). Collector collection/retirement package: NOT READY.** Reviewed `60048ec4d3d615fac3250404ce61b8cae14dfcb8` and `4358af92e6930514fac32d014b284591e58d47d3` against collector baseline2dc12ce3/fa0 execution recipe. Two consolidated collector blockers remain below. No Cargo, SSH, native launch, staging, cleanup, source edits or push ran. Existing failed compile1, preparation approximately45minutes plus unknown collector work, exhausted stdin history/native110-unallocated and other boundaries remain unchanged; no native acceptance, retry-count or cap reset is inferred.

Current root project instructions were read; agent-skills revision reconfirmed `faba3db3bef6891ad2c0b20d434963bb8fe9572d`. Applicable global/campaign/e2e/ocr instructions retained at that unchanged revision. OCR preview/rule resolution covered all six affected files; five selected automatically, contract Markdown included explicitly and reviewed manually (6/6, skipped0). Earlier unaffected conclusions remain applicable.

### Public API/compiler correction and prepared execution

The earlier review implicitly treated the generic `rhai::Variant` bounds as externally available. That assumption is withdrawn: `src/lib.rs` exports `Variant` only with `internals`, absent from this selected profile. The actual failed build101 established the compiler defect; it was not an intended behavioral RED and supplied no process-example acceptance.

The corrected example uses concrete public `Dynamic`/`INT` evaluation and public concrete `Dynamic::cast` conversions for bool/INT/String. No inaccessible generic trait name remains. `eval_with_scope` can be instantiated with these public types without naming its internal bound. The helper for `child.id` uses the actual property and concrete INT return. Pending waits/cleanup use Dynamic, terminal map conversion and all old assertions remain. String cast has the existing public conversion path. Atomic readiness, cloned cached-map equality, real host effects, exit7-as-data, completion/timeout flags and the wrong-exit8 final assertion are preserved. No source/API finding remains in this correction, but no compilation was performed here.

Checker, stage, launcher and contract consistently consume source `60048ec4d3d615fac3250404ce61b8cae14dfcb8`, archive `ce8bcb76a6e839a5ee293f53d70784731bcfbb65b6694aa0e5b1ded2b00661d6`, unchanged lock2ba4 and unique `60048ec4-20261004` stage/scope. The six behavior controls, private MSRV1.77.2/build-once contract, adaptive runner/helper/export bounds and platform limitations are unchanged. New stage/scope remain unallocated. A fresh guard using these new paths and exact new recipe hashes is required before any launch; the earlier66379d30 preflight is not a guard for this new stage. Actual native acceptance remains pending.

### Consolidated collector blockers

1. **Final receipt always fails after exact stage deletion.** In `retire`'s embedded deletion script, `groups=set(c['groups'])`, but the final `json.dumps` dictionary contains `'final_groups':groups`. A set is not JSON serializable. The failure occurs after files/directories/stage removal and after final PID/group checks, causing the SSH command to fail and preventing the local `retirement-receipt.json` from being written. This would leave required custody acceptance incomplete after irreversible retirement. Convert the groups to the required sorted numeric list and independently execute the actual final receipt expression/receiver contract before authorizing retirement. The isolated actual AST final receipt expression was executed with a two-group set and raised `TypeError: Object of type set is not JSON serializable`; no destructive script statements were executed.

2. **Raw acquisition still depends on a custody-scope query before tar export.** `REMOTE_INVENTORY` is documented as never querying the private scope, but its final output evaluates `scope.exists() or scope.is_symlink()` for `scope_present`. `collect()` calls this script before opening/exporting the tar. If this scope observation raises a permission/I/O error, readable stage originals still cannot be acquired. Remove the scope observation from raw inventory and its comparison keys, or capture unknown without aborting raw preservation; the separate custody call must remain responsible for scope absence and blocking retirement. A probe of the actual inventory output expression with a modeled denied scope observation raised `PermissionError` before any output. This is the remaining dependency in the original raw-preservation finding; it does not demonstrate an actual VM permission failure.

### Resolved collector portions and modeled evidence

The collector remains explicitly scoped to the original failed66379d30 invocation, never the new60048ec4 stage. It now embeds the exact original ten input pins and original manifest order, validates copied/fresh inventories, and repeats ten-input/manifest checks at deletion. Actual `validate_input_binding` accepted its consistent frozen-pin shape and rejected missing source, wrong manifest and inventory errors. This is modeled validation, not original remote proof.

Custody parsing now validates header/unique required labels and PIDs, positive recorded PID/PPID/PGID/start fields, owner/command parent relationships and command provenance. It records PID/start observations; only NotFound proves absence, changed start records original-absent, unknown reads fail. Strict ps census permits an unrelated numeric PGID0 (valid Linux census data), rejects malformed rows, and records group-query failures as unknown. Runtime grammar requires one direct scope child and one original PRIVATE_RUNTIME marker; symlink/present scope/runtime states reject custody. Separate custody calls occur after the retained original tar/extraction/preservation records, and decoding/group errors no longer roll back those records.

Actual embedded REMOTE_CUSTODY was run only against a bounded in-memory fake filesystem/proc/ps: valid owner relationships plus unrelated `1 0` census accepted; zero recorded PID, malformed ps rows, ps timeout and traversal runtime rejected. These probes verify the actual producer predicates, not OS custody. Root's supplementary66 identities/two groups/runtime-absence observation does not bypass collection binding or the reviewed gates.

Local originals/tree/tar hashes and fresh stage/custody equality gates are retained, with fresh PID/group/runtime/scope checks before deletion and an intended explicit post-deletion observation receipt. The serialization blocker must be fixed before this final receipt can exist. All collector/embedded Python AST and both Bash syntax checks passed. No native result, host receipt or cleanup was fabricated.

### Independently checked frozen hashes at4358af92

| File | SHA256 |
|---|---|
| examples/sys_process.rs | b73d175fccc4e8e5112d6d36f1e55ea6984a93c23592c10be7f931a05cbbd25b |
| check-linux-current-msrv-examples.py | c5422e7895f5afacf987be55df2297b63b0763618ccbdc2a8374116a1421edd9 |
| collect-linux-sys-process-example.py | 1e23abab1ea53812c35703349ec8dbbfff2a8f30281bb06d52f979f1aff3b16d |
| launch-linux-current-msrv-examples.sh | 1f544fd9c5bdd2594a17eaab9c803ed3b5a889ada66eaace6b0ce0a4d4b12675 |
| stage-linux-current-msrv-examples.sh | 6bdc4dd245e6e3df82318d42fe1c5e409aafc93031acc41373cbbe5ad9fa3bd1 |
| linux-sys-process-example-contract.md | 526a8d5a35910f097fc398fd218e8abae6cf1142c083aaf791bd08f4e9739abf |
