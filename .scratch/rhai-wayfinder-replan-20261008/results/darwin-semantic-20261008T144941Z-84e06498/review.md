# Independent combined review — Darwin semantic closure

Reviewed on 2026-10-08. **Scoped acceptance with one missing readiness oracle:** the original package proves the supported selected non-process results described below, but cannot close the promised outstanding-read cancellation criterion. Darwin filesystem `read_dir`/NotUtf8 behavior also remains explicitly unverified because its fixture was rejected with EILSEQ before that assertion ran. This is not complete TCP lifecycle, process, Windows, core MSRV, or release acceptance.

## Authority and exact inputs

Reloaded the current project `AGENTS.md` and unchanged installed Wayfinder at `/Users/hoppworks/.local/share/mattpocock-skills/f3fc5632f401156837ee3872f14fe33ccf1024ea/wayfinder/SKILL.md`. Loaded rule revision is **f3fc5632f401156837ee3872f14fe33ccf1024ea**, skill SHA-256 `9be7b478c389605a24517d27752f278933588da97a1b5921b165f455edf4c5b7`; project instruction SHA-256 `06b73a9db5691ff5a0c5b34f98ce61e2c5df08e77161f3f93c3f7ce119d7c5de`. The canonical implementation plan has SHA-256 `abd684c30562a2adcdbd13a391ffad7676bccc792d7efeeec5ef35e957428ddf` and records the owner's autonomous implementation authorization. The old global agent-skills layer is disabled and was not read. No builds, tests, cleanup, source changes, commits, configuration changes, network writes, or other-session messages were performed in this review. Only this report was written.

Reviewed `inputs.json`, `verify.py`, `payload.sh`, the owned patch, accepted lock, all native compiler/artifact/list/exact-test command records and original output files, `result.json`, `cleanup.json`, `scope.txt`, and `originals-manifest.json`; also the selected source bodies/helpers, applicable canonical feature/base-sys/TCP clauses, approved release proposal, and retained Linux policy/policy2 review, result, reuse, and independent-readback records.

| Bound input | SHA-256 |
| --- | --- |
| inputs.json | a6879f7e0136bd699948a0a84f3ebc8226ebc5cfeec9df60d0e6daabaf22bcea |
| verify.py | 0f38656b421a8900ffae03f4eff2e839057a8764c5c4a7266ca13a0a162be666 |
| payload.sh | 3d15f09f57076ec4beb68eb07978a0fe66c4925df73d1a3645bc189f41a0a06e |
| reused source.tar | 635a59827900b02ad82b0e53499f6b3fb2a5c5233326cac541c88c3e8b61265f |
| owned.patch | e57f1efff98d7457229fe5512ed556ba5c09defe44155f1c5651c56b5b8a17d6 |
| Cargo.lock.accepted | 2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425 |
| result.json | 02f3f31c871aabcf3de1c148ffe19408efe42246b786051dc6318236c76c4a8d |
| cleanup.json | e51a3c471c90a0c45fb2af4f06b8b33a3408b1d7613c39e10909cee9ce43729d |
| originals-manifest.json | 66f4c75a8c168715c412e5a4ecc3f4095d49c5577436c5da1a995bd76b41f807 |

Independently recomputed all **497 original manifest entries**, including byte lengths; every entry matches. The source archive is byte-for-byte `git archive --format=tar ef423a516617e128835d54af16d75f559b2b1bce`. The patch is exactly the committed diff from that revision through `19c3d1d044b51e9a3f3a0b80e27a5bd72ab59964` for `examples/sys_process.rs`, `tests/net_connect.rs`, `tests/net_listen.rs`, and `tests/sys_process.rs`; there are no other patched paths. The helper applies that patch to the private extracted source and overlays the pinned lock, rather than copying the dirty checkout.

