# Optional sys/net Rust 1.77.2 native proof

## Scope and immutable inputs

- Acceptance: strict Engine plus real OS fixtures for both optional packages at Rust 1.77.2 on native macOS, with `testing-environ,sys,net,metadata` enabled.
- Frozen source: commit `0c2dda12bd53d2a3477bea1ff98ea66ad0ab1fab`; `git status --porcelain=v1 --untracked-files=no` was empty before launch. Source and manifests were copied with `git archive`; no production files or manifests changed.
- Host: Darwin arm64 (`aarch64-apple-darwin`).
- Toolchain was installed using `/Users/hoppworks/.cargo/bin/rustup toolchain install 1.77.2 --profile minimal --no-self-update`, with `RUSTUP_HOME` and `CARGO_HOME` under the unique `AGENT_RUNTIME_DIR`. Direct private binaries reported rustc `1.77.2 (25ef9e3d8 2024-04-09)` and cargo `1.77.2 (e52e36006 2024-03-26)`; verbose logs are `evidence/rustc-version.log` and `evidence/cargo-version.log`.
- Resolution began from the accepted full-workspace v3 lock candidate at `.scratch/core-msrv-compatible-resolution/Cargo.lock`. Candidate and final copied lock are byte-identical, SHA-256 `8bd35d7d14b123c204f253e89e77c4f655815f141ccdb1ce4e44c4be837d8baa`; both are retained as `evidence/Cargo.lock.candidate` and `evidence/Cargo.lock`. Key selections include Rhai 1.26.1, codegen 3.2.0, cap-std 4.0.3, thin-vec 0.2.19 and js-sys 0.3.91. Cargo accepted it with `--locked`; no lock update was needed.

## Commands and results

The complete run was one invocation of:

```text
python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py --timeout 1055 -- python3 .scratch/optional-msrv-proof/run-proof.py
```

The driver SHA-256 was `7cff307ecd5b7abfdbc656dcc977755e814e7be841b2441da74e26192678db42`. The driver set `CARGO_BUILD_JOBS=2`, debug info off, incremental compilation off, and the absolute stop time to 2026-09-30 17:05:00 UTC. Its first Cargo command compiled the requested targets with `--no-run` (exit 0; `evidence/compile-test-targets.log`).

The assertion control ran the actual `sys_fs` test `test_file_handle_reads_obey_host_cap_and_reject_negative_lengths_without_moving` with `RHAI_FILE_READ_WRONG_EXPECTATION=1`. It ran exactly one test and exited 101 at the expected assertion: actual `"abc"`, deliberately wrong expected `"wrong expectation"` (`evidence/wrong-expectation-control.log`). The same exact test with the environment override removed ran exactly one test and passed (exit 0; `evidence/restored-targeted-test.log`).

Each full target then ran serially (`--test-threads=1 --nocapture`) through the combined-feature build. Every command exited 0 and every harness ran a nonzero number of tests:

| Integration target | Passed |
|---|---:|
| `sys_policy` | 26 |
| `sys_env` | 7 |
| `sys_fs` | 34 |
| `net_connect` | 4 |
| `net_listen` | 7 |
| `net_reads` | 7 |
| `net_writes` | 10 |
| `net_metadata` | 1 |
| **Total** | **96** |

Per-target raw logs are `evidence/fixture-<target>.log`. These use the existing public Engine/package tests, OS temporary files and real TCP peers; no fixture mocks were substituted.

## Resource custody and cleanup

- `run_scoped.py` created private runtime `/var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-cnn6m89c`; source, target artifacts, Rustup toolchain, Cargo registry and temporary files all lived below it. The runner's source supervises its child process group, but this proof did not export driver/child PID identities or independently read back per-process absence.
- Private runtime storage was sampled once per second with `du -sk`. The maximum sample was 802,248 KiB (about 783 MiB), below the 1,572,864 KiB preemptive threshold and 2,097,152 KiB hard ceiling. Samples are retained in `evidence/storage-samples.tsv`; this is sampled usage, not a continuous true peak.
- Descendants of the driver were counted from `ps` PID/PPID ancestry once per second. Maximum observed was 10, below the cap of 16; samples are in `evidence/process-samples.tsv`.
- Post-run cleanup readback: `test -e /var/folders/yk/m4dzf0ss5x9f4j4z3xb2rrv40000gn/T/agent-build-cnn6m89c` returned 1 (absent), independently confirmed by the coordinator. This confirms the scoped runtime is gone; it does not establish per-process absence.
- Execution session `49503` expired before a separately retrievable wrapper terminal exit code was available. The driver's success-only `ACCEPTED` marker was observed and each raw harness outcome was checked, but the wrapper's final status remains unverified.

## Conclusion and limits

The optional `sys` and `net` packages both compiled and their selected real Engine/OS fixtures passed with Rust 1.77.2 on native Darwin arm64. The wrong-expectation control demonstrated that the file-read assertion detects the wrong result, then passed when restored. This closes only the approved native macOS optional-package minimum proof. Linux, Windows, other feature combinations, and the broader release matrix remain unverified by this artifact.
