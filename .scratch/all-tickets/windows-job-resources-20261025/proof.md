# Native payload Job resource limits

Status: combined independent review PASS for actual payload/ordinary-child Job
resource configuration and affected environment acceptance. Basebd3556a62 plus
this package's changes; no Rust/library code, protocol, closure or resume changes.

## Problem and implemented behavior

The detached monitor does not inherit controller limits. The real payload Job
previously set only kill-on-close, so controller/compiler caps did not bound the
workload. MonitorPayloadJob now sets kill-on-close, active-process, per-process
memory and aggregate Job-memory flags before atomic JOB_LIST process association:
16 active processes,1GiB committed memory per process,2GiB committed memory per Job.
No breakaway/silent-breakaway flags are granted. A SetInformation failure follows
existing fail-closed setup unwind before any process is created or resumed.
Current source21e59d116fab58332ec4fea648cf5abfadc26782756da9cbf6343085b8af2942.

## Actual native test-first evidence

Workhorse VM rhai-win11-quality UUIDdc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19, existing
RhaiTest non-admin/Windows10.0.26300.0/64-bit PowerShell5.1/native C#4.14. No install,
login change, VM reset, foreign process action or Windows Cargo invocation.

Use the existing canonical RunSourceFixtures -BuildOnly
-PayloadWorkRetirementAbortOnly compiler bootstrap, then the existing public
MonitorAcceptanceDriver/ScopedRunner --lease-client after compiler-owner exit.
The existing RunPayloadEnvironmentControl now accepts Contract job-resources;
its existing environment/retirement branches remain intact. BuildRoot supplies
native manifest-derived binary pins, avoiding hardcoded previous binary hashes.
Hash-guarded Start commands,15-source manifests and both source snapshots are in
red/ and green/. Source review precedes native execution; host source-medium readback
guards the full Start SHA. Both builds have the same new fixture/oracle; RED uses
old production sourceadf9, GREEN uses21e59. Thus only actual resource setup changes.

| Case | Native result | Independent observations |
|---|---|---|
| Expected RED before fix | Driver0/payload42; fixture explicitly reports FAIL | Actual kernel flags00002000, active limit0, process/job memory0; fresh root record, intended assertion stderr, stopped exact actor, actual runtime absent |
| Resource GREEN | Driver0/payload0 | Root and ordinary child each read actual kernel flags00002308,16active,1073741824process bytes,2147483648job bytes; wrong expected flags rejected then correct values pass; distinct PID/start identities, work file, both stopped, actual runtime absent |
| Same-build environment GREEN | Driver0/payload0, no second GREEN build | Five correct private paths and child cwd; fresh native record, parent environment/cwd unchanged, actual runtime absent |

RED112contiguous frames/33files, resource GREEN118/35, environment GREEN114/33;
all strict length/SHA-checked originals and8CRC-valid ordered journal records per
case. Exact closed-Job proof, lifecycle cleanup, snapshot/manifest/stdout/stderr/
fixture identity/hash ties and final REMOVED agree. Literal runtime absence has
an existing-snapshot negative control before the positive, so hidden leftovers
cannot be accepted from a directory-filter count. Actor readiness is atomic file
publication with bounded wait; no sleep substitutes for readiness. The child holds
120s naturally and is instead stopped by the exact Job after root exit.

The first GREEN keyboard dispatch lost its leading `if ` and produced a confirmed
PowerShell ParserError before Start invocation. No compiler/control ran. The same
reviewed/hash-guarded command then executed successfully once; dispatch02 explicitly
records its later successful resource/environment results. This is a preparation
error, not a product failure or native test repeat. Original screenshot/metadata
are retained. No saved-trace parser bug required repeating a test.

Two owned native build allocations:8compiler processes (6binary compiles plus2
canonical deliberate missing-source status controls),3public Drivers including
expected RED. Native compilation/control elapsed totals are not captured by this
existing entry; do not invent timings from host/UI time. Source/commands/features,
results, bounds and originals remain available; token/cost totals are unknown.

## Resource ownership and cleanup

Compiler observer270s +30s exact exit reserve; each small control10s +10s exit
reserve +10s pipe drain, serial export180s/64files/4MiB each/16MiB total/3500encoded
frame. RED510s and GREEN+environment720s are finite stage bounds. Canonical native
compiler owner has its independent Job/watchdog. Host /var available104311480320bytes,
RAM76112MiB; new peak256MiB is an estimate, not a human cap. Guest entry checks2GiB
free. Original source/proof is outside private build/runtime outputs.

The hash-bound native cleanup receipt confirms4 exact completed scopes absent:
RED build and3exported controls (55/34/36/34files). It rechecks file inventories,
source/original hashes, reparse absence, exact actor identities/runtime absence
and executable-path inactivity before deletion. Parent/foreign scope paths are
excluded. All3 own ISO media were exported/hash-checked/removed after original sdc
restoration; original sdb remains. The54-entry own host staging tree was byte-checked
and retired, as were all POSIX runtimes and the empty decoder session.

One useful current GREEN build is intentionally retained in-place under the
original finite boundary 2026-10-25T12:13:54.403215+00:00:
`C:\Users\RhaiTest\.local\share\agent-builds\rhai\job-resource-build-green-cdcd7eebb7ec4c89b8aa2f9e8f2054f4\run\monitor-source-cdcd7eebb7ec4c89b8aa2f9e8f2054f4\build`.
retained-green-build.json binds exact owner purpose,15source/3binary pins and earlier
retirement on ended/cancelled reuse. Native cleanup confirms it preserved, no second
cache copy or expiry reset. Before reuse check current physical path/no-reparse,
source/compiler/native manifest/bin pins, custody receipt and capacity. All other
physical paths are historical; never use them as evidence of an available build.

## Applicability and remaining work

This proves configured/inherited real kernel resource limits and two small actors'
work/closure, not deliberate quota exhaustion or a real project command. Failed
atomic association/no unowned execution or leaked partial handles, remaining backend
failed export/cleanup, monitor30min/watchdog-specific and bounded project-command
custody remain open before native Windows Rhai/sys/net/MSRV/feature acceptance.
Earlier lease/deadline/membership proofs retain their original revision/config scope;
they are not relabelled as new-limit observations. No blanket rerun was needed.

Limit semantics: [extended Job limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information)
and [basic Job flags/process limit](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information).
Kernel configuration/readback concerns committed memory, not total system RAM.
