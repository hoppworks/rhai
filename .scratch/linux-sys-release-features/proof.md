# Native Linux sys release feature gates: incomplete attempt

## Result

This attempt does not prove any Linux sys feature gate. The single authorized remote
scoped invocation stopped before test execution because the private source archive
omitted a Cargo workspace member. No production files were changed and no release
acceptance claim is made.

## Tested source and host

- Intended source revision: `e1db9baafaaf30d94085f0cc6f661f363399f193`.
- Source archive SHA256: `af104355b6bf2efccaeb9aa0fbb26e64580a9524c8a436af4238429df435bd1e`.
- The archive contained `Cargo.toml`, `Cargo.msrv.lock`, `build.rs`, `build.template`,
  `src/`, and `tests/`, but omitted the `codegen/` workspace member.
- Native host: workhorse, Bazzite 44, x86_64; kernel
  `7.2.4-ogc3.1.fc44.x86_64`.
- Rust: `rustc 1.97.1 (8bab26f4f 2026-07-14)`; Cargo
  `1.97.1 (c980f4866 2026-06-30)`.

## Attempt and diagnosis

The command was run once through the copied scoped runner with its 900-second bound:

```sh
python3 /root/rhai-linux-sys-release-features-task/e1db9baa/run_scoped.py \
  --timeout 900 -- bash /root/rhai-linux-sys-release-features-task/e1db9baa/run-native.sh
```

The driver first ran `cargo generate-lockfile` so every feature target could use
the same generated lock with `--locked`. Cargo exited 101 before producing a lock:

```text
failed to load manifest for workspace member `/tmp/agent-build-syldwlya/source/.`
failed to load manifest for dependency `rhai_codegen`
failed to read `/tmp/agent-build-syldwlya/source/codegen/Cargo.toml`
No such file or directory (os error 2)
```

The scoped invocation returned exit 1. The error identifies a packaging omission in
the source archive, not a failed sys assertion. The fixed package cap allows one
remote scoped invocation; no relaunch was made.

## Gate inventory

None of the requested gates ran. The planned matrix comprised `sys_env`, `sys_fs`,
and `sys_policy`, one target at a time, for each feature set below.

| Feature set | Targets | Result |
|---|---|---|
| `testing-environ,sys` | `sys_env`, `sys_fs`, `sys_policy` | Not run |
| `testing-environ,sys,sync` | `sys_env`, `sys_fs`, `sys_policy` | Not run |
| `testing-environ,sys,no_index` | `sys_env`, `sys_fs`, `sys_policy` | Not run |
| `testing-environ,sys,metadata,serde` | `sys_env`, `sys_fs`, `sys_policy` | Not run |
| `testing-environ,sys,only_i32,no_float` | `sys_env`, `sys_fs`, `sys_policy` | Not run |
| `testing-environ,sys,unchecked` | `sys_env`, `sys_fs`, `sys_policy` | Not run |
| `testing-environ,sys,no_index,sync,metadata` | `sys_env`, `sys_fs`, `sys_policy` | Not run |
| `testing-environ,sys,f32_float` | `sys_env`, `sys_fs`, `sys_policy` | Not run |

The wrong-expectation control for
`test_file_handle_reads_obey_host_cap_and_reject_negative_lengths_without_moving`
and its corrected passing run were also not run. No Cargo.lock was generated or
captured because resolution failed first.

## Resource and cleanup record

- Exact stage: `/root/rhai-linux-sys-release-features-task/e1db9baa`.
- Scoped runtime: `/tmp/agent-build-syldwlya`.
- Remote runner PID: `1889620`; scoped supervisor PID: `1889685`.
- Read-back confirmed the runtime, runner PID, and supervisor PID were absent after
  the invocation. The stage was retained until its logs and identity were exported.
- The resource sampler reported zero one-second samples because lock generation
  failed before the first sampling interval. Its zero counters are not peak resource
  measurements; process and storage maxima remain unverified.
- No test fixture child process was launched. No feature behavior was observed.
- Remote stage cleanup and independent absence read-back are recorded in
  `evidence/cleanup-readback.log` after export.

## Retained evidence

- `evidence/attempt1-lockfile-setup-failure.log`: full remote driver log and Cargo
  diagnostic.
- `evidence/attempt1-ssh-output.log`: outer command and exit status.
- `evidence/attempt1-launch-identity.txt`: remote runner PID.
- `evidence/remote-stage-hashes-and-pids.txt`: hashes read back from the stage.
- `evidence/cleanup-readback.log`: exact-stage cleanup and independent absence
  checks.

This proof records only the failed setup attempt and cleanup. It does not establish
feature compatibility, fixture behavior, the file handle control, release readiness,
or MSRV 1.77.2 support.