Current reviewed HEAD is `da115c618c39fb1eca93aeba90a92478f09f5e29`. There is no committed drift from 19c3 to that HEAD in `src`, `tests`, `Cargo.toml`, `Cargo.lock`, or `build.rs`. Every one of the eleven selected target source files matches both its saved result SHA and the committed 19c3 bytes. The only relevant working-tree delta is the foreign shared process fixture, whose current SHA is `14a0808a8a5735d8f141ca1533d638d7b460392332d0021793f08da5b92c4fc2`. Its archived committed bytes have SHA `1faf45c57a4fefeaa05683043e064d3485e892887986fef749bedc974230b217`; the foreign delta was excluded and remains untouched.

## Findings and exclusions

**[P2] The read worker's readiness signal does not prove read-wait entry.** At `tests/net_reads.rs:423–428`, the worker sends `ready_tx` before `eval_with_scope("stream.read_string(1)")`. The controlling thread can therefore close the clone at lines 431–434 before the read begins. In that schedule, `NetStream::socket` rejects the already closed stream immediately, and the test's error, sub-second completion, quota reuse, peer EOF, and joins still pass. Neither saved invocation records a read-wait observation. This affects `sync/net_reads` and `scalar-sync-metadata/net_reads` (`*-net_reads-green-0`). Their results support shared close, bounded completion and quota release; they do **not** establish cancellation of an already outstanding read. The canonical sync requirement expressly includes outstanding-operation cancellation and explicit readiness. Keep that specific criterion open until a bounded Engine/real-socket oracle observes actual read-wait entry before close. An already-closed error and a generic `is_err()` are insufficient. This is an evidence gap, not proof that production cancellation is broken. Retained Linux passes of the same source do not supply the missing observation either.

The listener cancellation selector has a stronger oracle: after worker launch, a second Engine probes the same listener until it observes `ResourceLimit`, showing that the worker holds an accept reservation before clone close. The joined worker must then report the catchable `Io` outcome. The read finding does not invalidate those listener rows.

**Explicit host-unavailable exclusion:** `sys-alone-sys_fs-green-12` runs `test_non_utf8_file_name`, returns exit 0 and emits `filesystem rejects non-UTF-8 fixture with EILSEQ: Illegal byte sequence (os error 92)`. The macOS source branch returns immediately after that failed host write, before either Engine `read_dir` NotUtf8 assertion. Its raw test pass is retained as a host-unavailable observation; the promised Darwin filename/NotUtf8 behavior is not accepted or completed. Non-UTF-8 environment-value handling is a separate, successfully constructed isolated fixture and is supported.

## Original execution and oracle binding

Saved environment readbacks identify native `macOS-27.0.1-arm64-arm-64bit`, machine `arm64`, `rustc 1.77.2 (25ef9e3d8 2024-04-09)` and `cargo 1.77.2 (e52e36006 2024-03-26)`. All eleven compiler command records use `cargo +1.77.2 test --locked --features testing-environ,<exact features>`, the selected target names, `--no-run --message-format=json`, and the same private source cwd. Each exits 0, contains a successful build-finished record and exactly one matching executable artifact per requested target. No build stderr contains a compiler error.

Independently matched all 28 original executable `--list` commands and their unique test-name inventories to the helper's selections. All **120 GREEN invocations** use the artifact executable plus one listed selector, `--exact --nocapture --test-threads=1`, exit 0, and report exactly one passing, zero failed, zero ignored test. Filtering other tests is deliberate exact selection. No already accepted IPv6 selector was selected. Artifact feature closures match the requested rows, including metadata's implicit serde/serde_json dependencies.

