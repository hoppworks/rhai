# Linux process integer-only and unchecked proof

## Source and scope

The frozen source is `6c451c5c99e751e50023a08912a035a2c8754ff6`. Applying the
reviewed `process-feature.patch` (SHA-256 `5cf5d4533ca3adb99a9313e710b91f184bf5f2ee90ce2e215644fddf71b17693`)
produces `tests/sys_process.rs` with SHA-256
`8ec4d456672338920249446618ce768bc2fa1d29798d571dca1e897db87a076b`.
Production files are unchanged.

The test helper uses `rhai::INT`; integral script durations work without floats.
Fractional deadlines under `no_float` use host defaults. The unchecked row omits
the unavailable Engine setter and its string-expansion criterion. A new public
script test requests 8192 bytes against a host cap of 4096 bytes per stream. It
uses a real child, independently reads its record and confirms reaping before
checking exact retained output and typed errors.

Native invocation 93 completed successfully. Combined independent review accepts
the selected feature compatibility and host-cap criteria.

| Features | Original tests passed | Intended assertion controls failed |
| --- | ---: | ---: |
| `testing-environ,sys` | 11 | 2 |
| `testing-environ,sys,only_i32,no_float` | 11 | 16 |
| `testing-environ,sys,unchecked` | 10 | 15 |
| Total | 32 | 33 |

Every wrong overlay returns to the pinned patched original. Valid normal-row
sensitivity evidence from invocations 89 and 90 is reused; the two new normal-row
controls cover the host cap for stdout and stderr. New feature rows cover the
selected branches described in the combined review. The unchecked Engine lossy
expansion criterion is excluded, not counted as passed.

## Preserved preparation outcomes

Invocation 91 stopped before patching or assertions because the verifier expected
the reverse E0308 type direction. The compiler's actual diagnostic was expected
`i64`, found `i32`; invocation 92 matched it and closed that verifier cause.
Invocation 92 then stopped because the external `patch` program was absent.
No installation was performed. The replacement Python applicator checks exact
baseline and patch hashes, hunk context and counts, and final bytes before writing.
Its pure positive check reproduces the owned Rust file; corrupt source and patch
inputs are rejected. The production source patch remains unchanged.

The original failed-run evidence is in `linux-process-feature-evidence-91/` and
`linux-process-feature-evidence-92/`: proof recipes, diagnostics, command/status
logs, independent inventories and cleanup receipts. Neither failed run proves
patched behavior or patched-source restoration. Both baseline compiler
reproductions in invocation 92 have status 101 and are compatibility diagnostics,
not product assertion controls.

Independent readback verified 62 and 75 exact PID/start identities absent,
respectively, with empty scoped groups and no fixture receipts because no
assertion test had run. The exact 46 and 52 stage files and five subdirectories
per run were retired after exported hash verification and fresh readback.
Runtime, scope and stage absence are recorded. Export took 21.666 and 26.384
seconds. Sampled RSS maxima were 811068 and 834056 KiB, storage 770648 and
825756 KiB, and descendants seven and four. These are periodic samples, not
continuous peaks. Lock and manifests remain unchanged. All consumed attempts,
cause histories and hard limits remain preserved.

## Native invocation 93

All 71 helper commands reached their required outcome: three toolchain/version
commands, two baseline compiler reproductions, one strict patch application and
65 exact integration-test invocations. Each deliberate control failed with status
101 at its intended assertion after an independent child cleanup or denial check.
The correct originals passed with status 0. Original evidence records all 33
overlay hashes and the exact test outcomes.

Original bytes and the full stage identity inventory are in
`linux-process-feature-evidence-93/`. Original stage and launcher bytes are also
preserved in `linux-process-feature-executed-recipes-93/`; they match the remote
inventory hashes and reviewed local files. Tested identity is the frozen commit
plus the exact patch, rather than a claimed patched commit. Final restored test
bytes equal the reviewed patched original. The compatible lock
`2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425` and all
manifests remain unchanged.

Root independent readback confirms 445 exact PID/start identities absent,
42 unique printed fixture PIDs absent, empty scoped groups, and runtime/scope
absence. The exact 251 stage files and five subdirectories were removed after
exported hash verification and fresh process/inventory checks. Cleanup receipts
independently confirm stage/scope absence. Export took 80.216 seconds. Sampled
maxima were RSS 874544 KiB, storage 918968 KiB and six descendants. The conditional
launcher `/proc` exit-poll race diagnostic is retained; all four terminal/readback
statuses are 0, and independent closure checks pass.

## Coverage limits

`no_float` proves fractional host defaults, not fractional per-call script values.
`unchecked` does not prove Engine string-expansion limits. This package does not
close managed groups, `no_index`, Darwin, Windows, performance or full release
acceptance. Existing raw/text record-path reuse prevents unique receipt mapping
for each call. Positive cwd has no PID receipt; denied cwd checks the attempted
record's absence, not every transient process. Deadline behavior has no separate
upper elapsed latency claim. Periodic resource and PID samples do not continuously
capture all short-lived children.

Combined independent acceptance review is recorded in
`linux-process-feature-review.md`. The process ticket and release gate remain open. Applicability to integration requires unchanged production and
exact reviewed patched test bytes.
