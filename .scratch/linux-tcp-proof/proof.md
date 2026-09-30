# Native Linux TCP acceptance

## Source and environment

- Exact tested source revision: `2e945d9f3547a45e73e0fa8a8913847aec58cf1d`.
- Source archive SHA256: `e02c1a6d92962c177693c232bb4be6c5705a84ebfa07d99985c8c141e476a4be`.
- Native host: `workhorse`, Bazzite 44 x86_64; kernel `7.2.4-ogc3.1.fc44.x86_64`.
- Rust: `rustc 1.97.1 (8bab26f4f 2026-07-14)`; Cargo `1.97.1 (c980f4866 2026-06-30)`.
- Cargo generated a scoped lockfile with SHA256 `4aa2e32287d33184c12e98c7a86a17574dbf3a2361c968c76e9611bfd4396cc3`; the repository revision does not track `Cargo.lock`.
- The configured `run_scoped.py` and required `pyguard.py` were copied only to the fresh owned stage `/root/rhai-linux-tcp-proof-task/2e945d9f/runner/`. Their hashes match configured files: `9edd5bc53260c697174552498f6064e65ab821d28838af2291a0cbb6e510c36d` and `a3739f4947744303e1adf3fb0875ac743944a272e5b95c94b1baba53029d313f`.

## Results

The public `NetPackage` integration targets used Rhai `Engine` scripts and real loopback TCP sockets. Peer fixtures independently read or supplied OS socket bytes. All targets ran one at a time, each with `--jobs 2` and `--test-threads=1`:

| Feature set | `net_connect` | `net_listen` | `net_reads` | `net_writes` | Total |
|---|---:|---:|---:|---:|---:|
| `net` | 4 passed | 7 passed | 7 passed | 10 passed | 28 passed |
| `net,sync` | 4 passed | 8 passed | 8 passed | 10 passed | 30 passed |
| `net,no_index` | 4 passed | 7 passed | 7 passed | 10 passed | 28 passed |

Each of the 12 Cargo test invocations exited 0; each summary reported zero failed and zero ignored tests. The commands used were `cargo test --locked --jobs 2 --features <feature-set> --test <target> -- --test-threads=1 --nocapture`.

For the false-green control, `script_write_blob_preserves_exact_bytes` sent `[0, 255, 65]` through the public script API and the real peer observed those bytes. With the existing `RHAI_NET_WRONG_WRITE_EXPECTATION=1` control, its independent peer assertion expected `[0, 254, 65]` and failed with exit 101 at that assertion (`left: [0, 255, 65]`, `right: [0, 254, 65]`). With the environment override removed, the same test passed with exit 0.

The complete canonical output and exact statuses are retained in [native-linux-tcp.log](native-linux-tcp.log) and [status.tsv](status.tsv). Their SHA256 values are `84eb340904bc2b67ff80d8e3946d8b4b8d66a412000c9230ad6bca00e4e7e832` and `d8a5c9b3ee6df18054a678f120a82d09c35a23f8ff0b0bbcdb87085375d347a6`. The first run passed all 12 matrix targets and produced the expected 101 control failure, but its harness diagnostic matcher expected a one-line test status; Rust printed `FAILED` on a separate line. That retained diagnostic is [attempt1-diagnostic.log](attempt1-diagnostic.log); the corrected run above is canonical.

## Limits and cleanup

During the canonical remote scoped invocation, sampled descendant socket descriptors peaked at 5 (limit 16) and sampled allocated private-runtime storage peaked at 1,279,844,352 bytes (limit 2 GiB). These are sampled maxima, not continuous peak claims. Cargo ran each integration target serially. The remote scoped runner returned 0; independent readback confirmed launcher PID `1441067`, supervisor PID `1441127`, and runtime `/tmp/agent-build-8twb50ak` were absent. Exact stage cleanup is recorded in [cleanup-readback.log](cleanup-readback.log), SHA256 `ec87dfa6be368ee3dc8bd2efbf8d31158b26822d9976db995c87fd7308a4b30b`.

This closes only the native Linux `net`, `net,sync`, and `net,no_index` TCP integration slice. The `net_no_object` target, combined `sys,net`, metadata/serde and other release feature combinations, MSRV checks, and native Windows release proof were not run here. Existing macOS evidence remains separate platform evidence. No production source or tests were changed.