| Profile features, without testing-environ prefix | Target/profile results | Raw selected GREEN passes |
| --- | ---: | ---: |
| sys | 3 | 67 (one EILSEQ exclusion) |
| net | 4 | 28 |
| sys,net | 1 | 1 |
| sys,net,sync | 3 | 3 (read-wait claim restricted) |
| sys,net,no_index | 4 | 4 |
| sys,net,metadata,serde | 2 | 3 |
| sys,net,only_i32,no_float | 2 | 2 |
| sys,net,unchecked | 3 | 3 |
| sys,net,no_index,sync,metadata | 4 | 5 (read-wait claim restricted) |
| sys,net,f32_float | 1 | 1 |
| net,no_object | 1 | 3 |
| **Total** | **28** | **120** |

All four controls use the **existing same-profile binary**, with a child-command environment variable changing only the independent expected value; no source or product mutation is needed. Independently checked that RED and matched GREEN have identical executable paths and argv, equal recorded executable SHA-256, the same cwd and selector; RED has the intended control variable and GREEN has `control: null`. `run()` removes all declared controls from every child environment before setting only the requested RED control. There is no intervening Cargo build or executable edit in the helper's RED→GREEN path.

| RED original → restored GREEN original | Required wrong assertion independently observed |
| --- | --- |
| sys-alone-sys_fs-red → sys-alone-sys_fs-green-14 | Fresh host bytes `original XYyload` versus `wrong expectation`, left/right byte assertion at sys_fs.rs:42 |
| net-alone-net_reads-red → net-alone-net_reads-green-6 | Actual lossy peer text `a�b` versus `wrong peer payload`, net_reads.rs:68 |
| combined-combined_sys_net-red → combined-combined_sys_net-green-0 | Fresh host `filesystem-payload` versus `incorrect filesystem expectation`, combined_sys_net.rs:119 |
| net-no-object-net_no_object-red → net-no-object-net_no_object-green-2 | Independent peer `ping` versus `pang`, explicit wrong-peer assertion at net_no_object.rs:78 |

Every RED exits **101**, names the exact selected failing test, reports one failure, and contains the intended assertion; every restored GREEN exits **0**. These are meaningful assertion failures, not compile, panic-before-fixture, or zero-test controls. The read text and no_object controls execute their peer join before comparing the wrong oracle. The file control retains its explicit fresh host readback in both original stderr files.

## Supported standards and specification scope

The selected sys baseline exercises the public registered package through Engine. Fresh host bytes/existence and separately constructed fixture truth support mode, cursor sharing, confinement, read/write/delete authority, denied-state preservation, relative/absolute path and Unix symlink resolution, file/directory operations and metadata. The two Darwin system-prefix cases construct distinct `/var/../../…` and `/private/var/../../…` spellings and require host canonicalization to the owned fixture before applying grants. Their read and nested write/denial assertions ran; a scoped TMPDIR does not make them vacuous.

Environment cases construct only child-command environments using `env_clear`, an exact test selector and recursion marker. They check allowed, hidden, unset and non-UTF-8 values against explicit fixture truth and cwd against the child's host cwd. The bounded helper polls then reaps success or kills/reaps on timeout. The unlinked-cwd filesystem fixture also changes only an owned child's cwd, uses a real ready marker and release pipe, compares host metadata with Engine predicates, and has a child kill/wait guard. No test sets the parent environment or cwd.

TCP baseline binds OS-selected endpoints and checks exact connect/listen authority, denied peer absence, reported peer identity, real payload bytes, EOF, shared quota and final close/drop behavior. Read fixtures distinguish available short prefixes, EOF loops, lossy and split UTF-8, timeout classification/partial raw progress and checked Engine expansion limits. Write fixtures compare actual independent peer bytes with counts, enforce host/checked Engine caps before peer effects, prove both half-close directions and idempotence, and relate a bounded write timeout's partial count to the complete peer readback. Accepted streams inherit host read/write caps. The clone-listener wait/close case has the reservation observation described above. Only the active-read entry claim is withheld.

