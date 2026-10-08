# Independent combined source review of the native BuildOnly bootstrap

Reviewed 2026-10-08; final source inspection at 14:10:21 UTC.

**Verdict: ready for the exact narrow bootstrap invocation below.** No blocking finding or concrete unsafe native handle/job race was identified in its composed ownership, control/compiler execution, status, disposition or export path. This is source readiness for compiling the custody tools and executing the bounded bootstrap controls. It is not native acceptance of those controls, approval of public lease-client custody, permission to launch product Cargo, or full Windows/release acceptance. No additional specialist review is called for by the reviewed source.

No build, test, native process, product edit, cleanup, commit, push or message was performed for this review. Only this report is written. Earlier accepted Unix/example reviews were not repeated. The foreign dirty shared process fixture is unchanged at SHA-256 `14a0808a8a5735d8f141ca1533d638d7b460392332d0021793f08da5b92c4fc2`.

## Rules and immutable review binding

The loaded unchanged installed Wayfinder revision remains `f3fc5632f401156837ee3872f14fe33ccf1024ea`. `/Users/hoppworks/.agents/skills/wayfinder/SKILL.md` and its installed-revision copy below `/Users/hoppworks/.local/share/mattpocock-skills/` both hash to `9be7b478c389605a24517d27752f278933588da97a1b5921b165f455edf4c5b7`. Read current project `AGENTS.md` for product, security, public-Engine proof and ownership rules (SHA-256 `06b73a9db5691ff5a0c5b34f98ce61e2c5df08e77161f3f93c3f7ce119d7c5de`) and the canonical plan's **Windows custody prerequisite** (plan SHA-256 `abd684c30562a2adcdbd13a391ffad7676bccc792d7efeeec5ef35e957428ddf`). The owner has explicitly authorized autonomous implementation. The old global agent-skills layer is disabled and was not loaded.

Read the complete selected `RunSourceFixtures.ps1` bootstrap, the complete separate compiler-wrapper source to assess its owned pin/path delta, relevant README guidance, and the complete exact future `bootstrap-input/Start.ps1`. The selected entry invokes only `RunSourceFixtures.ps1 -BuildOnly`; it does not invoke `CompileMonitorAcceptanceDriver.ps1`, a synthetic fixture suite or the native driver. Execution readiness is limited to this selected entry, not the separate wrapper's later invocation.

| Reviewed file | SHA-256 |
|---|---|
| `fixtures/RunSourceFixtures.ps1` | `8769dc680724f3299067aa3d0bb9c5282f582ca2033463f65617a9151b817646` |
| `fixtures/CompileMonitorAcceptanceDriver.ps1` | `857250e0933c7bc0f196333693bbf1c7190b7be16684590d2e0e278295eeb0d8` |
| `tools/windows-scoped-runner/README.md` | `78cd6e3b6080306698af232c095e6d99d7057078297b6f8dd13991922c8290ee` |
| Current `bootstrap-input/Start.ps1`, including the monotonic export check | `9bef30d82ff81fd1b79515f477bcbcd8be2a91539d3a62f09e6c967d120e4b39` |
| `bootstrap-input/input-manifest.json` and `bootstrap-source-pins.json` | `51fdb3aba8a824bab3e58f7429af7bfee6fdfa7d61535f2a1f472d3f5baaae9f` |

Independently recomputed all 12 source pins against both current repository files and the staged `bootstrap-input/input` files. All match, and the two JSON pin maps match exactly. The 12 inputs are the nine production C# files, `MonitorAcceptanceDriver.cs`, finite `PayloadFixture.cs`, and the selected bootstrap script. All existing embedded production/fixture pins in `RunSourceFixtures.ps1` also match their current source files. Both compiler scripts now pin `WindowsCustodyBackend.cs` to actual source hash `368e230e67b6712a29386b8623c69bf9e58ab404687a79078685ffe5cf061ee5`; no pin check was disabled. The separate wrapper's driver-fixture pin also matches actual source `33581ea00e1dc536bf4afdd8842c0a9cc3fdd028514e228c8b1ca776d40e1db0`.

## Exact selected entry and private paths

The future entry is `bootstrap-input/Start.ps1`, invocation identity `rhai-bootstrap-20261008T125846Z-b7f83433`, reading the owner-prepared read-only transfer media at `E:\input` and `E:\input-manifest.json`. It hashes each staged input and parses the selected bootstrap before creating an execution session. It refuses an existing session and reparse ancestors. It creates only the current user's `.local\share\agent-builds\rhai\bootstrap-20261008-b7f83433\run` parent, then launches a new `$PSHOME\powershell.exe` child with:

