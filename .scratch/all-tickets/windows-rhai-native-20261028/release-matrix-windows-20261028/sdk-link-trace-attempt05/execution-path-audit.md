# Attempt 05 execution-path audit before native dispatch

This targets the two observed preparation failures; it is not execution proof.

| Boundary | Verified source path and expected effect |
|---|---|
| Media to guest source | `Start.ps1` checks nine media hashes, expands the pinned 448-file archive into own `n-1743a389\source`, then copies and hashes `probe.c`, `RunRhaiContract.cmd` and `ClearOwnedWorkReadOnly.ps1`. The public Driver and Runner are copied from the accepted native build under exact hashes. |
| Source to runtime | `MonitorPayloadJob.cs` stages the source files directly under its newly allocated runtime and calls `CreateProcessW` with that runtime as current directory. The Driver sends `/D /C RunRhaiContract.cmd`; the batch's first check requires `%CD% == %AGENT_RUNTIME_DIR%`. |
| Frozen input root | Before any directory change, the batch assigns `PROBE_SOURCE_ROOT=%CD%` and checks absolute `probe.c` and cleanup helper existence. There is no `%~dp0` expansion after the directory change. |
| Private work | The runner creates `runtime\work` and sets `CARGO_HOME`, `CARGO_TARGET_DIR`, `TMP` and `TEMP` below it. The batch changes to that exact directory, checks `%CD%`, and invokes pinned absolute CL/LINK. CL source is `%PROBE_SOURCE_ROOT%\probe.c`; object, executable, response file and logs are under `work`. The SDK library argument is the guest-hashed absolute `kernel32.lib` path. |
| Observable run | A newly linked `work\probe.exe` writes `RHAI_NATIVE_LINK_PROBE_EXECUTED` through `WriteFile` on inherited stdout and exits 0. The observer requires the exact retained `probe-run.log` text and fresh object/executable files. |
| Pre-retirement export | The batch checks the response file's presence and copies only extant, individually size-limited logs, object, executable and response file from work to the runtime root. Missing RSP, failed copy, compile/link/run errors each produce nonzero payload status. |
| Cleanup and custody | The helper is called from frozen `PROBE_SOURCE_ROOT`, not work. Its process exit and both exact output markers are required by the batch. The native runner then retires private work and snapshots the runtime root; the observer independently checks exported files, caps, journal and exact process closure. COM1 export precedes removal of only the owned guest/host scopes. |

The corrected command and hash chain require independent source review before
ISO creation. A successful explicit SDK path probe still does not identify
which SDK Cargo selected in the earlier test build.
