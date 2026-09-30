# Native Linux sys release feature gates

## Result

The third, explicitly authorized attempt passed the native Linux sys-only matrix:
eight feature profiles × `sys_env`, `sys_fs`, and `sys_policy`, with all 24 target
commands exiting 0. Their logs report 500 passing fixture tests. The wrong-value
control exited 101 on the exact file-read assertion (`abc` versus `wrong
expectation`), and the restored targeted assertion passed (exit 0). This closes the
approved Linux sys-only verification slice for the selected source revision. It does
not establish combined sys/net coverage, MSRV 1.77.2, Windows support, or overall
release readiness.

## Source and native run

- Selected production source: `e1db9baafaaf30d94085f0cc6f661f363399f193`;
  production files were unchanged.
- Complete source archive SHA256:
  `c934633c7889e4a427a87d557bbc578146e4db641c4fde2c93ff3fd4f047aa47`.
- Frozen follow-up driver/launcher source commit:
  `3386a82f8b6924b98b570046cb583eadd286f94a`.
- One native Linux x86_64 invocation on workhorse began at 2026-09-30 18:48:55 UTC
  with a 600-second cap and absolute cutoff 19:02:48 UTC. It exited at 18:49:50 UTC.
- Rust: `1.97.1 (8bab26f4f 2026-07-14)`; Cargo:
  `1.97.1 (c980f4866 2026-06-30)`.
- Existing `/root/.rustup` was used read-only. Generated and final exported
  `Cargo.lock` both have SHA256
  `4aa2e32287d33184c12e98c7a86a17574dbf3a2361c968c76e9611bfd4396cc3`; every test
  used `--locked`.
- All eight rows passed: `testing-environ,sys`; `testing-environ,sys,sync`;
  `testing-environ,sys,no_index`; `testing-environ,sys,metadata,serde`;
  `testing-environ,sys,only_i32,no_float`; `testing-environ,sys,unchecked`;
  `testing-environ,sys,no_index,sync,metadata`; and `testing-environ,sys,f32_float`.
- Target test counts by profile (`sys_env`, `sys_fs`, `sys_policy`) were 7/35/23,
  7/35/24, 7/24/23, 7/35/24, 7/35/23, 7/33/23, 7/24/25, and 7/35/23 respectively.
  All corresponding command statuses are 0.
- Wrong-value log confirms one exact named test panicked with thread ID 3343063,
  `left: "abc"`, `right: "wrong expectation"`, and `test result: FAILED. 0
  passed; 1 failed`. Its expected status is 101. The restored targeted command status
  is 0.
- Outer, scoped runner, PID cleanup, and runtime cleanup statuses are all 0. The
  wrapper observed sampled private-storage maximum 958832 KiB and sampled maximum
  six owned descendants. These one-second samples do not claim continuous process
  or true peak-resource measurement.

## Attempts and cause history

Attempt 1 was setup-incomplete: archive SHA256
`af104355b6bf2efccaeb9aa0fbb26e64580a9524c8a436af4238429df435bd1e` omitted
`codegen/Cargo.toml`, so lock generation failed before tests. Its immutable record is
commit `fd69fa1b20845f16d6280f03e7109b744ff2b6e3` and the earlier section of
`evidence/attempt1-*`.

Attempt 2 had the complete workspace archive and reached the wrong-value control,
which produced the intended actual-byte assertion and status 101. Its driver
expected an outdated panic-line layout without Rust's optional thread-ID token and
stopped before the matrix. This verifier infrastructure failure is preserved in
commit `a09d84b26a9f2540da3150984fca1f1397a64f9b` and
`evidence/attempt2/`; it was not a product-test failure. Attempt 3 made only the
approved matcher correction plus new fixed deadline/cap and unique stage path.
There was no automatic rerun.

## Custody and evidence

- The exact attempt-3 stage was
  `/root/rhai-linux-sys-release-features-task/followup-e1db9baa-attempt3`; the
  private runtime was `/tmp/agent-build-sdku18v2`.
- The wrapper recorded launcher PID 3339583/start ticks 43893235 and scoped runner
  PID 3339651/start ticks 43893241. Its exact PID/start-time and process-group
  readback passed after runner exit; private runtime cleanup status was 0.
- Root independently read 57 unique recorded PID/start identities: unknown identities
  0, matching processes alive 0; process groups 3339583 and 3339653 were empty and
  the private runtime was absent. After that readback and export-hash comparison,
  only the exact attempt-3 stage was removed; a second check confirmed the stage
  and runtime paths absent.
- Raw logs, 24 fixture statuses, both control statuses, generated/final lockfiles,
  raw process/storage observations, terminal statuses and readbacks are preserved
  in `evidence/attempt3/`. All 71 remote evidence-file SHA256 values matched the
  local export. Manifest SHA256:
  `2d5a8485dfa47b92ae38625b1cf71c0c20f99ad006f8cc6c47fb77036dd5c045`.
- The owned worktree remains preserved and clean; no unrelated remote path was
  removed.

No production change, push, merge, or public upstream write is part of this proof.
