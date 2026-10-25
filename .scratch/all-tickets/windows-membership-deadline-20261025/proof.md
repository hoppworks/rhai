# Native Windows membership and Driver-deadline acceptance

Status: combined independent review PASS for two named infrastructure criteria.
Base059bb5b10167e97cda6995dec860e3eb86a55207 plus this package's fixture/control changes.
No Rhai/Rust product, public Windows Runner or Driver source change.

## Actual entry and results

The existing workhorse VM rhai-win11-quality UUIDdc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19,
RhaiTest non-admin console, Windows10.0.26300.0/PowerShell5.1.26100.9444 and installed
C# compiler4.14 were reused. Hash-guarded original commands are in the dispatch files.
The physical source medium's pinned Start is invoked as an existing ScriptBlock:

```powershell
& ([scriptblock]::Create((Get-Content -LiteralPath E:\Start.ps1 -Raw))) -Phase build
& ([scriptblock]::Create((Get-Content -LiteralPath E:\Start.ps1 -Raw))) -Phase membership
& ([scriptblock]::Create((Get-Content -LiteralPath E:\Start.ps1 -Raw))) -Phase deadline
```

Start uses canonical RunSourceFixtures.ps1 -BuildOnly -MonitorDeathFixtureOnly,
under the already-proved native compiler Job owner. Only the changed finite fixture
is compiled; later public Drivers run after exact compiler-owner exit. All16 source
inventory pins, native manifest/compiler/fixture hashes and reused old13-source/
three-binary bindings are checked. The14 C# inventory entries are not14 compiler
inputs: this build compiles only MonitorDeathFixture.cs. Final fixture source
1a28841a7acbc270f8466a48cd1d51fb90952678573b2bb7cd60e117987c7a09,
control8928e526aae282827b3d6aefab7aed324d0f6d6b00177b1a3880a005b1665182,
native fixture b8066eaae4799f0c3829172b230b2b023fc5637a9c2b76394309a5d78be118e3; existing Runner/Driver remain72b02940…/27b1e6f3….

| Named row | Native observation | Independent readback |
|---|---|---|
| Both actor membership before work; root exits normally | Driver0/payload0,2.0517926s; both actors query complete four-PID immediate Job lists, each including the exact payload/ordinary-child pair before release/work | Fresh child/root work files, complete list/counts and exact PID/start records; wrong-self0 and wrong-work expectations fail then correct pair/work passes;8CRC records/exact Job closure, both stopped, literal runtime absent |
| Deliberate Driver180s stop | Driver2 after180.2336003s with exact whole-driver deadline error; actors hold240s, so natural expiry126 cannot satisfy observed payload125/MonitorStopped | Both actors seen live first and same PID/start pairs stopped afterward; same work/list assertions,8CRC records/exact closed Job/snapshot hashes/final REMOVED and literal runtime absence |

Each accepted row exports69 contiguous frames/17 bounded hash-checked originals.
Snapshot-as-absent RED precedes restored runtime-absence positive. Full four-PID lists
are retained; the two additional processes are not labelled or assumed unrelated.
The exact Job's whole membership is closed, not only two selected PIDs. Work retirement
is11entries/0bytes; useful actor work records are bounded retained runtime files,
not a Cargo output tree. No nonempty product-work interruption claim is made.

Deadline stderr is preserved: orderly client-exit/controller-Job release did not
complete, and kill-on-close custody remained until Driver process teardown. The
independent post-teardown stop/runtime proof passes; this is not successful orderly
pre-teardown disposition. The240s observer kill path was not reached. Separate
watchdog124 hard-termination and monitor30minute absolute deadline are unproved.

## Original failures and targeted correction

Attempt01 native public Driver2 failed its expected exit contract. Read-only export
of its existing completed journal/snapshot found parent exact-peer-exited-before-
handshake and child identity, without the child's original error. No rerun inferred
an unseen product cause. The next one-file build adds durable per-actor failure
records only. Attempt02's one bounded diagnostic call reveals the child failed the
unsupported exact-two-total-members assumption after native query success. Its
actual counts were not exported, so they are not retroactively asserted as four.

The agreed criterion is actual pair membership before work, not exclusivity. The
corrected fixture keeps complete list/positive unique PID/count bounds and requires
both exact actors. Original membership/work/closure checks are not removed. Both
current actors now independently observe four members and the normal criterion
passes. Source review covers each affected correction; original failed sources,
observers, diagnostics and empty-acceptance flags remain intact. This is a fixture
oracle correction, not a newly established product defect.

Three one-file C# compilers total 7.6156379s (2.6999864, 2.4326284, 2.4830231).
Four public Drivers total 189.8799055s (1.5679202, 6.0265924, 2.0517926, 180.2336003),
including the two failed criteria/diagnostic calls. Accepted candidate uses one build
and two real controls. Two additional read-only diagnostic exports launch no native
process workload. UI transport, review and preparation time are not included in
those native elapsed sums; token/cost totals are unknown.

An automatic2MiB serial log rotation changed inode102529120 to126648834. Build02's
original74 frames were recovered across the retained rotated/current files and
fully validated; no compiler/control was restarted for the observation boundary.

## Bounds and complete owned resource retirement

Each phase is host-admitted separately. Build observer270s +30s exact exit reserve;
controls240s +10s drain +60s exact closure observer; export180s/64files/4MiB each/
16MiB total/3500encoded frame. Host /var free104323104768bytes and RAM76151MiB;
new disk peak128MiB is a planning estimate; guest Start checks2GiB available. No
fixed heavy slots, foreign process stop or VM/guest reset/installation was used.

Before its expiry, compatible old cache retention was explicitly amended once from
2h to2h30 (09:35:52 to10:05:52UTC). That boundary was an agent-selected resource
estimate, not a human deadline/spend/attempt cap. Inputs, original creation/expiry,
reason, capacity and consumed work remain in retention-amendment.json/history.
Reuse ended earlier: the host-bound native cleanup receipt proves all8 exact own
build/control scopes absent after complete original export/hash/inventory checks,
fresh actor PID/start/runtime absence and exact executable-path inactivity. Two
failed criteria remain failed; closed custody permits their cleanup independently
of semantic acceptance. Native receipt is guest-cleanup-original.txt/json, not a
local decoder receipt.

All six exact own media were hash-checked/exported and removed after original sdc
restoration; original sdb is preserved. The91-entry own host staging copy was
byte-checked against local source/proofs then retired, as were all POSIX runtimes
and the empty decoder session. No cached build remains available. Accepted source-
bound proof remains applicable while relevant source/assertions/environment match;
physical historical paths are not reusable resources. Foreign work and guest
baseline remain unchanged.

## Open scope

The two named current rows close only their demonstrated membership/Driver-deadline
criteria. Actual failed atomic JOB_LIST association/no unowned resumption, monitor
absolute deadline/watchdog-specific paths, remaining failed export/cleanup and
bounded real project-command composition are still open. No Windows Cargo/Rust/
Rhai Engine/sys/net feature acceptance or full Ticket03/A–F/release completion is
claimed. Unchanged Linux/Darwin/API/earlier Windows evidence is reused, not rerun.

API semantics used by the fixture are documented in [QueryInformationJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-queryinformationjobobject)
and [JOBOBJECT_BASIC_PROCESS_ID_LIST](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_process_id_list).
The NULL-handle query observes the calling process’s immediate Job; complete list
counts and actual PIDs are recorded rather than inferred from successful spawning.