Feature selections support the changing assertions actually chosen: scalar/string operations and omitted blob registrations under no_index; shared file cursor and listener behavior under sync; public metadata inventory, exact ordered signatures, overload counts, returns and comments through Engine metadata; INT::MAX file-read requests and coexistence under only_i32/no_float; persistent host read/write/file bounds under unchecked; and f32 fractional/non-finite timeout rejection with the original peer byte still available and a finite host ceiling. The no_object fixtures invoke registered stream/listener/error functions with explicit handles, real peers and byte/EOF readback. The selected no_index ProcessReport case constructs an immutable report in Rust and reads scalar/indexed diagnostics through Engine; it certifies registration/access only, **not process execution or lifecycle**. Similarly, Child wait signatures in metadata are metadata proof only.

Fixture work is finite and owned: nonblocking accept/probe loops have monotonic deadlines, socket reads have deadlines, payloads and peer buffers are finite, and successful paths close/drop and join. Generic exact-test commands are bounded at 60 seconds and each Cargo build at 600 seconds. The payload sets private Cargo source/target/cache and two jobs, disables Python bytecode and clears compiler override flags. The helper retains original evidence outside the disposable runtime, checks the pinned lock after every profile and saves failures. Final runtime storage was 4,742,463,488 bytes, below its checked 8 GiB limit; this is a final sample, not a peak claim or continuous quota guarantee.

## Retained Linux applicability and cleanup

Retained Linux x86_64/Rust1.77.2 policy proof records seven accepted rows/430 test invocations plus policy2's two rows/171 invocations, **nine rows/601 passes**, five reused controls and the same accepted lock. Policy2's original result binds the scalar/sync/metadata 82-pass row and f32 89-pass row; its independent readback records outer status 0 and absence of the exact owned identities/groups. Those native results remain historical proof; no Linux execution was repeated.

Compared their frozen `a2d7a8c2ace21e63c18b2e64cdce74e5e10afc94` source with 19c3. Sys filesystem/environment/support, TCP read/write/coexistence/no_object sources remain unchanged. Relevant net production differences are documentation and explicit connect/listen metadata parameter information; the sys error differences are documentation. The Cargo manifest addition registers the sys_process example without changing dependencies/features. Process backend changes are outside this review. New IPv6 tests have separate accepted evidence and are excluded here. Later metadata and Darwin alias assertions are bound by this Darwin evidence; the old Linux proof does not retroactively run those added assertions. Reuse supports the unchanged native outcomes, subject to the read-wait oracle limitation above.

The exact runtime in result and cleanup agrees: `/Users/hoppworks/.local/share/agent-builds/rhai/darwin-semantic-84w72wdv/agent-build-_jxigi5x`, with recorded device 16777234/inode 226245675. `scope.txt` identifies its exact outer `/Users/hoppworks/.local/share/agent-builds/rhai/darwin-semantic-84w72wdv`. Cleanup records accepted export outside the runtime, outer exit 0, absent runtime and retired empty outer scope. A fresh read-only check confirms both exact paths are absent. This result folder contains no separate outer launcher/status transcript; the outer-status claim is bound to the cleanup receipt, while per-command exits have their original native records. No additional process-tree/interruption proof is inferred from directory absence. All original files and their manifest were preserved; this new review is not inserted into the immutable originals manifest.

**Final scope:** accept the controlled, source-bound Darwin non-process outcomes above: 11 chosen profiles, 28 target/profile results, 120 raw GREEN passes, 119 non-EILSEQ invocations, and four intended RED101→GREEN0 controls. Two of those non-EILSEQ invocations prove shared read-handle close/quota outcomes but leave actual outstanding-read cancellation open. Keep Darwin filename NotUtf8, that specific sync read-wait prerequisite, process and Windows work, unselected lifecycle criteria and the integrated release gate open. No other concrete blocker was found for the supported selected scope.


## Focused actual-read-entry addendum — 2026-10-08

