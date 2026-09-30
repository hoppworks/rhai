# Native Linux TCP release feature gates

**Result:** The remaining independent TCP feature gates passed on native Linux from source revision `243404c9e04350422b3d9f4e1cfee866b6b3ff2a`. The accepted baseline, sync and no-index evidence in `.scratch/linux-tcp-proof/proof.md` was reused and not rerun.

## Environment and command scope

- Native host: `workhorse`, Bazzite 44 x86_64; kernel `7.2.4-ogc3.1.fc44.x86_64`.
- Rust: `rustc 1.97.1 (8bab26f4f 2026-07-14)`; Cargo `1.97.1 (c980f4866 2026-06-30)`.
- Source archive SHA256: `741b622dec642ab3cdf36639405ac48d16802d6d481ac8a857dea15f56a50f12`.
- Cargo generated a scoped lockfile with SHA256 `4aa2e32287d33184c12e98c7a86a17574dbf3a2361c968c76e9611bfd4396cc3`; the repository revision does not track `Cargo.lock`.
- One remote private `run_scoped.py --timeout 900` invocation ran for 48.3 seconds. Cargo used `--locked --jobs 2`; each integration target used `--test-threads=1`. Dev/test debug info and incremental compilation were disabled. One private source tree, Cargo home, target directory and evidence directory shared the same runtime.
- The checked commands include 23 successful feature/target invocations, one wrong-peer control (expected exit 101), and one corrected readback (exit 0), plus lockfile generation. Exact per-command statuses are in [status.tsv](evidence/status.tsv), and commands and full output are in [native-linux-net-release.log](evidence/native-linux-net-release.log).

## Feature results

The existing Engine integration targets exercised the public `NetPackage` against real loopback TCP peers. Peers independently supplied or read the socket bytes.

| Feature set | `net_connect` | `net_listen` | `net_reads` | `net_writes` | `net_metadata` |
|---|---:|---:|---:|---:|---:|
| `net,metadata,serde` | 4 passed | 7 passed | 7 passed | 10 passed | 1 passed |
| `net,only_i32,no_float` | 4 passed | 7 passed | 7 passed | 10 passed | — |
| `net,unchecked` | 4 passed | 7 passed | 7 passed | 9 passed | — |
| `net,no_index,sync,metadata` | 4 passed | 8 passed | 8 passed | 10 passed | — |
| `net,f32_float` | 4 passed | 7 passed | 8 passed | 10 passed | — |

The dedicated `net,no_object` target passed 3/3. `net,no_object,metadata,serde --test net_metadata` passed 1/1. The ordinary dot-syntax integration suites were not run with `no_object`; the dedicated target covers its supported explicit-call API.

The deliberate `net,f32_float` peer-byte control exited 101 at the independent peer assertion: actual bytes were `[0, 255, 65]`, while the deliberately incorrect expected bytes were `[0, 254, 65]`. The same exact test then passed with the override removed. The output is retained in [wrong-peer-byte-control.log](evidence/wrong-peer-byte-control.log) and [restored-peer-byte-readback.log](evidence/restored-peer-byte-readback.log).

Across successful matrix and corrected-control invocations, 148 tests passed; the single control test failed at its intended assertion. There were no unexpected failures or ignored tests.

## Runtime cleanup and limits

The whole private runtime (source, Cargo home, target and runtime evidence) was sampled at one-second intervals with a preemptive stop at 1.5 GiB and an overall 2 GiB cap. The sampled maximum was 862,019,584 bytes. Sampled descendant socket descriptors peaked at 6 against the limit of 16. These are sampled maxima, not continuous peak measurements.

The scoped runner returned 0. Independent post-run readback found runtime `/tmp/agent-build-ecwjw3ay` absent and all 135 captured runner/descendant PIDs absent. Start/end timestamps, every captured PID, runtime and stage identities are recorded in [runner-result.txt](evidence/runner-result.txt) and [stage-hashes-and-identity.txt](evidence/stage-hashes-and-identity.txt). The exact owned staging directory was `/root/rhai-net-release-features/243404c9`; evidence was copied into this checkout before cleanup. [cleanup-readback.log](evidence/cleanup-readback.log) records the inode-checked stage and temporary hash file removal and their independent absence afterward.

The verifier starts each Cargo command in its own session. The outer scoped runner therefore cannot guarantee process-group cancellation of a Cargo child if the bounded invocation is interrupted. No interruption occurred; independent readback confirms all captured processes and the runtime were absent after normal completion. Do not reuse this driver for another invocation without fixing inherited process-group ownership or adding unconditional cleanup.

## Remaining release scope

This closes only the listed native Linux TCP feature rows. Combined `sys,net`, optional package MSRV 1.77.2, core MSRV, native Windows and process proof remain open. No production source or test files changed.
