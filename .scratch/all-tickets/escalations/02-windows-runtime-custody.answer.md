# Windows runtime custody design decision

Date: 2026-09-30. Reviewed the six references in the brief, including the candidate source identified as `2e65cb45`. This is a static design review. No guest operation, compilation, fixture, install, source implementation or remote write was performed.

## Recommendation

Use one independent, detached guest monitor per invocation, with the current runner reduced to a transport client. The monitor creates the runtime, creates and exclusively holds the payload job, creates the payload already associated with that job and suspended, then resumes it only after its custody handshake completes. The monitor survives client death and uses an end-to-end host lease plus a nonrenewable absolute deadline. It terminates its exact job, verifies emptiness, saves evidence outside the runtime and deletes only its recorded runtime.

Do not merely give a second process a duplicate of the existing runner's job handle. That keeps payloads alive after runner death until another actor notices, introduces a handle-transfer protocol, and still leaves the suspended-create/assign crash window. Moving all resource creation into the monitor is smaller and easier to audit.

The recommendation is a design that can be implemented locally; it does not accept the existing candidate or authorize Windows package execution. Guest availability, independent launch, bootstrap and native proof remain gates.

## Minimal actors and ownership

| Actor | Creates and holds | Death behavior |
| --- | --- | --- |
| Host controller | Connection, invocation identifier, challenge responses, exported evidence | Its silence expires the guest lease; no host process-group assumption |
| Guest runner/client | Starts monitor; holds its exact returned process handle and client pipe ends | Monitor observes its real process handle and/or pipe closure; runtime ownership stays with monitor |
| Guest monitor | Sole payload job handle; exact payload process/thread handles; runtime/ancestor directory handles; local evidence and ownership journal; watchdog | Its last job-handle close provides kernel termination fallback; retained journal/runtime have no successful cleanup claim |
| Payload and ordinary descendants | Only explicitly allowed standard I/O handles and scoped environment | Members of monitor's job; cannot prolong custody by inheriting its job handle |
| Native proof observer | Exact handles returned by its own fixture launches; separate sentinel job/runtime | Observes monitor failure without joining or terminating the payload job |

The monitor executable and its control/evidence directory must be outside the deletable payload runtime. The runtime remains an exclusive generated child of the already authorized `C:\RhaiQuality\runs`; never enumerate and clean every `scoped-*` directory. Monitor stdout must not be the diagnostic store. Store bounded logs directly in its exact evidence directory, with connection delivery optional.

## Independent launch and handshake

1. The runner constructs two private pipes and a real, inheritable handle to its own process with only synchronization/query rights. Pass only the monitor ends and that process handle using an explicit handle inheritance list. Do not pass a pseudo handle. Close every extra pipe end promptly; clear inheritance inside the monitor. Microsoft's [process attribute documentation](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute) defines the handle-list requirements.
2. Start the monitor without the connection's console (`DETACHED_PROCESS`) and without connection-owned standard handles. If the launch context has a job, request permitted breakaway rather than changing its limits. Detachment only separates the console; breakaway requires the existing job's permission. These are separate [creation flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags).
3. Before runtime allocation, the monitor checks itself with `IsProcessInJob(self, NULL)` and requires a successful false result. This conservative design refuses any ambient job rather than trying to infer an unknown transport job's lifetime. [IsProcessInJob](https://learn.microsoft.com/en-us/windows/win32/api/jobapi/nf-jobapi-isprocessinjob) supports the any-job query. Also verify that the monitor actually survives the authorized connection-loss fixture: an unjobbed process alone does not prove the transport lacks other termination behavior.
4. The monitor starts its watchdog first. The client sends a bounded immutable specification: source, relative executable, arguments and fixed policy limits; no caller-supplied cleanup path. The monitor generates the runtime and evidence identities, writes an allocation-intent journal, allocates exclusively, records directory identity, then returns `READY` with invocation nonce, exact paths, limits and its launch checks. All source staging and subsequent allocation are inside the monitor's setup budget.
5. Require a host round-trip challenge response before payload creation and again before resume. The client only forwards protocol messages; it must never renew the lease locally. Missing `READY`, missing commit, invalid specification or expired lease means no resume. Once control enters stopping, never accept a renewal or start another process.