**Scoped verdict: accept the outstanding-read cancellation prerequisite for the two affected sync profiles on native Darwin arm64 and Linux x86_64/Rust1.77.2.** The earlier P2 readiness finding is resolved by the owned test instrumentation and four original GREEN executions below. The historical report prefix and its observations remain unchanged. This addendum replaces only the restricted read-wait claim; it does not repeat or broaden the previously accepted semantic package, process, Windows or release scope.

The unchanged installed Wayfinder revision remains `f3fc5632f401156837ee3872f14fe33ccf1024ea`, resolved beneath `/Users/hoppworks/.local/share/mattpocock-skills/`, SKILL SHA-256 `9be7b478c389605a24517d27752f278933588da97a1b5921b165f455edf4c5b7`. Reloaded current project AGENTS.md (`06b73a9db5691ff5a0c5b34f98ce61e2c5df08e77161f3f93c3f7ce119d7c5de`) and the applicable canonical implementation-plan requirements (`abd684c30562a2adcdbd13a391ffad7676bccc792d7efeeec5ef35e957428ddf`): real Engine/OS truth, meaningful assertion RED, outstanding-operation readiness, bounded owned fixtures and cleanup. The owner's autonomous implementation authorization applies. The old global layer was disabled and was not read. This review ran no builds, tests, native fixtures or cleanup and changed only this report.

### Exact source and evidence binding

Reviewed the two-file working delta `src/packages/net/stream.rs` and `tests/net_reads.rs`, the RED test, both helpers/payloads, source input maps, original compiler/artifact/list/exact-test commands and logs, result/phase records, cleanup and exports in `../net-read-entry-20261008T151745Z-a2d7a5a5/` and its `linux/` directory. Current HEAD is `da115c618c39fb1eca93aeba90a92478f09f5e29`; no committed src/tests/Cargo.toml/Cargo.lock/build.rs change exists between the accepted semantic source at `19c3d1d044b51e9a3f3a0b80e27a5bd72ab59964` and that HEAD. The two current files are byte-identical to both frozen GREEN copies.

| Input | SHA-256 |
| --- | --- |
| Current/frozen GREEN tests/net_reads.rs, 20,444 bytes | `ade22ffae347d79f014600898a4859b1e565b7c2a40612d49cca4a3f3419bbc8` |
| Current/frozen GREEN src/packages/net/stream.rs, 44,196 bytes | `ce2b44b9ed42bd01026669f8e876db9471064af2297d1e3904a48392631c1d91` |
| RED tests/net_reads.rs | `a9f795ede3f654b2415aea2104c9828e404c81b9ef585792a5edcb7fb19547e0` |
| Original/RED stream.rs from 19c3 | `e846c03c38d2b7d930ba428f404ddf55d956130c3130a4e6cf0c809804ae607a` |
| Shared RED source patch | `478a90f0a248725edbb52a8611cc7599efcf31ac053953c5d301329c6ebacfb2` |
| Shared GREEN input map | `d52a3b25552a6e07cf6127c3e09d2b4df780fdc78608055892d44d4434478a13` |
| Accepted lock | `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425` |

The common ef423 source archive remains the previously independently accepted archive, SHA `635a59827900b02ad82b0e53499f6b3fb2a5c5233326cac541c88c3e8b61265f`. Independently compared each of the four committed example/IPv6/Unix-test patch chunks to the exact ef423→19c3 diff: every chunk matches. The only additional RED chunk is tests/net_reads.rs; applying that hunk in memory to the committed test reconstructs the frozen RED bytes exactly. The patch does not include stream instrumentation or the dirty foreign child fixture. Darwin's phase receipt binds the RED stream to the original 19c3 bytes, then permits only the two hash-checked GREEN overlays. Linux uses the identical archive/patch/lock/overlays. The foreign working fixture remains SHA `14a0808a8a5735d8f141ca1533d638d7b460392332d0021793f08da5b92c4fc2` and was not touched or incorporated.

