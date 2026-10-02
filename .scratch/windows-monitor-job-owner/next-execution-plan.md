# Next Windows monitor verification route

## Authority and current boundary

The 11:17–11:47 UTC entry in `windows-monitor-staging-ownership-review.md` is a
completed SOURCE allowance and records zero execution launches/resources; it
was not a human-imposed native cap. Root accepted the frozen source/custody
harness for one bounded Windows source-fixture invocation and authorized the
exact VM activation and read-only preflight. That invocation is limited to the
source compiler and fixtures; it is not real-client, payload, or native
acceptance. Preserve earlier work totals and all Expert02 policy/resource caps.
No historical human native run-count cap was found. The 30-minute source
planning estimate is not an execution cap.

Project `AGENTS.md` selects strict verification. The current human scope
authorizes writes only to the approved `hoppworks/rhai` fork; the public
original is forbidden. The reviewed harness checkpoint was pushed only to
`origin/task/windows-scoped-runner` at `5fe4a08a1dad49d1f24e7fedc0399b54d5c9acc8`;
this preflight adds no remote write. The prior
`acceptance.md` records the authorized
`rhai-win11-quality` VM on `workhorse`. Its earlier shut-off result and black
console are now superseded by the authorized 2026-10-01 activation. Read-back
reported `running`, 4 vCPUs, 8 GiB configured memory, enforcing SELinux and DHCP
lease `192.168.122.125` for MAC `52:54:00:58:9d:bf`. `dumpxml` shows the default
e1000e network, loopback-only VNC, serial/console PTY `/dev/pts/3`, and no
QEMU guest-agent channel or shared filesystem. `guest-ping` reports that the
guest agent is not configured. TCP connects to ports 22, 445, 3389, 5985 and
5986 all returned closed-or-filtered, so the existing transfer route is the
visible VM console plus outbound HTTPS, not SSH/SMB/RDP/WinRM into the guest.
No guest credentials were supplied or handled. The VM inventory documents
an existing Build Tools compiler at
`C:\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe`, Windows 11 Pro x64 and
SDK 26100. Earlier serial entries include a 2026-09-30
`RHAI_TOOLCHAIN_READY Rust=1.93.0 Target=x86_64-pc-windows-msvc` marker and a
successful Visual Studio Build Tools installer status; those are historical and
do not verify current toolchain versions. The live console readback and exact
compiler version are recorded in the current observations section below. No
install, bootstrap, admin change, home/config change, or baseline mutation
occurred.

## Frozen source input and fixture harness

`tools/windows-scoped-runner/fixtures/RunSourceFixtures.ps1` pins SHA-256 for
the accepted `c8c6b18caaa855d2f66e0fc1f84e594d4f1e5e6b` input set: nine
production C# files and eight C# fixtures. It copies only those inputs into an
exclusive GUID run directory and verifies every copied hash before compiling.
The initial script required PowerShell 7 and `.NET Core`
`NativeLibrary.GetExport`; live guest readback found only 64-bit Windows
PowerShell 5.1. The mutable source candidate now accepts PowerShell 5.1 or
later, chooses the matching dynamic-assembly API, and resolves kernel32
exports through an emitted `GetProcAddress` P/Invoke method. Native binding
creation stays in the current process before compiler launch. The existing
Roslyn compiler path is present and reports `4.14.0-3.24624.7 (a528c90a)`.
The emitted P/Invoke uses the eight-argument `TypeBuilder.DefinePInvokeMethod`
overload documented for .NET Framework 4.8.1; its method name is also the
entry-point name, and `PreserveSig` is retained. No script parse, compile,
fixture, build, or native API has run; root review of this adaptation is
pending.

Before any compiler/fixture process can start, the harness creates a private
Windows job, applies KILL_ON_JOB_CLOSE, process/job memory limits (1 GiB per
process, 2 GiB aggregate), a 16-process cap and no breakaway, then assigns the current PowerShell process
to that job. Native bindings use `Reflection.Emit` delegates; no `Add-Type`,
compiler, or other child is used to create the owner. Compiler and fixture
children inherit job membership at process creation. A one-hour .NET timer
terminates the exact PowerShell process even if its main thread is waiting; OS
process teardown closes the sole KILL_ON_JOB_CLOSE job handle and terminates
descendants. The timer stays armed through job accounting, limit clearing, and
exact job-handle disposition, then is disposed with a completion signal and
drained before the process handle is released. Its callback uses the retained
process handle, never a job handle that may have been closed or reused. The
owner checks job accounting for exactly
one remaining member (itself) after all children have been waited, clears
KILL_ON_JOB_CLOSE only then, and checks the exact job-handle close result. If
the outer guest is unscheduled, the timer cannot execute until scheduling
resumes; elapsed-time guarantees remain conditional on a running guest, as in
Expert02.