```text
-NoLogo -NoProfile -ExecutionPolicy Bypass -File E:\input\tools\windows-scoped-runner\fixtures\RunSourceFixtures.ps1
-SourceRoot E:\input
-RunRoot %USERPROFILE%\.local\share\agent-builds\rhai\bootstrap-20261008-b7f83433\run\monitor-source-6effa368078d4edfa0a7b2f8f684edc1
-BuildOnly
```

This is child-command execution-policy selection, not a persistent policy or interactive environment change. All variable path arguments are quoted; these fixed reviewed paths contain no embedded quote or trailing-root argument that requires different escaping. The bootstrap itself enforces 64-bit PowerShell 5.1 or later, canonical same-volume user-private session/run layout, no traversal, an absent `monitor-source-<32 hex>` child, every existing ancestor through the volume root, no reparse ancestors and at least 2 GiB free on that volume. It does not create a historical shared `C:\RhaiQuality` root or overwrite an existing run.

The separate wrapper delta moves its future `monitor-driver-<GUID>` path into the same user-private session/run tree and checks its ancestors; its stale backend pin is corrected. It is neither staged nor called by this entry. The README accurately separates this BuildOnly compiler owner from the independent later native-driver launch.

## Self-job setup, finite children and retained owners

The selected bootstrap obtains kernel32 delegates through Reflection.Emit, without Add-Type or an unsupervised compiler child. Its native owners are initialized before acquisition, and the encompassing try/finally covers job creation, limit setup, self-assignment, watchdog construction, controls and compilers. It creates an unnamed job, sets kill-on-close and no-breakaway with 16 active-process, 1 GiB per-process and 2 GiB job-memory limits, and assigns the current PowerShell process before any child launch. Setup or assignment failure cannot fall back to an unmanaged compiler.

The first native control is a nested copy of this bootstrap with `-SetupFailureControl`. That child joins its own configured self-job, starts only the finite 60-count loopback PING control, persists the exact child PID and injected pre-watchdog setup exception, then closes the kill-on-close job. The outer controller retains its exact child process handle, uses one shared 30-second wait/accounting deadline, rejects zero/unavailable exit status or missing/incorrect diagnostics, and requires its own job to return to exactly one active process. Thus the deliberately unconstructed child timer is covered by the parent's deadline and job, and the control cannot silently turn a setup failure into bootstrap success.

Next, real bounded PowerShell exit-17/wrong-expected, exit-0 and exit-17 controls check actual redirected output and status. The helper rejects null/non-Int32 status explicitly. Every control/compiler `Process` owner is disposed only after its synchronous status handling; the exact handle is accessed before waiting to avoid the redirected Start-Process null-status issue. The mismatch catch accepts only the intended actual-17/expected-0 diagnostic.

BuildOnly filters out synthetic source fixtures and serially compiles only `ScopedRunner.exe`, `MonitorAcceptanceDriver.exe` and `PayloadFixture.exe`. Each uses the installed exact compiler path `C:\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe`, frozen copied sources and an explicit `/main` / `/out` argument sequence. The driver is compiled with the nine production files and its own source; the payload is compiled independently. None is executed. A separate missing-source compiler control requires exit 1 and CS2001, distinguishing a real compiler rejection from unavailable status or a setup stop. The runtime target, input, logs and temp directories remain within the new run; TEMP/TMP changes affect only this bootstrap child and its descendants.

Every compiler has 180 seconds, ordinary exit controls 30 seconds, and remaining time is limited by the BuildOnly 900-second total. Log files are monitored at the 4 MiB polling threshold and rechecked at exit. Exceeding a live log/child limit terminates the exact owned job and fail-fasts the exact controller. This is a polling stop threshold, not a claim that a redirected writer can never briefly cross 4 MiB; oversized output is rejected, never accepted or silently truncated.

The native watchdog retains the current Process and its exact handle. Its callback touches that handle rather than the job handle; the main thread remains the sole job-handle disposition owner. It stays armed through job accounting and close. On the successful path, active count must be exactly one before kill-on-close is cleared, and no new child is launched afterward. A query/set/close failure fail-fasts while ownership is retained; after a successful flag clear, a close failure explicitly attempts termination of that exact job. Timer cancellation requires the drain event within five seconds before releasing the retained current-process owner. No handle is knowingly used after its owner is disposed in this selected path.

