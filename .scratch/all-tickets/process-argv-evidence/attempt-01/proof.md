# Ticket 03 X4–X6 argv preservation — Linux partial acceptance

Date: 2026-10-07. This acceptance covers only the named Linux x86_64, Rust/Cargo
1.93.0, `testing-environ,sys` row. It does not close the cross-platform, MSRV,
feature, or Ticket 03 matrix.

## Requirement and observed behavior

`tests/sys_process.rs::run_preserves_argv_boundaries_without_shell_interpolation`
uses the public Rhai `Engine` and public `run` function to start `/bin/sh` with
separate arguments. The child writes its received arguments as NUL-delimited
bytes to a file inside a unique `TempDir`, then writes its PID and exit status to
a second file. The test independently reads those files. It checks spaces,
both quote kinds, literal `$HOME`, `|`, `;`, `&&`, a `$(touch …)` marker payload,
and a trailing empty argument byte-for-byte; it also checks the marker is absent,
the public result is successful with exit code 0 and complete captured streams,
and the direct child is already reaped (`kill(pid, 0)` returns `ESRCH`).

## Exact execution

- Base repository revision: `17a41496ea14f9cb2345ca7abb02da2b5afaec92`.
- Tested integration source SHA-256: `dd121c760ace68c651b8c87e2354683cc075a459fcf32e41c83a86c7b32d11d1`.
- Accepted `Cargo.lock` input SHA-256: `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
- Linux: `7.2.7-ogc1.1.fc44.x86_64`; Rust `1.93.0 (254b59607 2026-01-19)`; Cargo `1.93.0 (083ac5135 2025-12-15)`.
- The installed canonical `tools/run_scoped.py` SHA-256 was `25d42cec15827652d08148f51d7f226aa23bbb58ee96ffd68594548044428c2e`.
- Exact test command: `cargo test --locked --features testing-environ,sys --test sys_process run_preserves_argv_boundaries_without_shell_interpolation -- --exact --nocapture --test-threads=1`.
- One paired run used the canonical scoped runner with a 585-second runner bound and 540 seconds of aggregate Cargo time. Cargo target and private Cargo home were under `AGENT_RUNTIME_DIR`; the absolute central scope was `/home/workhorse/.local/share/agent-builds/rhai/x4-x6-argv-20261007-141000z` (`TMPDIR` at runner invocation). Two Cargo jobs were allowed. The paired sequence used 16 seconds in total.

The RED changed only `expected[0]` in the extracted private runtime copy. It exited
101 at the intended exact-byte assertion with `child received different argv
boundaries or bytes`; no repository source was mutated. The staged tested source
was restored in that same runtime, and GREEN exited 0 with `1 passed; 0 failed`.
Both statuses, raw stdout/stderr and the run manifest are preserved under
`attempt-01/workhorse-output/`. The transferred files were independently
SHA-256-checked against the Workhorse output manifest.

## Inputs and resource closure

`attempt-01/sys_process.patch` hashes to
`1fb09a7a50fd96d99b45931dfe3f944bf84dfd09f4dd582ef4f538dcd1211b9f`; the tested
source copy is `attempt-01/sys_process.rs.tested-source`. The base source archive
SHA-256 was `20e9cd4db03c9a251964497099b0f8e120fd30819171b9e0cedbf6b535b76278`.
The paired command exported its outputs before exit. A fresh readback found the
runner runtime absent, no remaining Cargo/rustc/scoped-runner process, and the
central scope removed after output hash verification. No compiled build remains
available for reuse.

The applicable local and Workhorse Agent Skills checkout was
`14617043b70d1ba2d40b720832cbad294fa8c008`; the global instructions and relevant
campaign/TDD/E2E skill hashes matched across those machines. The project rules
are recorded in the repository `AGENTS.md`. No product implementation, tracked
lockfile, or configuration changed; only the integration test source changed.
