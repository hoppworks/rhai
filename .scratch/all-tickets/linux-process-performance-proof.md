# Linux process measurement proof

Status: accepted for the Linux Direct/Managed measurement criterion after combined independent review.

Baseline: `8c0ee4634355aee4e841b455461a7dd5aac2aa18`; reviewed overlay from `a7cef5661f696473631c2f71559561c43878ef6c`. Production sources are unchanged. Native Linux x86_64 on workhorse, private Rust/Cargo1.77.2, `testing-environ,sys`, locked dependencies and two build jobs. Admission recorded zero foreign heavy runs.

The public Rhai Engine and SysPackage execute real children. Start timing spans script spawn to independently validated child readiness. Capture timing spans the complete public `run_raw` call for exactly1MiB of zeros, including startup and collection. Alternating Direct/Managed order reduces a fixed order effect; this small sample does not establish causal overhead or a platform-wide benchmark.

| Measurement | Direct | Managed |
|---|---:|---:|
| Start to readiness, median [min,max],5 per mode | 1.356 [1.243,1.461] ms | 1.537 [1.380,1.612] ms |
| Whole captured run, median [min,max],3 per mode | 100.860 [100.831,101.153] ms | 201.227 [201.206,201.448] ms |
| Whole captured run rate, median [min,max],3 per mode | 9.915 [9.886,9.918] MiB/s | 4.970 [4.964,4.970] MiB/s |

Both held children had one thread and three descriptors. In each mode, the harness changed from2threads/4descriptors before spawn to3/6 while held, then returned to2/4 after public wait. These are one held snapshot per mode, not peaks. Managed had a dedicated one-member process group; Direct inherited a five-member group whose other members are context, not owned children.

Controls independently rejected a corrupted byte copy and a zero-descriptor expectation against real child observations. The proc census control rejected malformed/unreadable/entry-error states and skipped a genuinely vanished entry. Both native tests returned0; raw counts are10start,6capture,2live-resource and2closed-resource rows.

The helper completed its command sequence in23.270seconds.31periodic samples observed maxima862348KiB RSS,730888KiB storage and7descendants. These samples are not continuous peaks. Outer/runner/helper limits remained600/585/540seconds, descendant cap16, preemptive storage1572864KiB and hard RSS/storage2097152KiB.

Originals are preserved in `linux-process-performance-evidence/originals.originals.tar` and its verified extracted tree. Archive SHA256: `9d9a76ada075e53e47ae605509f89ee72e49a8be64ad4e4118e3e1dd732d7473`. Local source/lock/tool/control/measurement binding passed. First collector custody attempt rejected empty command-line observations for exited short-lived sampler instances. Reviewed local consumer correction `5b7088339e15d8c2b5083d814891fa9ca2c7ee53` preserved all identity/ancestry/absence checks, required exact observed argv for each sampler type, and rejected every populated wrong argv. Actual preserved-originals and wrong-runtime probes passed. The same archive resumed without another export or native allocation; fresh custody passed for82identities,62sampler instances and12public held fixtures, then the exact stage was retired. A separate fresh read checked84identities including both launchers,8owned groups and6logical/physical stage/scope/runtime paths, all absent or reused/empty. See `originals/{fresh-custody-readback.json,retirement-readback.json,root-fresh-closure.json}`. The archive retains the originally staged consumer; the accepted local correction is identified separately by `linux-process-performance-collector-repair-freeze.json`. Infrastructure failure1 was recovered once; no product failure was inferred.

Coverage is limited to the stated Linux Direct/Managed measurement criterion. Stdin, lifecycle precedence, native macOS/Windows, metadata/docs, broader feature/release acceptance and stopped cause histories remain open.