Only after successful owner-only accounting, job close and watchdog drain does the script write `build-manifest.txt`, the exact `BUILD_ONLY_PASS:` result and its final stdout line. The manifest records the observed installed compiler SHA-256, pinned source hashes and retained binary hashes. Compiler compatibility and those observed hashes remain native execution outputs to collect, not facts established by this source review.

## Observer, status and bounded serial export

The outer entry retains the exact bootstrap process handle before its independent 930-second wait. If that expires, it kills that exact controller and requires exit within ten more seconds; the controller's already configured kill-on-close job contains its descendants. Failed/unavailable status is recorded as a failure, and accepted stays false. Accepted becomes true only after an actual zero bootstrap exit and the result file whose prefix can be written solely after successful disposition/drain in the absent fresh run. The recorded failure string and actual bootstrap exit are preserved even when evidence export itself completes. The observer's script return/serial connection completion must not be substituted for its explicit `accepted` / `exit` fields.

Guest originals remain retained on success, failure and partial export. The observer inventories only this session's stdout/stderr/observer record, this run's direct logs and the two final result/manifest files. It refuses more than 64 files, aggregate size above 16 MiB, an individual file above 4 MiB, or a reparse file. Serial export uses COM1 at 115200, a two-second write timeout, a monotonic 180-second check before every frame, a bounded encoded frame, 1024-byte data chunks, invocation identity and monotonically increasing sequence. Each file has declared length and SHA-256 in FILE / FILE_END records; END binds the inventory and explicit outcome. The native host must require this run's complete frame sequence and independently check lengths/hashes; EOF, partial export or old serial text cannot establish success. A write already in progress can use its own two-second timeout after the monotonic frame check; the code does not claim an asynchronous hard interruption of every filesystem operation at exactly 180 seconds.

The entry disposes the serial resource in finally and contains no runtime deletion, broad process stop, foreign-root access, global configuration change, driver launch or Cargo command. All status/logs/binaries/input copies stay retained for readback. The two termination routes target an exact retained bootstrap controller or its own unnamed job, not a guessed PID/process tree or shared Windows service.

## Required native result and acceptance boundary

The exact invocation is source-ready. Its first native outcome must preserve the original bootstrap/compiler/control logs, the observer's real status, setup-control marker and owner-only return, real exit controls, CS2001 compiler control, three retained binaries, compiler/source/binary manifest and post-disposition result. Export must be complete and hash checked before claiming this bootstrap slice passed. Failure remains diagnostic evidence with the guest session preserved; it is not public-custody or product GREEN.

A successful bootstrap still leaves public `ScopedRunner --lease-client`, native driver protocol/OS readbacks, disconnect/death and other custody gates unaccepted. The driver must later start from an independently verified uncontained process after this compiler child exits. This report grants no source-readiness verdict for that later composed driver/product route, the alternate compiler-wrapper invocation, or the full Windows/release matrix.

## Focused native-outcome and allocation02 delta review

Reviewed 2026-10-08. **Verdict: ready for the exact allocation02 BuildOnly invocation bound below.** The narrow failure-disposition repair addresses the observed false-zero exit route without changing successful accounting, job disposition, watchdog drain or post-disposition result creation. No blocking source finding or concrete unsafe handle/job race was identified in this delta. This is readiness for a new native invocation; allocation01 remains failed diagnostic evidence, and allocation02 has no native acceptance yet.

The same unchanged Wayfinder revision `f3fc5632f401156837ee3872f14fe33ccf1024ea`, current project rules and autonomous implementation plan remain loaded. Their hashes still match those above. The old global layer remains disabled. Only this combined report is appended; no process, compiler, fixture, cleanup, product change, commit or external message was performed. The original 13,102-byte report is retained byte-for-byte as the prefix, SHA-256 `9363cdbd6e1e2c8e1e2558699ef506d716ca73751b25b9cab179c08fa854e7f9`. All allocation01 source/entry snapshots, pin maps, native exports, serial originals and launch/media history remain untouched.

### Original causal evidence