Anonymous pipes can use dedicated blocking I/O threads, but no watchdog/control-thread wait may depend on their completion. Limit frame lengths and queues; never perform a pipe flush that waits for the absent peer. An implementation may use overlapped local named pipes instead, with explicit user ACL and remote rejection, but that adds endpoint setup and is not necessary for this topology.

## Close the suspended-process custody gap

The current `CreateProcessW(CREATE_SUSPENDED)` followed by `AssignProcessToJobObject` has an interval in which a dead creator leaves a suspended process outside the new job. A second process cannot repair an unknown handle by guessing a PID. A `finally` block cannot run after forced termination.

For this Windows 11 guest, use `STARTUPINFOEXW` with `PROC_THREAD_ATTRIBUTE_JOB_LIST = [monitorJob]`, `EXTENDED_STARTUPINFO_PRESENT`, `CREATE_SUSPENDED` and `CREATE_UNICODE_ENVIRONMENT`. Windows documents job association as part of creation, with this attribute supported since Windows 10. This supplies assignment before payload execution without a separate unowned interval. Keep the job handle non-inheritable; putting it in the job attribute is not putting it in the inheritance list. [Job-list attribute](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute), [CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw).

Immediately verify `IsProcessInJob(payloadHandle, monitorJob)` while suspended. Resume only on success and only once; for the newly created primary thread require the expected previous suspension count of one. Any unsupported attribute, job-association failure, unexpected membership or resume result fails closed. No retry using ordinary unowned creation. Native testing must verify creation-time failure and forced monitor death at this boundary; this crash-safety conclusion is an inference from the documented creation attribute, not measured guest behavior.

