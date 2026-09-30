# POSIX process lifecycle prototype

This is a bounded native macOS prototype, not the Rhai process implementation. It tests only the OS/process/I/O seam required before production work.

## Observed

- Rust std `CommandExt::process_group(0)` creates an owned Unix process group. The fixture records `getpgrp()` as its first user-code record; it equals the child PID on every run. This avoids a parent-side `setpgid` race and does not require a post-spawn setup window.
- With a 2 MiB stdin payload, separate nonblocking writer and stdout/stderr reader workers finish without deadlock and capture the exact independent payload on both output streams.
- An active child with a full, unread stdin pipe can be killed by its negative-PGID group ID. A descendant deliberately placed in its own process group continues to hold inherited stdout/stderr open; a cancellation token lets all three workers join promptly despite the held pipes. The harness then kills that exact recorded PID and waits for it to disappear.
- The same escaped pipe-holder remains after the managed direct child exits. Explicit cancellation ends collection workers without waiting for EOF; exact-PID cleanup follows. The independent `/bin/sleep` sentinel survives group cancellation and is explicitly reaped by the harness.
- `Child::wait` reports the direct child's signal status after active cancellation; `try_wait` observes/reaps the direct child that exits while its escaped descendant remains.
- A deliberately wrong expected record fails, and the original expected record passes.

## Run and evidence

Run on native macOS ARM64, Darwin 27.0.0, Rust 1.93.0, Cargo 1.93.0. The command copied the complete prototype source into the private `AGENT_RUNTIME_DIR`, set `CARGO_HOME` and `CARGO_TARGET_DIR` there, built, ran the passing case, then ran `--wrong-assertion` and required its nonzero exit. The required scoped runner was invoked with Python because its executable bit is not set. The exact reproducible invocation is:

```sh
python3 /Users/hoppworks/projects/agent-skills/tools/run_scoped.py -- sh /Users/hoppworks/projects/rhai-process-prototype/.scratch/process-prototype/run-scoped.sh
```

Detailed successful and false-green output is in `evidence/native-macos.log` and `evidence/wrong-assertion.log`. The source has no Cargo dependencies. Build artifacts and caches were removed with the scoped runtime.

## Rust MSRV assessment and limits

The production Rhai manifest declares Rust 1.66; the requested release gate under discussion is Rust 1.77.2. `CommandExt::process_group` is documented stable since 1.64, and `AsRawFd` since 1.63, so the demonstrated standard-library process-group mechanism fits 1.77.2 by API stabilization. The prototype was compiled only with 1.93.0; an exact 1.77.2 compile was not performed because that toolchain is not installed and installing toolchains would alter the agent home. The prototype uses Rust 2021-compatible `extern` declarations, standard `Read`/`Write` and threads, and no crates.

The FFI constants and `fcntl`/`kill` calls here are macOS-specific scaffolding. This run proves macOS ARM64 only. It does not establish Linux or other Unix behavior, Windows job semantics, existing host process-group behavior, partial setup failure, process-group escape prevention (escape is explicitly possible), deadline/output-limit policy, backpressure benchmarks, bounded retained output, or full Rhai API behavior. Unix process groups do not contain descendants that deliberately leave the group. Production should keep direct-child and managed-group modes distinct, request group membership as part of spawn, and cancel I/O workers independently of EOF. A private OS adapter will need platform bindings for nonblocking setup and group signaling; this prototype did not add dependencies, so dependency selection and MSRV review remain open for implementation.