Verified all **75 entries** of the retained manifest, SHA `0d4137e418c644346393278ae537a962a5bcee7985f8b2fe8460beae6461da0e`. Its coverage has no unexpected missing original: only the later proof.md, the manifest itself and the separately verified remote-export-manifest.json lie outside it. Independently recomputed the byte lengths and SHA-256 of all **34 native Linux exported files** against that separate manifest, SHA `c5081d0c8d8f1cf4d5928435b15b8a6f0d4bab4960e138dfa27a04160118ffd6`. Manifest claims were checked against actual local exported bytes, not accepted from a boolean alone.

### Standards, readiness oracle and failure custody

The doc-hidden Rust host hook is gated by `testing-environ`; it is not registered as a script function. It stores one sender in the stream's shared state and removes it with `take()` only after the actual `TcpStream::read` returns `WouldBlock`. `try_send("read_wait")` is finite and cannot hold up the socket operation while waiting for a receiver. It does not alter socket state, read limits, timeout calculation, polling or close semantics. Builds without testing-environ exclude all added state and branches. In other instrumented tests no sender is installed, so the optional observation leaves their result conditions unchanged.

The test installs this hook on the same shared stream before spawning the Engine reader. The independent loopback peer accepts the real connection, reports readiness, retains that socket and sends no data. The main thread now waits for the actual WouldBlock notification and requires `result_rx.try_recv()` to return **Empty**, rejecting a completed or disconnected reader. An already-closed stream cannot produce this observation: socket acquisition would fail before the read/WouldBlock branch. Only after both observations does the controlling Engine execute the public clone `stream.close()`.

The reader must return an error within one second of close, ahead of its two-second host deadline, and join. With the package quota still fixed at one, a second public Engine connection must succeed and close; the independent peer then accepts that connection, reads actual EOF and joins. The first peer cannot explain an early EOF/error because it remains open until the explicit release after reader completion. The recorded entire exact-test durations, 0.007–0.026 seconds for GREEN, also exclude the two-second host timeout as the cause in these accepted native runs. This establishes an entered, unfinished real read followed by public shared-close cancellation rather than the former pre-read signal.

The new guard owns the control Engine, stream clone and both JoinHandles before assertion-prone reader setup. Unwinding closes the shared stream through Engine, attempts a nonblocking false release and joins any retained reader/peer. A false release makes the peer leave its second-connection phase. Existing monotonic first/second accept limits are two seconds, peer release is bounded at four seconds, peer read is one second, read readiness/result waits are one second and the host read is two seconds. If a later failure occurs after true release, the second accept remains bounded. On the RED assertion unwind the saved native process finishes in 0.012 seconds; no reader/peer handle is detached by that path. Success takes and joins both handles before its final diagnostic marker. No parent environment or foreign resource is changed.

### Original RED and four native GREEN executions

The exact selector in every row is `closing_a_clone_cancels_an_outstanding_read_and_releases_quota`. Each original successful compiler record has the proper --locked/features/net_reads target, a successful build-finished record and exactly one matching executable artifact. Each artifact's original --list contains the selector exactly once. The test argv is that artifact plus the exact selector, `--exact --nocapture --test-threads=1`; all four GREEN logs show one pass, zero failures and zero ignored. Requested features include the testing-environ prefix, with metadata's declared serde closure where relevant.

Darwin captures native macOS27.0.1/arm64 and Rust/Cargo1.77.2 from actual helper readbacks and uses `cargo +1.77.2`. Linux captures native Linux7.2.8/x86_64 and Rust/Cargo1.77.2; its payload pins Cargo/rustc/rustdoc directly under `/var/home/workhorse/.rustup/toolchains/1.77.2-x86_64-unknown-linux-gnu/bin/`. The Linux compiler records resolve the source under `/var/roothome/...` while the launcher/cwd/target use `/root/...`; both preserve the exact unique runtime suffix, and the artifact executable exactly matches the listed/executed target path. Neither source nor target refers to a foreign checkout.