Read `bootstrap-failure-analysis.md`, all nine files in `bootstrap-export`, `bootstrap-export-readback.json` and the original serial stream. Independently decoded the invocation-bound 29 frames, required sequence 0 through 28, matched BEGIN/END to the saved readback and reconstructed each file from contiguous chunk offsets. All nine reconstructed lengths, SHA-256 values and bytes match both the exported files and readback inventory. The raw serial SHA-256 is `649f11f0c44e1a5d1288f9def93861a3caa87118c80af679e4565bc21f8fcc75`; the readback SHA-256 is `f77a14b42f0c936f09db75b5a893037bcf3195b0a3e1fb0caefac610534315f0`.

The nested marker preserves `CONTROL_INJECTED_AFTER_JOB_ASSIGNMENT_BEFORE_TIMER`, PowerShell PID 7764, child PID 3184 and the intended injected setup exception. The child stdout independently records the finite loopback PING reaching execution. The outer stdout contains only the private-root policy pass, and its persisted primary failure is `Setup-failure control unexpectedly succeeded.` The exact selected source checks that error only after obtaining the nested controller's actual exit status and observing zero. The outer observer records exit 0, `accepted=false`, no native driver launch and a missing `run-result.txt`; END likewise records false acceptance and retained guest evidence. No compiler command was reached: setup-control validation precedes every compiler launch in the pinned source, and the retained output contains neither the later exit-control passes nor compiler outputs. This establishes the status defect's causal path, not a product assertion failure or independent proof that PING membership was cleaned up. The failed guest session remains retained; no cleanup acceptance is inferred.

The saved launch history separately records the earlier console command without `-Raw` failing before native execution because the pipeline supplied individual source lines. Its corrected whole-script invocation did not change the source or pins. That parser failure is not a native control result; its historical pending label is superseded by the preserved native allocation01 outcome above.

### Changed failure disposition and custody

Compared the allocation01 and allocation02 snapshots directly. The bootstrap source changes only by inserting the twelve-line `if (!$success)` branch at the start of the existing nonzero-job-handle disposition try. Primary setup diagnostics are persisted and flushed by the existing catch before finally reaches that branch. The branch flushes its failure diagnostic, invokes `TerminateJobObject` with the retained exact unnamed job and explicit unsigned status `3758096387` (`0xE0000003`, signed Int32 `-536870909`), and fail-fasts if termination reports failure or if control unexpectedly returns. An exception while disposing also reaches the existing fail-fast catch. Thus failure cannot proceed to ordinary job close, watchdog cancellation or current-process owner disposal and reproduce the reviewed close-without-failure-status route.

For the injected nested control, self-assignment precedes the PING child, so the retained nested job owns that controller and its child; the outer controller belongs to its separate retained outer job. The repair targets the nested controller's exact job rather than its parent or a PID-derived process tree. The parent still retains its exact nested Process handle, shares one 30-second deadline for wait/accounting, requires an available nonzero Int32 exit, checks the persisted primary marker and child PID, rejects the existing disposition diagnostics, and requires outer active-process accounting to return to exactly one. The native control does not promise an exact E0000003 observed status: its acceptance checks valid nonzero failure plus the primary marker and actual accounting. The new explicit code and fail-fast fallback must be assessed from the next original native status/logs, rather than assuming an exit code from this source review.

The owner and watchdog remain retained through failed-controller death. The watchdog still touches only its retained process handle; the main thread owns the job handle and never introduces a competing close. If job creation/configuration/self-assignment fails before membership exists, the new branch still terminates only that owned job and fail-fasts on return, with no compiler or fixture child having been launched. If no job handle was acquired, the existing primary exception path remains. The successful owner-only accounting, limit clear, exact close, timer cancellation/drain, retained-owner release and final manifest/result are byte-for-byte unchanged. No success marker moves ahead of disposition, and no resource/export bound is relaxed. An additional specialist review is not required by a concrete race in this delta.

### Fresh entry and pin binding

All twelve allocation02 source pins independently match both current repository files and their `bootstrap02-input/input` snapshots. Compared both pin maps: only `RunSourceFixtures.ps1` changes; the eleven C# input pins are identical to allocation01. The old input map and `bootstrap-source-pins.json` still match their original snapshots. The separate compiler wrapper and README remain at their earlier reviewed hashes.

