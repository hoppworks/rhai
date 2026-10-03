# Linux process-options acceptance evidence

Status: combined independent review accepts the targeted eight-case branch proof across five checked Linux feature rows.

Frozen source `469998db6e23e3ce68f000fa01bf2dc44f709ced`, archive SHA256
`3ab4701771809777afe6555c382da8719ed8b201844ebcabff85a82959199100`, compatible
v3 lock `2ba4b3a0807e32b613ff2e972b893c3fd2e0923fd91803611963f09e93265425`.
Workhorse native Linux x86_64, private Rust/Cargo1.77.2; original version logs,
commands and results are in `linux-process-options-evidence-90`. Exact executed
recipes/contract are in `linux-process-options-outer-evidence-90`; root compared
them byte-for-byte with reviewed local recipes. Runtime and test sources are
unchanged from invocation89; its original positive evidence remains applicable.

## Coverage

Five rows share one bounded invocation90: `testing-environ,sys`, plus `sync`,
`metadata,serde`, `net,sync,metadata,serde`, or `f32_float`. Exact commands use
`cargo test --locked --features <row> --test sys_process <name> -- --exact
--nocapture --test-threads=1`. These prove feature coexistence, not unrelated
network or serialization functionality.

Eight real public Engine/OS cases pass after byte restoration in every row,
40GREEN0 in total. Sixteen selected branch controls per row produce80 intended
RED101, with exact failing-test results, intended assertion diagnostics and
independent child reap/absence checks preceding intentional failures:

| Case | Branch controls |
|---|---|
| Raw/text exact capture and nonzero exit as result data | Raw/text each under exit0 and exit7, wrong output expectation |
| Cap+1 primary OutputLimit and retained prefix | stdout and stderr wrong retained prefixes |
| Zero cap | Silent empty success, stdout first byte, stderr first byte |
| Ordinary deadline partial output | Raw and text wrong output markers after timed-child reap |
| Unit timeout override | Wrong timed_out expectation after independent readiness/reap |
| Unit stdin EOF | Wrong expected EOF bytes after independent record/reap |
| Capability-held cwd and denied symlink escape | Wrong cwd output; wrong denial expectation after attempted-record absence |
| Lossy UTF-8 string-limit expansion | Wrong retained final byte after independent record/reap |

Private-only assertion-order and expectation overlays are recorded incrementally,
never change fixture output or production source, and are restored byte-for-byte.
All original positives pass exactly one test/zero failures/zero ignored. Root
compared current source test SHA256 `379db748d4b84a60538d172059df1feafaa62b337eaf49c1178d3e6467d40c74`
with original/restored proof, and matched manifests and lock before/after.
No managed-group, resource-census or overhead suite was selected.

## Closure and resources

Native, runner and outer status0. Fresh root independent readback proves729
exact PID/start identities absent,95 unique printed control-fixture PIDs absent,
scoped groups empty and private runtime/central scope absent. This is not a
complete census of every short-lived positive fixture. Root hash-verified exported
original artifacts before removing401 exact owned stage files and six directories.
No retained build/cache/stage. Receipts are `linux-process-options-root-readback-90.json`,
`linux-process-options-owned-stage-files-90.json` and `linux-process-options-stage-cleanup-90.json`.

Export137.482seconds; periodic sampled maxima987612KiB RSS,1117404KiB storage,
seven descendants. Samples are not continuous peaks. Bounds600outer/585scoped/
540helper seconds including30export reserve, jobs2/desc16/2GiB policies and
1572864KiB storage preemption remain unchanged. Conditional /proc stat exit-race
warning is preserved in original outer.log; final custody/cleanup statuses0.

## Limits and remaining work

Raw/text ordinary capture reuse a record path; records alone do not establish
unique second-call PID identity. Cwd positive /bin/pwd has no PID receipt; denial
proves no attempted fixture record, not absence of every transient process.
Deadline tests assert configured timeout/partial-output behavior without a
per-call elapsed upper bound. No no_float/unchecked/no_index, managed-groups,
performance, Windows/Darwin or final-release acceptance claim follows.
Invocation89 two accepted sensitivity-backed cases remain unchanged.
