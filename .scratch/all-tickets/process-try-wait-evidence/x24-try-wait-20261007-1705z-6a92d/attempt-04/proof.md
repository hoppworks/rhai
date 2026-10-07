# X24 Workhorse Linux Rust 1.77.2 proof

## Acceptance

Ticket 03 / X24: `tests/sys_process.rs::direct_spawn_try_wait_returns_unit_until_child_exits`.
The exact filtered public-Engine integration test passed on Workhorse Linux x86_64 with
`testing-environ,sys`, Rust/Cargo 1.77.2. This accepts only that named Linux/MSRV/feature
row; other operating systems and feature combinations remain open.

The test launched a real child through Rhai `Engine`, observed it alive while
`Child.try_wait()` returned unit, released it, and observed terminal exit code 0 from
`try_wait()` before calling `wait()`. It then verified the cached `wait()` result and
confirmed the exact child PID was reaped through the OS `ESRCH` probe.

## Frozen inputs

- Source commit: `d3eabc005242129dbb8ad124def0f0ada2aff71d`.
- Filtered source archive: `source.tar.gz`, SHA-256
  `d758387232e08a757798800f2c3fc576fde750decc2e16e9f69511bd155cf76b`; 579 entries,
  1,493,624 compressed bytes. It excludes tracked `.scratch/` evidence; no build or source
  include references `.scratch/`.
- Test source: SHA-256
  `7ddc87f6e4b57d61d077445a81f1c3ef2f2e54cb35ac8c90a7ed328245d14017`.
- Product source `src/packages/sys/process.rs`: SHA-256
  `090094476662417aa94e2ff519cb8038c1d3721e02be6ec166762502bfbff2e2`; it matches
  attempt 03.
- Accepted Cargo lock: SHA-256
  `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- Canonical `run_scoped.py`: SHA-256
  `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`.

Attempt 03's assertion sensitivity control remains applicable because both the exact test
source and product source are unchanged. Its wrong-result mutation failed as expected
(status 101 with the intended direct-post-exit assertion diagnostic), and its restored
GREEN passed. Attempt 04 validates and reuses that recorded result; it does not rerun RED.
See `../attempt-03/remote-output/attempt-03/proof-result.json` and its `SHA256SUMS`.

## Run and readback

Command:

```text
cargo test --locked --features testing-environ,sys --test sys_process direct_spawn_try_wait_returns_unit_until_child_exits -- --exact --nocapture --test-threads=1
```

The run manifest records `rustc 1.77.2 (25ef9e3d8 2024-04-09)` and
`cargo 1.77.2 (e52e36006 2024-03-26)`. The exact test and outer runner both returned
status 0 in 18.967 seconds. Raw output records PID 44409 alive before pending `try_wait`,
the direct terminal `try_wait` result before `wait`, and `reaped_esrch=true`. The
independent readback is in `remote-output/attempt-04/proof-result.json`; all six files
listed in `remote-output/attempt-04/SHA256SUMS` match their local hashes.

Periodic resource samples observed at most 6 owned processes, 962,432 KiB RSS and
749,440 KiB private runtime storage; these are sampled values, not continuous peaks.
The exact limits remained 510 seconds Cargo work, 540 seconds helper, 585 seconds outer
runner, 2 Cargo jobs, 16 owned processes, 1,572,864 KiB preemptive storage, 2,097,152 KiB
storage/RSS hard caps. The admission measured 662,504,214,528 free bytes and
86,863,638,528 available RAM bytes; no active Cargo/Rust compiler process was present.

## Resource closure

The canonical runner removed its private `AGENT_RUNTIME_DIR`. After exporting the output,
the exact session scope `/root/.local/share/agent-builds/rhai/x24-trywait-msrv-20261007-2cd5d0062869`
was removed. `cleanup-precheck.json` shows no process referencing the scope before cleanup;
`cleanup-readback.json` confirms the scope is absent and no session process remains. Workhorse
had 663,809,056,768 free bytes after cleanup. No shared cache, service, toolchain or foreign
resource was changed.

## Independent review

Combined package review: READY, 2026-10-07. Independent review confirmed the
frozen inputs, Rust 1.77.2 run, output hashes, direct `try_wait()` result,
ESRCH readback, applicable attempt-03 sensitivity evidence, and exact-scope
cleanup. No material findings. Acceptance remains limited to the two named
Workhorse Linux rows with `testing-environ,sys`.