Create the unnamed job with kill-on-close and neither breakaway permission. Normal `CreateProcess` descendants inherit membership; brokered launches such as WMI are outside that promise. The payload contract must prohibit creating work through outside brokers/services or manipulating supervisors. Job Objects are resource custody, not a sandbox for hostile same-user code. [Job lifetime and descendant rules](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

## Finite lease and stopping policy

Suggested fixed implementation defaults: one challenge every 2 seconds, 15 seconds to lease expiry, 120 seconds for setup, a nonrenewable 30-minute monitor lifetime before stopping, then 30 seconds for termination confirmation and 30 seconds total for evidence finalization/deletion. These are proposed runtime policy constants, not permission for a measurement campaign or additional recovery attempts. Make all bounds explicit in `READY`; do not let input raise them.

Each challenge contains a fresh nonce and increasing sequence. Accept only the outstanding challenge's response before its expiry; duplicates, old frames and prebuffered future renewals do not count. The response must traverse the live controlling connection. Host renewal can extend only the short lease, never the absolute deadline. Runner exit, pipe EOF/error, cancellation, setup expiry, lease expiry, absolute deadline or payload completion all enter one idempotent stopping state.

Use `GetTickCount64` differences for these budgets, with short finite waits and a deadline recheck before processing renewal/resume. It is independent of system-time adjustment; Microsoft's [interrupt-time guidance](https://learn.microsoft.com/en-us/windows/win32/sysinfo/interrupt-time) identifies it for elapsed durations including sleep/hibernation. Windows 8+ relative [wait timeouts](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject) exclude low-power time, so one long wait alone is insufficient. After resume from sleep, check expired deadlines before accepting traffic. Hypervisor pause behavior needs native validation; no process can act while the whole guest is unscheduled.

Keep watchdog execution independent of source copies, filesystem I/O, log writes and blocked client pipes. Use a single synchronized handle owner; never close a handle another thread is waiting on. At a hard final deadline, terminate the monitor itself if its workers cannot finish; job-handle closure still supplies the fallback, while the journal remains incomplete. User-mode scheduling/storage stalls prevent an unconditional real-time guarantee. State bounds as policy under a running guest, with retained incomplete custody on exceptional failure.

## Process readback and cleanup are separate

On stopping, prohibit new launches, call `TerminateJobObject` on the exact owned job (including on ordinary success to remove residual members), and record its Boolean result/error. Wait for the exact root process with finite waits, capture its exit code only after a signaled wait, then release payload process/thread handles. Poll `QueryInformationJobObject` on the still-open job for `ActiveProcesses == 0` within the shared termination budget. Job termination includes child jobs; nesting restrictions must fail closed. [TerminateJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject), [nested jobs](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs).

Process references can delay accounting decrements even after termination. Release fixture observer handles when no longer needed, and release monitor-held root handles after status collection. A nonzero count after the deadline is an inconclusive cleanup failure, never justification to scan/kill by PID. [Accounting semantics](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information), [job query API](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-queryinformationjobobject). Completion notifications may optimize wakeups, but do not replace a successful final query.

Preserve payload exit status separately from supervision/cleanup status. Successful acceptance requires both a passing payload and confirmed cleanup. A payload exit code of zero with lease loss, failed query, failed evidence export or retained runtime is not acceptance. Do not overload all results into a single integer that can collide with a legitimate payload exit code.

Only after confirmed emptiness may the monitor finalize the local evidence and remove runtime content. Keep the job open until that confirmation. Record `termination_confirmed`, `evidence_saved_locally`, `exported_to_host` and `runtime_removed` independently. A broken host connection cannot receive an export; retain exact local evidence for later retrieval. It is valid to remove the runtime after a successful local export, but do not call it host-exported.

## Filesystem custody and partial setup

The candidate's string prefix checks and ordinary `Directory.Delete` would not prove exact safe deletion. Use the following contract, with native handle behavior tested before acceptance:

- Validate the existing allowed root and every ancestor component as local directories without reparse points. Open/pin relevant directory components with `FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT`, inspect attributes by handle, and omit delete sharing to prevent rename/replacement while held. The reparse flag applies to the opened component; it does not make unchecked intermediate components safe. Record volume/file identity, not just a spelling. [CreateFile handle/sharing flags](https://learn.microsoft.com/windows/win32/api/fileapi/nf-fileapi-createfilea), [handle information](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getfileinformationbyhandleex).
- Allocate the new runtime with an explicit protected DACL for the current task user and necessary system access; verify it. Do not recursively change the existing root's ACL or take ownership. Windows otherwise permits inherited/default descriptors. If the existing root cannot be safely used without altering foreign configuration, refuse it. [File security](https://learn.microsoft.com/en-us/windows/win32/fileio/file-security-and-access-rights).
- Pin the exclusive runtime for its entire lifetime, and keep its journal/logs outside payload writable paths. Before allocation, flush an intent record with the generated exact path; after allocation, flush its identity. A crash between those records leaves an uncertain allocation for exact investigation, not automatic deletion. Check regular-file flush outcomes; no volume flush/admin operation. [FlushFileBuffers](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers).
- Stage sources without following reparses; validate by opened handles rather than check-then-copy attributes. Validate the relative executable against Windows path syntax, including drive-relative/device/ADS forms, and open the actual staged file through checked components. Avoid relying solely on `IsPathRooted` and a textual prefix. Source mutation or sharing failure must stop setup.
- After job emptiness, enumerate only the held runtime. For each child, open without following reparses and pin directories before descending. Reject unexpected reparse points and retain the exact runtime instead of traversing them. Delete opened, verified entries by handle; remove directories bottom-up and the empty runtime using handle disposition. Never clear reparse metadata and then recurse into the target. [Reparse handling](https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-points-and-file-operations), [SetFileInformationByHandle](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-setfileinformationbyhandle), [file disposition](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_disposition_info).
- Close disposition handles and independently read back absence through the pinned parent. Sharing violations, read-only files, identity mismatch, unsupported filesystem, failed reads or cleanup timeout retain exact data and a failure receipt. Never delete evidence to make a failed cleanup appear clean.

ACLs cannot distinguish the monitor from a malicious payload with the same user token. Holding handles and refusing reparses protect the intended operational contract; they do not establish adversarial isolation against same-user processes, DACL changes or supervisor attacks. If hostile payload containment is required, this topology is insufficient and a separate authorization/isolation decision is needed. Existing task scope is owned builds and fixtures, not hostile execution.

All allocation, staging, validation and environment setup must enter the monitor's cleanup state machine; currently allocation/copy precede the candidate's `try/finally`. Before a payload exists, there is no process cleanup to claim. After creation succeeds, the exact job owns even an unresumed payload. On setup failure, preserve diagnostics and remove only verified monitor-owned allocations. If identity was not recorded or all supervisors were lost, retain data for recovery.

No third perpetual reaper is necessary under the brief's explicit allowance for recoverable data after loss of all supervisors. After monitor death its unnamed job may be gone; a later journal reader cannot reconstruct a live job handle from a GUID, PID or old path. Recovery remains exact investigation with unknown termination/cleanup status until independently established. Never synthesize a successful receipt from the monitor's disappearance.

## Native proof required before package use

Use owned toy fixtures first; preserve baselines and a separately owned sentinel. Every injected interruption is bounded and predeclared. This list defines coverage, not permission to start measurements now.

| Case | Independent observation required |
| --- | --- |
| READY/commit interrupted; copy fails; invalid executable; monitor dies during allocation | No payload execution; exact partial runtime/evidence inventory; uncertainty preserved where identity was not recorded |
| Monitor dies during creation, after creation while suspended, and before resume | No unowned suspended orphan; exact fixture handles signal; no false cleanup receipt |
| Root plus live grandchild | Actual job membership, finite root/descendant exits; separate sentinel still responds |
| Root success/failure with residual child | Correct payload status recorded; child terminated; job empty; runtime absence and local evidence read back |
| Runner forced termination | Same monitor remains alive long enough to stop exact job, save evidence and delete runtime |
| Actual controlling transport disconnect, plus black-holed connection with client still alive | Monitor survives transport teardown; EOF or challenge lease triggers within bounds; saved local evidence later retrievable |
| Lease replay, stalled pipes, expired commit, maximum deadline with valid renewals | No lease extension by stale/local frames; no late resume; output backlog cannot block watchdog |
| Job-list assignment failure and incompatible nested context | Creation fails closed; no normal-creation fallback; only fixture-owned resources affected |
| Monitor itself inherits transport job | Refusal before payload/runtime setup; no detach-equals-independence claim |
| Runtime/source reparse, ancestor substitution, ACL/sharing failure | Foreign target unchanged; exact runtime retained when safe deletion cannot be proven |
| Monitor death with live descendants; simulated cleanup/export failure | Kernel job fallback observed; incomplete journal retained; no successful removal receipt |
| Sleep/resume and deadline recheck | Expired work does not resume/renew; observed timing and scheduling limits reported |
| Negative assertion, restored assertion, then real Rhai command | Wrong expectation fails; restored expectation passes; only then scoped native full-stack acceptance |

## Remaining blockers and local next step

The authorized guest's two black framebuffer captures remain the current evidence. This review creates no safe interactive desktop or compiler path. No package build should run.

Local work can implement the monitor/client split, creation-time job assignment, state machine, protocol, journal schema, bounds and handle-based filesystem operations, plus source-level contract fixtures and documentation. The bounded native correction justified by this answer should implement these together; preserve this escalation/attempt history.

Native work must establish a credential-free permitted launch that genuinely survives connection death, a bounded/private bootstrap of the first monitor binary, installed-runtime/ABI compatibility, source/runtime ACL and filesystem behavior, and every proof row above. An unowned compiler invoked to build the first supervisor does not satisfy custody merely because its output directory is unique. Use an already safely bounded bootstrap mechanism or a reviewed prebuilt monitor whose guest runtime compatibility is established; do not invent a silent bootstrap exemption.

No new product/release/API decision is needed for this proposed lifecycle design. If ambient jobs prevent breakaway, the authorized root requires foreign ACL changes, bootstrap cannot be bounded, or guest access remains unavailable, stop the dependent native path and report the exact external-state blocker. No service, scheduled task, administrator change, credentials, global configuration or further escalation chain is part of the recommendation.
