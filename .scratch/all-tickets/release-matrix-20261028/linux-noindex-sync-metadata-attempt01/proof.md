# Native Linux combined `no_index,sync,metadata` profile

Status: **accepted for the 11 executed targets and this feature/OS/toolchain
binding**. Full release and A–F/Ticket03 acceptance remain open.

## Binding and run

At fork-main `b93645f46a1262a0b4c7b83135ad29ea89e5d3fe`, all 448 archived
source files matched the checkout. The immutable archive SHA-256 was
`0005b38a387b419802335e141cb259de86f1ec9424e6e4cf2b8bc3beaf30bdd7`,
manifest `254d021566408f44b2b645551e2598f7cf9db5fee63c5e34bcc7ea20012ec9ba`,
and Cargo.lock `12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
These are the same verified inputs retained in the [Windows profile media](../../windows-rhai-native-20261028/release-matrix-windows-20261028/noindex-sync-metadata-attempt01/media-input/).
[binding.json](binding.json) pins source, toolchain, features, targets and limits.

The existing POSIX scoped runner (SHA-256 `25d42cec...`) executed
[run-linux-noindex-sync-metadata.py](run-linux-noindex-sync-metadata.py) with
`TMPDIR` set to the exact owned, initially empty session scope. The script
verified every archive entry, extracted an owned source copy under
`AGENT_RUNTIME_DIR`, copied the exact lock there, and set private
`CARGO_TARGET_DIR` and `CARGO_HOME`. No shared source/build tree was mutated.
Workhorse reported Linux `7.2.11-ogc4.1.fc44.x86_64`, glibc 2.43, and native
Rust/Cargo 1.77.2. The outer runner limit was 1200 seconds; compile, RED and
suite step limits were 900, 60 and 600 seconds.

## Original results

The [run record](evidence/run.json) and original logs record:

| Step | Exit | Duration | Result |
| --- | ---: | ---: | --- |
| Eleven-target `--no-run` | 0 | 14.330 s | All target executables compiled. |
| Exact combined wrong expectation | 101 | 0.064 s | One test failed at fresh host-file assertion: actual `filesystem-payload`, deliberately expected `incorrect filesystem expectation`. |
| Eleven-target restored suite | 0 | 0.814 s | 102 passed, 0 failed, 0 ignored; each named target ran nonzero tests. |

The targets were `combined_sys_net`, `sys_env`, `sys_fs`, `sys_policy`,
`net_connect`, `net_listen`, `net_reads`, `net_writes`, `net_metadata`,
`sys_process`, and `sys_process_report`, all with
`testing-environ,sys,net,no_index,sync,metadata`. The exact combined test uses
a real Rhai Engine with both registered packages, a fresh independent host
file read and a real TCP peer on an OS-selected port. Its restored run passed
the same assertion and typed-error checks. The `sys_process` target ran only
two enabled cases under this profile; omitted cases are not claimed. The wrong
control establishes sensitivity for the combined assertion, not automatically
for every assertion in all 11 suites.

Each original step log's SHA-256 and size matches `run.json`. The outer runner
exited 0, removed its private runtime, and `rmdir` retired the exact empty
session scope (exit 0). [Remote readback](remote-readback.json) enumerated and
hash-checked all 13 owned staging files against saved local/shared originals.
[Guarded retirement](stage-cleanup.json) removed only that stage; a fresh
[post-cleanup readback](postcleanup-readback.json) finds stage and scope absent.

One independent combined correctness, repository standards and specification
review returned PASS for these executed cases and their cleanup; see
[combined-review.md](combined-review.md). Other OSes, assertions and release
rows remain separately open.