| Allocation02 input | SHA-256 |
|---|---|
| Current and staged `fixtures/RunSourceFixtures.ps1` | `d2d1f93e2e34d2470ac3aa65b5214ba406dd408ba613cf775d0393b9cdbccb80` |
| `bootstrap02-input/input-manifest.json` | `56ebf28211262f8c522e14fa2f014d568a9575ee64c3af20ba99937ccd4eb6f0` |
| `bootstrap02-input/Start.ps1` | `680a6dc1dc7e73631954b6ac321c7e7715d4c75faf90eccdfd673cfb0d17478f` |

The entry differs from allocation01 only in invocation identity `rhai-bootstrap02-20261008T125846Z-b7f83433`, fresh session `bootstrap02-20261008-b7f83433` and absent run GUID `monitor-source-c03ad72ea8c04bceaf8e624b133610f1`. Its selected child still receives `-BuildOnly` and the freshly pinned `E:\input` source; no alternate compiler wrapper, native driver or Cargo command is introduced. Use the complete console invocation:

```powershell
Get-Content -Raw E:\start.ps1 | Invoke-Expression
```

Source pin verification and bootstrap parsing still precede session creation. Private ancestor checks, exact observer Process retention, 930-second observer wait plus ten-second termination wait, explicit false status on failure, post-disposition result gate and bounded serial export remain unchanged, including the 180-second monotonic frame check. The new session cannot consume allocation01's result/logs; that session and its evidence are preserved.

Native readiness remains narrow: the next run must retain actual nonzero setup-control status and primary diagnostics, owner-only accounting, real exit-zero/17 controls, compiler CS2001 rejection, the three compiled binaries and compiler/source/binary manifest, the post-disposition result and a complete independently hash-checked export. A false observer outcome or missing result remains a failure even if a console/serial transport exits zero. The foreign dirty shared process fixture remains at `14a0808a8a5735d8f141ca1533d638d7b460392332d0021793f08da5b92c4fc2`. No public lease-client custody, product Cargo or full Windows/release acceptance follows from this addendum.

## Focused allocation02/03 source and native-evidence acceptance

Reviewed 2026-10-08. **Verdict: ACCEPTED only for the narrow native BuildOnly bootstrap at allocation03.** No unresolved blocking standards, specification, source-binding, assertion-control or retained-owner finding was identified in this package. Allocation03 compiled the three selected tools, completed its setup/status/compiler controls, performed successful owner-only job disposition and watchdog drain, and produced the result accepted by the independent observer. This supersedes the preceding allocation02 readiness state for this narrow slice. Allocation01 and allocation02 remain failed historical attempts. Public lease-client/driver execution, product Cargo, full Windows custody and release acceptance remain open.

The unchanged Wayfinder revision `f3fc5632f401156837ee3872f14fe33ccf1024ea`, project `AGENTS.md` and autonomous plan remain loaded with the same hashes recorded above; the disabled global layer was not loaded. This is a focused continuation of the same combined review, not a new general review. The prior 21,653-byte report prefix is preserved exactly, SHA-256 `48229ab14d620a879ef7493296f0d16abc6fffa0a697664c2b7a549f985bd4a9`; its original 13,102-byte prefix also remains unchanged. Only this report was appended. No build, native process, fixture execution, cleanup, other file edit, configuration change, commit or external message was performed.

### Allocation02 failure and minimal source correction

Read `bootstrap02-failure-analysis.md`, the original allocation02 export/readback/serial stream and its immutable input snapshots. The native stdout records the setup-failure control returning the outer job to exactly its owner, the intended real exit-17/expected-0 rejection, actual exit-zero and exit-17 passes, explicit unavailable-status rejection and production runner compiler exit 0. The nested marker records PowerShell PID 672, PING child PID 5372 and the injected pre-watchdog exception; its stderr records the explicit E0000003 disposition. Driver compiler output then contains the single CS0103 error at `MonitorAcceptanceDriver.cs(143,33)`: `TerminateJobObject` had been referenced but not declared. The persisted primary failure correctly records driver compiler exit 1 versus expected 0. The observer receives actual signed exit `-536870909` (`0xE0000003`), `accepted=false`, no driver launch and no post-disposition manifest/result. This is native evidence that failure status now survives teardown, while the compilation defect remains a failed attempt rather than a bootstrap pass.

