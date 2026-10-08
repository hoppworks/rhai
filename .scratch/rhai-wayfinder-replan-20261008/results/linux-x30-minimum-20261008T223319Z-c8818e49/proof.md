# Linux package-minimum repeated-process descriptor acceptance

Status: ACCEPTED by the same combined independent source/evidence review.
This result adds only X30 on native LLLM Linux x86_64, Rust/Cargo 1.77.2,
features testing-environ,sys. It does not close other X30 platforms/features,
Windows product acceptance, the release matrix, Ticket03 or A–F.

## Exact sources and execution

Committed fork source: 0fad14acff5e09d2cd873eed5c64e0eff852737c.
No dirty Windows source, test, configuration or foreign fixture was overlaid.
The compatible v3 lock SHA-256 is
2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425.
selection.json and source-inputs.json bind the actual committed Cargo manifest,
build source, unchanged Unix backend, public test, shared support and committed
fixture. The private official Rust/Cargo/std distributions and their independently
retrieved official digests are recorded in portable-1.77.2.json.

From the explicit private source cwd, the existing scoped runner executed:
    <private-cargo> test --locked --features testing-environ,sys --test sys_process --no-run --message-format=json
It selected the unique actual Cargo compiler-artifact executable, confirmed
the exact --list entry, then ran:
    <actual-executable> repeated_public_run_calls_keep_fd_count_stable --exact --nocapture --test-threads=1

The build returned0 in23.700s; the selected executable returned0 in7.479s.
Both the parent and its actual isolated census child report one passed test.
The isolated child invokes the public Rhai Engine 200 times with real /bin/true:
tasks3→3, file descriptors4→4, cleanup workers1→1 after the warm-up.
This is an independent /proc census, not a timing-only or zero-test assertion.
The parent has its existing finite60-second child/process-group failure cleanup.

## Reused meaningful sensitivity control

historical/ retains the original accepted1.93 expected RED101 at
'200 sequential public run calls changed the descriptor count', left4/right5,
plus restored GREEN0, command/lock/source/toolchain manifests and exact cleanup.
The unique expected-count mutation reconstructs the saved mutant source hash.
All four current test/census functions and full shared Engine/TempDir support
are byte-identical to those original sources; identities are in selection.json.
Only unchanged oracle sensitivity is reused. No old1.93 runtime result is claimed
as the new1.77.2 GREEN. historical-export-readback.json confirms every entry in the
original output SHA256SUMS exists and matches. No historical execution replayed.

## Custody and limits

One finite invocation; actual scoped-runner exit0 and outer59.165s.
The fresh session directory used absolute TMPDIR; compiler, std, sources, target,
Cargo cache and mutable test data stayed in AGENT_RUNTIME_DIR.
The private runtime and exact empty UID/device/inode-bound outer scope are absent;
all27 observed PID/start identities are absent. cleanup.json retains original
checks. Foreign processes, resources, configuration and the Windows VM were untouched.
Periodic samples record storage1,772,667,030bytes and RSS972,386,304bytes maxima
within declared8GiB storage/RSS,32members,2Cargo jobs and1200seconds. These are
samples, not continuous peaks. All private compilers/caches/binaries were retired;
only exported immutable evidence is reusable.

The source review corrected one missing-identity bookkeeping guard before the
only launch. Its before-source and exact diff remain preserved. The earlier
read-only inventory corrected engine's import location before any execution.
Neither preparation issue is a product RED or another native attempt.
phases.json deliberately preserves the original accepted:false pending marker;
the separate final acceptance.json records the accepted independent disposition.

## Final independent disposition

combined-review.md is the verbatim new Linux X30 section of the existing combined
report, SHA-256 304bb1c3ba0c50f67eecca060e9b9684530de69d768f8e5fbe6cc3a5e340fa9b for the complete report at acceptance.
The reviewer verified all73 then-present output-manifest entries and original
status/source/lock/toolchain/census/cleanup evidence. It accepts only this native
Linux1.77.2 baseline X30 row; native Windows and broader coverage stay OPEN.