The harness requires a fresh direct child of `C:\RhaiQuality\runs` named
`monitor-source-<32 lowercase hex>`, rejects reparse ancestors, requires at
least 2 GiB free on C:, redirects TEMP/TMP, and retains source copies, binaries,
logs and fixture artifacts under that one run directory. It never deletes the
run directory. Each compiler and fixture has an individual ceiling; their
combined schedule is below the one-hour wall timer. `CustodyBackendFixture`
uses at most 576 MiB logical fixture source plus 512 MiB destination data;
fixtures run sequentially. All exits and diagnostic logs remain in the run
directory for inspection.

After root source review and a fresh read-only guest-state check, the intended
single harness invocation is:

```powershell
& "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NonInteractive -File `
  '<immutable guest input copy>\tools\windows-scoped-runner\fixtures\RunSourceFixtures.ps1' `
  -SourceRoot '<same immutable guest input copy>' `
  -RunRoot 'C:\RhaiQuality\runs\monitor-source-<fresh-guid>'
```

That batch compiles the normal runner, six `SCOPED_RUNNER_TESTING` fixture
executables, and the payload marker, then executes the six fixtures. It does not
run the legacy `RunProcessCreationFixtures.ps1`, which calls the disabled
`--source` path. Current fixture sources do not launch real payload processes;
they exercise protocol, storage and injected-native-operation seams. A green
batch would prove compilation and those source fixtures only.

## Current console, toolchain, and transfer observations

On 2026-10-01, the existing read-only `virsh screenshot` route captured the
currently running domain to the uniquely named workhorse file
`/tmp/rhai-win11-quality-preflight-20261001.png`; existing SSH/SCP copied it to
`console-preflight-20261001.png` beside this plan. The 1280x800 image is
uniformly black (SHA-256
`05713dbacb00cfa92e8cad1581147b0f1349f6ee14c97d122440aff36011bd53`). This is
a fresh observation and supersedes the old black screenshot as the current
frame. After the separately authorized single 100ms left-Shift wake, a second
fresh 1280x800 screenshot was captured two seconds later at
`console-after-shift-20261001.png` (SHA-256
`bf252f7f1a61beeac5e1845bd54b5370864c417540bc42dcaaf12e0f12d45cff`). It
shows the unlocked Windows desktop with Recycle Bin, Edge and taskbar. The
authorized console was then used for read-only PowerShell probes. `get-host`
reported Windows PowerShell `5.1.26100.9444`; the 64-bit executable resolves
under `C:\Windows\System32\WindowsPowerShell\v1.0`. `pwsh.exe` was not found,
and `Test-Path C:\Program Files\PowerShell\7\pwsh.exe` returned `False`.
`Test-Path C:\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe` returned
`True`; the correctly quoted compiler `-version` invocation returned
`4.14.0-3.24624.7 (a528c90a)`. An earlier unquoted compiler path was parsed by
PowerShell as module `c` and failed before starting the compiler; the quoted
read-only version query then succeeded. No compilation occurred.

The guest's `Test-NetConnection github.com -Port 443` succeeded to
`140.82.121.3` from `192.168.122.125` on Ethernet. A read-only HEAD request to
the exact accepted input URL
`https://github.com/hoppworks/rhai/archive/c8c6b18caaa855d2f66e0fc1f84e594d4f1e5e6b.zip`
returned `HTTP/1.1 302 Found` followed by `HTTP/1.1 200 OK` when following the
GitHub redirect. This establishes pinned-commit archive endpoint availability,
not downloaded bytes or their hash. No archive was downloaded. It also does
not establish that this older archive contains the newly revised PowerShell
harness. After source review and an exact owner checkpoint, fetch that exact
owner commit's archive, verify its commit identity and all 17 expected source
hashes in the guest, then run the reviewed harness from the unique run root.
The archive fetch and compiler/fixture batch have not run.

The guest agent is absent and guest SSH/SMB/RDP/WinRM ports remain
closed-or-filtered; direct console plus outbound HTTPS is the established
transfer route. The exact archive for approved owner checkpoint
`5fe4a08a1dad49d1f24e7fedc0399b54d5c9acc8` was downloaded to the uniquely
owned `C:\Users\RhaiTest\owner.zip` and extracted to
`C:\Users\RhaiTest\owner-extract\rhai-5fe4a08a1dad49d1f24e7fedc0399b54d5c9acc8`.
The archive SHA-256 readback was
`A174F4AB28492CC1766F387D0451363CB2BB17191422F8A89B949C2D33AD1457`; the
reviewed harness SHA-256 was
`611B5236A5A5648B0C2584984F6100553448DECB45FB983DFE6583531F034E2E`. The
17 required C# source hashes matched the frozen harness dictionary, and
`Parser.ParseFile` reported `$e.Count = 0`. The guest execution policy list
returned `Undefined` for MachinePolicy, UserPolicy, Process, CurrentUser and
LocalMachine. A direct first invocation was rejected before loading the script
with `PSSecurityException` because the effective default policy disables
scripts. After that readback, Process scope alone was set to Bypass in the
existing interactive PowerShell process and read back as Bypass; no persistent
policy was changed. The same-process script retry loaded but failed in the
PowerShell 5.1 `Get-KernelDelegate` path before job creation/self-assignment:
reflection could not convert a `System.Management.Automation.PSObject` argument
to `System.IntPtr` at the emitted `GetProcAddress` call. No compiler or fixture
child started and the run directory was not created. This is a harness
compatibility defect to correct and review before a new attempt. A prior long
console keystroke entry was interrupted with Ctrl+C before execution; it did
not create another process. The `C:\RhaiQuality\runs` ancestor was created as a plain directory;
C: showed 66.18 GB free, and the selected unique child did not exist at the
preflight check. The harness rechecks path, reparse status, space, and collision
before compiling. No credentials, mount, bootstrap, service change, or VM
baseline modification occurred. The VM remains running. Earlier no-shell and
no-transfer conclusions above are historical observations preceding the
authorized desktop wake and preflight.