Compared allocation02 to allocation03 snapshots: the driver adds exactly one matching kernel32 declaration, `[DllImport("kernel32.dll", SetLastError=true)] private static extern bool TerminateJobObject(IntPtr job,uint exitCode);`. It resolves the existing call using the retained job handle and unsigned exit-code type, consistent with the surrounding Win32 declarations. No driver control flow changes. The selected bootstrap changes only its checked driver-source hash; the separate compiler wrapper likewise changes only that driver pin relative to its prior reviewed bytes. The README remains byte-for-byte at its previously reviewed hash. Allocation03's entry changes only its invocation identity, fresh session and run GUID. No new wrapper, process launch, relaxed bound or changed success/disposition condition is introduced.

Reviewed the exact current four-file diff at fork head `19c3d1d044b51e9a3f3a0b80e27a5bd72ab59964`, SHA-256 `2e405f2851143074cbbef6d5e988aa54f6b97f472fa208506fbd3ad509ea7990`. The earlier BuildOnly selection, retained Process handles, finite controls, private path policy, explicit failure termination and post-disposition manifest/result remain applicable. The separate wrapper is not invoked by the native allocation03 entry; its execution is not accepted here. Adding the driver's missing import establishes native compilation, not runtime correctness of that unexecuted driver's custody path.

| Current reviewed file | SHA-256 |
|---|---|
| `MonitorAcceptanceDriver.cs` | `80235547abbf1ccdaed6bac7aae816a236676ef38f3055366fb206255e95a550` |
| `fixtures/RunSourceFixtures.ps1` | `f8fa614557c458b5546067712139a159ed2c5ecb79e434e3c3dc319a7e405ee9` |
| `fixtures/CompileMonitorAcceptanceDriver.ps1` | `4b2f5bab2175b9f239f3d9bc6874bf20847c3f263da9a2354c0c589ba4ca9d33` |
| `README.md` | `78cd6e3b6080306698af232c095e6d99d7057078297b6f8dd13991922c8290ee` |
| `bootstrap03-input/Start.ps1` | `2593d185d95a276aaa4d5a911641e220f80c2738d02d27ba810b3edb3608216a` |
| `bootstrap03-input/input-manifest.json` | `ba5db9ecc7e1379245d9ae8cc1072dcba1c300b0f8023ee80c4d38667096cadc` |

Independently verified all twelve allocation02 input pins against its retained snapshots and all twelve allocation03 pins against both retained snapshots and current repository source. All eleven selected C# pins also match the bootstrap's embedded map. Only the driver and the bootstrap script pins change between allocation02 and allocation03. The nine production sources and finite payload remain identical. The media receipt binds the new entry hash, read-only ISO and the same recorded Windows VM identity; the observer's input-map hash matches allocation03's exact saved map.

### Original native controls and successful completion

Allocation03 is invocation `rhai-bootstrap03-20261008T125846Z-b7f83433`, with run root `C:\Users\RhaiTest\.local\share\agent-builds\rhai\bootstrap03-20261008-b7f83433\run\monitor-source-5158297562ef46ec9a1431d9ed3a2b89`. Its fresh identity prevents the observer from using earlier attempts' files. The selected entry still passes `-BuildOnly` to the pinned source, uses the complete script invocation, checks pins and parsing before session creation, and retains the existing private ancestor policy, independent observer wait/status and bounded export.

The original setup marker records PowerShell PID 6136, child PID 2404 and the intended exception after job assignment but before watchdog construction. Independent PING stdout proves the child ran. The setup-control stderr contains only the explicit E0000003 disposition message; there is no fallback/disposition error. The outer stdout reports the exact child PID, retained primary exception, nested teardown and owner-only return. By the unchanged selected source, this pass requires a valid nonzero native child exit and actual `QueryInformationJobObject` accounting of one active process within the shared 30-second deadline. The nested exact numerical exit is not separately printed; no stronger status claim is made for it.

The three real redirected exit-control outputs exactly equal `EXIT_CODE_REGRESSION_17_WRONG_EXPECTED`, `EXIT_CODE_REGRESSION_ZERO` and `EXIT_CODE_REGRESSION_17`, with empty corresponding stderr. Native stdout reports that actual 17 versus expected 0 was rejected, then actual 0 and 17 were accepted, and unavailable status was rejected. These are the intended failing expectation and valid controls of the retained-handle/status helper; they were not replaced by an aggregate count or compiler success alone.

