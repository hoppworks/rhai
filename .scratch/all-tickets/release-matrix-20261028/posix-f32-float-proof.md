# Native POSIX combined `f32_float` profile — bounded acceptance slice

At fork-main base `0cec849682e177c8149f5f15dc28bcaedae6e59f`, native
macOS 27.2 arm64 and Workhorse Linux kernel 7.2.11 x86_64 used Rust/Cargo
1.77.2 with `testing-environ,sys,net,f32_float` and Cargo.lock SHA-256
`12084a90214418632e80bbaf95983925c2c3886f57f40e2a305b4a1ec353d802`.
Both runners verified the 448-file frozen source manifest and archive. Relative
to that manifest, only `tests/sys_process.rs`, `tests/serde.rs` and
`tests/net_reads.rs` were overlaid from the current checkout; their exact
SHA-256 values are in each `run.json` and `linux-f32-float-binding.json`.
The product sources and lock were identical across the three runs. Source,
Cargo target and cache lived under each owned `AGENT_RUNTIME_DIR`.

The macOS attempt 01 compiled all 11 named targets and ran three expected
wrong-expectation controls. Each exited Cargo 101 with one named failed test:

| Control | Observed assertion |
|---|---|
| Combined sys/net | Fresh host filesystem readback differed from the deliberately wrong bytes. |
| TCP `f32_float` timeout | A real peer supplied `Z`; the script rejected fractional and nonfinite timeout inputs without consuming it. The test returned true, deliberately expected false. |
| Process `f32_float` output bound | Invalid durations left the child record absent; a finite fractional duration launched and reaped the child. The later over-cap child produced `abcde`, the host retained `[97, 98, 99, 100]`, and the deliberate expectation was `[97, 98, 99]`. |

The first runner stopped after these valid controls because its parser searched
for literal `abc` and `abcd`, while Rust formatted the compared byte slices as
number arrays. It did not reach GREEN. The source, lock, profile and controls
were unchanged for macOS attempt 02. That separate bounded invocation
recompiled the same 11 targets and ran their restored suite: 159 top-level
tests passed, 0 failed, 1 ignored. The exact `net_reads` target passed 8 tests
including the `f32_float` case, and `sys_process` passed 53 with 1 ignored.
The runner now checks the actual byte-array format for future full invocations.

Linux ran all steps in one bounded scope: 11-target compile exit 0, the same
three intended assertion REDs exit 101, then restored suite exit 0 with 167
top-level passed, 0 failed, 3 ignored. The exact `net_reads` target passed 8
tests and `sys_process` passed 62 with 3 ignored. `net_metadata` compiled but
ran zero tests in both OS profiles because `metadata` was not enabled. The
suite counts exclude nested child-harness output in the process target.

Both runs used actual Rhai scripts through the public Engine/host API and
real OS peers or child processes. They support the named f32 duration
validation and bounds under this combined profile, not every possible
duration, Windows, unrelated feature combinations or release completion.
All step-log hashes match their exported `run.json`; the Workhorse `run.json`
SHA-256 matched the remote original before exact stage retirement. The three
private runtimes were removed by the scoped runner. Both exact empty macOS
session scopes and the exact inactive Linux transfer stage and empty scope
were retired after export. Foreign resources were untouched.

Independent combined correctness/spec/repository review: PASS for the named
POSIX cases. The reviewer verified source, lock, feature and log-hash binding
and the intended assertions, including the original macOS parser failure.
Cleanup is supported by the recorded exact-scope and stage readbacks; the
reviewer did not independently query the retired resources.
