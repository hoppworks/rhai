# Next Windows monitor verification route

## Authority and current boundary

The 11:17–11:47 UTC entry in `windows-monitor-staging-ownership-review.md` is a
completed SOURCE allowance and records zero execution launches/resources. It is
not a human-imposed native cap. The current task instruction separately says to
hold guest/build/native work until root reviews this source and custody harness.
No historical human native run-count or resource cap was found in the cited
instructions. Keep prior activity totals intact; do not convert the 30-minute
source planning estimate into an execution cap.

Project `AGENTS.md` selects strict verification. The current human scope
authorizes writes only to the approved `hoppworks/rhai` fork; the public
original is forbidden. This preparation makes no remote write. The prior
`acceptance.md` records the authorized
`rhai-win11-quality` VM on `workhorse`. A current read-only
`virsh -c qemu:///system domstate rhai-win11-quality` query via `workhorse`
returned status 0 and `shut off`; the old black-console observation is stale.
No start, configuration, or guest command was issued. This does not establish a
safe guest compiler/bootstrap route. The VM inventory documents
an existing Build Tools compiler at
`C:\BuildTools\MSBuild\Current\Bin\Roslyn\csc.exe`, Windows 11 Pro x64 and
SDK 26100. It does not establish current guest reachability or provide a current
PowerShell 7 path. No credentials, install, bootstrap, admin change, home/config
change, baseline mutation, or guest command is part of this preparation.

## Frozen source input and fixture harness

`tools/windows-scoped-runner/fixtures/RunSourceFixtures.ps1` pins SHA-256 for
the accepted `c8c6b18caaa855d2f66e0fc1f84e594d4f1e5e6b` input set: nine
production C# files and eight C# fixtures. It copies only those inputs into an
exclusive GUID run directory and verifies every copied hash before compiling.
The script uses an already-installed 64-bit PowerShell 7 host and the existing
`csc.exe`; absent hosts/compiler fail closed without bootstrapping.

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
& '<resolved existing 64-bit pwsh.exe>' -NoLogo -NoProfile -NonInteractive -File `
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

No PowerShell parser/runtime, compiler, fixture, native API, guest, SSH, UI,
bootstrap, build, or runtime-removal command has run for this preparation. The
host has neither `pwsh` nor `powershell` on PATH, so even PowerShell syntax has
not been parsed locally. `git diff --check` is the only executed source check.
The authorized VM's current read-only state is `shut off`. The next safe action
after root reviews the frozen harness is to reconcile an activation/launch path
against existing authority and custody. No VM start has occurred; do not infer
guest availability from the state query alone.
