# Frozen Linux overhead launch package

This is the source-only preflight for the single POSIX overhead package. It
binds candidate commit `00bed4a0dfeb103ff209ba4c76dac7ae797b7c56`, source archive
SHA-256 `5414ea195ad00152b1eae36b3f4e10943ba5d9bf323baff6410cca0c5b4d8b98`,
baseline lock SHA-256
`8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa`, and
the private libc-edge lock SHA-256
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.

Stage a fresh absent-only directory containing `source.tar`,
`Cargo.lock.baseline`, `process-overhead-proof.py`,
`measure-process-overhead.py`, `remote-overhead-launch.sh`, and
`runner/tools/run_scoped.py`. Create an empty real `evidence/` directory.
The staged launcher's independent monitor records exact PID/start-tick lineage,
samples descendants and private runtime storage at one-second intervals, fails
closed above16 owned descendants or at1,572,864KiB sampled storage, and performs
exact cleanup/readback after `run_scoped` exits.

Run from the remote stage directory with an external600-second bound:

```sh
PROOF_STAGE=/root/<fresh-stage> timeout --signal=TERM --kill-after=2 598s bash /root/<fresh-stage>/remote-overhead-launch.sh
```

The shell launcher runs the copied `run_scoped.py` with a585-second limit. Its
private driver allows at most580 seconds total and invokes the reviewed
measurement driver, which limits Cargo to540 seconds and two jobs. Direct
preinstalled Rust1.93 toolchain binaries are used. Source, Cargo home, target,
rustup home and temporary files stay inside `AGENT_RUNTIME_DIR`; the private
source lock starts from the accepted baseline and adds only the reviewed libc
edge. No rustup install/default change, global cache, or home configuration is
permitted.

The ignored public integration test performs exactly120 executions:30 paired
samples per workload for `DirectChild` and `Managed`, with alternating scope and
workload order, no warmups, and no retry. The workloads are platform `true` at a
2-second API timeout and exact8MiB stdout plus8MiB stderr capture at6 seconds.
The theoretical API timeout sum is480 seconds. First failure, timeout, missing
sample, output mismatch, or cleanup failure stops the package. Raw CSV is
exported before optional toolchain metadata collection.

The fixture test proves only that its exact capture child PID is absent at the
API return boundary; it does not measure retained descriptors or perform a
global resource census. The independent runner ledger and final cleanup readback
provide package-wide process/group evidence. Retained worker/handle/descriptor
counts by scope remain open unless existing instrumentation exposes them.
Resource policy stays at2GiB memory,16 descendants, and the sampled storage stop
above; a sampled maximum is not a continuous peak. Unix/Linux measurement is
scoped to this package. No claim is made for Windows.

Before any execution, independently read back every staged hash and the empty
evidence directory. At termination preserve raw samples, summary/toolchain
metadata, source manifest, runner identity/heartbeat ledger, process and resource
samples, command identities, outer statuses, and exact PID/start/PGID cleanup
readback outside the private runtime. Do not relaunch after a failure without a
new diagnosis and root review.
