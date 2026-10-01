# Next Windows monitor verification route

## Authority and current boundary

The 11:17–11:47 UTC entry in `windows-monitor-staging-ownership-review.md` is a
completed SOURCE allowance and records zero execution launches/resources. It is
not a human-imposed native cap. The current task instruction separately says to
hold VM activation until the source/custody harness review, then authorized the
exact VM activation and read-only guest preflight. Compile/fixture/native work
still requires an established bounded input-transfer route and current toolchain
readback. No historical human native run-count or resource cap was found in the
cited instructions. Keep prior activity totals intact; do not convert the
30-minute source planning estimate into an execution cap.

Project `AGENTS.md` selects strict verification. The current human scope
authorizes writes only to the approved `hoppworks/rhai` fork; the public
original is forbidden. The reviewed harness checkpoint was pushed only to
`origin/task/windows-scoped-runner` at `d9480102a7f1d0cc87a7c294e2898995ed98dfd0`;
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
closed-or-filtered; direct console plus outbound HTTPS is the currently
established transfer route. SSH/SCP has only copied host-created screenshots
from the hypervisor. No credentials, attachment, mount, bootstrap, service
change, or VM baseline modification occurred. The VM remains running. This
supersedes the earlier no-shell/no-transfer conclusions in this plan; retain
those as historical observations preceding the authorized desktop wake and
preflight.

## Native custody acceptance route after the harness

The current workspace has no host controller fixture that speaks the real
`--lease-client` protocol, supplies the immutable specification, responds to
fresh challenges, and independently reads evidence. Do not launch the monitor
from the source harness and label a disconnect/EOF run as successful protocol
coverage. Add that bounded driver as the next source subrequirement after review;
keep its controller process inside the harness job. The compiler/fixture
harness does not launch `MonitorTransport` and does not grant breakaway. A
separate source gate must reconcile the monitor's
`CREATE_BREAKAWAY_FROM_JOB` request against its bounded launcher before a real
client driver can run. The production payload job remains kill-on-close with no
breakaway permission. The monitor independently owns the payload job and runtime, and observes client
process/pipe death. This monitor lifetime model is the Expert02 route; an SSH or
PowerShell job alone does not replace it.

Once the driver is present and reviewed, use one finite acceptance batch with
the same 1-hour outer bound, 2 GiB job memory cap, 16-process limit, 2 GiB free
space preflight, and exact unique run root. Run ordinary-success/residual-child,
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

No PowerShell parser invocation, compiler, fixture, native API, source archive
download, bootstrap, package build, or runtime-removal command has run. The
current host has neither `pwsh` nor `powershell` on PATH, but the Windows guest
has read-back-confirmed Windows PowerShell 5.1 and Roslyn 4.14.0. `git diff
--check` is the only executed source check. The exact authorized VM is running
after activation; console evidence is recorded above. The harness compatibility
adaptation remains mutable and awaits independent source review before guest
transfer/compile/fixture launch. A reviewed real-client host driver and bounded
launch path remain prerequisites for later native acceptance. No shutdown or
VM reconfiguration was performed.