| Native row | Exit | Executable SHA-256 |
| --- | ---: | --- |
| Darwin test-first RED, sys,net,sync | 101 | `6a37d74209e903ce46b78fe7edf0f82a06434098a059ab98de15eeed55f6f711` |
| Darwin GREEN, sys,net,sync | 0 | `b5306672a205094a143a45d2b00fea14ccef4ca7acbf35d8742ec33e02f0a85f` |
| Darwin GREEN, sys,net,no_index,sync,metadata | 0 | `202e8623be19653f1bd6721e300d3bb48b1ec76e871e291e1721e7f6c697a312` |
| Linux GREEN, sys,net,sync | 0 | `1794dd451a53e7c3c68e5ed2a19d850604b228358281c963b96e4f8f99e2e5e6` |
| Linux GREEN, sys,net,no_index,sync,metadata | 0 | `4017fa48ec6d920223931f2090a552ab55c4b4962bdeb512a1b706212e87ff61` |

The RED intentionally uses the old worker-start notification with the strengthened readiness contract: original stderr names the selected test and exact assertion, left `"thread_started"`, right `"read_wait"`, and stdout reports one failed test. Compilation and listing succeeded first. The red-complete receipt saves this failure and original stream hash before the helper waits finitely for implementation inputs; only then are the two GREEN source overlays applied and rebuilt. Thus this is a meaningful test-first oracle repair, not a failed compiler control or a claim that production close was previously broken. RED and GREEN are rebuilt sources with different binary hashes; they are not represented as same-binary wrong-expectation controls. The four previously accepted semantic same-binary controls remain retained separately.

Both GREEN stderr markers are present in every native row: actual read wait/pending result/open silent peer, followed by cancelled read/reader join/quota reuse/real peer EOF/peer join. The helper verifies those markers and the exact pass, source hashes and final lock. Per exact test the subprocess bound is 15 seconds; Cargo builds have 600-second limits. The Linux runner's original argv has a 1,200-second outer bound. Payloads retain source/target/cache below their one private runtime, two Cargo jobs, disabled bytecode and cleared compiler override flags. Linux final storage is 1,822,240,768 bytes, below the checked 8 GiB final sample limit; this is not a peak quota claim.

### Cleanup, retained acceptance and remaining boundary

Darwin runner.status is 0. Its result and cleanup bind runtime `/Users/hoppworks/.local/share/agent-builds/rhai/net-read-entry-x58rv1t_/agent-build-b9ignbb5`, device16777234/inode226335893, and the exact retired empty outer scope device16777234/inode226333938/uid501. Cleanup records retained originals and absence of runtime/outer; a fresh read-only local check confirms both exact paths are absent. Linux runner.status and original runner.stdout bind both GREEN0 rows and final runner0, with empty runner.stderr. Its native cleanup binds the original scope device58/inode117308687/uid0, verifies that ownership before empty rmdir and records exact scope/runtime absence, runtime inode117308692 and retained logs. Linux absence is the exported native cleanup receipt, not a new remote process readback performed by this review.

**Updated final scope:** retain the original 11-profile/28-target-profile semantic evidence, 120 raw GREEN invocations with **119 non-EILSEQ invocations**, and four meaningful original wrong-oracle controls. The two formerly restricted Darwin read rows are now supplemented by replacement GREEN evidence with actual read-wait entry; matching Linux evidence closes the same prerequisite in those two Linux feature profiles. This addendum contributes four exact native GREEN executions and one Darwin test-first RED101, without inflating the original distinct semantic count or rerunning its unaffected rows. The P2 actual-read-entry finding is resolved for this source-bound Darwin/Linux scope. Darwin non-UTF-8 filename NotUtf8 remains host-unavailable/EILSEQ and open. Windows read cancellation, process lifecycle, other unselected TCP criteria and integrated release acceptance remain open. No further concrete blocker was found in the reviewed two-file/original-evidence package.
