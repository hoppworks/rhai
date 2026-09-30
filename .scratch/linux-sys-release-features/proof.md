# Native Linux sys release feature gates: incomplete

## Result

Neither authorized attempt proves a Linux sys feature gate. Attempt 1 stopped before
testing because its source archive omitted the `codegen/` workspace member. The
corrected, single follow-up invocation generated a lockfile and compiled the wrong-
expectation control, which exited 101 and showed the intended `abc` versus `wrong
expectation` assertion. The driver then stopped because its panic-line matcher did
not account for Rust 1.97's test-thread ID inserted between the quoted test name and
`panicked`. No feature matrix or restored targeted test ran. This is a verifier
infrastructure error; it is not a product-test failure or feature acceptance.

No production files were changed. No release acceptance claim is made. The prior
setup failure and cause history are preserved below and in `evidence/attempt1-*`.

## Follow-up source and execution

- Selected production source: `e1db9baafaaf30d94085f0cc6f661f363399f193`.
- Source archive SHA256:
  `c934633c7889e4a427a87d557bbc578146e4db641c4fde2c93ff3fd4f047aa47`.
- One remote invocation ran on workhorse, Linux x86_64, kernel
  `7.2.4-ogc3.1.fc44.x86_64`.
- Rust: `1.97.1 (8bab26f4f 2026-07-14)`; Cargo:
  `1.97.1 (c980f4866 2026-06-30)`.
- Absolute deadline: 2026-09-30 18:05:14 UTC; bounded invocation timeout was 752s.
- Existing `/root/.rustup` was used read-only. Private Cargo home, build target, and
  runtime were under `/tmp/agent-build-neth2npq`.
- Cargo generated `Cargo.lock` successfully (SHA256
  `4aa2e32287d33184c12e98c7a86a17574dbf3a2361c968c76e9611bfd4396cc3`).
- The wrong-expectation control exited 101 and captured `left: "abc"` and
  `right: "wrong expectation"`. Rust's output includes the thread id, e.g.
  `thread 'test_name' (2763223) panicked at ...`; the driver only accepted the
  substring `thread 'test_name' panicked` and therefore stopped on its own check.
- Control status file SHA256:
  `39b8dc3fc8b44765c8e6f1adee04c5b465e555ab791cc42d0d9e810d5b64297c`.
- Driver, runner, and outer wrapper statuses were all 1 due to that verifier
  exception. The runtime cleanup status was 0; sampled storage peak was 269192 KiB
  and six owned descendants were observed. These are sampled maxima, not exhaustive
  process or peak-use guarantees.
- Independent readback confirmed the exact launcher PID/start identity
  (2759568/43555984), all 17 uniquely sampled PID/start identities, and the scoped
  process group were gone; unknown fast PIDs: 0. The private runtime was absent.
- Evidence was copied to `evidence/attempt2/`; file hashes were compared with the
  remote stage before cleanup. The exact owned stage
  `/root/rhai-linux-sys-release-features-task/followup-e1db9baa` was then removed.
  No other remote path was touched.

## Gate inventory

All planned feature tests were not run. The matrix was `sys_env`, `sys_fs`, and
`sys_policy` for each feature set below.

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

The corrected passing control for
`test_file_handle_reads_obey_host_cap_and_reject_negative_lengths_without_moving`
was not run. There is no feature compatibility, fixture behavior, release
readiness, or MSRV 1.77.2 conclusion.

## Previous setup attempt

Attempt 1, retained as commit `fd69fa1b20845f16d6280f03e7109b744ff2b6e3`, used
source archive SHA256
`af104355b6bf2efccaeb9aa0fbb26e64580a9524c8a436af4238429df435bd1e`. The archive
omitted `codegen/Cargo.toml`; `cargo generate-lockfile` failed before tests could
start. Its logs and cleanup readback remain in `evidence/attempt1-*` and
`evidence/cleanup-readback.log`.

## Evidence

- `evidence/attempt2/` contains the raw per-command logs/statuses, generated lock,
  process and storage samples, PID readback, runtime readback, and
  `SHA256SUMS`.
- `evidence/attempt1-*` and `evidence/cleanup-readback.log` preserve the first
  attempt and prior cleanup evidence.
- Corrected source gate commit: `552e957631e299451f7ca83fd5b4506d6a088418`.
- No retry or source correction was launched after this follow-up.