Original compiler output identifies Microsoft Visual C# Compiler `4.14.0-3.26424.7 (a528c90a)`. The production runner, acceptance driver and finite payload each have recorded compiler exit 0. Production/driver output contains the inherited CS0618, CS0219 and CS0414 warnings, with no errors; the payload has no warnings or errors. The separate missing-source compiler command has exit 1 and exactly the intended CS2001 diagnostic for the allocation03 private input path. Its checked diagnostic distinguishes actual compiler rejection from missing exit status or an infrastructure stop. No selected binary, synthetic source fixture, native acceptance driver or Cargo command was executed by this BuildOnly route.

The native `run-result.txt` is exactly `BUILD_ONLY_PASS: exact job owner-only accounting, successful disposition and drained watchdog; native driver not launched.` In the pinned source it is written only after all compiler children have been synchronously handled, actual final job accounting equals one, clearing kill-on-close and closing the exact job succeed, and the timer's drain event is signaled before retained-owner release. Exceptions in those steps fail-fast and cannot reach this result. The independent outer observer confirms the exact bootstrap process has exited with actual exit 0, then reads this fresh result; it records `accepted=true`, empty failure and `driver_launched=false`. Bootstrap stderr is empty. This composition supports successful native owner disposition/drain, not merely compilation or transport completion.

The final manifest contains the observed compiler hash `cf32cb7e8e5691b962e1b6f92b03d87409dd9e7afbed71c5bf77b8203cc56ee1`, exactly the eleven selected C# source hashes and these three retained executable digests:

| Retained guest binary | SHA-256 from the post-disposition native manifest |
|---|---|
| `ScopedRunner.exe` | `33ea1e97546ac5797f576dc9e0388281432edac46db623c8d8583b70d9761812` |
| `MonitorAcceptanceDriver.exe` | `026f12ef1ca17cec95aa1994591e1d59656f0279acca5f5ba53c9c798f0457c0` |
| `PayloadFixture.exe` | `b571f5b91d632feac3a7770f5a116d3e0947bdf73fe388213fc11ffb72f7da6d` |

All eleven manifest source entries match the frozen input map and current selected source. The manifest SHA-256 is `ae88f82361557d4526bb6ebce6360890794e217bdbd2c0889cefe97da8811f6c`; the result SHA-256 is `79c5b9102422b2f755e2aed8ef416a0a3ab0156de7c5ba4c85dbeda2e6ac6761`. Executable bytes remain retained in the guest; this review verifies their original manifest receipts and successful compile composition, without downloading, executing or freshly probing them. Any later native driver/product route must bind its exact binaries independently before use.

### Complete export, preservation and scope

Independently reconstructed allocation02's 58 invocation-bound serial frames (sequence 0–57) into all nineteen exported files and allocation03's 71 frames (sequence 0–70) into all twenty-four files. For each, BEGIN and END match the saved readback and observer, every FILE/FILE_END length/hash agrees, every CHUNK has the next exact offset and at most 1024 bytes, and reconstructed bytes match the complete local export inventory. No unlisted file or missing frame is accepted. Allocation02 totals 8,597 exported bytes; allocation03 totals 10,101 bytes, with the largest file 2,811 bytes. These remain within the unchanged file, aggregate, chunk and serial bounds. Allocation03 END records exit 0, true acceptance, retained guest evidence and no driver launch.

| Original evidence | SHA-256 |
|---|---|
| `bootstrap02-serial-original.txt` | `136a36af11fd93487343a3c8eb5e4b3fd0fc4cf6fffa6928448dae482237b19a` |
| `bootstrap02-export-readback.json` | `8629ef4efed259dbaaa43cb8ca45a091e463522351bbd7045396d9a58dad8493` |
| `bootstrap03-serial-original.txt` | `59b60bef640e265063369d3f8576282ed5a96973e9b78f17aad16fcd5beba063` |
| `bootstrap03-export-readback.json` | `5589518ea85209b1b95ac83e56b65781dacfde18f666ba4e00bebb992477a221` |

Original failed attempts, their input/pin snapshots, partial build outputs, native diagnostics and prior report prefixes remain preserved. Guest filesystem retirement is not claimed: allocation03 deliberately retains its accepted build inputs/logs/binaries for later binding. The accepted completion here concerns its owned compiler/control process disposition and bounded evidence export. The foreign dirty shared process fixture remains unchanged at `14a0808a8a5735d8f141ca1533d638d7b460392332d0021793f08da5b92c4fc2`. No additional specialist review is warranted by a concrete handle/job race in this delta, and no previous product tests need repetition for this bootstrap outcome. The lease-client/driver, product and wider native/release gates remain outside this acceptance.