## Native custody acceptance route after the harness

The bounded host controller fixture that speaks the real `--lease-client`
protocol, supplies the immutable specification, responds to fresh challenges,
and independently reads evidence is frozen at
`tools/windows-scoped-runner/MonitorAcceptanceDriver.cs` in commit
`5583d7b3de50bb0f8c2706b837d2d4ba64ff9368` on the separate
`task/windows-real-client` branch. It is not included in this compiler/fixture
invocation, which does not launch `MonitorTransport` and does not grant
breakaway. This source-fixture task makes no claim about running that driver.
The production payload job remains kill-on-close with no breakaway permission;
the monitor source owns the payload job and runtime and observes client
process/pipe death. This monitor lifetime model is the Expert02 route; an SSH or
PowerShell job alone does not replace it.

The separately frozen driver is not part of the one-hour source-fixture batch.
Any later native monitor acceptance should use the existing Expert02 limits:
the same 1-hour outer bound, 2 GiB job memory cap, 16-process limit, 2 GiB free
space preflight, and exact unique run root. Cases include ordinary-success/residual-child,
payload-failure, lease expiry, connection loss while client is alive, client
death, expired/replayed challenge, suspended-create/resume failure, nested-job
refusal, output-cap, evidence/readback failure and cleanup-timeout cases. Each
monitor has the Expert02 fixed policy: 2-second challenges, 15-second lease,
120-second setup, nonrenewable 30-minute absolute lifetime, 30 seconds for
termination/emptiness/handle closure, and one shared 30-second evidence
finalization/removal deadline. The maximum-deadline case consumes its full
30-minute lifetime; all other cases should trigger earlier bounded exits.
Record each run's actual elapsed time and storage use separately. Preserve every
runtime/evidence directory and journal on failure; do not retry a failed case
until the cause has been diagnosed and root has read back the preserved state.

Native evidence must independently establish exact payload/job membership,
root completion, zero active job members, owned handle closure, retained
bounded stdout/stderr and complete runtime snapshot, independent evidence and
manifest readback, correct outcome, and runtime disposition only after the
bound receipt. Include live-child cleanup, monitor survival of client loss,
negative assertion then restored assertion, and sentinel survival. Host export
remains unimplemented; report locally retained evidence honestly and do not
claim host delivery. This execution route does not authorize package build,
bootstrap/install, or release acceptance.

## Present status

The immutable 7b source archive and harness/parser/17-input preflight are recorded above. The one authorized harness invocation used `C:\RhaiQuality\runs\monitor-source-c58407e0123145698ab1d70e70473f7e`; its 17-input hash/copy gate passed. Compilation then stopped on five `CS0103` errors because `EnsureFinalizationBudgetIfSet` was scoped inside `RuntimeAllocation` but called by five enclosing-backend copy/scan/transfer/readback methods. No fixtures ran. Preserve this failed run root and its original logs/screenshots.

The local source candidate `WindowsCustodyBackend.cs` SHA-256 is `368e230e67b6712a29386b8623c69bf9e58ab404687a79078685ffe5cf061ee5`. It moves the required-deadline and optional-deadline helpers unchanged to backend scope and removes their nested copies. Static brace/scope/call-site checks and `git diff --check` pass; no compile or guest retry has occurred on this candidate. Root accepted the focused source change. The harness pin for this backend was updated; a static comparison confirms all 17 pins match the current tree and the other 16 hashes are unchanged. Updated `RunSourceFixtures.ps1` SHA-256: `b1ce7161c87d8aead4d46953f87719dba1f3203a166973ff6bdee655e8c2e372`. No guest input or invocation has used the updated harness. Do not restart from or alter the previous root. Any later run must use a fresh unique path under the new private guest resource convention, after source review, and remain within the original one-hour source-fixture bound. Expert02 monitor limits and all earlier launch/cause history remain unchanged. This source-fixture attempt does not establish native monitor, payload custody, runtime removal, or full acceptance.
